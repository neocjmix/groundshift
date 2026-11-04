#!/usr/bin/env python3
"""Acquire a small, posed and undistorted Nerfstudio dozer image dataset.

Uses HTTP ranges to avoid downloading the original 1.35 GB ZIP. No cloud
computation: undistortion and point-cloud coordinate conversion run locally.
Requires numpy and opencv-python-headless (see docs/M1.md).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import struct
import time
import urllib.request
import zlib

REVISION = "6a638951a007c8b47eb8a0301d48b04d18e955cf"
BASE = f"https://huggingface.co/datasets/nerfbaselines/nerfbaselines-data/resolve/{REVISION}/nerfstudio"
ARCHIVE_SIZE = 1347483375
ARCHIVE = BASE + "/dozer.zip"


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
    args = parser.parse_args()
    if not 4 <= args.frames <= 100:
        parser.error("--frames must be between 4 and 100")
    started = time.monotonic()
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"Output already exists: {output}; choose a fresh --output")
    import cv2
    import numpy as np

    cache = output.parent / ".dozer-download-cache"
    cache.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=False)
    (output / "images").mkdir()
    index = archive_index()
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
    report = {"status": "PASS", "elapsedSeconds": time.monotonic()-started,
              "frames": len(chosen), "width": size[0], "height": size[1],
              "initialPoints": len(points), "maxCameraTransformError": max(errors),
              "colmapToNerfstudio": world_transform.tolist(),
              "opencvVersion": cv2.__version__, "numpyVersion": np.__version__,
              "files": {str(p.relative_to(output)): {"bytes": p.stat().st_size,
                         "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                        for p in sorted(output.rglob("*")) if p.is_file()}}
    (output / "acquisition.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("files", "colmapToNerfstudio")}, indent=2))
    print(output)


if __name__ == "__main__":
    main()
