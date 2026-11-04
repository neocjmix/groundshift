#!/usr/bin/env python3
"""Estimate camera poses locally with CPU PyCOLMAP; retain logs and a report.

Requires pycolmap==4.2.1. Outputs a COLMAP dataset with undistorted images.
No supplied camera extrinsics are read. See docs/COLMAP.md.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import sqlite3
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


def database_diagnostics(database):
    """Describe actual feature/match coverage, including disconnected images."""
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        images = dict(connection.execute("SELECT image_id, name FROM images"))
        features = dict(connection.execute("SELECT image_id, rows FROM keypoints"))
        raw_pairs = [row[0] for row in connection.execute("SELECT rows FROM matches WHERE rows > 0")]
        pairs = list(connection.execute("SELECT pair_id, rows FROM two_view_geometries WHERE rows > 0"))
    neighbors = {key: set() for key in images}
    for pair, _ in pairs:
        first, second = divmod(pair, 2147483647)
        if first in neighbors and second in neighbors:
            neighbors[first].add(second)
            neighbors[second].add(first)
    unseen, components = set(images), []
    while unseen:
        todo, component = [unseen.pop()], []
        while todo:
            item = todo.pop()
            component.append(images[item])
            new = neighbors[item] & unseen
            unseen -= new
            todo.extend(new)
        components.append(sorted(component))
    return {"featuresByImage": {images[key]: value for key, value in features.items()},
            "rawMatchedPairs": len(raw_pairs),
            "rawPairMatches": {"min": min(raw_pairs, default=0), "max": max(raw_pairs, default=0),
                               "mean": sum(raw_pairs) / max(len(raw_pairs), 1)},
            "verifiedPairs": len(pairs),
            "verifiedPairInliers": {"min": min((row[1] for row in pairs), default=0),
                                   "max": max((row[1] for row in pairs), default=0),
                                   "mean": sum(row[1] for row in pairs) / max(len(pairs), 1)},
            "matchGraphComponents": sorted(components, key=len, reverse=True)}


def reconstruction_note(camera_params, fixed_intrinsics, frames, points):
    calibration = (
        "Provided lens calibration was supplied through --camera-params and "
        + ("kept fixed during SfM." if fixed_intrinsics else "allowed to refine during SfM.")
        if camera_params else
        "No lens parameters were supplied through --camera-params; intrinsics used image metadata/default initialization and local estimation."
    )
    return (
        f"For this output, {frames} camera poses and {points} sparse points were estimated locally from input images. "
        "No supplied extrinsics, sparse geometry, Gaussian model or checkpoint was used by pose estimation. "
        + calibration
        + " COLMAP camera-to-world axes were converted to OpenGL by negating camera Y/Z; world gravity and metric scale are not measured."
    )


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
    parser.add_argument("--max-features", type=int, default=8192,
                        help="Maximum SIFT features per image")
    parser.add_argument("--matching", choices=("exhaustive", "sequential"), default="exhaustive",
                        help="Sequential uses filename order; choose it only for ordered captures")
    parser.add_argument("--overlap", type=int, default=10,
                        help="Sequential neighboring images, with quadratic neighbors also enabled")
    parser.add_argument("--guided-matching", action="store_true",
                        help="Use verified geometry to find additional feature correspondences")
    parser.add_argument("--affine-features", action="store_true",
                        help="Use slower affine shape estimation and domain-size pooling (DSP-SIFT)")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--provenance", type=Path,
                        help="Source provenance.json to retain for the reconstruction adapter")
    args = parser.parse_args()
    if args.threads < 1 or args.max_image_size < 64 or args.max_features < 128 or args.overlap < 1:
        parser.error("Require positive threads/overlap, image size at least 64 and at least 128 features")
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
        "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "pycolmapVersion": pycolmap.__version__, "architecture": platform.machine(),
        "device": "cpu", "hasCuda": pycolmap.has_cuda,
        "input": str(images), "inputImages": names,
        "registeredImages": [], "unregisteredImages": names,
        "registrationCoverage": 0.0, "fullRegistration": "NOT RUN",
        "cameraModel": args.camera_model, "cameraParams": args.camera_params,
        "singleCamera": args.single_camera, "maxImageSize": args.max_image_size,
        "fixedIntrinsics": args.fix_intrinsics,
        "providedCameraCalibrationUsed": bool(args.camera_params),
        "providedCameraPosesUsed": False, "providedSparseGeometryUsed": False,
        "intrinsicsSource": "Provided calibrated parameters" if args.camera_params else "Estimated from image metadata and local bundle adjustment; no calibration file read",
        "matching": args.matching, "sequentialOverlap": args.overlap if args.matching == "sequential" else None,
        "maxFeatures": args.max_features, "guidedMatching": args.guided_matching,
        "affineFeatures": args.affine_features,
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
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        try:
            result = operation()
            record["status"] = "PASS"
            return result
        except BaseException as error:
            record.update(status="CANCELLED" if cancelled(error) else "FAIL", error=str(error))
            raise
        finally:
            record["elapsedSeconds"] = time.monotonic() - stage_started
            report_path.write_text(json.dumps(report, indent=2) + "\n")

    print(f"Estimating poses for {len(names)} images on CPU. Log: {output / 'execution.log'}", flush=True)
    with native_log(output / "execution.log"), cancellation_signals():
        try:
            # The first RUNNING report is only written after handlers exist.
            report_path.write_text(json.dumps(report, indent=2) + "\n")
            report["inputFileHashes"] = {name: hashlib.sha256((images / name).read_bytes()).hexdigest()
                                        for name in names}
            print(json.dumps(report, indent=2), flush=True)
            database = output / "database.db"
            sparse = output / "sparse"
            sparse.mkdir()
            reader = pycolmap.ImageReaderOptions({"camera_model": args.camera_model,
                                                  "camera_params": args.camera_params})
            extraction = pycolmap.FeatureExtractionOptions({
                "num_threads": args.threads, "use_gpu": False,
                "max_image_size": args.max_image_size,
                "sift": {"max_num_features": args.max_features,
                         "estimate_affine_shape": args.affine_features,
                         "domain_size_pooling": args.affine_features},
            })
            stage("feature-extraction", lambda: pycolmap.extract_features(
                database, images, image_names=names,
                camera_mode=pycolmap.CameraMode.SINGLE if args.single_camera else pycolmap.CameraMode.AUTO,
                reader_options=reader, extraction_options=extraction, device=pycolmap.Device.cpu))
            matching = pycolmap.FeatureMatchingOptions({"num_threads": args.threads, "use_gpu": False,
                                                        "guided_matching": args.guided_matching})
            if args.matching == "sequential":
                pairing = pycolmap.SequentialPairingOptions({
                    "overlap": args.overlap, "quadratic_overlap": True,
                    "loop_detection": False, "num_threads": args.threads,
                })
                stage("sequential-matching", lambda: pycolmap.match_sequential(
                    database, matching_options=matching, pairing_options=pairing, device=pycolmap.Device.cpu))
            else:
                stage("exhaustive-matching", lambda: pycolmap.match_exhaustive(
                    database, matching_options=matching, device=pycolmap.Device.cpu))
            report["matchingDiagnostics"] = database_diagnostics(database)
            mapping = pycolmap.IncrementalPipelineOptions({
                "num_threads": args.threads, "ba_use_gpu": False, "random_seed": 0,
            })
            mapping.mapper.num_threads = args.threads
            if args.fix_intrinsics:
                mapping.ba_refine_focal_length = False
                mapping.ba_refine_principal_point = False
                mapping.ba_refine_extra_params = False
                mapping.mapper.abs_pose_refine_focal_length = False
                mapping.mapper.abs_pose_refine_extra_params = False
            def recover_models():
                result = pycolmap.incremental_mapping(database, images, sparse, options=mapping)
                if not result:
                    report["fullRegistration"] = "FAIL"
                    raise RuntimeError("COLMAP produced no reconstruction. Inspect execution.log; no poses were exported.")
                return result

            models = stage("incremental-mapping", recover_models)
            model_id, model = max(models.items(), key=lambda item: item[1].num_reg_images())
            registered = sorted(image.name for image in model.images.values() if image.has_pose)
            report.update(models=[{"id": key, "registeredImages": value.num_reg_images(),
                                   "points3D": value.num_points3D()} for key, value in models.items()],
                          selectedModel=model_id, registeredImages=registered,
                          unregisteredImages=sorted(set(names) - set(registered)),
                          registrationCoverage=len(registered) / len(names),
                          fullRegistration="PASS" if len(registered) == len(names) else "FAIL",
                          meanReprojectionErrorPixels=model.compute_mean_reprojection_error(),
                          meanTrackLength=model.compute_mean_track_length(),
                          cameras=[{"id": camera.camera_id, "model": camera.model_name,
                                    "width": camera.width, "height": camera.height,
                                    "parameters": camera.params.tolist()}
                                   for camera in model.cameras.values()])
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
            # Sequence metadata describes the source capture, not recovered
            # geometry. Keep omitted frames in it so route consumers can stop at
            # registration gaps rather than inventing a continuous path.
            sequence = images.parent / "sequence.json"
            if sequence.is_file():
                shutil.copyfile(sequence, dataset / "sequence.json")
                report["sourceSequence"] = {"path": str(sequence),
                                            "sha256": hashlib.sha256(sequence.read_bytes()).hexdigest()}
            if args.provenance:
                provenance = source_provenance
                provenance["backend"] = f"PyCOLMAP {pycolmap.__version__} CPU SfM"
                provenance["notes"] = (
                    "Source acquisition notes: " + provenance.get("notes", "") + " "
                    + reconstruction_note(args.camera_params, args.fix_intrinsics,
                                          len(frames), undistorted.num_points3D())
                )
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
