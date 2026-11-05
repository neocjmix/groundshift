#!/usr/bin/env python3
"""Compare relative-depth ordering with existing sparse SfM observations.

The SfM model and RGB images are not held-out ground truth. This reports only
within-camera ranking agreement, not metric accuracy or novel-view quality.
"""
import argparse
import json
from pathlib import Path


def rank(values):
    import numpy as np
    order = np.argsort(values, kind='stable')
    result = np.empty(len(values), dtype=float)
    result[order] = np.arange(len(values))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inference', type=Path)
    parser.add_argument('sparse', type=Path)
    args = parser.parse_args()
    import numpy as np
    import pycolmap

    report = json.loads((args.inference / 'report.json').read_text())
    if report['status'] != 'PASS':
        parser.error('Require completed depth inference')
    reconstruction = pycolmap.Reconstruction(args.sparse)
    by_name = {image.name: image for image in reconstruction.images.values()}
    results = []
    for index, item in enumerate(report['images']):
        name = Path(item['source']).name
        if name not in by_name:
            parser.error(f'Image missing from SfM model: {name}')
        image = by_name[name]
        prediction = np.load(args.inference / f'view-{index:02d}-relative.npy')
        width, height = item['size']
        if prediction.shape != (height, width):
            parser.error(f'Depth dimensions differ: {name}')
        samples = []
        for observation in image.points2D:
            if not observation.has_point3D():
                continue
            xyz = reconstruction.points3D[observation.point3D_id].xyz
            camera_point = image.cam_from_world() * xyz
            if camera_point[2] <= 0:
                continue
            # COLMAP stores pixel-center coordinates with the top-left corner
            # at (0,0); the array cell center is at (column+0.5,row+0.5).
            x = int(np.clip(round(float(observation.xy[0]) - 0.5), 0, width - 1))
            y = int(np.clip(round(float(observation.xy[1]) - 0.5), 0, height - 1))
            samples.append((float(prediction[y, x]), float(camera_point[2])))
        if len(samples) < 30:
            parser.error(f'Too few positive-depth sparse observations: {name}')
        values = np.asarray(samples)
        relative, inverse_z = values[:, 0], 1 / values[:, 1]
        results.append({
            'image': name,
            'sparseObservations': len(samples),
            'pearsonRelativeVsInverseSfMZ': float(np.corrcoef(relative, inverse_z)[0, 1]),
            'spearmanRelativeVsInverseSfMZ': float(np.corrcoef(rank(relative), rank(inverse_z))[0, 1]),
        })
    output = {
        'schemaVersion': 1,
        'status': 'PASS',
        'scope': 'Depth ordering of observed features against all-image SfM estimates; not independent depth truth, metric calibration, temporal consistency, warp coverage or GS quality',
        'results': results,
    }
    (args.inference / 'geometry-check.json').write_text(json.dumps(output, indent=2, allow_nan=False) + '\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
