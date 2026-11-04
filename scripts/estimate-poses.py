#!/usr/bin/env python3
"""Estimate camera poses locally with CPU PyCOLMAP; retain logs and a report.

Requires pycolmap==4.2.1. Outputs a COLMAP dataset with undistorted images.
No supplied camera extrinsics are read. See docs/COLMAP.md.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import sys
import time
import traceback


class CancellationRequested(KeyboardInterrupt):
    def __init__(self, signum):
        self.signum = signum
        super().__init__(f"Received {signal.Signals(signum).name}")


@contextmanager
def cancellation_signals():
    """Turn termination into an exception so the job report is finalized."""
    signals = (signal.SIGINT, signal.SIGTERM)
    previous = {signum: signal.getsignal(signum) for signum in signals}

    def cancel(signum, _frame):
        # A second signal must not interrupt report/log cleanup.
        for pending in signals:
            signal.signal(pending, signal.SIG_IGN)
        raise CancellationRequested(signum)

    try:
        for signum in signals:
            signal.signal(signum, cancel)
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def cancelled(error):
    return isinstance(error, (KeyboardInterrupt, InterruptedError))


@contextmanager
def native_log(path):
    """Capture native COLMAP stderr as well as Python output."""
    sys.stdout.flush()
    sys.stderr.flush()
    stdout, stderr = os.dup(1), os.dup(2)
    with path.open("w") as stream:
        try:
            os.dup2(stream.fileno(), 1)
            os.dup2(stream.fileno(), 2)
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(stdout, 1)
            os.dup2(stderr, 2)
            os.close(stdout)
            os.close(stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path,
                        help="New directory; existing directories are never overwritten")
    parser.add_argument("--camera-model", default="SIMPLE_RADIAL")
    parser.add_argument("--camera-params", default="",
                        help="Optional calibrated parameters in COLMAP model order")
    parser.add_argument("--single-camera", action="store_true",
                        help="Use only when all images share a camera and intrinsics")
    parser.add_argument("--fix-intrinsics", action="store_true",
                        help="Keep provided calibrated intrinsics fixed during pose estimation")
    parser.add_argument("--max-image-size", type=int, default=1280)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--provenance", type=Path,
                        help="Source provenance.json to retain for the reconstruction adapter")
    args = parser.parse_args()
    if args.threads < 1 or args.max_image_size < 64:
        parser.error("--threads must be positive and --max-image-size at least 64")
    if args.fix_intrinsics and not args.camera_params:
        parser.error("--fix-intrinsics requires calibrated --camera-params")
    images, output = args.images.resolve(), args.output.resolve()
    if not images.is_dir():
        parser.error(f"Image directory does not exist: {images}")
    names = sorted(str(p.relative_to(images)) for p in images.rglob("*")
                   if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff"})
    if len(names) < 3:
        parser.error("At least three supported images are required")
    if output.exists():
        parser.error(f"Output already exists: {output}; choose a fresh directory")
    try:
        import pycolmap
    except ImportError:
        parser.error("Install pycolmap==4.2.1 in a local environment; see docs/COLMAP.md")
    source_provenance = None
    if args.provenance:
        try:
            source_provenance = json.loads(args.provenance.read_text())
            if not isinstance(source_provenance, dict):
                raise ValueError("Expected a JSON object")
            if not isinstance(source_provenance.get("notes", ""), str):
                raise ValueError("notes must be a string")
        except (OSError, ValueError) as error:
            parser.error(f"Invalid provenance: {error}")

    output.mkdir(parents=True)
    report = {
        "schemaVersion": 1, "status": "RUNNING",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pycolmapVersion": pycolmap.__version__, "architecture": platform.machine(),
        "device": "cpu", "hasCuda": pycolmap.has_cuda,
        "input": str(images), "inputImages": names,
        "cameraModel": args.camera_model, "cameraParams": args.camera_params,
        "singleCamera": args.single_camera, "maxImageSize": args.max_image_size,
        "fixedIntrinsics": args.fix_intrinsics,
        "threads": args.threads, "stages": [],
        "poses": "Estimated from images by this run; no provided extrinsics read",
    }
    started = time.monotonic()
    status = 0
    report_path = output / "report.json"

    def stage(name, operation):
        record = {"name": name, "status": "RUNNING"}
        report["stages"].append(record)
        stage_started = time.monotonic()
        try:
            result = operation()
            record["status"] = "PASS"
            return result
        except BaseException as error:
            record.update(status="CANCELLED" if cancelled(error) else "FAIL", error=str(error))
            raise
        finally:
            record["elapsedSeconds"] = time.monotonic() - stage_started

    print(f"Estimating poses for {len(names)} images on CPU. Log: {output / 'execution.log'}", flush=True)
    with native_log(output / "execution.log"), cancellation_signals():
        try:
            # The first RUNNING report is only written after handlers exist.
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2), flush=True)
            database = output / "database.db"
            sparse = output / "sparse"
            sparse.mkdir()
            reader = pycolmap.ImageReaderOptions({"camera_model": args.camera_model,
                                                  "camera_params": args.camera_params})
            extraction = pycolmap.FeatureExtractionOptions({
                "num_threads": args.threads, "use_gpu": False,
                "max_image_size": args.max_image_size,
            })
            stage("feature-extraction", lambda: pycolmap.extract_features(
                database, images, image_names=names,
                camera_mode=pycolmap.CameraMode.SINGLE if args.single_camera else pycolmap.CameraMode.AUTO,
                reader_options=reader, extraction_options=extraction, device=pycolmap.Device.cpu))
            matching = pycolmap.FeatureMatchingOptions({"num_threads": args.threads, "use_gpu": False})
            stage("exhaustive-matching", lambda: pycolmap.match_exhaustive(
                database, matching_options=matching, device=pycolmap.Device.cpu))
            mapping = pycolmap.IncrementalPipelineOptions({
                "num_threads": args.threads, "ba_use_gpu": False, "random_seed": 0,
            })
            if args.fix_intrinsics:
                mapping.ba_refine_focal_length = False
                mapping.ba_refine_principal_point = False
                mapping.ba_refine_extra_params = False
                mapping.mapper.abs_pose_refine_focal_length = False
                mapping.mapper.abs_pose_refine_extra_params = False
            models = stage("incremental-mapping", lambda: pycolmap.incremental_mapping(
                database, images, sparse, options=mapping))
            if not models:
                raise RuntimeError("COLMAP produced no reconstruction. Inspect execution.log; no poses were exported.")
            model_id, model = max(models.items(), key=lambda item: item[1].num_reg_images())
            registered = sorted(image.name for image in model.images.values() if image.has_pose)
            report.update(models=[{"id": key, "registeredImages": value.num_reg_images(),
                                   "points3D": value.num_points3D()} for key, value in models.items()],
                          selectedModel=model_id, registeredImages=registered,
                          unregisteredImages=sorted(set(names) - set(registered)),
                          registrationCoverage=len(registered) / len(names),
                          fullRegistration="PASS" if len(registered) == len(names) else "FAIL",
                          meanReprojectionErrorPixels=model.compute_mean_reprojection_error())
            stage("undistortion", lambda: pycolmap.undistort_images(
                output / "dataset", sparse / str(model_id), images,
                image_names=registered, output_type="COLMAP", num_threads=args.threads,
                undistort_options=pycolmap.UndistortCameraOptions({"max_image_size": args.max_image_size})))
            # COLMAP camera coordinates are right/down/forward. NeRF transforms
            # use camera-to-world with right/up/back: invert, then flip Y and Z.
            import numpy as np
            dataset = output / "dataset"
            undistorted = pycolmap.Reconstruction(dataset / "sparse")
            frames = []
            for image in sorted(undistorted.images.values(), key=lambda item: item.name):
                camera = undistorted.cameras[image.camera_id]
                if camera.model_name not in {"PINHOLE", "SIMPLE_PINHOLE"}:
                    raise ValueError(f"Unexpected undistorted camera model: {camera.model_name}")
                intrinsic = camera.calibration_matrix()
                matrix = np.eye(4)
                matrix[:3] = image.cam_from_world().inverse().matrix()
                matrix = matrix @ np.diag([1, -1, -1, 1])
                frames.append({"file_path": f"images/{image.name}",
                               "w": camera.width, "h": camera.height,
                               "fl_x": float(intrinsic[0, 0]), "fl_y": float(intrinsic[1, 1]),
                               "cx": float(intrinsic[0, 2]), "cy": float(intrinsic[1, 2]),
                               "transform_matrix": matrix.tolist()})
            undistorted.export_PLY(dataset / "init.ply")
            (dataset / "transforms.json").write_text(json.dumps({
                "camera_model": "OPENCV", "ply_file_path": "init.ply", "frames": frames,
            }, indent=2) + "\n")
            if args.provenance:
                provenance = source_provenance
                provenance["backend"] = f"PyCOLMAP {pycolmap.__version__} CPU SfM"
                provenance["notes"] = "Source acquisition notes: " + provenance.get("notes", "") + " For this output, camera poses were re-estimated locally from input images; no supplied extrinsics used. COLMAP camera-to-world axes converted to OpenGL by negating camera Y/Z."
                (dataset / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
                license_path = args.provenance.parent / "LICENSE"
                if license_path.is_file():
                    shutil.copyfile(license_path, dataset / "LICENSE")
            report.update(status="PASS", datasetPath=str(output / "dataset"))
            if len(registered) != len(names) or len(models) != 1:
                report["warning"] = "Only the largest connected model was exported; inspect registration coverage before training."
        except BaseException as error:
            if cancelled(error):
                signum = getattr(error, "signum", signal.SIGINT)
                report.update(status="CANCELLED", error=str(error),
                              cancellationSignal=signal.Signals(signum).name)
                status = 128 + signum
            else:
                report.update(status="FAIL", error=str(error))
                status = 1
            traceback.print_exc()
        finally:
            # Preserve the final report even if termination is requested again.
            for signum in (signal.SIGINT, signal.SIGTERM):
                signal.signal(signum, signal.SIG_IGN)
            report["elapsedSeconds"] = time.monotonic() - started
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report["peakResidentBytes"] = peak if sys.platform == "darwin" else peak * 1024
            report["finishedAt"] = datetime.now(timezone.utc).isoformat()
            report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['status']}: {report_path}")
    if "registeredImages" in report:
        print(f"Registered {len(report['registeredImages'])}/{len(names)} images in the selected model.")
    if "warning" in report:
        print(f"Warning: {report['warning']}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
