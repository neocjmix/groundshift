#!/usr/bin/env python3
"""Calibrate two observed relative-depth maps to sparse SfM and warp real RGB.

The target image is NEVER opened. Its camera metadata comes from all-image SfM,
so this is an appearance holdout, not independent camera/geometry validation.
Run with the local PyCOLMAP environment plus Pillow and NumPy.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time
import traceback


ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stereo_helpers():
    spec = importlib.util.spec_from_file_location('groundshift_stereo', ROOT / 'scripts/warp-panorama-gap.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bilinear(array, x, y):
    import numpy as np
    height, width = array.shape
    if not (0 <= x <= width - 1 and 0 <= y <= height - 1):
        return None
    x0, y0 = int(x), int(y)
    x1, y1 = min(x0 + 1, width - 1), min(y0 + 1, height - 1)
    wx, wy = x - x0, y - y0
    return float((1 - wx) * (1 - wy) * array[y0, x0] +
                 wx * (1 - wy) * array[y0, x1] +
                 (1 - wx) * wy * array[y1, x0] + wx * wy * array[y1, x1])


def sparse_pairs(reconstruction, image, prediction):
    import numpy as np
    rows = []
    for observation in image.points2D:
        if not observation.has_point3D():
            continue
        point = reconstruction.points3D[observation.point3D_id]
        z = float((image.cam_from_world() * point.xyz)[2])
        if z <= 0 or not np.isfinite(z):
            continue
        # SfM uses corner-origin coordinates: first array cell is at 0.5, 0.5.
        value = bilinear(prediction, float(observation.xy[0]) - 0.5,
                         float(observation.xy[1]) - 0.5)
        if value is not None and np.isfinite(value):
            rows.append((value, 1 / z, int(observation.point3D_id)))
    if len(rows) < 50:
        raise ValueError(f'Too few sparse depth pairs: {image.name} ({len(rows)})')
    return np.asarray(rows, dtype=np.float64)


def robust_affine(x, y):
    """Huber IRLS: SfM inverse-Z = a * model relative depth + b."""
    import numpy as np
    if len(x) < 30 or len(x) != len(y) or not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError('Need at least 30 finite calibration pairs')
    design = np.column_stack((x, np.ones(len(x))))
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    for _ in range(20):
        residual = y - design @ beta
        centered = residual - np.median(residual)
        sigma = max(float(1.4826 * np.median(np.abs(centered))), 1e-6)
        weights = np.minimum(1.0, 1.345 * sigma / np.maximum(np.abs(residual), 1e-12))
        scaled = np.sqrt(weights)
        updated = np.linalg.lstsq(design * scaled[:, None], y * scaled, rcond=None)[0]
        if np.max(np.abs(updated - beta)) < 1e-10:
            beta = updated
            break
        beta = updated
    if beta[0] <= 0 or not np.all(np.isfinite(beta)):
        raise ValueError('Learned-depth scale must be finite and positive')
    return beta


def calibrated_depth(prediction, beta):
    import numpy as np
    inverse = beta[0] * prediction.astype(np.float64) + beta[1]
    valid = np.isfinite(inverse) & (inverse > 1e-6)
    depth = np.zeros(prediction.shape, dtype=np.float32)
    depth[valid] = (1 / inverse[valid]).astype(np.float32)
    return depth


def backproject_to_target(depth, source_frame, target_frame, helpers):
    import numpy as np
    height, width = depth.shape
    y, x = np.nonzero(depth > 0)
    z = depth[y, x].astype(np.float64)
    k = helpers.intrinsics(source_frame)
    source_points = np.column_stack(((x - k[0, 2]) * z / k[0, 0],
                                     (y - k[1, 2]) * z / k[1, 1], z))
    target_from_source = np.linalg.inv(helpers.camera(target_frame)) @ helpers.camera(source_frame)
    target_points = source_points @ target_from_source[:3, :3].T + target_from_source[:3, 3]
    return target_points, y, x


def run(args):
    import numpy as np
    import pycolmap
    from PIL import Image

    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Output must be a new directory')
    args.output.mkdir(parents=True)
    started = time.monotonic()
    report = {
        'schemaVersion': 1, 'status': 'RUNNING',
        'startedAt': datetime.now(timezone.utc).isoformat(),
        'scope': 'Observed source RGB only; per-image relative inverse-depth calibrated to all-image SfM sparse points. Target RGB is not read. This is an appearance holdout, not metric or independent geometry truth.',
        'targetImagePixelsRead': False,
        'calibration': 'Huber IRLS affine inverse-camera-Z fit, separately per source image; deterministic 20% sparse-point internal holdout',
        'inputs': {}, 'sources': [],
    }

    def save():
        (args.output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')

    save()
    try:
        depth_report_path = args.inference / 'report.json'
        depth_report = json.loads(depth_report_path.read_text())
        if depth_report.get('status') != 'PASS' or depth_report.get('device') != 'mps':
            raise ValueError('Require successful locally inferred MPS depth maps')
        dataset_path = args.dataset / 'transforms.json'
        dataset = json.loads(dataset_path.read_text())
        if dataset.get('camera_model') != 'PINHOLE':
            raise ValueError('Require PINHOLE camera dataset')
        frames = {Path(row['file_path']).name: row for row in dataset['frames']}
        names = (args.left, args.right, args.target)
        if len(set(names)) != 3 or any(name not in frames for name in names):
            raise ValueError('Require distinct source and target cameras in dataset')
        helpers = stereo_helpers()
        for name in names:
            helpers.camera(frames[name])
            helpers.intrinsics(frames[name])
        reconstruction = pycolmap.Reconstruction(args.sparse)
        sfm_images = {image.name: image for image in reconstruction.images.values()}
        inferred = {Path(item['source']).name: (index, item)
                    for index, item in enumerate(depth_report['images'])}
        report['inputs'] = {
            'depthReportSha256': sha256(depth_report_path),
            'transformsSha256': sha256(dataset_path),
            'targetCamera': args.target,
            'sourceCameras': [args.left, args.right],
            'sparseModel': str(args.sparse),
        }
        report['targetCamera'] = frames[args.target]
        report['cameras'] = {'target': frames[args.target]}
        colors_and_points = []
        for name in (args.left, args.right):
            if name not in inferred or name not in sfm_images:
                raise ValueError(f'Missing depth or SfM image: {name}')
            index, item = inferred[name]
            source_path = (args.dataset / frames[name]['file_path']).resolve()
            if source_path != Path(item['source']).resolve() or not source_path.is_relative_to(args.dataset.resolve()):
                raise ValueError(f'Depth prediction does not match source dataset: {name}')
            if sha256(source_path) != item['sourceSha256']:
                raise ValueError(f'Source RGB hash mismatch: {name}')
            prediction_path = args.inference / f'view-{index:02d}-relative.npy'
            if sha256(prediction_path) != item['relativeNpySha256']:
                raise ValueError(f'Depth array hash mismatch: {name}')
            prediction = np.load(prediction_path, allow_pickle=False)
            if prediction.shape != (frames[name]['h'], frames[name]['w']) or not np.isfinite(prediction).all():
                raise ValueError(f'Invalid depth dimensions/values: {name}')
            pairs = sparse_pairs(reconstruction, sfm_images[name], prediction)
            fit = pairs[:, 2].astype(np.int64) % 5 != 0
            if min(np.count_nonzero(fit), np.count_nonzero(~fit)) < 30:
                raise ValueError(f'Insufficient deterministic calibration split: {name}')
            held_beta = robust_affine(pairs[fit, 0], pairs[fit, 1])
            held_error = np.abs(held_beta[0] * pairs[~fit, 0] + held_beta[1] - pairs[~fit, 1])
            beta = robust_affine(pairs[:, 0], pairs[:, 1])
            depth = calibrated_depth(prediction, beta)
            with Image.open(source_path) as image:
                rgb = np.asarray(image.convert('RGB'))
            if rgb.shape != (*depth.shape, 3):
                raise ValueError(f'RGB/depth size mismatch: {name}')
            points, y, x = backproject_to_target(depth, frames[name], frames[args.target], helpers)
            bgr = rgb[y, x, ::-1].copy()
            warped, target_depth = helpers.forward_splat(points, bgr,
                helpers.intrinsics(frames[args.target]), frames[args.target]['w'], frames[args.target]['h'], 2)
            Image.fromarray(warped[:, :, ::-1]).save(args.output / f'{name}-warp.png')
            np.save(args.output / f'{name}-calibrated-z.npy', depth)
            colors_and_points.append((warped, target_depth))
            report['sources'].append({
                'name': name, 'sourceSha256': item['sourceSha256'],
                'predictionSha256': item['relativeNpySha256'],
                'sparsePairs': len(pairs), 'fitPairs': int(np.count_nonzero(fit)),
                'internalHoldoutPairs': int(np.count_nonzero(~fit)),
                'internalHoldoutMedianAbsInverseZError': float(np.median(held_error)),
                'inverseZPerRelativeUnit': float(beta[0]),
                'inverseZIntercept': float(beta[1]),
                'positiveCalibratedDepthFraction': float(np.mean(depth > 0)),
                'sourceWarpPixels': int(np.count_nonzero(target_depth)),
            })
        (left_rgb, left_z), (right_rgb, right_z) = colors_and_points
        left_valid, right_valid = left_z > 0, right_z > 0
        choose_left = left_valid & (~right_valid | (left_z <= right_z))
        choose_right = right_valid & ~choose_left
        result = np.zeros_like(left_rgb)
        result[choose_left] = left_rgb[choose_left]
        result[choose_right] = right_rgb[choose_right]
        target_z = np.where(choose_left, left_z, np.where(choose_right, right_z, 0))
        mask = np.where(target_z > 0, 0, 255).astype(np.uint8)
        overlap = left_valid & right_valid
        conflict = np.zeros_like(mask)
        agreement = np.zeros_like(left_valid)
        if np.any(overlap):
            relative_z_error = np.abs(left_z[overlap] - right_z[overlap]) / np.maximum(np.minimum(left_z[overlap], right_z[overlap]), 1e-6)
            rgb_error = np.mean(np.abs(left_rgb[overlap].astype(np.int16) - right_rgb[overlap].astype(np.int16)), axis=1)
            conflict[overlap] = np.where(relative_z_error > 0.2, 255, 0).astype(np.uint8)
            # The 32/255 color tolerance matches the existing SGBM consistency
            # test. This is a source-to-source check; target RGB is not used.
            agreement[overlap] = (relative_z_error <= 0.2) & (rgb_error <= 32)
            report['overlap'] = {
                'pixels': int(np.count_nonzero(overlap)),
                'medianRelativeDepthDisagreement': float(np.median(relative_z_error)),
                'fractionDepthDisagreementOver20Percent': float(np.mean(relative_z_error > 0.2)),
                'medianRgbMae255': float(np.median(rgb_error)),
                'agreementPixelsAt20PercentDepthAnd32RgbMae': int(np.count_nonzero(agreement)),
            }
        else:
            report['overlap'] = {'pixels': 0}
        conservative = (left_valid ^ right_valid) | agreement
        consistent_rgb = result.copy()
        consistent_rgb[~conservative] = 0
        consistent_mask = np.where(conservative, 0, 255).astype(np.uint8)
        Image.fromarray(result[:, :, ::-1]).save(args.output / 'warp.png')
        Image.fromarray(mask).save(args.output / 'mask.png')
        Image.fromarray(conflict).save(args.output / 'conflict-mask.png')
        Image.fromarray(consistent_rgb[:, :, ::-1]).save(args.output / 'warp-consistent.png')
        Image.fromarray(consistent_mask).save(args.output / 'mask-consistent.png')
        np.save(args.output / 'target-depth.npy', target_z)
        report['coverage'] = {
            'targetPixels': int(target_z.size),
            'projectedSourcePixels': int(np.count_nonzero(target_z)),
            'projectedSourceFraction': float(np.mean(target_z > 0)),
            'holePixels': int(np.count_nonzero(mask)),
            'sourceConsistentPixels': int(np.count_nonzero(conservative)),
            'sourceConsistentFraction': float(np.mean(conservative)),
            'consistencyRule': 'Keep a singly projected source pixel; if both sources project here, require relative target-Z difference <= 20% and their RGB MAE <= 32/255. Reject other overlapping pixels; no target RGB is read.',
        }
        report['outputs'] = {p.name: {'sha256': sha256(p), 'bytes': p.stat().st_size}
                             for p in sorted(args.output.iterdir()) if p.is_file() and p.name != 'report.json'}
        report['status'] = 'PASS'
        report['statusMeaning'] = 'Depth calibration and observed-pixel warp executed; photometric accuracy, novel geometry and GS benefit require separate evaluation.'
    except KeyboardInterrupt as error:
        report['status'] = 'CANCELLED'
        report['error'] = str(error) or 'Interrupted'
        report['traceback'] = traceback.format_exc()
        raise
    except Exception as error:
        report['status'] = 'FAIL'
        report['error'] = f'{type(error).__name__}: {error}'
        report['traceback'] = traceback.format_exc()
        raise
    finally:
        report['elapsedSeconds'] = time.monotonic() - started
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inference', type=Path)
    parser.add_argument('sparse', type=Path)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--left', default='pano_000004_view_02.png')
    parser.add_argument('--right', default='pano_000006_view_02.png')
    parser.add_argument('--target', default='pano_000005_view_02.png')
    args = parser.parse_args()
    previous = signal.signal(signal.SIGTERM, lambda _sig, _frame: (_ for _ in ()).throw(KeyboardInterrupt('Interrupted by SIGTERM')))
    try:
        report = run(args)
        print(json.dumps({'status': report['status'], 'elapsedSeconds': report['elapsedSeconds'],
                          'coverage': report['coverage'], 'overlap': report['overlap']}))
    except KeyboardInterrupt as error:
        print(f'CANCELLED: {error}', file=sys.stderr)
        return 130
    except Exception as error:
        print(f'FAIL: {error}', file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
