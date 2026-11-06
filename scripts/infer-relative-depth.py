#!/usr/bin/env python3
"""Run a pinned relative-depth model on selected local perspective crops.

This is a diagnostic only. Output is neither metric depth nor verified 3D.
Run with the locally installed PyTorch/Transformers environment and HF_HOME.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time


MODEL = 'depth-anything/Depth-Anything-V2-Small-hf'
REVISION = '5426e4f0f36572d16453bbda7a8389317b1bef99'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('images', nargs='+', type=Path)
    parser.add_argument('--input-size', type=int, help='Explicit neural input edge, multiple14; historical default remains unchanged')
    args = parser.parse_args()
    if args.input_size is not None and (args.input_size<14 or args.input_size>1400 or args.input_size%14):
        parser.error('input-size must be a multiple14 from14 through1400')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output already exists; prior evidence is never overwritten')
    for image in args.images:
        if not image.is_file() or image.is_symlink():
            parser.error(f'Missing or symlink input: {image}')
    args.output.mkdir(parents=True)

    import numpy as np
    from PIL import Image
    import torch
    from transformers import pipeline

    if not torch.backends.mps.is_available():
        parser.error('Apple MPS unavailable; this experiment requires local Metal inference')
    started = time.monotonic()
    report = {
        'schemaVersion': 1,
        'status': 'RUNNING',
        'startedAt': datetime.now(timezone.utc).isoformat(),
        'device': 'mps',
        'model': MODEL,
        'revision': REVISION,
        'torchVersion': torch.__version__,
        'outputMeaning': 'Relative inverse-depth-like prediction; not meters, calibrated distance, measured depth or a reconstructed world',
        'images': [],
    }

    def save():
        (args.output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')

    save()
    try:
        pipe = pipeline('depth-estimation', model=MODEL, revision=REVISION, device='mps')
        if args.input_size is not None:
            pipe.image_processor.size={'height':args.input_size,'width':args.input_size}
        report['requestedInputSize']=args.input_size
        observed=[]
        def observe(_module, positional, keyword):
            tensor=keyword.get('pixel_values',positional[0] if positional else None)
            if tensor is not None:observed.append(list(tensor.shape))
        hook=pipe.model.register_forward_pre_hook(observe,with_kwargs=True)
        report['modelLoadSeconds'] = time.monotonic() - started
        for index, source in enumerate(args.images):
            with Image.open(source) as loaded:
                rgb = loaded.convert('RGB')
            before = time.monotonic()
            result = pipe(rgb)
            torch.mps.synchronize()
            seconds = time.monotonic() - before
            depth = result['predicted_depth'].squeeze().detach().cpu().numpy().astype(np.float32)
            if depth.shape != (rgb.height, rgb.width) or not np.isfinite(depth).all() or depth.max() <= depth.min():
                raise ValueError(f'Invalid depth prediction for {source}')
            stem = f'view-{index:02d}'
            np.save(args.output / f'{stem}-relative.npy', depth)
            display = ((depth - depth.min()) / (depth.max() - depth.min()) * 255).clip(0, 255).astype(np.uint8)
            Image.fromarray(display).save(args.output / f'{stem}-visual.png')
            rgb.save(args.output / f'{stem}-source.png')
            report['images'].append({
                'source': str(source),
                'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'size': [rgb.width, rgb.height],
                'actualModelTensorShape': observed[-1] if observed else None,
                'inferenceSeconds': seconds,
                'predictionMin': float(depth.min()),
                'predictionMax': float(depth.max()),
                'relativeNpySha256': hashlib.sha256((args.output / f'{stem}-relative.npy').read_bytes()).hexdigest(),
                'visualSha256': hashlib.sha256((args.output / f'{stem}-visual.png').read_bytes()).hexdigest(),
            })
            save()
        hook.remove()
        report['status'] = 'PASS'
    except Exception as error:
        report['status'] = 'FAIL'
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        report['elapsedSeconds'] = time.monotonic() - started
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        save()


if __name__ == '__main__':
    main()
