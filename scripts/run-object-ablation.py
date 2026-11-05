#!/usr/bin/env python3
"""Repeat the scooter pipeline with only the nine real crops; no interpolation or diffusion.

Reuse the exact original crops, original-only camera solution and depth predictions
from the reference job. Recompute point fusion and train a separate Gaussian world.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source, job = args.reference.resolve(), args.output.resolve()
    job.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = dict(status='RUNNING', startedAt=datetime.now(timezone.utc).isoformat(),
                  variant='real-only', reference=str(source), generation='NOT RUN: all intermediate generation and interpolation omitted',
                  reused=['originals', 'poses-real', 'depth-real'], stages=[])

    def run(name, command, env=None):
        print('Starting', name, flush=True)
        item = dict(stage=name, startedAt=datetime.now(timezone.utc).isoformat(), command=[str(x) for x in command])
        report['stages'].append(item)
        write(job/'ablation.json', report)
        before = time.monotonic()
        with (job/(name+'.log')).open('w') as log:
            result = subprocess.run(item['command'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env)
        item.update(exitCode=result.returncode, elapsedSeconds=time.monotonic()-before,
                    status='PASS' if result.returncode == 0 else 'FAIL')
        write(job/'ablation.json', report)
        result.check_returncode()
        print('Completed', name, flush=True)

    try:
        for folder in report['reused']:
            shutil.copytree(source/folder, job/folder)
        for name in ['originals-contact.jpg', 'inputs.json']:
            shutil.copyfile(source/name, job/name)
        frames = sorted((job/'originals/images').glob('*.png'))
        expected = [f'frame_{i*8:04d}.png' for i in range(9)]
        if [p.name for p in frames] != expected:
            raise ValueError('Reference must contain the exact nine original crops')
        output = job/'augmented'; (output/'images').mkdir(parents=True)
        records = []
        for image in frames:
            shutil.copyfile(image, output/'images'/image.name)
            records.append(dict(file='images/'+image.name, kind='observed',
                                sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
        provenance = json.loads((job/'originals/provenance.json').read_text())
        provenance['notes'] = ('Nine real object-centered panorama crops only. No intermediate image generation, '
                               'RIFE interpolation or diffusion is used. Original-only camera estimates and relative '
                               'depth predictions are reused from the reference job; point fusion and GS training run anew. '
                               'Analytical perspective crop intrinsics; estimated camera poses; arbitrary scale.')
        write(output/'provenance.json', provenance)
        write(output/'sequence.json', dict(frames=records, notes='Only nine observed crops in capture order. No synthetic images or camera positions.'))
        shutil.copytree(job/'poses-real', job/'poses')
        poses = json.loads((job/'poses/dataset/transforms.json').read_text())
        write(job/'poses/report.json', dict(status='PASS', operation='Reuse original-only image-estimated camera solution',
             registeredImages=[Path(f['file_path']).name for f in poses['frames']], unregisteredImages=[], reference=str(source/'poses-real')))
        write(job/'poses/dataset/provenance.json', provenance)
        shutil.copytree(job/'depth-real', job/'depth')
        depth = json.loads((job/'depth/report.json').read_text())
        by_name = {Path(record['source']).name: record for record in depth['images']}
        for record in records:
            name = Path(record['file']).name
            if by_name[name]['sourceSha256'] != record['sha256']:
                raise ValueError('Cached depth input hash differs from the real crop')
        report['inputImages'] = records
        report['originalSeedSha256'] = hashlib.sha256((job/'poses/dataset/transforms.json').read_bytes()).hexdigest()
        colmap = ROOT/'data/tools/colmap-venv/bin/python'
        run('fusion', [colmap, 'scripts/fuse-object-depth.py', job/'poses/dataset', job/'depth', job/'fusion'])
        run('training', [ROOT/'data/tools/venv/bin/python', 'scripts/reconstruct.py', job/'fusion/dataset', job/'training',
            '--steps', '5000', '--resolution', '512', '--max-splats', '150000', '--title', 'Scooter real photos only',
            '--id', 'scooter-real-context', '--sequence', output/'sequence.json', '--component-id', 'scooter-sfm'])
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=f'{type(error).__name__}: {error}')
        traceback.print_exc()
        raise
    finally:
        report.update(finishedAt=datetime.now(timezone.utc).isoformat(), elapsedSeconds=time.monotonic()-started)
        write(job/'ablation.json', report)


if __name__ == '__main__':
    main()
