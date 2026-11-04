#!/usr/bin/env python3
"""Build a local world from images or a short video, retaining every stage log.

CPU camera estimation and native Metal training run as local processes. A
successful command validates export, not visual quality or browser rendering.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def coverage_gate(report, minimum):
    if report.get("status") != "PASS":
        raise ValueError("Camera estimation did not finish successfully; inspect poses/report.json")
    inputs, registered = report.get("inputImages", []), report.get("registeredImages", [])
    if not inputs or not registered or len(set(inputs)) != len(inputs) or len(set(registered)) != len(registered):
        raise ValueError("Camera report has invalid image coverage")
    if not set(registered).issubset(inputs):
        raise ValueError("Registered camera names do not match the input images")
    if "selectedModel" not in report or len(registered) < 2:
        raise ValueError("Camera report has no usable selected reconstruction component")
    fraction = len(registered) / len(inputs)
    if fraction < minimum:
        raise ValueError(f"Coverage gate failed: {len(registered)}/{len(inputs)} images ({fraction:.1%}); "
                         f"required {minimum:.1%}. Training was not started.")
    return {"status": "PASS", "registered": len(registered), "input": len(inputs),
            "fraction": fraction, "minimum": minimum,
            "fullRegistration": "PASS" if fraction == 1 else "FAIL",
            "notes": "Coverage is a processing gate, not a geometry or visual-quality guarantee."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Local video, image directory, or dataset containing images/")
    parser.add_argument("output", type=Path, help="New job directory; existing jobs are never overwritten")
    parser.add_argument("--provenance", type=Path)
    parser.add_argument("--sequence", type=Path, help="Optional JSON with chronologically ordered frames[].file")
    parser.add_argument("--colmap-python", type=Path, default=ROOT / "data/tools/colmap-venv/bin/python")
    parser.add_argument("--brush", type=Path, default=ROOT / "data/tools/brush-0.3.0/brush-app-aarch64-apple-darwin/brush_app")
    parser.add_argument("--camera-model", default="SIMPLE_RADIAL")
    parser.add_argument("--camera-params", default="", help="Optional actual lens calibration in the selected COLMAP model order")
    parser.add_argument("--fix-intrinsics", action="store_true", help="Keep the explicitly supplied lens calibration fixed")
    parser.add_argument("--single-camera", action="store_true", help="Share estimated intrinsics; enabled automatically for video")
    parser.add_argument("--matching", choices=("sequential", "exhaustive"), default="exhaustive")
    parser.add_argument("--overlap", type=int, default=12)
    parser.add_argument("--guided-matching", action="store_true")
    parser.add_argument("--max-image-size", type=int, default=1280)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--min-coverage", type=float, default=1.0)
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--duration", type=float, default=15)
    parser.add_argument("--fps", type=float, default=4)
    parser.add_argument("--max-edge", type=int, default=960)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--max-splats", type=int, default=200000)
    parser.add_argument("--title", default="Local reconstruction")
    parser.add_argument("--id", default="local-world")
    parser.add_argument("--publish", type=Path, help="Copy only the successful world to a NEW local directory")
    args = parser.parse_args()
    if not 0 < args.min_coverage <= 1:
        parser.error("--min-coverage must be greater than zero and at most one")
    if args.fix_intrinsics and not args.camera_params:
        parser.error("--fix-intrinsics requires actual --camera-params")
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}")
    if args.publish and args.publish.exists():
        parser.error(f"Publish destination already exists: {args.publish}")
    output.mkdir(parents=True)
    report_path = output / "pipeline.json"
    report = {"status": "RUNNING", "startedAt": datetime.now(timezone.utc).isoformat(),
              "source": str(source), "stages": [], "browserRendering": "NOT RUN",
              "visualQuality": "NOT RUN"}
    process, cancelled = None, False
    started = time.monotonic()

    def stop(signum, _frame):
        nonlocal cancelled
        cancelled = True
        # Each adapter owns and terminates its native children. Signal the
        # adapter so it can preserve its own failure/cancellation report.
        if process is not None and process.poll() is None:
            process.send_signal(signum)

    def run_stage(name, command):
        nonlocal process
        if cancelled:
            raise RuntimeError("Pipeline cancelled before next stage")
        entry = {"name": name, "status": "RUNNING", "command": [str(arg) for arg in command],
                 "log": str(output / f"{name}.log")}
        report["stages"].append(entry)
        write_json(report_path, report)
        tick = time.monotonic()
        print(f"{name}: {entry['log']}", flush=True)
        with Path(entry["log"]).open("w") as log:
            process = subprocess.Popen(entry["command"], stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            if cancelled:
                process.send_signal(signal.SIGTERM)
            code = process.wait()
        entry.update(exitCode=code, elapsedSeconds=time.monotonic() - tick,
                     status="CANCELLED" if cancelled else "PASS" if code == 0 else "FAIL")
        write_json(report_path, report)
        if cancelled or code != 0:
            raise RuntimeError(f"{name} {entry['status']}; inspect {entry['log']}")

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        write_json(report_path, report)
        if not source.exists():
            raise FileNotFoundError(f"Source does not exist: {source}")
        is_video = source.is_file()
        sequence_path = args.sequence
        if is_video:
            command = [sys.executable, ROOT / "scripts/prepare-video.py", source, output / "frames",
                       "--start", str(args.start), "--duration", str(args.duration), "--fps", str(args.fps),
                       "--max-edge", str(args.max_edge), "--max-frames", str(args.max_frames)]
            if args.provenance:
                command.extend(["--provenance", args.provenance.resolve()])
            run_stage("prepare-video", command)
            images, provenance = output / "frames/images", output / "frames/provenance.json"
            sequence_path = output / "frames/sequence.json"
        else:
            images = source / "images" if (source / "images").is_dir() else source
            provenance = args.provenance or images.parent / "provenance.json"
            if not provenance.is_file():
                raise ValueError("Images require --provenance or a sibling provenance.json; source/license are never guessed")
            if sequence_path is None:
                sequence_path = next((path for path in (images.parent / "sequence.json", images.parent / "selected-frames.json")
                                      if path.is_file()), None)
        if sequence_path:
            sequence = json.loads(sequence_path.read_text())
            sequence_path = output / "sequence.json"
            write_json(sequence_path, sequence)
        command = [args.colmap_python.absolute(), ROOT / "scripts/estimate-poses.py", "--images", images,
                   "--output", output / "poses", "--provenance", provenance.resolve(),
                   "--camera-model", args.camera_model, "--matching", args.matching,
                   "--overlap", str(args.overlap), "--max-image-size", str(args.max_image_size),
                   "--threads", str(args.threads)]
        if is_video or args.single_camera:
            command.append("--single-camera")
        if args.camera_params:
            command.extend(["--camera-params", args.camera_params])
        if args.fix_intrinsics:
            command.append("--fix-intrinsics")
        if args.guided_matching:
            command.append("--guided-matching")
        run_stage("estimate-poses", command)
        poses = json.loads((output / "poses/report.json").read_text())
        report["coverage"] = coverage_gate(poses, args.min_coverage)
        write_json(report_path, report)
        command = [sys.executable, ROOT / "scripts/reconstruct.py", output / "poses/dataset", output / "training",
                   "--brush", args.brush.resolve(), "--steps", str(args.steps), "--resolution", str(args.resolution),
                   "--max-splats", str(args.max_splats), "--title", args.title, "--id", args.id]
        if sequence_path:
            command.extend(["--sequence", sequence_path, "--component-id", f"colmap-{poses['selectedModel']}"])
        run_stage("reconstruct", command)
        training = json.loads((output / "training/job.json").read_text())
        if training.get("status") != "PASS":
            raise RuntimeError("Training report did not pass")
        world = output / "training/world"
        report.update(status="PASS", manifestPath=str(world / "world.json"),
                      artifact=training["artifact"], trainingReport=str(output / "training/job.json"))
        if cancelled:
            raise RuntimeError("Pipeline cancelled before publication; completed local artifacts preserved")
        if args.publish:
            shutil.copytree(world, args.publish.resolve())
            report["publishedManifestPath"] = str(args.publish.resolve() / "world.json")
    except Exception as error:
        report.update(status="CANCELLED" if cancelled else "FAIL", error=str(error))
        if report["stages"] and report["stages"][-1]["status"] == "RUNNING":
            report["stages"][-1]["status"] = report["status"]
        print(str(error), file=sys.stderr)
    finally:
        if cancelled:
            report.update(status="CANCELLED", error="Pipeline cancelled; logs and any completed files are preserved")
        report.update(elapsedSeconds=time.monotonic() - started,
                      finishedAt=datetime.now(timezone.utc).isoformat())
        write_json(report_path, report)
        print(f"{report['status']}: {report_path}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
