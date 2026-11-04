#!/usr/bin/env python3
"""Train a local posed pinhole image dataset with Brush and export a world artifact.

The process owns training and exports. This adapter owns validation, logs,
measurements and the portable manifest, with no GPU implementation abstraction.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRUSH = ROOT / "data/tools/brush-0.3.0/brush-app-aarch64-apple-darwin/brush_app"


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def unit(vector):
    length = math.sqrt(sum(x*x for x in vector))
    if length < 1e-8:
        raise ValueError("Camera directions are degenerate; an explicit orientation is needed")
    return [x / length for x in vector]


def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]


def align_up(up):
    """Quaternion rotating the measured average camera-up direction onto +Y."""
    direction = unit(up)
    if direction[1] < -1 + 1e-8:
        return [1, 0, 0, 0]
    return unit([*cross(direction, [0, 1, 0]), 1 + direction[1]])


def rotate(vector, quaternion):
    xyz, w = quaternion[:3], quaternion[3]
    t = [2*x for x in cross(xyz, vector)]
    c = cross(xyz, t)
    return [vector[i] + w*t[i] + c[i] for i in range(3)]


def validate_provenance(provenance):
    if provenance.get("sourceType") not in ("images", "video", "sample"):
        raise ValueError("Dataset provenance sourceType must be images, video or sample")
    for key in ("sourceUrl", "license", "licenseUrl", "attribution"):
        if not isinstance(provenance.get(key), str) or not provenance[key].strip():
            raise ValueError(f"Dataset provenance requires {key}")
    for key in ("sourceUrl", "licenseUrl"):
        value = provenance[key]
        try:
            parsed = urlsplit(value)
            valid = parsed.scheme in ("http", "https", "file")
            valid = valid and parsed.username is None and parsed.password is None
            valid = valid and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)
            valid = valid and "\\" not in value
            valid = valid and (parsed.path.startswith("/") if parsed.scheme == "file" else bool(parsed.hostname))
            _ = parsed.port  # Reject malformed port syntax before launching the trainer.
        except ValueError:
            valid = False
        if not valid:
            raise ValueError(f"Dataset provenance {key} requires an absolute HTTP(S) or file URL without credentials")
    if "notes" in provenance and not isinstance(provenance["notes"], str):
        raise ValueError("Dataset provenance notes must be a string when provided")


def validate_dataset(dataset):
    dataset = dataset.resolve()
    transforms = json.loads((dataset / "transforms.json").read_text())
    frames = transforms.get("frames", [])
    if len(frames) < 2:
        raise ValueError("At least two supplied camera poses are required")
    if transforms.get("camera_model", "OPENCV") not in ("OPENCV", "PINHOLE"):
        raise ValueError("Undistort input images to a pinhole model before Brush 0.3 training")
    for index, frame in enumerate(frames):
        for key in ("k1", "k2", "k3", "k4", "p1", "p2"):
            if abs(frame.get(key, transforms.get(key, 0))) > 1e-12:
                raise ValueError("Brush 0.3 ignores distortion; undistort the dataset first")
        matrix = frame.get("transform_matrix")
        if not isinstance(matrix, list) or len(matrix) != 4 or any(len(row) != 4 for row in matrix):
            raise ValueError(f"Invalid camera matrix for frame {index}")
        if not all(isinstance(x, (int, float)) and math.isfinite(x) for row in matrix for x in row):
            raise ValueError(f"Nonfinite camera pose for frame {index}")
        if any(abs(matrix[3][i] - [0, 0, 0, 1][i]) > 1e-5 for i in range(4)):
            raise ValueError(f"Invalid homogeneous camera matrix for frame {index}")
        for i in range(3):
            for j in range(3):
                product = sum(matrix[k][i] * matrix[k][j] for k in range(3))
                if abs(product - int(i == j)) > 1e-3:
                    raise ValueError(f"Camera matrix is not rigid for frame {index}")
        columns = [[matrix[i][j] for i in range(3)] for j in range(3)]
        determinant = sum(a*b for a, b in zip(cross(columns[0], columns[1]), columns[2]))
        if abs(determinant - 1) > 1e-3:
            raise ValueError(f"Camera orientation is not right-handed for frame {index}")
        for key in ("w", "h", "fl_x", "fl_y"):
            value = frame.get(key, transforms.get(key))
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Positive finite {key} intrinsics required for frame {index}")
        for key in ("cx", "cy"):
            value = frame.get(key, transforms.get(key, 0))
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Finite {key} intrinsics required for frame {index}")
        relative = Path(frame["file_path"])
        image = (dataset / relative).resolve()
        if relative.is_absolute() or not image.is_relative_to(dataset) or not image.is_file():
            raise ValueError(f"Missing image or image outside dataset: {relative}")
    provenance = json.loads((dataset / "provenance.json").read_text())
    validate_provenance(provenance)
    return transforms, provenance


def ply_info(path):
    with path.open("rb") as stream:
        header = bytearray()
        while len(header) < 65536:
            line = stream.readline()
            header.extend(line)
            if line.strip() == b"end_header":
                break
            if not line:
                raise ValueError("Truncated PLY header")
        else:
            raise ValueError("PLY header too large")
    text = header.decode("ascii")
    count = re.search(r"^element vertex (\d+)$", text, re.MULTILINE)
    required = ("x", "y", "z", "f_dc_0", "opacity", "scale_0", "rot_0")
    if not text.startswith("ply\nformat binary_little_endian 1.0\n") or not count or int(count[1]) == 0:
        raise ValueError("Brush did not export a nonempty binary PLY")
    if any(f"property float {field}\n" not in text for field in required):
        raise ValueError("PLY does not contain Gaussian Splatting attributes")
    properties = len(re.findall(r"^property float ", text, re.MULTILINE))
    if path.stat().st_size != len(header) + int(count[1]) * properties * 4:
        raise ValueError("Exported PLY payload size disagrees with its vertex count")
    return {"splats": int(count[1]), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def artifact(transforms, provenance, title, world_id):
    for key, value in (("title", title), ("id", world_id)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"World {key} must not be blank")
    validate_provenance(provenance)
    frames = transforms["frames"]
    up = [sum(f["transform_matrix"][i][1] for f in frames) for i in range(3)]
    quaternion = align_up(up)
    first = frames[0]["transform_matrix"]
    position = rotate([first[i][3] for i in range(3)], quaternion)
    forward = rotate([-first[i][2] for i in range(3)], quaternion)
    camera_up = rotate([first[i][1] for i in range(3)], quaternion)
    # Orbit focus distance is a viewing choice derived from the camera baseline;
    # it is not a recovered surface or a claim that the origin is safe to walk.
    distances = [math.dist([first[i][3] for i in range(3)],
                           [f["transform_matrix"][i][3] for i in range(3)]) for f in frames[1:]]
    distance = statistics.median(x for x in distances if x > 1e-6)
    target = [position[i] + forward[i] * distance for i in range(3)]
    h = frames[0].get("h", transforms.get("h"))
    fy = frames[0].get("fl_y", transforms.get("fl_y"))
    if not h or not fy or h <= 0 or fy <= 0:
        raise ValueError("Exporter requires positive h and fl_y intrinsics")
    fov = math.degrees(2 * math.atan(h / (2 * fy)))
    cameras = []
    for frame in frames:
        matrix = frame["transform_matrix"]
        columns = [rotate([matrix[i][j] for i in range(3)], quaternion) for j in range(4)]
        cameras.append({"image": frame["file_path"], "cameraToWorld":
                        [[columns[j][i] for j in range(4)] for i in range(3)] + [[0, 0, 0, 1]]})
    notes = provenance.get("notes", "") + " Asset coordinates are unchanged Brush output. World orientation aligns mean supplied camera up with +Y; gravity and metric scale are not measured. Spawn is the first supplied camera; orbit focus uses median camera baseline."
    manifest = {
        "schemaVersion": 1, "id": world_id, "title": title,
        "assets": [{"kind": "gaussian-splat", "format": "ply", "path": "scene.ply"}],
        "coordinates": {"handedness": "right", "upAxis": "y", "unit": "arbitrary",
                        "assetToWorld": {"position": [0, 0, 0], "quaternion": quaternion, "scale": 1}},
        "navigation": {"mode": "orbit", "camera": {"position": position, "target": target,
                       "up": camera_up, "fov": fov, "near": max(distance/1000, .001),
                       "far": max(distance*100, 100)}, "camerasPath": "cameras.json"},
        "provenance": {**{key: provenance[key] for key in
                          ("sourceType", "sourceUrl", "license", "licenseUrl", "attribution")},
                       "backend": "Brush 0.3.0 / native WebGPU (Metal on macOS)", "notes": notes},
    }
    return manifest, {"schemaVersion": 1, "cameraConvention": "OpenGL: +X right, +Y up, -Z forward",
                      "worldConvention": "right-handed Y-up, arbitrary units", "frames": cameras}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path, help="New job directory; never overwrites a prior run")
    parser.add_argument("--brush", type=Path, default=DEFAULT_BRUSH)
    parser.add_argument("--steps", type=int, default=1500)
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--max-splats", type=int, default=200000)
    parser.add_argument("--publish", type=Path, help="Copy successful artifact to a new viewer directory")
    parser.add_argument("--title", default="Dozer · local reconstruction")
    parser.add_argument("--id", default="dozer-local")
    args = parser.parse_args()
    if args.steps < 1 or args.resolution < 64 or args.max_splats < 1000:
        parser.error("Invalid training budget")
    dataset, output = args.dataset.resolve(), args.output.resolve()
    if output.exists():
        parser.error(f"Output already exists: {output}")
    output.mkdir(parents=True)
    report = {"status": "RUNNING", "startedAt": datetime.now(timezone.utc).isoformat(),
              "dataset": str(dataset), "output": str(output)}
    write_json(output / "job.json", report)
    process, cancelled = None, False
    started = time.monotonic()

    def stop(signum, _frame):
        nonlocal cancelled
        cancelled = True
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signum)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        transforms, provenance = validate_dataset(dataset)
        world, cameras = artifact(transforms, provenance, args.title, args.id)
        brush = args.brush.resolve()
        if not brush.is_file():
            raise FileNotFoundError("Brush missing: run python3 scripts/install-brush.py")
        help_result = subprocess.run([str(brush), "--help"], capture_output=True, text=True, check=True)
        (output / "brush-help.txt").write_text(help_result.stdout)
        version = subprocess.run([str(brush), "--version"], capture_output=True, text=True, check=True).stdout.strip()
        if version != "brush-cli 0.3.0":
            raise ValueError(f"This adapter was verified against brush-cli 0.3.0, found {version}")
        artifact_dir = output / "world"
        artifact_dir.mkdir()
        command = [str(brush), str(dataset), "--total-steps", str(args.steps),
                   "--max-resolution", str(args.resolution), "--max-splats", str(args.max_splats),
                   "--export-every", str(args.steps), "--export-path", str(artifact_dir),
                   "--export-name", "scene.ply", "--sh-degree", "1", "--seed", "42"]
        report.update(command=command, toolVersion=version, imageCount=len(transforms["frames"]),
                      options={"steps": args.steps, "resolution": args.resolution, "maxSplats": args.max_splats})
        write_json(output / "job.json", report)
        # macOS time reports process maximum RSS in bytes. Unified GPU memory is
        # not separately measured by this metric.
        measured = ["/usr/bin/time", "-l", "-o", str(output / "resources.txt"), *command]
        environment = {**os.environ, "RUST_LOG": "info", "RUST_BACKTRACE": "1", "WGPU_BACKEND": "metal"}
        if cancelled:
            report["status"] = "CANCELLED"
            raise RuntimeError("Reconstruction cancelled before training started")
        print(f"Training {len(transforms['frames'])} views; logs: {output / 'training.log'}", flush=True)
        with (output / "training.log").open("w") as log:
            process = subprocess.Popen(measured, stdout=log, stderr=subprocess.STDOUT,
                                       env=environment, start_new_session=True)
            returncode = process.wait()
        report["exitCode"] = returncode
        resources = (output / "resources.txt").read_text()
        memory = re.search(r"(\d+)\s+maximum resident set size", resources)
        if memory:
            report["maximumResidentSetBytes"] = int(memory[1])
        footprint = re.search(r"(\d+)\s+peak memory footprint", resources)
        if footprint:
            report["peakMemoryFootprintBytes"] = int(footprint[1])
        training_log = (output / "training.log").read_text()
        adapter = re.search(r'Using adapter AdapterInfo \{[^\n]+', training_log)
        if adapter:
            report["adapterEvidence"] = adapter[0]
        if cancelled:
            report["status"] = "CANCELLED"
            raise RuntimeError("Reconstruction cancelled; logs and partial outputs preserved")
        if returncode != 0:
            raise RuntimeError(f"Brush exited with status {returncode}; see training.log")
        report["artifact"] = ply_info(artifact_dir / "scene.ply")
        write_json(artifact_dir / "world.json", world)
        write_json(artifact_dir / "cameras.json", cameras)
        if (dataset / "LICENSE").exists():
            shutil.copy2(dataset / "LICENSE", artifact_dir / "SOURCE_LICENSE")
        report.update(status="PASS", browserRendering="NOT RUN", manifestPath=str(artifact_dir / "world.json"))
        if args.publish:
            shutil.copytree(artifact_dir, args.publish.resolve())
            report["publishedManifestPath"] = str(args.publish.resolve() / "world.json")
    except Exception as error:
        if report["status"] != "CANCELLED":
            report["status"] = "FAIL"
        report["error"] = str(error)
        print(str(error), file=sys.stderr)
    finally:
        report["elapsedSeconds"] = time.monotonic() - started
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        write_json(output / "job.json", report)
        print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
