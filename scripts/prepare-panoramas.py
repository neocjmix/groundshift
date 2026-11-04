#!/usr/bin/env python3
"""Resample local 2:1 equirectangular panoramas into overlapping pinhole images.

Requires NumPy and OpenCV (data/tools/venv/bin/python on the validation Mac).
This changes image projection only: it does not estimate world camera poses,
generate missing views, or establish capture order for route playback.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import resource
import signal
import sys
import time
import traceback
from urllib.parse import urlsplit


EXTENSIONS = {".jpg", ".jpeg", ".png"}
ORIENTATION_MEANING = (
    "Analytic crop rotation relative to each input panorama's image sphere, "
    "not a measured world orientation, compass heading or camera translation. "
    "Crops from one panorama have no new physical baseline."
)


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_provenance(value):
    if not isinstance(value, dict):
        raise ValueError("Provenance must be a JSON object")
    if value.get("sourceType") not in ("images", "sample"):
        raise ValueError("Panorama provenance sourceType must be images or sample")
    for key in ("sourceUrl", "license", "licenseUrl", "attribution"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(f"Provenance requires a nonempty {key}")
    for key in ("sourceUrl", "licenseUrl"):
        url = value[key]
        parsed = urlsplit(url)
        valid = parsed.scheme in ("http", "https", "file")
        valid = valid and parsed.username is None and parsed.password is None
        valid = valid and (parsed.path.startswith("/") if parsed.scheme == "file" else bool(parsed.hostname))
        valid = valid and "\\" not in url and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url)
        _ = parsed.port
        if not valid:
            raise ValueError(f"Provenance {key} requires an absolute HTTP(S) or file URL without credentials")
    if "notes" in value and not isinstance(value["notes"], str):
        raise ValueError("Provenance notes must be a string")


def angles(value):
    try:
        result = [float(part) for part in value.split(",")]
    except ValueError as error:
        raise argparse.ArgumentTypeError("Yaws must be comma-separated numbers") from error
    if not result or len(result) > 24 or not all(math.isfinite(x) for x in result):
        raise argparse.ArgumentTypeError("Require between 1 and 24 finite yaw angles")
    result = [angle % 360 for angle in result]
    if len({round(angle, 9) for angle in result}) != len(result):
        raise argparse.ArgumentTypeError("Yaw angles must be distinct modulo 360 degrees")
    return result


def intrinsics(size, hfov):
    if not isinstance(size, int) or size < 1 or not math.isfinite(hfov) or not 0 < hfov < 180:
        raise ValueError("Require a positive integer size and horizontal FOV between 0 and 180 degrees")
    focal = round(size / (2 * math.tan(math.radians(hfov) / 2)), 12)
    return {"cameraModel": "PINHOLE", "width": size, "height": size,
            "fx": focal, "fy": focal, "cx": size / 2, "cy": size / 2,
            "horizontalFovDegrees": hfov,
            "source": "Exact mathematical output projection; not measured source-lens calibration",
            "pixelConvention": "Pixel centers are (column + 0.5, row + 0.5); principal point is (width/2, height/2)"}


def crop_rotation(yaw, pitch):
    """Camera-to-panorama 3x3 rotation, both +X right, +Y down, +Z forward."""
    import numpy as np
    if not all(math.isfinite(angle) for angle in (yaw, pitch)) or not -90 <= pitch <= 90:
        raise ValueError("Require finite yaw and pitch between -90 and 90 degrees")
    y, p = math.radians(yaw), math.radians(pitch)
    cy, sy, cp, sp = math.cos(y), math.sin(y), math.cos(p), math.sin(p)
    return np.array([[cy, sy * sp, sy * cp], [0, cp, -sp], [-sy, cy * sp, cy * cp]])


def sampling_map(width, height, size, hfov, yaw, pitch):
    import numpy as np
    if width != 2 * height or height < 2:
        raise ValueError("Input must be an uncropped 2:1 equirectangular panorama")
    calibration = intrinsics(size, hfov)
    x, y = np.meshgrid(np.arange(size) + 0.5, np.arange(size) + 0.5)
    rays = np.stack(((x - calibration["cx"]) / calibration["fx"],
                     (y - calibration["cy"]) / calibration["fy"], np.ones_like(x)), axis=-1)
    rays = rays @ crop_rotation(yaw, pitch).T
    rays /= np.linalg.norm(rays, axis=-1, keepdims=True)
    longitude = np.arctan2(rays[..., 0], rays[..., 2])
    latitude = np.arcsin(np.clip(-rays[..., 1], -1, 1))
    map_x = (longitude / (2 * np.pi) + 0.5) * width - 0.5
    map_y = (0.5 - latitude / np.pi) * height - 0.5
    return map_x.astype(np.float32), map_y.astype(np.float32)


def crop_panorama(pixels, size, hfov, yaw, pitch):
    import cv2
    import numpy as np
    if pixels.ndim != 3 or pixels.shape[2] != 3 or pixels.dtype != np.uint8:
        raise ValueError("Require an 8-bit, three-channel panorama; convert HDR/alpha explicitly first")
    height, width = pixels.shape[:2]
    map_x, map_y = sampling_map(width, height, size, hfov, yaw, pitch)
    # Horizontal wrap only: north/south poles must never wrap onto each other.
    padded = np.concatenate((pixels[:, -1:], pixels, pixels[:, :1]), axis=1)
    return cv2.remap(padded, np.mod(map_x, width) + 1, np.clip(map_y, 0, height - 1),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


class Cancelled(KeyboardInterrupt):
    def __init__(self, signum):
        self.signum = signum
        super().__init__(f"Received {signal.Signals(signum).name}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panoramas", type=Path, help="Directory of uncropped, upright 2:1 JPEG/PNG panoramas")
    parser.add_argument("output", type=Path, help="New directory; existing paths are never overwritten")
    parser.add_argument("--provenance", type=Path, required=True, help="Source/license/attribution JSON")
    parser.add_argument("--size", type=int, default=512, help="Square crop dimensions (default: 512)")
    parser.add_argument("--hfov", type=float, default=90, help="Horizontal field of view in degrees (default: 90)")
    parser.add_argument("--yaws", type=angles, default=angles("0,60,120,180,240,300"),
                        help="Comma-separated angles; positive turns right (default: 0,60,120,180,240,300)")
    parser.add_argument("--pitch", type=float, default=0, help="Pitch in degrees, positive up (default: 0)")
    args = parser.parse_args(argv)
    if not 16 <= args.size <= 2048 or not math.isfinite(args.hfov) or not 10 <= args.hfov <= 150:
        parser.error("Require --size 16..2048 and --hfov 10..150")
    if not math.isfinite(args.pitch) or not -90 <= args.pitch <= 90:
        parser.error("Require finite --pitch between -90 and 90")
    source = args.panoramas.expanduser().resolve()
    requested_output = args.output.expanduser()
    output = requested_output.resolve()
    if output.exists() or requested_output.is_symlink():
        parser.error(f"Output already exists: {output}")
    if not source.is_dir():
        parser.error(f"Input panorama directory does not exist: {source}")
    if output.is_relative_to(source):
        parser.error("Output must be outside the input panorama directory")
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"Output already exists: {output}")
    started = time.monotonic()
    report = {"schemaVersion": 1, "operation": "local-panorama-pinhole-preparation", "status": "RUNNING",
              "startedAt": datetime.now(timezone.utc).isoformat(), "inputDirectory": str(source),
              "gpuUsed": False, "diffusionUsed": False, "worldCameraPosesProvided": False,
              "cameraEstimation": "NOT RUN", "reconstruction": "NOT RUN", "browserRendering": "NOT RUN"}
    received_signal = None

    def on_signal(signum, _frame):
        nonlocal received_signal
        if received_signal is None:
            received_signal = signum
            raise Cancelled(signum)

    previous = {signum: signal.signal(signum, on_signal) for signum in (signal.SIGINT, signal.SIGTERM)}
    exit_code = 1
    with (output / "execution.log").open("w") as log:
        try:
            write_json(output / "report.json", report)
            import cv2
            import numpy as np
            report["versions"] = {"numpy": np.__version__, "opencv": cv2.__version__}
            provenance_bytes = args.provenance.expanduser().read_bytes()
            provenance = json.loads(provenance_bytes)
            validate_provenance(provenance)
            # Force finite JSON also for optional provider-specific metadata.
            json.dumps(provenance, allow_nan=False)
            (output / "source-provenance.json").write_bytes(provenance_bytes)
            report["sourceProvenanceSha256"] = digest(provenance_bytes)
            derived = {**provenance, "sourceType": "images", "backend": "OpenCV equirectangular-to-pinhole resampling",
                       "notes": (provenance.get("notes", "") + " " + ORIENTATION_MEANING
                                 + " Original source projection must be full equirectangular; 2:1 dimensions alone do not prove it."
                                 + " No diffusion, pose estimation or reconstruction was performed.").strip()}
            write_json(output / "provenance.json", derived)
            files = sorted(path for path in source.iterdir() if path.suffix.lower() in EXTENSIONS)
            if not files:
                raise ValueError("Input directory contains no supported JPEG/PNG panoramas")
            (output / "images").mkdir()
            calibration = intrinsics(args.size, args.hfov)
            write_json(output / "intrinsics.json", calibration)
            manifest = {"schemaVersion": 1, "kind": "panorama-pinhole-crops", "orientationMeaning": ORIENTATION_MEANING,
                        "panoramaAxes": "+X right, +Y down, +Z toward the panorama image center; right-handed",
                        "equirectangularConvention": "Image center longitude 0, latitude 0; longitude increases right, latitude increases up; horizontal seam at +/-180 degrees",
                        "intrinsics": calibration, "sourcePanoramas": [], "crops": [],
                        "sourceOrderMeaning": "Lexicographic filename order only; no chronological or spatial continuity is inferred",
                        "worldCameraPosesProvided": False, "diffusionUsed": False}
            for index, path in enumerate(files):
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f"Input must be a regular, non-symlink image file: {path.name}")
                data = path.read_bytes()
                pixels = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                if pixels is None:
                    raise ValueError(f"Cannot decode panorama: {path.name}")
                height, width = pixels.shape[:2]
                if width != 2 * height:
                    raise ValueError(f"Panorama must have exact 2:1 dimensions: {path.name} is {width}x{height}")
                source_id = path.name
                manifest["sourcePanoramas"].append({"sourceId": source_id, "sourceFile": path.name,
                                                    "sha256": digest(data), "bytes": len(data), "width": width, "height": height})
                for view, yaw in enumerate(args.yaws):
                    cropped = crop_panorama(pixels, args.size, args.hfov, yaw, args.pitch)
                    relative = f"images/pano_{index + 1:06d}_view_{view + 1:02d}.png"
                    ok, encoded = cv2.imencode(".png", cropped, [cv2.IMWRITE_PNG_COMPRESSION, 3])
                    if not ok:
                        raise RuntimeError(f"Failed to encode {relative}")
                    encoded_bytes = encoded.tobytes()
                    (output / relative).write_bytes(encoded_bytes)
                    manifest["crops"].append({"file": relative, "sourceId": source_id, "sourceIndex": index,
                                              "yawDegrees": yaw, "pitchDegrees": args.pitch,
                                              "relativeCameraToPanoramaRotation": crop_rotation(yaw, args.pitch).tolist(),
                                              "sha256": digest(encoded_bytes), "bytes": len(encoded_bytes)})
                print(f"Prepared {path.name}: {width}x{height}, {len(args.yaws)} crops", file=log, flush=True)
            write_json(output / "crops.json", manifest)
            params = ",".join(f"{calibration[key]:.12g}" for key in ("fx", "fy", "cx", "cy"))
            report["result"] = {"panoramaCount": len(manifest["sourcePanoramas"]), "cropCount": len(manifest["crops"]),
                                "imageBytes": sum(crop["bytes"] for crop in manifest["crops"]),
                                "manifestSha256": digest((output / "crops.json").read_bytes()),
                                "colmapArguments": ["--camera-model", "PINHOLE", "--camera-params", params,
                                                    "--single-camera", "--fix-intrinsics"]}
            report["status"], exit_code = "PASS", 0
        except KeyboardInterrupt as error:
            signum = getattr(error, "signum", signal.SIGINT)
            report.update(status="CANCELLED", error=str(error), cancellationSignal=signal.Signals(signum).name)
            traceback.print_exc(file=log)
            exit_code = 128 + signum
        except Exception as error:
            report.update(status="FAIL", error=f"{type(error).__name__}: {error}")
            traceback.print_exc(file=log)
        finally:
            report["elapsedSeconds"] = round(time.monotonic() - started, 6)
            report["finishedAt"] = datetime.now(timezone.utc).isoformat()
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report["peakProcessRssBytes"] = int(rss if sys.platform == "darwin" else rss * 1024)
            report["memoryMeasurement"] = "Whole-process peak resident memory; CPU image preparation only"
            report["exitCode"] = exit_code
            write_json(output / "report.json", report)
            for signum, handler in previous.items():
                signal.signal(signum, handler)
    print(f"{report['status']}: {output / 'report.json'}")
    if report.get("error"):
        print(report["error"], file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
