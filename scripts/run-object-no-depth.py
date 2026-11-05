#!/usr/bin/env python3
"""Train the same nine-image scooter experiment without learned depth or fusion.

Reuse exactly the previous run's training RGB and camera matrices. Initialize
only from triangulated SfM points inside the same observed object rectangles.
No learned-depth outputs are read by this runner.
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

import numpy as np
import pycolmap

ROOT = Path(__file__).resolve().parents[1]
BOUNDS = {'frame_0000.png': [150, 177, 299, 288],
          'frame_0032.png': [50, 115, 305, 350],
          'frame_0064.png': [166, 145, 329, 341]}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source, job = args.reference.resolve(), args.output.resolve()
    job.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = dict(status='RUNNING', startedAt=datetime.now(timezone.utc).isoformat(),
                  reference=str(source), learnedDepth='NOT RUN: intentionally omitted',
                  interpolation='NOT RUN: intentionally omitted', diffusion='NOT RUN: intentionally omitted')
    try:
        dataset = job/'dataset'; dataset.mkdir()
        shutil.copytree(source/'fusion/dataset/images', dataset/'images')
        shutil.copyfile(source/'fusion/dataset/transforms.json', dataset/'transforms.json')
        shutil.copyfile(source/'augmented/sequence.json', job/'sequence.json')
        shutil.copyfile(source/'originals-contact.jpg', job/'originals-contact.jpg')
        files = sorted((dataset/'images').glob('*.png'))
        if [p.name for p in files] != [f'frame_{i*8:04d}.png' for i in range(9)]:
            raise ValueError('Expected exactly the same nine observed training images')
        report['images'] = [dict(file=p.name, sha256=sha(p),
                                referenceSha256=sha(source/'fusion/dataset/images'/p.name)) for p in files]
        report['cameraSha256'] = sha(dataset/'transforms.json')
        report['referenceCameraSha256'] = sha(source/'fusion/dataset/transforms.json')
        model = pycolmap.Reconstruction(source/'poses/dataset/sparse')
        points = list(model.points3D.values())
        xyz = np.array([p.xyz for p in points]); colors = np.array([p.color for p in points], dtype=np.uint8)
        keep = np.isfinite(xyz).all(1); clipping = []
        for image in model.images.values():
            if image.name not in BOUNDS:
                continue
            transform = image.cam_from_world().matrix()
            intrinsics = model.cameras[image.camera_id].calibration_matrix()
            b = BOUNDS[image.name]
            projected = (xyz @ transform[:, :3].T + transform[:, 3]) @ intrinsics.T
            uv = projected[:, :2] / np.maximum(projected[:, 2:], 1e-8)
            keep &= ((projected[:, 2] > 0) & (uv[:, 0] >= b[0]) & (uv[:, 0] <= b[2])
                     & (uv[:, 1] >= b[1]) & (uv[:, 1] <= b[3]))
            clipping.append(dict(file=image.name, bounds=b, worldToCamera=transform.tolist(), intrinsics=intrinsics.tolist()))
        xyz, colors = xyz[keep], colors[keep]
        if len(clipping) != 3 or len(xyz) < 4:
            raise ValueError('Object selection has insufficient triangulated points')
        data = np.empty(len(xyz), dtype=[('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('red', 'u1'), ('green', 'u1'), ('blue', 'u1')])
        for index, name in enumerate(['x', 'y', 'z']): data[name] = xyz[:, index]
        for index, name in enumerate(['red', 'green', 'blue']): data[name] = colors[:, index]
        header = f'ply\nformat binary_little_endian 1.0\nelement vertex {len(xyz)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n'
        with (dataset/'init.ply').open('wb') as handle:
            handle.write(header.encode()); data.tofile(handle)
        provenance = json.loads((source/'poses/dataset/provenance.json').read_text())
        provenance['notes'] = ('Nine real perspective crops only, exactly matching the preceding real-only training RGB and cameras. '
                               'No RIFE, diffusion, learned monocular depth, depth calibration or depth fusion. '
                               'Initialization uses image-correspondence triangulated SfM points inside the same three observed object rectangles. '
                               'Estimated cameras and arbitrary scale; no metric geometry claim.')
        write(dataset/'provenance.json', provenance)
        transforms = json.loads((dataset/'transforms.json').read_text())
        home = np.array(next(f['transform_matrix'] for f in transforms['frames'] if Path(f['file_path']).name == 'frame_0032.png'))
        center = np.median(xyz, axis=0); radius = float(np.quantile(np.linalg.norm(xyz-center, axis=1), .98))
        write(job/'cloud.json', dict(positions=xyz.reshape(-1).tolist(), colors=colors.reshape(-1).tolist(),
              center=center.tolist(), radius=radius, camera=dict(position=home[:3, 3].tolist(), up=home[:3, 1].tolist(), fov=45)))
        report.update(sfmPoints=len(points), initialPoints=len(xyz), initialPointSha256=sha(dataset/'init.ply'),
                      clipping=clipping, focus=center.tolist())
        command = [str(ROOT/'data/tools/venv/bin/python'), 'scripts/reconstruct.py', str(dataset), str(job/'training'),
                   '--steps', '5000', '--resolution', '512', '--max-splats', '150000', '--title', 'Scooter without learned depth',
                   '--id', 'scooter-nodepth-context', '--sequence', str(job/'sequence.json'), '--component-id', 'scooter-sfm']
        report['command'] = command; write(job/'ablation.json', report)
        print(f'Training from {len(xyz)} triangulated points; nine identical RGB inputs; no learned depth', flush=True)
        with (job/'training.log').open('w') as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        report['exitCode'] = result.returncode; result.check_returncode()
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=f'{type(error).__name__}: {error}')
        traceback.print_exc(); raise
    finally:
        report.update(finishedAt=datetime.now(timezone.utc).isoformat(), elapsedSeconds=time.monotonic()-started)
        write(job/'ablation.json', report)


if __name__ == '__main__': main()
