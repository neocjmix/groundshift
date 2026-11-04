#!/usr/bin/env python3
"""Acquire 9 licensed consecutive 360 photos from the public Commons mirror.

No Mapillary account or token is needed. Images remain byte-for-byte upstream
JPEGs; source coordinates are metadata, never invented camera extrinsics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request


MANIFEST = Path(__file__).parent / "samples" / "mapillary-beijing.json"
USER_AGENT = "GroundshiftPrototype/0.1 (github.com/neocjmix/groundshift; local research)"


def verify_source(data, entry):
    if len(data) != entry["size"]:
        raise ValueError(f"Source byte length changed: {entry['image_id']}")
    if hashlib.sha1(data).hexdigest() != entry["sha1"]:
        raise ValueError(f"Source SHA-1 mismatch: {entry['image_id']}")
    if entry.get("sha256") and hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"Source SHA-256 mismatch: {entry['image_id']}")
    return hashlib.sha256(data).hexdigest()


def download(entry):
    """Respect source throttling; no alternate hosts or authentication bypass."""
    for attempt in range(3):
        request = urllib.request.Request(entry["url"], headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read(entry["size"] + 1)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 2:
                raise
            retry = error.headers.get("Retry-After", "30")
            # For long/date-based server cooldowns, preserve the failure for a
            # later manual rerun rather than retrying before the requested time.
            if not retry.isdigit() or int(retry) > 60:
                raise
            delay = max(30, int(retry))
            print(f"Source rate limit; waiting {delay}s before retry", flush=True)
            time.sleep(delay)


def acquire(output):
    source = json.loads(MANIFEST.read_text())
    output.mkdir(parents=True, exist_ok=True)
    images = output / "images"
    images.mkdir(exist_ok=True)
    started = time.monotonic()
    report = {"schemaVersion": 1, "status": "RUNNING", "source": source,
              "providedCameraPosesUsed": False, "frames": []}
    try:
        for index, entry in enumerate(source["images"]):
            filename = f"{index:03d}_{entry['image_id']}.jpg"
            destination = images / filename
            cached = destination.exists()
            if cached:
                data = destination.read_bytes()
            else:
                # Read at most the pinned size + 1, avoiding unbounded downloads.
                data = download(entry)
            sha256 = verify_source(data, entry)
            if not cached:
                temporary = destination.with_suffix(".jpg.part")
                temporary.write_bytes(data)
                temporary.replace(destination)
            report["frames"].append({"file": f"images/{filename}",
                                     "imageId": entry["image_id"], "sha256": sha256,
                                     "bytes": len(data), "cached": cached})
            print(f"Verified {index + 1}/{len(source['images'])}: {filename}", flush=True)
            if not cached and index < len(source["images"]) - 1:
                time.sleep(5)
        provenance = {
            "sourceType": "images", "sourceUrl": source["images"][0]["commons_page"],
            "license": source["license"], "licenseUrl": source["licenseUrl"],
            "attribution": "Photographs by Cicero101 on Mapillary, redistributed by Wikimedia Commons; CC-BY-SA-4.0.",
            "backend": "source acquisition only; reconstruction not yet run",
            "notes": "9 consecutive 7680x3840 equirectangular panoramas, 2025-05-27 05:11:05–05:11:13 (timezone unspecified in source). Source bytes preserved. GPS is not a full camera pose. Not a globally densest-area claim. See acquisition.json for per-image attribution and hashes. Original 12-image attempt stopped on source rate limiting; only the 9 acquired originals are selected.",
        }
        (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
        (output / "ATTRIBUTION.txt").write_text(
            "Cicero101 / Mapillary / Wikimedia Commons\n"
            "Creative Commons Attribution-ShareAlike 4.0 International\n"
            + source["licenseUrl"] + "\n\n"
            + "\n".join(f"{x['image_id']}: {x['mapillary_url']}\n{x['commons_page']}" for x in source["images"])
            + "\n\nSource JPEGs unchanged. Derivative works must record changes and preserve applicable attribution and ShareAlike terms.\n")
        report["status"] = "PASS"
        report["totalImageBytes"] = sum(x["bytes"] for x in report["frames"])
    except Exception as error:
        report["status"] = "FAIL"
        report["error"] = str(error)
        raise
    finally:
        report["elapsedSeconds"] = time.monotonic() - started
        (output / "acquisition.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=Path("data/samples/mapillary-beijing"))
    args = parser.parse_args()
    try:
        report = acquire(args.output)
        print(f"PASS: {len(report['frames'])} source panoramas, {report['totalImageBytes']} bytes")
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
