#!/usr/bin/env python3
"""Acquire a small Nerfstudio dozer image dataset.

Uses HTTP ranges to avoid downloading the original 1.35 GB ZIP. No cloud
computation. Default: posed, undistorted images (requires numpy and OpenCV).
--unposed: unchanged source JPEGs only, with no camera or sparse-point data;
uses Python's standard library. See docs/SAMPLES.md and docs/M1.md.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import struct
import time
import urllib.request
import zlib

REVISION = "6a638951a007c8b47eb8a0301d48b04d18e955cf"
BASE = f"https://huggingface.co/datasets/nerfbaselines/nerfbaselines-data/resolve/{REVISION}/nerfstudio"
ARCHIVE_SIZE = 1347483375
ARCHIVE = BASE + "/dozer.zip"


def write_acquisition_report(output, report):
    """Hash only finalized output files, then write the report last.

    Callers must finish every image/metadata/license write first. The report
    excludes itself; adding a field to a prepared manifest requires a new run.
    """
    files = {str(p.relative_to(output)): {"bytes": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(output.rglob("*"))
             if p.is_file() and p.name not in {"acquisition.json", "acquisition.json.tmp"}}
    report.update(reportSchemaVersion=2, files=files,
                  hashScope="Final prepared files; acquisition.json excluded. No files modified after hashing.")
    temporary = output / "acquisition.json.tmp"
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    temporary.replace(output / "acquisition.json")
    return report


def jpeg_dimensions(data):
    """Read JPEG dimensions without decoding/re-encoding pixels or EXIF."""
    if not data.startswith(b"\xff\xd8"):
        raise ValueError("Expected JPEG source bytes")
    offset = 2
    while offset + 3 < len(data):
        if data[offset] != 0xFF:
            raise ValueError("Invalid JPEG marker")
        while data[offset] == 0xFF:
            offset += 1
        marker = data[offset]
        offset += 1
        if marker == 0xDA:
            break
        if marker in {0x01, 0xD8, 0xD9, *range(0xD0, 0xD8)}:
            continue
        length, = struct.unpack_from(">H", data, offset)
        if length < 2 or offset + length > len(data):
            raise ValueError("Invalid JPEG segment length")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height, width = struct.unpack_from(">HH", data, offset + 3)
            return width, height
        offset += length
    raise ValueError("JPEG has no supported frame dimensions")


def fetch_unposed(output, cache, index, frame_count, image_scale, started):
    directory = "images" if image_scale == 1 else f"images_{image_scale}"
    pattern = re.compile(rf"^dozer/{directory}/frame_\d+\.jpeg$")
    all_members = sorted(name for name in index if pattern.fullmatch(name))
    if frame_count > len(all_members):
        raise ValueError(f"Only {len(all_members)} source images are available")
    indices = [round(i * (len(all_members) - 1) / (frame_count - 1))
               for i in range(frame_count)]
    if len(set(indices)) != frame_count:
        raise ValueError("Image selection contains duplicate indices")
    expected_size = (3008 // image_scale, 2000 // image_scale)

    def fetch_image(source_index):
        name = all_members[source_index]
        encoded = member(index, name, cache)
        dimensions = jpeg_dimensions(encoded)
        if dimensions != expected_size:
            raise ValueError(f"Unexpected source image dimensions for {name}: {dimensions}")
        filename = Path(name).name
        # Preserve original member bytes, including any EXIF; no undistortion.
        (output / "images" / filename).write_bytes(encoded)
        return {"sourceIndex": source_index,
                "sourceSequence": int(Path(filename).stem.split("_")[-1]),
                "file": f"images/{filename}", "archiveMember": name,
                "bytes": len(encoded), "zipCrc32": index[name]["crc"],
                "sha256": hashlib.sha256(encoded).hexdigest()}

    print(f"Downloading {frame_count} unchanged {directory} JPEGs; no camera/point data", flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        selected = list(pool.map(fetch_image, indices))
    selection = {
        "sourceImageDirectory": f"dozer/{directory}",
        "sourceImageCount": len(all_members), "selectedImageCount": len(selected),
        "selection": "Sorted source filenames; evenly spaced indices including both endpoints, using round(i*(N-1)/(n-1))",
        "indicesAreZeroBased": True, "frames": selected,
    }
    (output / "selected-frames.json").write_text(json.dumps(selection, indent=2) + "\n")
    with urllib.request.urlopen(BASE + "/LICENSE", timeout=30) as response:
        (output / "LICENSE").write_bytes(response.read())
    provenance = {
        "sourceType": "images", "sourceUrl": ARCHIVE, "license": "Apache-2.0",
        "licenseUrl": BASE.replace("/resolve/", "/blob/") + "/LICENSE",
        "attribution": "Nerfstudio team and contributors; dozer dataset distributed by NerfBaselines",
        "backend": "source JPEG acquisition only; camera estimation not yet run",
        "notes": f"{len(selected)} of {len(all_members)} upstream {directory} JPEGs copied byte-for-byte, with original lens distortion and any EXIF preserved. No source camera calibration, extrinsics, transforms.json, COLMAP model, or sparse geometry was read or copied by this acquisition. No video or timestamps are provided.",
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    return write_acquisition_report(output, {
        "status": "PASS", "mode": "unposed", "elapsedSeconds": time.monotonic() - started,
        "revision": REVISION, "archive": ARCHIVE, "archiveBytes": ARCHIVE_SIZE,
        "frames": len(selected), "sourceFrames": len(all_members),
        "width": expected_size[0], "height": expected_size[1], "sourceImageScale": image_scale,
        "sourceBytesUnmodified": True, "providedCameraPosesUsed": False,
        "providedCameraCalibrationUsed": False, "providedSparseGeometryUsed": False,
        "sourceImageBytes": sum(frame["bytes"] for frame in selected),
        "selectedSourceIndices": indices,
    })


def get_range(start, end):
    request = urllib.request.Request(
        f"{ARCHIVE}?range={start}-{end}", headers={"Range": f"bytes={start}-{end}"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        expected = f"bytes {start}-{end}/{ARCHIVE_SIZE}"
        if response.status != 206 or response.headers.get("Content-Range") != expected:
            raise ValueError("Server did not honor the requested ZIP byte range")
        data = response.read(end - start + 2)
    if len(data) != end - start + 1:
        raise ValueError("Truncated ZIP range")
    return data


def archive_index():
    tail = get_range(ARCHIVE_SIZE - 22, ARCHIVE_SIZE - 1)
    header = struct.unpack("<4s4H2LH", tail)
    if header[0] != b"PK\x05\x06" or header[-1] != 0:
        raise ValueError("Unexpected ZIP end record")
    directory = get_range(header[6], header[6] + header[5] - 1)
    offset, result = 0, {}
    while directory[offset:offset + 4] == b"PK\x01\x02":
        entry = struct.unpack_from("<4s6H3L5H2L", directory, offset)
        name = directory[offset + 46:offset + 46 + entry[10]].decode()
        result[name] = {"compressed": entry[8], "size": entry[9],
                        "offset": entry[16], "method": entry[4], "crc": entry[7]}
        offset += 46 + entry[10] + entry[11] + entry[12]
    if len(result) != header[4]:
        raise ValueError("Incomplete ZIP directory")
    return result


def member(index, name, cache):
    # The name is selected by this script, never accepted as a destination path.
    entry = index[name]
    cached = cache / hashlib.sha256(name.encode()).hexdigest()
    if cached.exists():
        data = cached.read_bytes()
        if len(data) == entry["size"] and zlib.crc32(data) == entry["crc"]:
            return data
    offset = entry["offset"]
    header = get_range(offset, offset + 29)
    local = struct.unpack("<4s5H3L2H", header)
    if local[0] != b"PK\x03\x04":
        raise ValueError("Invalid ZIP local header")
    start = offset + 30 + local[-2] + local[-1]
    compressed = get_range(start, start + entry["compressed"] - 1)
    data = zlib.decompress(compressed, -15) if entry["method"] == 8 else compressed
    if len(data) != entry["size"] or zlib.crc32(data) != entry["crc"]:
        raise ValueError(f"ZIP integrity check failed for {name}")
    cached.write_bytes(data)
    return data


def colmap_cameras_to_world(data, np):
    """Read COLMAP images.bin camera-to-world matrices with OpenGL camera axes."""
    count, = struct.unpack_from("<Q", data)
    offset, cameras = 8, {}
    for _ in range(count):
        values = struct.unpack_from("<i7di", data, offset)
        offset += 64
        end = data.index(0, offset)
        name = data[offset:end].decode()
        offset = end + 1
        w, x, y, z = values[1:5]
        rotation = np.array([
            [1-2*y*y-2*z*z, 2*x*y-2*z*w, 2*x*z+2*y*w],
            [2*x*y+2*z*w, 1-2*x*x-2*z*z, 2*y*z-2*x*w],
            [2*x*z-2*y*w, 2*y*z+2*x*w, 1-2*x*x-2*y*y],
        ])
        matrix = np.eye(4)
        matrix[:3, :3] = rotation.T @ np.diag([1, -1, -1])
        matrix[:3, 3] = -rotation.T @ np.array(values[5:8])
        cameras[name] = matrix
        points, = struct.unpack_from("<Q", data, offset)
        offset += 8 + points * 24
    return cameras


def point_cloud(data, world_transform, np):
    count, = struct.unpack_from("<Q", data)
    offset, points = 8, []
    for _ in range(count):
        values = struct.unpack_from("<Q3d3BdQ", data, offset)
        position = world_transform @ np.array([*values[1:4], 1.0])
        points.append((*position[:3], *values[4:7]))
        offset += 51 + values[-1] * 8
    return points


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/datasets/dozer-small"))
    parser.add_argument("--frames", type=int, default=40)
    parser.add_argument("--unposed", action="store_true",
                        help="Copy unchanged source JPEGs; do not load calibration, poses or points")
    parser.add_argument("--image-scale", type=int, choices=[1, 2, 4, 8],
                        help="Source downsampling factor (default: 2 for unposed, 4 for posed)")
    args = parser.parse_args()
    maximum = 359 if args.unposed else 100
    if not 4 <= args.frames <= maximum:
        parser.error(f"--frames must be between 4 and {maximum}")
    image_scale = args.image_scale or (2 if args.unposed else 4)
    if not args.unposed and image_scale != 4:
        parser.error("Posed mode currently supports only --image-scale 4")
    started = time.monotonic()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"Output already exists: {output}; choose a fresh --output")
    cache = output.parent / ".dozer-download-cache"
    cache.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=False)
    (output / "images").mkdir()
    index = archive_index()
    if args.unposed:
        report = fetch_unposed(output, cache, index, args.frames, image_scale, started)
        print(json.dumps({k: v for k, v in report.items() if k not in ("files", "selectedSourceIndices")}, indent=2))
        print(output)
        return
    import cv2
    import numpy as np

    transforms = json.loads(member(index, "dozer/transforms.json", cache))
    original = json.loads(json.dumps(transforms))
    all_frames = transforms["frames"]
    chosen = [all_frames[round(i * (len(all_frames)-1)/(args.frames-1))]
              for i in range(args.frames)]

    def fetch_image(frame):
        name = frame["file_path"].split("/")[-1]
        return name, member(index, f"dozer/images_4/{name}", cache)

    print(f"Downloading {len(chosen)} images and supplied camera/point data", flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        images = list(pool.map(fetch_image, chosen))
    scale = 4
    size = (int(transforms["w"] / scale), int(transforms["h"] / scale))
    intrinsics = np.array([[transforms["fl_x"]/scale, 0, transforms["cx"]/scale],
                           [0, transforms["fl_y"]/scale, transforms["cy"]/scale], [0, 0, 1.]])
    distortion = np.array([transforms[f"k{i}"] for i in range(1, 5)])
    # A centered pinhole camera with balance=0 preserves valid image pixels.
    new_intrinsics = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
        intrinsics, distortion, size, np.eye(3), balance=0)
    new_intrinsics[0, 2], new_intrinsics[1, 2] = size[0] / 2, size[1] / 2
    maps = cv2.fisheye.initUndistortRectifyMap(
        intrinsics, distortion, np.eye(3), new_intrinsics, size, cv2.CV_32FC1)
    for name, encoded in images:
        image = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.shape[:2] != (size[1], size[0]):
            raise ValueError(f"Unexpected image dimensions: {name}")
        image = cv2.remap(image, *maps, cv2.INTER_LINEAR)
        if not cv2.imwrite(str(output / "images" / name), image):
            raise OSError(f"Could not write {name}")

    print("Converting measured sparse points into the supplied camera coordinate frame", flush=True)
    colmap = colmap_cameras_to_world(member(index, "dozer/colmap/sparse/0/images.bin", cache), np)
    first = all_frames[0]
    world_transform = np.array(first["transform_matrix"]) @ np.linalg.inv(
        colmap[Path(first["file_path"]).name])
    errors = [float(np.max(np.abs(world_transform @ colmap[Path(f["file_path"]).name]
                                - np.array(f["transform_matrix"])))) for f in all_frames]
    if max(errors) > 1e-5:
        raise ValueError(f"COLMAP and Nerfstudio camera frames disagree: {max(errors)}")
    points = point_cloud(member(index, "dozer/colmap/sparse/0/points3D.bin", cache), world_transform, np)
    with (output / "init.ply").open("wb") as stream:
        stream.write(("ply\nformat binary_little_endian 1.0\n" + f"element vertex {len(points)}\n"
                      + "property float x\nproperty float y\nproperty float z\n"
                      + "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n").encode())
        for point in points:
            stream.write(struct.pack("<3f3B", *point))
    for name in ("k1", "k2", "k3", "k4", "p1", "p2"):
        transforms.pop(name, None)
    transforms.update(camera_model="OPENCV", ply_file_path="init.ply", w=size[0], h=size[1],
                      fl_x=float(new_intrinsics[0, 0]), fl_y=float(new_intrinsics[1, 1]),
                      cx=float(new_intrinsics[0, 2]), cy=float(new_intrinsics[1, 2]), frames=chosen)
    (output / "transforms.json").write_text(json.dumps(transforms, indent=2) + "\n")
    (output / "source-transforms.json").write_text(json.dumps(original, indent=2) + "\n")
    with urllib.request.urlopen(BASE + "/LICENSE", timeout=30) as response:
        (output / "LICENSE").write_bytes(response.read())
    provenance = {
        "sourceType": "images", "sourceUrl": ARCHIVE,
        "license": "Apache-2.0",
        "licenseUrl": BASE.replace("/resolve/", "/blob/") + "/LICENSE",
        "attribution": "Nerfstudio team and contributors; dozer dataset distributed by NerfBaselines",
        "backend": "supplied COLMAP poses; OpenCV fisheye undistortion",
        "notes": "Subset of 359 supplied posed views; images_4 undistorted locally. Original camera transforms preserved. Dataset license is from the NerfBaselines distribution, separately from software licenses.",
    }
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    report = {"status": "PASS", "mode": "posed", "elapsedSeconds": time.monotonic()-started,
              "frames": len(chosen), "width": size[0], "height": size[1],
              "initialPoints": len(points), "maxCameraTransformError": max(errors),
              "colmapToNerfstudio": world_transform.tolist(),
              "opencvVersion": cv2.__version__, "numpyVersion": np.__version__}
    report = write_acquisition_report(output, report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("files", "colmapToNerfstudio")}, indent=2))
    print(output)


if __name__ == "__main__":
    main()
