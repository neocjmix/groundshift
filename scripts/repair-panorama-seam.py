#!/usr/bin/env python3
"""Equalize the left/right edge of generated equirectangular frames.

Only interior generated frames are changed. The two photographed endpoint
frames are copied byte-for-byte. This is a seam blend, not diffusion or 3D.
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
    parser.add_argument('source', type=Path, help='Completed frame sequence and report.json')
    parser.add_argument('output', type=Path)
    parser.add_argument('--band', type=int, default=64)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output already exists; use a new directory')
    from PIL import Image
    import numpy as np

    source = args.source.resolve(strict=True)
    original = json.loads((source / 'report.json').read_text())
    if original.get('encoding', {}).get('status') != 'PASS' or original.get('frameCount', 0) < 3:
        parser.error('Source must have completed encoding and at least three frames')
    count = original['frameCount']
    width, height = original['imageSize']
    if args.band < 2 or args.band > width // 8:
        parser.error('--band must be 2..width/8')
    args.output.mkdir(parents=True)
    frames = args.output / 'frames'
    frames.mkdir()
    began = time.monotonic()
    seam = []
    j = np.arange(args.band, dtype=np.float32)
    w = np.sin((j / (args.band - 1)) * np.pi / 2) ** 2
    weight = w[None, :, None]
    for index in range(count):
        src = source / 'frames' / f'frame_{index:03d}.png'
        dst = frames / src.name
        if index in (0, count - 1):
            shutil.copyfile(src, dst)
            with Image.open(dst) as image:
                pixels = np.asarray(image)
            before = after = float(np.abs(pixels[:, 0].astype(np.int16) - pixels[:, -1].astype(np.int16)).mean())
        else:
            with Image.open(src) as image:
                pixels = np.asarray(image.convert('RGB')).copy()
            if pixels.shape != (height, width, 3):
                raise ValueError(f'Unexpected frame shape: {src}')
            before = float(np.abs(pixels[:, 0].astype(np.int16) - pixels[:, -1].astype(np.int16)).mean())
            original_left = pixels[:, :args.band].astype(np.float32)
            original_right = pixels[:, -args.band:][:, ::-1].astype(np.float32)
            common = (original_left[:, :1] + original_right[:, :1]) / 2
            pixels[:, :args.band] = np.rint(common * (1 - weight) + original_left * weight).astype(np.uint8)
            pixels[:, -args.band:] = np.rint(common * (1 - weight) + original_right * weight).astype(np.uint8)[:, ::-1]
            after = float(np.abs(pixels[:, 0].astype(np.int16) - pixels[:, -1].astype(np.int16)).mean())
            Image.fromarray(pixels).save(dst, compress_level=2)
        seam.append({'frame': index, 'edgeMaeBefore': round(before, 3), 'edgeMaeAfter': round(after, 3)})
    video = args.output / 'interpolation.mp4'
    command = [args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-framerate', str(original['fps']),
               '-i', str(frames / 'frame_%03d.png'), '-c:v', 'libx264', '-preset', 'medium',
               '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)]
    encode = subprocess.run(command, capture_output=True, text=True)
    report = {'schemaVersion': 1, 'method': original['method'] + f'; generated-frame {args.band}-pixel periodic seam blend',
              'isDiffusion': False, 'cameraPosesEstimated': False,
              'createdUtc': datetime.now(timezone.utc).isoformat(), 'sourceReportSha256': digest(source / 'report.json'),
              'inputs': original['inputs'], 'model': original['model'],
              'imageSize': original['imageSize'], 'frameCount': count, 'fps': original['fps'],
              'generationSeconds': original['generationSeconds'], 'seamBandPixels': args.band,
              'postprocessSeconds': round(time.monotonic() - began, 3), 'seam': seam,
              'encoding': {'status': 'PASS' if encode.returncode == 0 else 'FAIL',
                           'exitCode': encode.returncode, 'stderr': encode.stderr[-4000:], 'command': command}}
    if encode.returncode == 0:
        report['video'] = {'file': video.name, 'bytes': video.stat().st_size, 'sha256': digest(video)}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    if encode.returncode:
        raise SystemExit(f'FFmpeg failed; details in {args.output / "report.json"}')
    print(json.dumps({'frameCount': count, 'seamBandPixels': args.band,
                      'midpointSeam': seam[count // 2], 'video': report['video']}, indent=2))


if __name__ == '__main__':
    main()
