#!/usr/bin/env python3
"""Assemble actual matched codec renders for inspection; no image generation."""
import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageChops, ImageDraw


def label(image, text):
    out = Image.new('RGB', (image.width, image.height + 36), '#17242d')
    out.paste(image, (0, 36))
    ImageDraw.Draw(out).text((12, 8), text, fill='white', font_size=19)
    return out


def triplet(root, frame, crop=None):
    a = Image.open(root / 'ply' / (frame + '.png')).convert('RGB')
    b = Image.open(root / 'spz' / (frame + '.png')).convert('RGB')
    if crop:
        a, b = a.crop(crop), b.crop(crop)
    diff = ImageChops.difference(a, b).point(lambda value: min(255, value * 8))
    items = [label(a, 'Original PLY'), label(b, 'SPZ v3 - same camera'), label(diff, 'Absolute RGB difference x8')]
    out = Image.new('RGB', (a.width * 3, a.height + 36))
    for i, image in enumerate(items):
        out.paste(image, (i * a.width, 0))
    return out


def main(args):
    args.output.mkdir(exist_ok=False)
    root = args.comparison / 'renders'
    config = json.loads((args.comparison / 'config.json').read_text())
    panels = []
    for frame, title, crop in [
        ('held-5-level-300', 'Same camera: street overview', None),
        ('held-5-level-000', 'Same camera: facade and thin structures', None),
        ('held-5-level-300', 'Native pixel crop: railing and branches', (480, 160, 992, 672)),
        ('display-120-pitch80', 'Near-pole display view', None),
    ]:
        image = triplet(root, frame, crop)
        name = 'comparison-' + str(len(panels)) + '.jpg'
        image.save(args.output / name, quality=94)
        panels.append(dict(title=title, image='./' + name, caption='Left PLY, center SPZ, right absolute per-channel difference multiplied by8. Same actual1024px Chrome render; crop is not upscaled. This does not compare against independent geometry.'))
    preview = Image.open(root / 'spz/held-5-level-300.png').convert('RGB')
    preview.thumbnail((640, 400))
    preview.save(args.output / 'preview.jpg', quality=91)
    frames = args.output / 'motion-frames'
    frames.mkdir()
    path_cameras = [c for c in config['cameras'] if c['kind'] == 'path']
    for i, camera in enumerate(path_cameras):
        pair = Image.new('RGB', (1280, 676), '#17242d')
        for column, key in enumerate(['ply', 'spz']):
            image = Image.open(root / key / (camera['id'] + '.png')).convert('RGB').resize((640, 640))
            pair.paste(label(image, 'Original PLY' if key == 'ply' else 'SPZ v3 - same camera'), (column * 640, 0))
        pair.save(frames / f'{i:04d}.jpg', quality=92)
    subprocess.run([args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-n', '-framerate', '10', '-i', str(frames / '%04d.jpg'),
                    '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(args.output / 'motion.mp4')], check=True)
    (args.output / 'panels.json').write_text(json.dumps(dict(comparisons=panels, video='./motion.mp4', frames=len(path_cameras)), indent=2) + '\n')
    print(json.dumps(dict(status='PASS', panels=len(panels), motionFrames=len(path_cameras))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('comparison', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    main(parser.parse_args())
