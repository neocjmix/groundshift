#!/usr/bin/env python3
"""Reproduce labeled sheets from the completed matched tangent experiment."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw


def review(job, output=None):
    config = json.loads((job / 'render-config.json').read_text())
    cameras = {row['id']: row for row in config['cameras']}
    detail = json.loads((job / 'render-config-detail.json').read_text())
    detail_cameras = {row['id']: row for row in detail['cameras']}
    output = output or job / 'visual-review'
    output.mkdir(exist_ok=False)
    sets = [
        ('held-512', ['held-5-level-' + v for v in ['000', '060', '120', '180', '240', '300']], ['reference', 'baseline', 'tangent'], 256),
        ('route', ['path-' + str(v).zfill(3) for v in [0, 8, 16, 24, 32, 40, 48]], ['baseline', 'tangent'], 256),
        ('offpath', ['offpath-left', 'offpath-right'], ['baseline', 'tangent'], 384),
    ]
    for name, ids, models, size in sets:
        canvas = Image.new('RGB', (size * len(ids), (size + 24) * len(models)), (24, 29, 35))
        draw = ImageDraw.Draw(canvas)
        for row, model in enumerate(models):
            for column, ident in enumerate(ids):
                source = Path(cameras[ident]['reference']) if model == 'reference' else job / 'renders' / model / (ident + '.png')
                image = Image.open(source).convert('RGB').resize((size, size), Image.Resampling.LANCZOS)
                canvas.paste(image, (column * size, row * (size + 24) + 24))
                draw.text((column * size + 4, row * (size + 24) + 4), model + ' / ' + ident, fill='white')
        canvas.save(output / (name + '.jpg'), quality=93)
    ids = ['held-5-level-000', 'held-5-level-180', 'held-5-level-300']
    boxes = [(256, 256, 768, 768), (128, 256, 640, 768), (256, 128, 768, 640)]
    canvas = Image.new('RGB', (1536, 1620), (24, 29, 35))
    draw = ImageDraw.Draw(canvas)
    for row, model in enumerate(['reference', 'baseline', 'tangent']):
        for column, (ident, box) in enumerate(zip(ids, boxes)):
            source = Path(detail_cameras[ident]['reference']) if model == 'reference' else job / 'renders-detail' / model / (ident + '.png')
            image = Image.open(source).convert('RGB')
            if image.size != (1024, 1024):
                raise ValueError('Require actual 1024 output/reference; do not upsample detail')
            canvas.paste(image.crop(box), (column * 512, row * 540 + 28))
            draw.text((column * 512 + 4, row * 540 + 5), model + ' / ' + ident + ' / native1024 angular patch', fill='white')
    canvas.save(output / 'detail-1024.jpg', quality=95)
    print('Actual six-direction / seven-route / two-offpath / three-detail comparison sheets; geometry NOT ACCEPTED.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path)
    parser.add_argument('--output', type=Path, help='Fresh output directory; default JOB/visual-review')
    args = parser.parse_args()
    review(args.job.resolve(), args.output.resolve() if args.output else None)
