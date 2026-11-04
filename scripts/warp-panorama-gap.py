#!/usr/bin/env python3
"""Stereo-warp two observed crops into a supplied target camera, without its pixels.

Uses CPU OpenCV StereoSGBM, left/right consistency, estimated positive depth and
nearest-depth forward splatting. Unknown pixels remain black and have mask=255.
The supplied camera poses may have been estimated using all images: this is an
appearance holdout experiment, not independent held-out camera estimation.
Requires NumPy/OpenCV (data/tools/venv/bin/python on the validation Mac).
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
import traceback


def camera(frame):
    import numpy as np
    matrix = np.asarray(frame["transform_matrix"], dtype=np.float64)
    if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
        raise ValueError("Camera transform must be a finite 4x4 matrix")
    if not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-8):
        raise ValueError("Camera transform must be homogeneous")
    rotation = matrix[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-5) or not np.isclose(np.linalg.det(rotation), 1, atol=1e-5):
        raise ValueError("Camera rotation must be orthonormal and right handed")
    # Nerfstudio/OpenGL camera: +X right, +Y up, -Z forward.
    # OpenCV camera: +X right, +Y down, +Z forward. World is unchanged.
    return matrix @ np.diag([1., -1., -1., 1.])


def intrinsics(frame):
    import numpy as np
    values = [frame[x] for x in ("fl_x", "fl_y", "cx", "cy")]
    if not np.all(np.isfinite(values)) or min(values[:2]) <= 0:
        raise ValueError("Require finite positive focal lengths")
    # Crop/COLMAP coordinates place the first pixel center at (0.5, 0.5).
    # OpenCV remap, stereo and target raster projection use integer centers.
    return np.array([[values[0], 0, values[2] - 0.5],
                     [0, values[1], values[3] - 0.5], [0, 0, 1.]], dtype=np.float64)


def relative_camera(left, right):
    """Transform left OpenCV camera coordinates into the right camera."""
    import numpy as np
    return np.linalg.inv(camera(right)) @ camera(left)


def rectification(left, right, scale=2):
    import cv2
    import numpy as np
    size = (int(left["w"]), int(left["h"]))
    k = intrinsics(left)
    swapped = False
    for attempt in range(2):
        relative = relative_camera(left, right)
        if np.linalg.norm(relative[:3, 3]) < 1e-8:
            raise ValueError("Stereo cameras must have a nonzero estimated baseline")
        r1, r2, _, _, _, _, _ = cv2.stereoRectify(
            k, np.zeros(5), k, np.zeros(5), size, relative[:3, :3].copy(),
            relative[:3, 3].reshape(3, 1).copy(), flags=cv2.CALIB_ZERO_DISPARITY, alpha=-1)
        translation = r2 @ relative[:3, 3]
        axis = int(np.argmax(np.abs(translation[:2])))
        if translation[axis] < 0:
            break
        left, right, swapped = right, left, True
    else:
        raise ValueError("Unable to obtain a negative rectified stereo translation")
    baseline = float(-translation[axis])
    if np.linalg.norm(np.delete(translation, axis)) > baseline * 1e-5:
        raise ValueError("Rectified baseline is not aligned with the selected image axis")
    rectified_size = (size[0] * scale, size[1] * scale)
    # Automatic P can become unbounded when a source corner meets the epipolar
    # horizon. Retain measured rectification rotations, choose a finite canvas,
    # and center the two input optical rays in it. This is a raster projection,
    # not a change to the source calibration or estimated world poses.
    rays = np.array([r1[:, 2], r2[:, 2]])
    if np.any(rays[:, 2] <= 0.05):
        raise ValueError("Stereo optical rays are too close to the rectification horizon")
    centers = (rays[:, :2] / rays[:, 2:]).mean(axis=0)
    rectified_k = k.copy()
    rectified_k[0, 2] = (rectified_size[0] - 1) / 2 - k[0, 0] * centers[0]
    rectified_k[1, 2] = (rectified_size[1] - 1) / 2 - k[1, 1] * centers[1]
    return left, right, r1, r2, rectified_k, rectified_size, axis, baseline, swapped


def rectify_image(image, frame, rotation, k, size, block_size):
    import cv2
    import numpy as np
    mx, my = cv2.initUndistortRectifyMap(intrinsics(frame), np.zeros(5), rotation, k, size, cv2.CV_32FC1)
    valid = (mx >= 0) & (mx < image.shape[1] - 1) & (my >= 0) & (my < image.shape[0] - 1)
    valid = cv2.erode(valid.astype(np.uint8), np.ones((block_size, block_size), dtype=np.uint8)).astype(bool)
    result = cv2.remap(image, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return result, valid


def matching_orientation(image, axis, inverse=False):
    import cv2
    if axis == 0:
        return image
    if axis != 1:
        raise ValueError("Stereo axis must be horizontal or vertical")
    return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE if inverse else cv2.ROTATE_90_COUNTERCLOCKWISE)


def stereo_disparities(left, right, axis, max_disparity, block_size):
    import cv2
    a = matching_orientation(cv2.cvtColor(left, cv2.COLOR_BGR2GRAY), axis)
    c = matching_orientation(cv2.cvtColor(right, cv2.COLOR_BGR2GRAY), axis)
    kwargs = dict(numDisparities=max_disparity, blockSize=block_size,
                  P1=8 * block_size ** 2, P2=32 * block_size ** 2,
                  disp12MaxDiff=1, uniquenessRatio=10, speckleWindowSize=80,
                  speckleRange=2, preFilterCap=31, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
    dl = cv2.StereoSGBM_create(minDisparity=0, **kwargs).compute(a, c).astype("float32") / 16
    dr = cv2.StereoSGBM_create(minDisparity=1 - max_disparity, **kwargs).compute(c, a).astype("float32") / 16
    return matching_orientation(dl, axis, inverse=True), matching_orientation(dr, axis, inverse=True)


def valid_matches(disparity, reverse, own_valid, other_valid, own_image, other_image,
                  axis, sign, max_disparity, lr_tolerance, photo_tolerance):
    import cv2
    import numpy as np
    y, x = np.indices(disparity.shape, dtype=np.float32)
    other_x = x - disparity if axis == 0 else x
    other_y = y - disparity if axis == 1 else y
    reverse_at_match = cv2.remap(reverse, other_x, other_y, cv2.INTER_NEAREST,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=-max_disparity - 1)
    other_valid_at_match = cv2.remap(other_valid.astype(np.uint8), other_x, other_y, cv2.INTER_NEAREST).astype(bool)
    other_color = cv2.remap(other_image, other_x, other_y, cv2.INTER_LINEAR)
    valid = own_valid & other_valid_at_match & (sign * disparity > 0.5) & (sign * disparity < max_disparity)
    reverse_valid = (-sign * reverse_at_match > 0.5) & (-sign * reverse_at_match < max_disparity)
    valid &= reverse_valid & (np.abs(disparity + reverse_at_match) <= lr_tolerance)
    residual = np.mean(np.abs(own_image.astype(np.float32) - other_color.astype(np.float32)), axis=2)
    valid &= residual <= photo_tolerance
    return valid


def depth_points(disparity, valid, k, baseline, axis, sign):
    import numpy as np
    y, x = np.nonzero(valid)
    if np.any(sign * disparity[y, x] <= 0) or not np.isfinite(baseline) or baseline <= 0:
        raise ValueError("Stereo triangulation requires positive disparity and baseline")
    depth = k[axis, axis] * baseline / (sign * disparity[y, x].astype(np.float64))
    points = np.column_stack(((x - k[0, 2]) * depth / k[0, 0],
                              (y - k[1, 2]) * depth / k[1, 1], depth))
    if not np.all(np.isfinite(points)) or np.any(depth <= 0):
        raise ValueError("Stereo produced invalid or nonpositive depth")
    return points, y, x


def to_target(points_rectified, source_frame, source_rectification, target_frame):
    """Rectified source points -> original source -> world -> target OpenCV."""
    import numpy as np
    source_points = points_rectified @ source_rectification
    target_from_source = np.linalg.inv(camera(target_frame)) @ camera(source_frame)
    return source_points @ target_from_source[:3, :3].T + target_from_source[:3, 3]


def forward_splat(points, colors, k, width, height, footprint=2):
    import numpy as np
    valid = np.all(np.isfinite(points), axis=1) & (points[:, 2] > 1e-8)
    points, colors = points[valid], colors[valid]
    uv = points[:, :2] / points[:, 2:] * np.array([k[0, 0], k[1, 1]]) + np.array([k[0, 2], k[1, 2]])
    # Restrict before integer conversion to avoid huge near-camera coordinates.
    valid = (uv[:, 0] >= -1) & (uv[:, 0] < width) & (uv[:, 1] >= -1) & (uv[:, 1] < height)
    uv, points, colors = uv[valid], points[valid], colors[valid]
    pixels = np.floor(uv).astype(np.int64) if footprint == 2 else np.rint(uv).astype(np.int64)
    offsets = ((0, 0), (1, 0), (0, 1), (1, 1)) if footprint == 2 else ((0, 0),)
    indices, depths, samples = [], [], []
    for offset in offsets:
        p = pixels + offset
        keep = (p[:, 0] >= 0) & (p[:, 0] < width) & (p[:, 1] >= 0) & (p[:, 1] < height)
        indices.append(p[keep, 1] * width + p[keep, 0])
        depths.append(points[keep, 2])
        samples.append(colors[keep])
    indices, depths, samples = np.concatenate(indices), np.concatenate(depths), np.concatenate(samples)
    # Sort depth inside each pixel; keep its nearest triangulated sample.
    order = np.lexsort((depths, indices))
    sorted_indices = indices[order]
    first = np.r_[True, np.diff(sorted_indices) != 0] if len(order) else np.zeros(0, dtype=bool)
    chosen = order[first]
    flat = np.zeros((height * width, 3), dtype=np.uint8)
    depth = np.zeros(height * width, dtype=np.float32)
    flat[indices[chosen]] = samples[chosen]
    depth[indices[chosen]] = depths[chosen]
    return flat.reshape(height, width, 3), depth.reshape(height, width)


def run(args):
    import cv2
    import numpy as np
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("Output must be a new directory")
    if args.max_disparity < 16 or args.max_disparity % 16 or args.rectified_scale not in (1, 2, 3):
        raise ValueError("Disparity range must be a positive multiple of 16; rectified scale must be 1–3")
    if not all(np.isfinite(x) and x >= 0 for x in (args.lr_tolerance, args.photo_tolerance)):
        raise ValueError("Matching tolerances must be finite and nonnegative")
    args.output.mkdir(parents=True)
    started = time.monotonic()
    report = {"schemaVersion": 1, "status": "RUNNING", "createdAt": datetime.now(timezone.utc).isoformat(),
              "inputs": {}, "targetImagePixelsRead": False,
              "scope": "Two observed images stereo-warped into a supplied target pose. Pose estimation used all images; this is an appearance holdout only. No target pixels, invented depths, diffusion or Gaussian training are used by this command.",
              "coordinateConvention": "Input OpenGL camera-to-world multiplied on right by diag(1,-1,-1,1) to obtain OpenCV camera-to-world; world coordinates unchanged.",
              "pixelConvention": "Input crop/COLMAP intrinsics use corner-origin pixel centers. Subtract 0.5 from cx and cy for OpenCV integer pixel centers, for both observed and target cameras.",
              "settings": {"maxDisparity": args.max_disparity, "blockSize": 5, "rectifiedScale": args.rectified_scale,
                           "leftRightTolerancePixels": args.lr_tolerance, "photometricTolerance255": args.photo_tolerance,
                           "forwardSplatFootprintPixels": args.footprint, "uniquenessRatio": 10,
                           "speckleWindowSize": 80, "speckleRange": 2, "opencvVersion": cv2.__version__,
                           "sgbmMode": "SGBM_3WAY", "P1": 200, "P2": 800, "disp12MaxDiff": 1,
                           "preFilterCap": 31, "minimumAbsoluteDisparity": 0.5}}
    try:
        raw = (args.dataset / "transforms.json").read_bytes()
        data = json.loads(raw)
        report["inputs"]["transforms"] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        if data.get("camera_model") != "PINHOLE":
            raise ValueError("Only undistorted PINHOLE datasets are supported")
        frames = []
        for name in (args.left, args.right, args.target):
            matches = [frame for frame in data["frames"] if Path(frame["file_path"]).name == name]
            if len(matches) != 1:
                raise ValueError(f"Frame must match exactly once: {name}")
            frames.append(matches[0])
        if len({frame["file_path"] for frame in frames}) != 3:
            raise ValueError("Two observations and target must be distinct frames")
        left, right, target = frames
        source_k = intrinsics(left)
        for frame in frames:
            camera(frame)
            intrinsics(frame)
        if right["w"] != left["w"] or right["h"] != left["h"] or not np.allclose(intrinsics(right), source_k, atol=1e-8):
            raise ValueError("Both observed frames must share fixed intrinsics and dimensions")
        left, right, r1, r2, rk, size, axis, baseline, swapped = rectification(left, right, args.rectified_scale)
        images = []
        # Deliberately open only the two observed source images. Target appears
        # solely as transform metadata, so reference pixels cannot leak in.
        for frame in (left, right):
            path = (args.dataset / frame["file_path"]).resolve()
            if not path.is_relative_to(args.dataset.resolve()):
                raise ValueError("Source image escapes the dataset directory")
            encoded = path.read_bytes()
            image = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None or image.shape != (frame["h"], frame["w"], 3):
                raise ValueError("Source image dimensions differ from camera metadata")
            images.append(image)
            report["inputs"][Path(frame["file_path"]).name] = {"sha256": hashlib.sha256(encoded).hexdigest(), "bytes": len(encoded)}
        report["cameras"] = {"left": left, "right": right, "target": target}
        report["rectification"] = {"swappedSources": swapped, "matchingAxis": "horizontal" if axis == 0 else "vertical-rotated",
                                   "baselineInReconstructionUnits": baseline, "intrinsics": rk.tolist(), "size": list(size),
                                   "leftRotation": r1.tolist(), "rightRotation": r2.tolist(),
                                   "projectionNote": "Finite raster intrinsics centered on observed optical rays; source intrinsics/poses unchanged. Not a measured metric scale."}
        a, av = rectify_image(images[0], left, r1, rk, size, 5)
        c, cv = rectify_image(images[1], right, r2, rk, size, 5)
        dl, dr = stereo_disparities(a, c, axis, args.max_disparity, 5)
        all_points, all_colors, counts = [], [], {}
        for name, own, other, disparity, reverse, own_valid, other_valid, frame, rotation, sign in (
            ("left", a, c, dl, dr, av, cv, left, r1, 1),
            ("right", c, a, dr, dl, cv, av, right, r2, -1)):
            valid = valid_matches(disparity, reverse, own_valid, other_valid, own, other,
                                  axis, sign, args.max_disparity, args.lr_tolerance, args.photo_tolerance)
            points, y, x = depth_points(disparity, valid, rk, baseline, axis, sign)
            all_points.append(to_target(points, frame, rotation, target))
            all_colors.append(own[y, x])
            counts[name] = {"validRectifiedPixels": int(own_valid.sum()), "acceptedStereoPixels": len(points)}
        points, colors = np.concatenate(all_points), np.concatenate(all_colors)
        if not len(points):
            raise ValueError("No consistent positive-depth stereo matches")
        warped, target_depth = forward_splat(points, colors, intrinsics(target), target["w"], target["h"], args.footprint)
        if not np.count_nonzero(target_depth):
            raise ValueError("No stereo points project in front of the target camera")
        hole_mask = (target_depth == 0).astype(np.uint8) * 255
        for name, image in (("warp.png", warped), ("mask.png", hole_mask), ("rectified-left.png", a), ("rectified-right.png", c)):
            if not cv2.imwrite(str(args.output / name), image):
                raise ValueError(f"Failed to write {name}")
        np.savez_compressed(args.output / "depth-and-disparity.npz", target_depth=target_depth, left_disparity=dl, right_disparity=dr)
        report["matching"] = counts
        report["coverage"] = {"targetPixels": int(target_depth.size), "observedWarpPixels": int(np.count_nonzero(target_depth)),
                              "holePixels": int(np.count_nonzero(hole_mask)), "holeFraction": float(np.count_nonzero(hole_mask) / hole_mask.size)}
        report["outputs"] = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
                             for p in sorted(args.output.iterdir()) if p.is_file()}
        report["status"] = "PASS"
        report["statusMeaning"] = "Stereo warp executed; visual usability and held-out photometric comparison remain separate checks."
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
        (args.output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--left", default="pano_000004_view_02.png")
    parser.add_argument("--right", default="pano_000006_view_02.png")
    parser.add_argument("--target", default="pano_000005_view_02.png")
    parser.add_argument("--max-disparity", type=int, default=256)
    parser.add_argument("--rectified-scale", type=int, default=2)
    parser.add_argument("--lr-tolerance", type=float, default=1.5)
    parser.add_argument("--photo-tolerance", type=float, default=32)
    parser.add_argument("--footprint", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    def cancelled(_signum, _frame):
        raise KeyboardInterrupt("Interrupted by SIGTERM")
    previous = signal.signal(signal.SIGTERM, cancelled)
    try:
        report = run(args)
        print(json.dumps({"status": report["status"], "elapsedSeconds": report["elapsedSeconds"], "coverage": report["coverage"]}))
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
