#!/usr/bin/env python3
"""Read-only P0 inventory and measured-pose export; never retrain or edit inputs.

Run in the existing PyCOLMAP environment. The output is a new local job directory,
not a replacement for any source artifact. --verify checks a previous inventory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'data/jobs/object-focus-real-only-20261105'
RIG = ROOT / 'data/jobs/mapillary-beijing-rig-poses-v2'
SAMPLE = ROOT / 'data/samples/mapillary-beijing'
PREPARED = ROOT / 'data/jobs/mapillary-beijing-crops'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def freeze(output):
    import numpy as np
    import pycolmap
    from PIL import Image

    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    inventory = {}

    def pin(path, role):
        key = relative(path)
        if key not in inventory:
            inventory[key] = {'path': key, 'role': role, 'bytes': path.stat().st_size, 'sha256': sha(path)}
        return inventory[key]

    source_frames = read(SAMPLE / 'acquisition.json')['frames']
    if len(source_frames) != 9:
        raise ValueError('Expected exactly nine preserved source panoramas')
    sources = []
    for item in source_frames:
        path = SAMPLE / item['file']
        record = dict(pin(path, 'observed ERP source'), imageId=item['imageId'])
        if record['sha256'] != item['sha256']:
            raise ValueError(f'Source acquisition hash mismatch: {path.name}')
        with Image.open(path) as image:
            record['width'], record['height'] = image.size
        sources.append(record)
    for path in [SAMPLE / 'acquisition.json', SAMPLE / 'provenance.json', SAMPLE / 'ATTRIBUTION.txt',
                 PREPARED / 'crops.json', RIG / 'report.json', RIG / 'rig-image-mapping.json',
                 RIG / 'dataset/transforms.json', RIG / 'dataset/init.ply', RIG / 'dataset/provenance.json']:
        pin(path, 'fixed-rig source, calibration and pose evidence')
    for path in sorted((RIG / 'dataset/sparse').glob('*')):
        if path.is_file():
            pin(path, 'fixed-rig SfM model')
    for path in sorted((BASELINE / 'fusion/dataset/images').glob('*.png')):
        pin(path, 'actual best-scooter RGB training raster')
    for path in sorted((BASELINE / 'originals/images').glob('*.png')):
        pin(path, 'pre-undistortion observed scooter crop')
    for directory in ['originals', 'poses/dataset', 'fusion/dataset', 'training/world', 'object/world']:
        for path in sorted((BASELINE / directory).glob('*')):
            if path.is_file():
                pin(path, 'best-scooter input, camera or output artifact')
    for directory in ['depth', 'fusion', 'poses/dataset/sparse']:
        for path in sorted((BASELINE / directory).glob('*')):
            if path.is_file() and path.suffix in ('.npy', '.json', '.bin'):
                pin(path, 'best-scooter raw depth, calibration or SfM evidence')
    for name in ['inputs.json', 'ablation.json', 'control-check.json', 'poses/report.json',
                 'training/job.json', 'training/training.log', 'training/resources.txt',
                 'object/report.json', 'browser-public.json']:
        pin(BASELINE / name, 'preserved baseline execution and validation evidence')
    for name in ['object-focus.py', 'run-object-ablation.py', 'fuse-object-depth.py',
                 'warp-learned-depth.py', 'reconstruct.py', 'estimate-panorama-poses.py',
                 'prepare-panoramas.py', 'freeze-panoramic-baseline.py']:
        pin(ROOT / 'scripts' / name, 'implementation used to define or audit baseline')

    crops = read(PREPARED / 'crops.json')['crops']
    transforms = read(RIG / 'dataset/transforms.json')['frames']
    model = pycolmap.Reconstruction(RIG / 'dataset/sparse')
    crop_by_name = {Path(crop['file']).name: crop for crop in crops}
    pose_by_source, deviations = {}, []
    for frame in transforms:
        crop = crop_by_name[Path(frame['file_path']).name]
        world_from_camera = np.array(frame['transform_matrix']) @ np.diag([1, -1, -1, 1])
        pose = world_from_camera.copy()
        pose[:3, :3] = world_from_camera[:3, :3] @ np.array(crop['relativeCameraToPanoramaRotation']).T
        if crop['sourceId'] in pose_by_source:
            deviations.append(float(np.max(np.abs(pose - pose_by_source[crop['sourceId']]))))
        else:
            pose_by_source[crop['sourceId']] = pose
    if max(deviations) > 1e-10:
        raise ValueError('Virtual crop poses do not reproduce one common panorama pose')
    centers = {key: pose[:3, 3] for key, pose in pose_by_source.items()}
    selected_source = Path(source_frames[4]['file']).name
    selected_pose = pose_by_source[selected_source]
    selected_images = [im for im in model.images.values() if crop_by_name[im.name]['sourceId'] == selected_source]
    selected_ids = sorted({p.point3D_id for im in selected_images for p in im.points2D if p.has_point3D()})
    anchors, rejected = [], []
    for point_id in selected_ids:
        point = model.points3D[point_id]
        local = selected_pose[:3, :3].T @ (point.xyz - selected_pose[:3, 3])
        distance = float(np.linalg.norm(local))
        track_sources = sorted({crop_by_name[model.images[e.image_id].name]['sourceId'] for e in point.track.elements})
        if not np.isfinite(local).all() or distance <= 0 or len(track_sources) < 2:
            rejected.append(point_id)
            continue
        ray = local / distance
        longitude = float(np.arctan2(ray[0], ray[2]))
        latitude = float(np.arcsin(np.clip(-ray[1], -1, 1)))
        directions = np.array([(point.xyz - centers[name]) / np.linalg.norm(point.xyz - centers[name]) for name in track_sources])
        max_angle = float(np.degrees(np.arccos(np.clip((directions @ directions.T).min(), -1, 1))))
        observed = []
        for element in point.track.elements:
            image = model.images[element.image_id]
            if crop_by_name[image.name]['sourceId'] == selected_source:
                observed.append({'image': image.name, 'xyCornerOrigin': image.points2D[element.point2D_idx].xy.tolist()})
        anchors.append({'point3DId': point_id, 'xyzWorld': point.xyz.tolist(),
                        'color': point.color.tolist(), 'rayPanorama': ray.tolist(),
                        'radialRangeSfm': distance, 'erpNormalizedUv': [(longitude / (2 * np.pi) + .5) % 1, .5 - latitude / np.pi],
                        'latitudeDegrees': float(np.degrees(latitude)), 'longitudeDegrees': float(np.degrees(longitude)),
                        'meanReprojectionErrorPixels': float(point.error), 'observedSelectedCropPixels': observed,
                        'distinctPhysicalPanoramaCount': len(track_sources), 'trackObservationCount': len(point.track.elements),
                        'maxTriangulationAngleDegrees': max_angle, 'physicalPanoramaIds': track_sources})
    uv = np.array([row['erpNormalizedUv'] for row in anchors])
    histogram, _, _ = np.histogram2d(uv[:, 1], uv[:, 0], bins=(6, 12), range=((0, 1), (0, 1)))
    selected = {
        'schemaVersion': 1, 'status': 'PASS', 'panoramaName': 'pano_000005',
        'source': sources[4], 'coordinateFrame': 'fixed-rig-sfm-20261104',
        'sourceModel': relative(RIG / 'dataset/sparse'), 'modelFileHashes': [row for row in inventory.values() if row['role'] == 'fixed-rig SfM model'],
        'worldFromPanorama': selected_pose.tolist(), 'panoramaAxes': '+X right, +Y down, +Z forward; right handed',
        'erpConvention': 'u=(atan2(x,z)/(2*pi)+0.5) mod 1, v=0.5-asin(-y)/pi; pixel center uv=((column+0.5)/width,(row+0.5)/height)',
        'units': 'arbitrary SfM scale, NOT meters; radial range is norm(Xworld-cameraCenter)',
        'poseMeaning': 'Existing image-estimated fixed-rig pose; no new pose estimation or independent pose validation',
        'poseDerivation': 'worldFromOpenGLCamera @ diag(1,-1,-1,1), then rotation @ relativeCameraToPanoramaRotation.T',
        'allSixCropPoseMaxElementDeviation': max(deviations), 'candidateUniquePoints': len(selected_ids),
        'acceptedAnchors': len(anchors), 'rejectedPointIds': rejected, 'anchors': anchors,
        'coverage': {'longitudeBins': 12, 'latitudeBins': 6, 'countsNorthToSouth': histogram.astype(int).tolist(),
                     'occupiedBins': int(np.count_nonzero(histogram)), 'totalBins': 72,
                     'latitudeRangeDegrees': [min(a['latitudeDegrees'] for a in anchors), max(a['latitudeDegrees'] for a in anchors)],
                     'perVirtualCameraObservations': {im.name: sum(p.has_point3D() for p in im.points2D) for im in selected_images}},
        'independentGeometryValidation': 'NOT RUN',
        'limits': ['Anchors and poses are jointly estimated from all nine panoramas; calibration anchors are not independent ground truth.',
                   'No semantic sky filtering is applied to sparse anchors; angular coverage is sparse and biased by feature visibility.',
                   'Different virtual crop observations share a physical panorama center and are not independent viewpoints.']}
    write(output / 'selected-panorama.json', selected)

    ordered = [(Path(row['file']).name, pose_by_source[Path(row['file']).name]) for row in source_frames]
    cameras = []
    for index, (name, pose) in enumerate(ordered):
        cameras.append({'id': f'panorama-{index + 1:02d}', 'kind': 'observed', 'poseSource': 'image-estimated fixed-rig SfM',
                        'coordinateFrame': 'fixed-rig-sfm-20261104', 'sourceId': name, 'worldFromPanorama': pose.tolist(),
                        'renderStatus': 'NOT RUN', 'geometryGroundTruth': False})
    # Predeclared display diagnostics, deliberately not inferred physical measurements.
    for index in range(8):
        left, right = ordered[index][1], ordered[index + 1][1]
        midpoint = left.copy()
        midpoint[:3, 3] = (left[:3, 3] + right[:3, 3]) / 2
        cameras.append({'id': f'midpoint-{index + 1:02d}-{index + 2:02d}', 'kind': 'interpolated',
                        'coordinateFrame': 'fixed-rig-sfm-20261104', 'worldFromPanorama': midpoint.tolist(),
                        'definition': 'Halfway between estimated centers; retains left panorama orientation, not an observed pose.',
                        'renderStatus': 'NOT RUN', 'geometryGroundTruth': False})
    spacing = float(np.median([np.linalg.norm(ordered[i+1][1][:3, 3]-ordered[i][1][:3, 3]) for i in range(8)]))
    for sign in (-1, 1):
        lateral = selected_pose.copy()
        lateral[:3, 3] += sign * .1 * spacing * selected_pose[:3, 0]
        cameras.append({'id': 'middle-left' if sign < 0 else 'middle-right', 'kind': 'extrapolated',
                        'coordinateFrame': 'fixed-rig-sfm-20261104', 'worldFromPanorama': lateral.tolist(),
                        'definition': 'Diagnostic camera displaced along middle panorama local X by 0.1 times median adjacent-center spacing. Not a measured safe walkable position.',
                        'offsetSfmUnits': sign * .1 * spacing, 'renderStatus': 'NOT RUN', 'geometryGroundTruth': False})
    scooter_frames = read(BASELINE / 'fusion/dataset/transforms.json')['frames']
    evaluation = {'schemaVersion': 1, 'fixedRigCameras': cameras, 'medianAdjacentCenterSpacingSfm': spacing,
                  'scooterObservedCameras': [{'id': Path(f['file_path']).stem, 'kind': 'observed',
                       'coordinateFrame': 'scooter-original-only-sfm-20261105', 'poseMeaning': 'image-estimated camera, not surveyed truth', **f} for f in scooter_frames],
                  'targetViews': [{'target': 'scooter', 'status': 'PASS for existing observed crop selection only',
                       'cameraSet': 'scooterObservedCameras', 'matchedNewStreetRenderStatus': 'NOT RUN'}] +
                      [{'target': target, 'status': 'NOT RUN', 'reason': 'No reviewed target coordinate or matched evaluation crop selected in this bounded baseline freeze.'} for target in ('tree', 'doorway', 'facade', 'road')],
                  'limits': 'Scooter and full-street fixed-rig models use separate SfM frames. No alignment is estimated here. Diagnostic interpolated/extrapolated cameras are display choices, not invented measurements.'}
    write(output / 'evaluation-cameras.json', evaluation)
    training = read(BASELINE / 'training/job.json')
    fusion = read(BASELINE / 'fusion/report.json')
    rig_report = read(RIG / 'report.json')
    report = {'schemaVersion': 1, 'status': 'PASS', 'operation': 'Read-only baseline hash freeze and camera metadata export',
              'createdAt': datetime.now(timezone.utc).isoformat(), 'baselineJob': relative(BASELINE),
              'baselineEvidenceReexecuted': False, 'newTraining': 'NOT RUN', 'newDepthInference': 'NOT RUN',
              'sourcePanoramas': sources, 'files': list(inventory.values()), 'runtime': {'pycolmapVersion': pycolmap.__version__},
              'baseline': {'images': training['imageCount'], 'options': training['options'], 'brushCommand': training['command'],
                           'depthModel': read(BASELINE / 'depth/report.json')['model'],
                           'depthOutputMeaning': read(BASELINE / 'depth/report.json')['outputMeaning'],
                           'calibrationFormula': 'camera-Z = 1 / (scale * predicted_relative_inverse_depth + offset), arbitrary scooter-SfM units',
                           'calibration': fusion['calibration'], 'clipping': fusion['clipping'], 'voxelSize': fusion['voxelSize'],
                           'fusionSettings': {'sampleStridePixels': 2, 'neighborOriginalViews': 2, 'relativeDepthAgreementBelow': .15,
                                              'meanAbsoluteRgbErrorBelow': 50, 'initialRadiusRule': '.40 times median camera-to-focus distance', 'voxelSpacingRule': 'initial radius / 180',
                                              'sourceScript': 'scripts/fuse-object-depth.py'},
                           'initialPoints': fusion['points'], 'exportedGaussians': training['artifact']['splats'],
                           'trainingSeconds': training['elapsedSeconds'], 'adapterEvidence': training['adapterEvidence'],
                           'sourceFrame': 'scooter-original-only-sfm-20261105',
                           'publicComparison': 'https://groundshift-viewer-production.up.railway.app/experiments/object-real/',
                           'publicScene': 'https://groundshift-viewer-production.up.railway.app/?world=/worlds/scooter-real-object/world.json'},
              'rig': {'images': model.num_reg_images(), 'physicalPanoramas': len(ordered), 'points3D': model.num_points3D(),
                      'meanReprojectionErrorPixels': model.compute_mean_reprojection_error(), 'recordedRigCheck': rig_report['rigConstraintCheck'],
                      'sourceFrame': 'fixed-rig-sfm-20261104', 'selectedPanorama': 'selected-panorama.json'},
              'limits': ['Baseline training timing and visual observations are reused evidence, not newly benchmarked.',
                        'The best baseline remains recognizable but blurred with stretched splats; independent geometric accuracy is NOT RUN.',
                        'Original and actual training RGB differ at one-pixel borders; both are separately pinned. See control-check.json.',
                        'Mean reprojection residual is an internal SfM fit measure, not independent geometry accuracy.',
                        'Freeze creates hashes and metadata only; it does not replace or duplicate original sources or large artifacts.'],
              'elapsedSeconds': time.monotonic() - started}
    write(output / 'baseline.json', report)
    verify(output)
    print(json.dumps({'status': 'PASS', 'pinnedFiles': len(inventory), 'anchors': len(anchors), 'output': relative(output),
                      'elapsedSeconds': time.monotonic()-started}, indent=2))


def verify(output):
    report = read(output / 'baseline.json')
    mismatches = [row['path'] for row in report['files'] if (not (ROOT / row['path']).is_file()
                  or (ROOT / row['path']).stat().st_size != row['bytes'] or sha(ROOT / row['path']) != row['sha256'])]
    if mismatches:
        raise ValueError(f'Pinned inputs changed: {mismatches}')
    print(f'PASS: all {len(report["files"])} pinned input files retain their original hashes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New snapshot directory, or prior snapshot for --verify')
    parser.add_argument('--verify', action='store_true', help='Verify source hashes without modifying snapshot or sources')
    args = parser.parse_args()
    output = args.output.resolve()
    if args.verify:
        verify(output)
    else:
        freeze(output)


if __name__ == '__main__':
    main()
