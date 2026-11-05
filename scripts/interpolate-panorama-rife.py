#!/usr/bin/env python3
"""Create a reproducible 360° frame-interpolation control on Apple MLX.

This is optical-flow interpolation, not diffusion or camera-pose estimation.
The two input images must be aligned 2:1 equirectangular panoramas. A wrapped
horizontal margin gives RIFE periodic context at the panorama seam.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path)
    parser.add_argument('last', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--levels', type=int, default=6)
    parser.add_argument('--wrap', type=int, default=128)
    parser.add_argument('--scale', type=float, default=0.5)
    parser.add_argument('--fps', type=int, default=24)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    if not 1 <= args.levels <= 8:
        parser.error('--levels must be 1..8')
    if args.wrap < 0 or args.wrap % 32:
        parser.error('--wrap must be nonnegative and divisible by 32')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output already exists; use a fresh directory')

    import numpy as np
    from PIL import Image
    import mlx.core as mx
    from rife_mlx.pipeline_mlx import interpolate_pair
    from rife_mlx.utils.weights import build_model

    sources = []
    for path in (args.first, args.last):
        path = path.resolve(strict=True)
        with Image.open(path) as image:
            if image.mode != 'RGB' or image.width != 2 * image.height:
                parser.error(f'Expected 2:1 RGB equirectangular image: {path}')
            sources.append((path, np.asarray(image).copy()))
    if sources[0][1].shape != sources[1][1].shape:
        parser.error('Input sizes differ')
    height, width = sources[0][1].shape[:2]
    if args.wrap >= width // 4:
        parser.error('--wrap must be less than 1/4 of panorama width')
    if args.weights.is_dir() is False:
        parser.error('Local RIFE weights directory missing')
    model = build_model('4.25', weights_dir=str(args.weights.resolve()))
    args.output.mkdir(parents=True)
    frames_dir = args.output / 'frames'
    frames_dir.mkdir()
    last_index = 2 ** args.levels
    images = {0: sources[0][1], last_index: sources[1][1]}
    timings = []
    started = time.monotonic()

    def infer(left, right):
        if args.wrap:
            left = np.concatenate((left[:, -args.wrap:], left, left[:, :args.wrap]), axis=1)
            right = np.concatenate((right[:, -args.wrap:], right, right[:, :args.wrap]), axis=1)
        result = interpolate_pair(model, left, right, 0.5, args.scale)
        if args.wrap:
            result = result[:, args.wrap:-args.wrap]
        return result

    for level in range(1, args.levels + 1):
        stride = 2 ** (args.levels - level)
        for index in range(stride, last_index, 2 * stride):
            tick = time.monotonic()
            images[index] = infer(images[index - stride], images[index + stride])
            seconds = round(time.monotonic() - tick, 3)
            timings.append({'frame': index, 'level': level, 'seconds': seconds})
            print(f'frame {index:03d}/{last_index:03d} level {level} {seconds:.3f}s', flush=True)

    for index in range(last_index + 1):
        target = frames_dir / f'frame_{index:03d}.png'
        if index in (0, last_index):
            shutil.copyfile(sources[0 if index == 0 else 1][0], target)
        else:
            Image.fromarray(images[index]).save(target, compress_level=2)
        del images[index]

    video = args.output / 'interpolation.mp4'
    command = [args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-framerate', str(args.fps),
               '-i', str(frames_dir / 'frame_%03d.png'), '-c:v', 'libx264', '-preset', 'medium',
               '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)]
    encode = subprocess.run(command, capture_output=True, text=True)
    report = {
        'schemaVersion': 1, 'method': 'Practical-RIFE 4.25 via MLX; recursive midpoint interpolation',
        'isDiffusion': False, 'cameraPosesEstimated': False,
        'createdUtc': datetime.now(timezone.utc).isoformat(),
        'inputs': [{'file': p.name, 'sha256': digest(p)} for p, _ in sources],
        'model': {'repo': 'mlx-community/RIFE-4.25', 'revision': '6b650eaa5664aab280119511fe944861491aa15e',
                  'weightsSha256': digest(args.weights / 'model.safetensors')},
        'imageSize': [width, height], 'frameCount': last_index + 1,
        'wrapPixels': args.wrap, 'scale': args.scale, 'fps': args.fps,
        'generationSeconds': round(sum(t['seconds'] for t in timings), 3),
        'totalSeconds': round(time.monotonic() - started, 3),
        'timings': timings,
        'encoding': {'status': 'PASS' if encode.returncode == 0 else 'FAIL',
                     'exitCode': encode.returncode, 'stderr': encode.stderr[-4000:],
                     'command': command},
    }
    if encode.returncode == 0:
        report['video'] = {'file': video.name, 'bytes': video.stat().st_size, 'sha256': digest(video)}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    if encode.returncode:
        raise SystemExit(f'FFmpeg failed; details in {args.output / "report.json"}')
    print(json.dumps({k: report[k] for k in ('frameCount', 'generationSeconds', 'totalSeconds', 'video')}, indent=2))


if __name__ == '__main__':
    main()
