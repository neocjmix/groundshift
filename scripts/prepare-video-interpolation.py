#!/usr/bin/env python3
"""Prepare two explicit equirectangular images for a local video experiment.

This only resizes and records provenance. It does not invent camera motion,
sample generated frames, or touch the held-out target photograph.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


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
    parser.add_argument('--width', type=int, default=2048)
    args = parser.parse_args()
    if args.width < 512 or args.width > 4096 or args.width % 64:
        parser.error('Width must be 512..4096 and divisible by 64')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output already exists; use a new directory')
    from PIL import Image
    inputs = []
    for path in (args.first, args.last):
        path = path.resolve(strict=True)
        with Image.open(path) as image:
            if image.mode != 'RGB' or image.width != 2 * image.height:
                parser.error(f'Expected upright 2:1 RGB panorama: {path}')
            inputs.append((path, image.size, digest(path)))
    args.output.mkdir(parents=True)
    files = []
    for name, (path, size, source_sha) in zip(('first', 'last'), inputs, strict=True):
        with Image.open(path) as image:
            resized = image.resize((args.width, args.width // 2), Image.Resampling.LANCZOS)
            target = args.output / f'{name}.png'
            resized.save(target, format='PNG', optimize=True)
        files.append({'role': name, 'source': str(path), 'sourceSize': size,
                      'sourceSha256': source_sha, 'prepared': target.name,
                      'preparedSize': [args.width, args.width // 2],
                      'preparedSha256': digest(target)})
    report = {'schemaVersion': 1, 'status': 'PASS',
              'operation': 'equirectangular-video-input-preparation',
              'time': datetime.now(timezone.utc).isoformat(),
              'method': 'Lanczos resize, no pixel synthesis or yaw adjustment',
              'heldOutTargetPixelsRead': False, 'inputs': files}
    (args.output / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
