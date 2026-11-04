#!/usr/bin/env python3
"""Measure photometric errors against a reference image, without geometric claims.

Usage: compare-gap.py reference baseline completed output [--mask mask.png]
Inputs must be equally sized 8-bit RGB images (opaque RGBA is also accepted).
An optional mask is an 8-bit grayscale image containing only 0 and 255; white
selects the gap. Both masked and unmasked regions must be nonempty. No resizing,
alignment, exposure adjustment, linearization or color-profile conversion occurs.
Requires NumPy/OpenCV: use data/tools/venv/bin/python on the validation Mac.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import signal
import sys
import time
import traceback


def read_image(path, mask=False):
    import cv2
    import numpy as np
    data = path.read_bytes()
    # IMREAD_UNCHANGED deliberately avoids EXIF orientation transformations.
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None or image.size == 0:
        raise ValueError(f"Cannot decode image: {path.name}")
    if image.dtype != np.uint8:
        raise ValueError(f"Expected 8-bit image: {path.name}")
    if mask:
        if image.ndim != 2:
            raise ValueError("Mask must be single-channel grayscale")
        if not np.all((image == 0) | (image == 255)):
            raise ValueError("Mask must be binary grayscale with values 0 and 255")
    else:
        if image.ndim == 3 and image.shape[2] == 4:
            if not np.all(image[:, :, 3] == 255):
                raise ValueError(f"Image has nonopaque alpha: {path.name}")
            image = image[:, :, :3]
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(f"Expected RGB image: {path.name}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image, {"filename": path.name, "bytes": len(data),
                   "sha256": hashlib.sha256(data).hexdigest(),
                   "width": int(image.shape[1]), "height": int(image.shape[0])}


def region_metrics(reference, candidate, selected):
    import numpy as np
    pixel_count = int(np.count_nonzero(selected))
    if pixel_count == 0:
        raise ValueError("Comparison region is empty")
    # Convert before subtracting to avoid unsigned 8-bit wraparound.
    difference = candidate[selected].astype(np.float64) - reference[selected].astype(np.float64)
    mse = float(np.mean(difference * difference))
    exact_match = mse == 0
    return {"pixelCount": pixel_count, "channelValueCount": pixel_count * 3,
            "mae": float(np.mean(np.abs(difference))), "mse": mse,
            "psnrDb": None if exact_match else 10 * math.log10(255 * 255 / mse),
            "exactMatch": exact_match,
            "psnrInterpretation": "positive infinity (exact match)" if exact_match else "finite decibels"}


def compare(reference, baseline, completed, output, mask=None):
    import numpy as np
    # Never overwrite another experiment, including through a dangling symlink.
    if output.exists() or output.is_symlink():
        raise ValueError("Output must be a new directory")
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {"schemaVersion": 1, "status": "RUNNING",
              "createdAt": datetime.now(timezone.utc).isoformat(), "inputs": {},
              "scope": "Photometric comparison only; does not validate camera poses, 3D geometry, multi-view consistency or factual accuracy of generated content.",
              "pixelDomain": "Decoded 8-bit RGB channel values, range 0–255. No geometric alignment, resampling, exposure normalization, gamma linearization, EXIF rotation or color-profile conversion.",
              "maskConvention": "255 selects the gap; 0 selects the unmasked region."}
    try:
        decoded = {}
        for name, path in (("reference", reference), ("baseline", baseline), ("completed", completed)):
            decoded[name], report["inputs"][name] = read_image(path)
        shape = decoded["reference"].shape
        if any(image.shape != shape for image in decoded.values()):
            raise ValueError("Reference, baseline and completed image dimensions must match")
        regions = {"full": np.ones(shape[:2], dtype=bool)}
        if mask is not None:
            mask_image, report["inputs"]["mask"] = read_image(mask, mask=True)
            if mask_image.shape != shape[:2]:
                raise ValueError("Mask dimensions must match image dimensions")
            regions["masked"] = mask_image == 255
            regions["unmasked"] = mask_image == 0
            if any(not np.any(region) for region in regions.values()):
                raise ValueError("Both masked and unmasked regions must be nonempty")
        report["regions"] = {}
        for name, selected in regions.items():
            report["regions"][name] = {
                "status": "PASS", "pixelCount": int(np.count_nonzero(selected)),
                **{candidate: region_metrics(decoded["reference"], decoded[candidate], selected)
                   for candidate in ("baseline", "completed")}}
        if mask is None:
            for name in ("masked", "unmasked"):
                report["regions"][name] = {"status": "NOT RUN", "reason": "No mask supplied"}
        report["status"] = "PASS"
        report["statusMeaning"] = "Metrics computed successfully; PASS is not a quality acceptance decision."
    except KeyboardInterrupt as error:
        report["status"] = "CANCELLED"
        report["error"] = str(error) or "Interrupted"
        report["traceback"] = traceback.format_exc()
        raise
    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = str(error)
        report["traceback"] = traceback.format_exc()
        raise
    finally:
        report["elapsedSeconds"] = time.monotonic() - started
        temporary = output / "report.json.tmp"
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        temporary.replace(output / "report.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "baseline", "completed", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--mask", type=Path)
    args = parser.parse_args()
    def cancelled(_signum, _frame):
        raise KeyboardInterrupt("Interrupted by SIGTERM")
    previous = signal.signal(signal.SIGTERM, cancelled)
    try:
        report = compare(args.reference, args.baseline, args.completed, args.output, args.mask)
        print(f"PASS: photometric metrics written to {args.output / 'report.json'}")
        for name, metrics in report["regions"].items():
            if metrics["status"] == "PASS":
                print(f"{name}: baseline MAE={metrics['baseline']['mae']:.6f}, completed MAE={metrics['completed']['mae']:.6f}")
    except KeyboardInterrupt as error:
        print(f"CANCELLED: {error or 'Interrupted'}", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
