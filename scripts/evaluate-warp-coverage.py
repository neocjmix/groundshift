#!/usr/bin/env python3
"""Compare two geometric warps against a real held-out RGB image after generation.

The reference is read only by this evaluator. Coverage, photometric error and
visual/3D quality are distinct; this script makes no quality acceptance claim.
Run with the local NumPy/OpenCV environment.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time


def load_rgb(path):
    import cv2
    import numpy as np
    raw = path.read_bytes()
    value = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if value is None or value.ndim != 3 or value.shape[2] != 3:
        raise ValueError(f'Expected RGB image: {path}')
    return value, {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def load_known(path, shape):
    import cv2
    import numpy as np
    raw = path.read_bytes()
    value = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if value is None or value.shape != shape or not np.all((value == 0) | (value == 255)):
        raise ValueError(f'Expected binary mask of matching dimensions: {path}')
    return value == 0, {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def error(reference, candidate, support):
    import numpy as np
    count = int(np.count_nonzero(support))
    if count == 0:
        return {'pixels': 0, 'mae255': None, 'psnrDb': None}
    delta = reference[support].astype(np.float64) - candidate[support].astype(np.float64)
    mse = float(np.mean(delta * delta))
    return {'pixels': count, 'mae255': float(np.mean(np.abs(delta))),
            'psnrDb': None if mse == 0 else float(10 * math.log10(255 * 255 / mse))}


def evaluate(reference, stereo, learned, output):
    import numpy as np
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be a new directory')
    output.mkdir(parents=True)
    started = time.monotonic()
    result = {'schemaVersion': 1, 'status': 'RUNNING',
              'createdAt': datetime.now(timezone.utc).isoformat(),
              'scope': 'Held-out RGB photometric diagnostic. The target RGB was not available to the warp commands. Poses and sparse calibration used all-image SfM, so this is not an independent geometry test.',
              'inputs': {}, 'variants': {}}
    try:
        target, result['inputs']['reference'] = load_rgb(reference)
        variants = {
            'stereo': (stereo / 'warp.png', stereo / 'mask.png'),
            'learnedRaw': (learned / 'warp.png', learned / 'mask.png'),
            'learnedSourceConsistent': (learned / 'warp-consistent.png', learned / 'mask-consistent.png'),
        }
        loaded = {}
        for name, (image_path, mask_path) in variants.items():
            image, image_info = load_rgb(image_path)
            if image.shape != target.shape:
                raise ValueError(f'Image size differs for {name}')
            support, mask_info = load_known(mask_path, target.shape[:2])
            loaded[name] = (image, support)
            result['inputs'][name] = {'image': image_info, 'mask': mask_info}
            result['variants'][name] = {
                'projectedSourcePixels': int(np.count_nonzero(support)),
                'projectedSourceFraction': float(np.mean(support)),
                'onOwnSupport': error(target, image, support),
                'fullBlackUnknownCanvas': error(target, image, np.ones(support.shape, dtype=bool)),
            }
        stereo_support = loaded['stereo'][1]
        for name in ('learnedRaw', 'learnedSourceConsistent'):
            candidate, candidate_support = loaded[name]
            common = stereo_support & candidate_support
            gained = candidate_support & ~stereo_support
            result['variants'][name]['vsStereo'] = {
                'commonPixels': int(np.count_nonzero(common)),
                'stereoOnCommon': error(target, loaded['stereo'][0], common),
                'learnedOnCommon': error(target, candidate, common),
                'learnedOnlyPixels': int(np.count_nonzero(gained)),
                'learnedOnlyError': error(target, candidate, gained),
            }
        result['status'] = 'PASS'
        result['statusMeaning'] = 'Coverage and pixel error measured; pass does not imply better geometry or accepted visual quality.'
    except Exception as exc:
        result['status'] = 'FAIL'
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        result['elapsedSeconds'] = time.monotonic() - started
        (output / 'report.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('stereo', type=Path)
    parser.add_argument('learned', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.reference, args.stereo, args.learned, args.output)
    except Exception as exc:
        parser.exit(1, f'FAIL: {exc}\n')
    print(json.dumps({'status': result['status'], 'variants': result['variants']}, allow_nan=False))


if __name__ == '__main__':
    main()
