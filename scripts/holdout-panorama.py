#!/usr/bin/env python3
"""Exclude one complete panorama from RGB training, keeping honest SfM provenance.

Requires PyCOLMAP. Input: the rig estimator's dataset with COLMAP sparse model.
This does not rerun SfM without the holdout and must not be called independent
camera/geometry validation. New initialization excludes points with fewer than
two observations among retained images; remaining point colors still come from
the all-image SfM model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--panorama', required=True, help='Exact crop prefix, e.g. pano_000005')
    args = parser.parse_args()
    import pycolmap
    src, dst = args.dataset.resolve(), args.output.resolve()
    if dst.exists() or args.output.is_symlink():
        parser.error('Output exists; preserve it and use a fresh directory')
    original = (src / 'transforms.json').read_bytes()
    transforms = json.loads(original)
    prefix = args.panorama + '_view_'
    held = [f for f in transforms['frames'] if Path(f['file_path']).name.startswith(prefix)]
    train = [f for f in transforms['frames'] if f not in held]
    if not held or len(train) < 3:
        parser.error('Require a matching held-out panorama and at least three training images')
    for frame in transforms['frames']:
        relative = Path(frame['file_path'])
        if relative.is_absolute() or not (src / relative).resolve().is_relative_to(src):
            parser.error('Dataset image escapes source directory')
        if not (src / relative).is_file():
            parser.error('Dataset image missing')
    dst.mkdir(parents=True)
    report = {'status': 'RUNNING', 'panorama': args.panorama,
              'sourceTransformsSha256': hashlib.sha256(original).hexdigest(),
              'limits': 'Appearance holdout only: SfM poses and retained initialization colors use all images. '
                        'Not independent pose/geometry ground truth; no generated training pixels.'}
    try:
        for frame in train:
            target = dst / frame['file_path']; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / frame['file_path'], target)
        model = pycolmap.Reconstruction(src / 'sparse')
        retained = {i for i, image in model.images.items() if not Path(image.name).name.startswith(prefix)}
        remove = [k for k, point in model.points3D.items()
                  if sum(element.image_id in retained for element in point.track.elements) < 2]
        for key in remove:
            model.delete_point3D(key)
        model.export_PLY(dst / 'init.ply')
        transforms['frames'] = train; transforms['ply_file_path'] = 'init.ply'
        (dst / 'transforms.json').write_text(json.dumps(transforms, indent=2) + '\n')
        provenance = json.loads((src / 'provenance.json').read_text())
        provenance['notes'] = provenance.get('notes', '') + ' ' + report['limits']
        (dst / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
        for name in ('LICENSE', 'ATTRIBUTION.txt'):
            if (src / name).is_file(): shutil.copyfile(src / name, dst / name)
        report.update(status='PASS', trainingImages=len(train), heldOutImages=held,
                      initialPoints=model.num_points3D(), removedPoints=len(remove))
    except BaseException as error:
        report.update(status='FAIL', error=str(error)); raise
    finally:
        (dst / 'holdout.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'heldOutImages'}, indent=2))


if __name__ == '__main__':
    main()
