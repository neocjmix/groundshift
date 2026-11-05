#!/usr/bin/env python3
"""Add one generated panorama at an existing, measured target rig pose.

This is an appearance experiment. The six camera matrices are copied from
all-image SfM of the held-out real panorama; the generated image did not
produce or validate those poses. The held-out photo pixels are never read.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time
import traceback


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parent
RECONSTRUCT = load_module('reconstruct', ROOT / 'reconstruct.py')
PANORAMA = load_module('prepare_panoramas', ROOT / 'prepare-panoramas.py')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('real_dataset', type=Path, help='48-view dataset without the target RGB')
    parser.add_argument('all_image_poses', type=Path, help='54-view transforms.json with measured target rig pose')
    parser.add_argument('generated_panorama', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--target', required=True, help='Six-view prefix, e.g. pano_000006')
    parser.add_argument('--generation-report', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output already exists; use a fresh directory')
    import cv2
    import numpy as np
    from PIL import Image

    real = args.real_dataset.resolve(strict=True)
    full = args.all_image_poses.resolve(strict=True)
    generated = args.generated_panorama.resolve(strict=True)
    report_path = args.generation_report.resolve(strict=True)
    output = args.output.resolve()
    if any(output.is_relative_to(p) for p in (real, full, generated.parent)):
        parser.error('Output must be separate from all inputs')
    generation = json.loads(report_path.read_text())
    source_entry = generation.get('video')
    if generation.get('encoding', {}).get('status') != 'PASS' or not source_entry:
        parser.error('Generation report must show successful video encoding')
    index = 2 ** int(round((generation['frameCount'] - 1).bit_length() - 1)) // 2
    expected_name = f'frame_{index:03d}.png'
    if generated.name != expected_name or generated.parent.name != 'frames' or generated.parent.parent != report_path.parent:
        parser.error(f'Generated panorama must be the midpoint {expected_name} of this report')
    report = {'schemaVersion': 1, 'status': 'RUNNING', 'operation': 'interpolated-panorama-training-view',
              'startedAt': datetime.now(timezone.utc).isoformat(), 'target': args.target,
              'heldOutRealPixelsRead': False, 'poseMeaning':
              'Six all-image SfM camera matrices copied from the held-out real rig; generated pixels did not estimate these poses. Appearance may not correspond to the measured center.'}
    output.mkdir(parents=True)
    began = time.monotonic()
    try:
        transforms, provenance = RECONSTRUCT.validate_dataset(real)
        all_poses = json.loads((full / 'transforms.json').read_text())
        target_frames = [f for f in all_poses['frames'] if Path(f['file_path']).stem.startswith(args.target + '_view_')]
        if len(target_frames) != 6 or len({f['file_path'] for f in target_frames}) != 6:
            raise ValueError('Target must have six distinct measured crop poses')
        if len(transforms['frames']) != 48:
            raise ValueError('Require 48 observed training views after one complete panorama holdout')
        baseline = {f['file_path']: f for f in transforms['frames']}
        for frame in all_poses['frames']:
            if frame['file_path'] in baseline and frame != baseline[frame['file_path']]:
                raise ValueError('Base dataset changes a measured pose')
        if any(f['file_path'] in baseline for f in target_frames):
            raise ValueError('Target real RGB already occurs in training dataset')
        with Image.open(generated) as image:
            if image.mode != 'RGB' or image.width != 2 * image.height:
                raise ValueError('Generated panorama must be 2:1 RGB')
            pixels = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        # The fixed rig's source crop convention is 512 px, 90° HFOV and six
        # yaws at 60° intervals. Verify every copied calibration before using it.
        expected = PANORAMA.intrinsics(512, 90)
        for frame in target_frames:
            for key, reference in (('w', 512), ('h', 512), ('fl_x', expected['fx']),
                                   ('fl_y', expected['fy']), ('cx', 256), ('cy', 256)):
                if frame.get(key) != reference:
                    raise ValueError(f'Unexpected target calibration: {key}')
        (output / 'images').mkdir()
        for frame in transforms['frames']:
            source = real / frame['file_path']
            target = output / frame['file_path']
            shutil.copyfile(source, target)
        shutil.copyfile(real / transforms.get('ply_file_path', 'init.ply'), output / 'init.ply')
        views = []
        for frame in sorted(target_frames, key=lambda f: f['file_path']):
            view_number = int(Path(frame['file_path']).stem.rsplit('_', 1)[1])
            yaw = (view_number - 1) * 60
            crop = PANORAMA.crop_panorama(pixels, 512, 90, yaw, 0)
            target = output / frame['file_path']
            ok, encoded = cv2.imencode('.png', crop, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            if not ok:
                raise RuntimeError(f'Could not encode {target.name}')
            target.write_bytes(encoded.tobytes())
            views.append({'file': frame['file_path'], 'yawDegrees': yaw,
                          'sha256': digest(target), 'pose': frame['transform_matrix'],
                          'poseOrigin': 'all-image-SfM real target image'})
        transforms['frames'].extend(target_frames)
        transforms['ply_file_path'] = 'init.ply'
        RECONSTRUCT.write_json(output / 'transforms.json', transforms)
        provenance['notes'] = (provenance.get('notes', '') + ' Synthetic midpoint panorama at '
                               + args.target + '. ' + report['poseMeaning'] + ' Generated frame: RIFE 4.25 MLX recursive interpolation, not diffusion. '
                               'Original endpoint panoramas: Cicero101 / Mapillary, Wikimedia Commons, CC-BY-SA-4.0. '
                               'This dataset is a synthetic appearance experiment, not independently validated geometry.').strip()
        RECONSTRUCT.write_json(output / 'provenance.json', provenance)
        for name in ('LICENSE', 'ATTRIBUTION.txt'):
            if (real / name).is_file():
                shutil.copyfile(real / name, output / name)
        RECONSTRUCT.write_json(output / 'synthetic-views.json', {
            'schemaVersion': 1, 'method': 'RIFE 4.25 MLX recursive panorama midpoint',
            'sourcePanoramaSha256': digest(generated), 'generationReportSha256': digest(report_path),
            'target': args.target, 'heldOutRealPixelsRead': False,
            'poseMeaning': report['poseMeaning'], 'views': views})
        RECONSTRUCT.validate_dataset(output)
        report.update(status='PASS', trainingImages=len(transforms['frames']), syntheticViews=len(views),
                      generatedPanoramaSha256=digest(generated), generationReportSha256=digest(report_path),
                      sourceDatasetSha256=digest(real / 'transforms.json'))
    except Exception as error:
        report.update(status='FAIL', error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
        raise
    finally:
        report['elapsedSeconds'] = round(time.monotonic() - began, 3)
        RECONSTRUCT.write_json(output / 'augmentation.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
