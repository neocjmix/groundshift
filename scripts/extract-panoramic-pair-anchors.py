#!/usr/bin/env python3
"""Extract adjacent-pair sparse evidence without editing the frozen P0 snapshot.

Requires the existing PyCOLMAP environment. Outputs are local diagnostic evidence,
not independent camera/geometry truth. Dense model outputs are never read here.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('frozen_baseline', Path(__file__).with_name('freeze-panoramic-baseline.py'))
BASE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BASE)


def held_out(point_id):
    """Same global point-ID split as evaluate-panoramic-depth.py, across views."""
    return int(hashlib.sha256(str(int(point_id)).encode()).hexdigest()[:8], 16) % 5 == 0


def derive_poses(crops, frames):
    crop_by_name = {Path(crop['file']).name: crop for crop in crops}
    poses, deviations = {}, []
    for frame in frames:
        crop = crop_by_name[Path(frame['file_path']).name]
        pose = np.asarray(frame['transform_matrix'], dtype=float) @ np.diag([1, -1, -1, 1])
        pose[:3, :3] = pose[:3, :3] @ np.asarray(crop['relativeCameraToPanoramaRotation']).T
        if crop['sourceId'] in poses:
            deviations.append(float(np.max(np.abs(pose - poses[crop['sourceId']]))))
        else:
            poses[crop['sourceId']] = pose
    deviation = max(deviations, default=0.)
    if deviation > 1e-10:
        raise ValueError('Virtual crop poses do not reproduce a co-located panorama rig')
    return crop_by_name, poses, deviation


def pair_geometry(point, first_pose, second_pose):
    vectors = np.asarray([point - first_pose[:3, 3], point - second_pose[:3, 3]])
    ranges = np.linalg.norm(vectors, axis=1)
    if not np.isfinite(vectors).all() or np.any(ranges <= 0):
        raise ValueError('Point must have finite positive range from both cameras')
    cosine = np.dot(vectors[0] / ranges[0], vectors[1] / ranges[1])
    angle = float(np.arccos(np.clip(cosine, -1, 1)))
    return ranges, angle


def summary(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return {'samples': len(values), 'median': float(np.median(values)) if len(values) else None,
            'p90': float(np.quantile(values, .9)) if len(values) else None,
            'max': float(np.max(values)) if len(values) else None}


def angular_coverage(anchors):
    uv = np.asarray([a['erpNormalizedUv'] for a in anchors])
    counts, _, _ = np.histogram2d(uv[:, 1], uv[:, 0], bins=(6, 12), range=((0, 1), (0, 1)))
    return {'samples': len(anchors), 'longitudeBins': 12, 'latitudeBins': 6,
            'countsNorthToSouth': counts.astype(int).tolist(), 'occupiedBins': int(np.count_nonzero(counts)),
            'totalBins': 72, 'latitudeRangeDegrees': [min(a['latitudeDegrees'] for a in anchors), max(a['latitudeDegrees'] for a in anchors)]}


def tolerance_record(sparse):
    return {'schemaVersion': 1, 'declaredAt': sparse['createdAt'],
            'declaredBeforeDenseComparison': True, 'source': 'pair-sparse.json',
            'sourceOperation': sparse['operation'], **sparse['toleranceRecommendation'],
            'commonTrackCount': sparse['commonTracks'],
            'pairTriangulationDegrees': sparse['pairTriangulationDegrees'],
            'firstOrderRelativeSamplingBand': sparse['firstOrderRelativeSamplingBand'],
            'p2Acceptance': 'NOT RUN; do not convert this diagnostic band into an accuracy PASS',
            'diagnosticDecision': 'Record distributions and coverage. A disagreement outside the band is a diagnostic concern; agreement is insufficient for fusion acceptance.'}


def sampling_relative_band(angle_radians, angular_error_radians, height=546, width=1092):
    """First-order conditioning diagnostic, NOT a confidence interval.

    A half-pixel ERP diagonal at the equator and the empirical sparse bearing
    residual are conservatively added. Two independent rays combine by sqrt(2).
    Near-collinear rays have no finite, useful triangulation bound.
    """
    angle = np.asarray(angle_radians, dtype=float)
    if height <= 0 or width != 2 * height or angular_error_radians < 0:
        raise ValueError('Expected 2:1 ERP and nonnegative angular residual')
    half_diagonal = .5 * np.hypot(2 * np.pi / width, np.pi / height)
    denominator = np.abs(np.sin(angle))
    return np.divide(np.sqrt(2) * (half_diagonal + angular_error_radians), denominator,
                     out=np.full_like(angle, np.inf), where=denominator > 1e-12)


def extract(output, source_name, frozen):
    import pycolmap

    output.mkdir(parents=True, exist_ok=False)
    reference = BASE.read(frozen / 'selected-panorama.json')
    inventory = BASE.read(frozen / 'baseline.json')
    # The immutable input model and originals must still match the old snapshot.
    roles = {'observed ERP source', 'fixed-rig SfM model', 'fixed-rig source, calibration and pose evidence'}
    pinned = [row for row in inventory['files'] if row['role'] in roles]
    for row in pinned:
        path = ROOT / row['path']
        if path.stat().st_size != row['bytes'] or BASE.sha(path) != row['sha256']:
            raise ValueError(f'Frozen source changed: {row["path"]}')
    source = next(row for row in inventory['sourcePanoramas'] if Path(row['path']).name == source_name)
    crops = BASE.read(BASE.PREPARED / 'crops.json')['crops']
    frames = BASE.read(BASE.RIG / 'dataset/transforms.json')['frames']
    by_name, poses, deviation = derive_poses(crops, frames)
    pose = poses[source_name]
    reference_name = Path(reference['source']['path']).name
    np.testing.assert_allclose(poses[reference_name], reference['worldFromPanorama'], atol=1e-12, rtol=0)
    model = pycolmap.Reconstruction(BASE.RIG / 'dataset/sparse')
    images = [image for image in model.images.values() if by_name[image.name]['sourceId'] == source_name]
    ids = sorted({p.point3D_id for image in images for p in image.points2D if p.has_point3D()})
    anchors, rejected = [], []
    for point_id in ids:
        point = model.points3D[point_id]
        local = pose[:3, :3].T @ (point.xyz - pose[:3, 3])
        distance = float(np.linalg.norm(local))
        track_sources = sorted({by_name[model.images[e.image_id].name]['sourceId'] for e in point.track.elements})
        if not np.isfinite(local).all() or distance <= 0 or len(track_sources) < 2:
            rejected.append(point_id)
            continue
        ray = local / distance
        longitude, latitude = float(np.arctan2(ray[0], ray[2])), float(np.arcsin(np.clip(-ray[1], -1, 1)))
        directions = np.asarray([(point.xyz - poses[name][:3, 3]) / np.linalg.norm(point.xyz - poses[name][:3, 3]) for name in track_sources])
        max_angle = float(np.degrees(np.arccos(np.clip((directions @ directions.T).min(), -1, 1))))
        observed = []
        for element in point.track.elements:
            image = model.images[element.image_id]
            if by_name[image.name]['sourceId'] == source_name:
                observed.append({'image': image.name, 'xyCornerOrigin': image.points2D[element.point2D_idx].xy.tolist()})
        anchors.append({'point3DId': point_id, 'xyzWorld': point.xyz.tolist(), 'color': point.color.tolist(),
                        'rayPanorama': ray.tolist(), 'radialRangeSfm': distance,
                        'erpNormalizedUv': [(longitude / (2 * np.pi) + .5) % 1, .5 - latitude / np.pi],
                        'latitudeDegrees': float(np.degrees(latitude)), 'longitudeDegrees': float(np.degrees(longitude)),
                        'meanReprojectionErrorPixels': float(point.error), 'observedSelectedCropPixels': observed,
                        'distinctPhysicalPanoramaCount': len(track_sources), 'trackObservationCount': len(point.track.elements),
                        'maxTriangulationAngleDegrees': max_angle, 'physicalPanoramaIds': track_sources})
    uv = np.asarray([a['erpNormalizedUv'] for a in anchors])
    histogram, _, _ = np.histogram2d(uv[:, 1], uv[:, 0], bins=(6, 12), range=((0, 1), (0, 1)))
    selected = {**reference, 'panoramaName': images[0].name.split('_view_')[0], 'source': source,
                'worldFromPanorama': pose.tolist(), 'allSixCropPoseMaxElementDeviation': deviation,
                'candidateUniquePoints': len(ids), 'acceptedAnchors': len(anchors), 'rejectedPointIds': rejected,
                'anchors': anchors, 'coverage': {'longitudeBins': 12, 'latitudeBins': 6,
                'countsNorthToSouth': histogram.astype(int).tolist(), 'occupiedBins': int(np.count_nonzero(histogram)),
                'totalBins': 72, 'latitudeRangeDegrees': [min(a['latitudeDegrees'] for a in anchors), max(a['latitudeDegrees'] for a in anchors)],
                'perVirtualCameraObservations': {image.name: sum(p.has_point3D() for p in image.points2D) for image in images}}}
    BASE.write(output / 'selected-panorama.json', selected)
    common = sorted(set(a['point3DId'] for a in anchors) & set(a['point3DId'] for a in reference['anchors']))
    tracks, all_errors, all_angles = [], [], []
    for point_id in common:
        point = model.points3D[point_id]
        ranges, angle = pair_geometry(point.xyz, pose, poses[reference_name])
        observations = []
        for element in point.track.elements:
            image = model.images[element.image_id]
            name = by_name[image.name]['sourceId']
            if name not in (source_name, reference_name):
                continue
            camera, observed = model.cameras[image.camera_id], image.points2D[element.point2D_idx].xy
            local = image.cam_from_world() * point.xyz
            pixel_error = float(np.linalg.norm(camera.img_from_cam(local) - observed))
            bearing = camera.cam_ray_from_img(observed)
            angular_error = float(np.arccos(np.clip(np.dot(bearing, local / np.linalg.norm(local)), -1, 1)))
            observations.append({'panorama': name, 'image': image.name, 'reprojectionPixels': pixel_error,
                                 'bearingErrorRadians': angular_error})
            all_errors.append(pixel_error)
            all_angles.append(angular_error)
        tracks.append({'point3DId': point_id, 'heldOutFromBothCalibrations': held_out(point_id),
                       'rangesSfm': ranges.tolist(), 'pairTriangulationAngleDegrees': float(np.degrees(angle)),
                       'observations': observations})
    angular_p90 = float(np.quantile(all_angles, .9))
    angles = np.radians([t['pairTriangulationAngleDegrees'] for t in tracks])
    bands = sampling_relative_band(angles, angular_p90)
    for track, band in zip(tracks, bands):
        track['firstOrderRelativeSamplingBand'] = float(band) if np.isfinite(band) else None
    report = {'schemaVersion': 1, 'status': 'PASS', 'createdAt': datetime.now(timezone.utc).isoformat(),
              'operation': 'Adjacent-pair sparse evidence only; no dense output is read',
              'sources': [source_name, reference_name], 'coordinateFrame': reference['coordinateFrame'],
              'centerSeparationSfm': float(np.linalg.norm(pose[:3, 3] - poses[reference_name][:3, 3])),
              'commonTracks': len(common), 'commonHeldOutTracks': sum(held_out(i) for i in common),
              'sharedPointIdHoldout': 'SHA256(str(point3DId)) first eight hex digits modulo 5 == 0; excluded in every panorama',
              'commonCropReprojectionPixels': summary(all_errors), 'commonCropBearingErrorRadians': summary(all_angles),
              'pairTriangulationDegrees': summary(np.degrees(angles)), 'belowOneDegreeTracks': int(np.sum(angles < np.radians(1))),
              'firstOrderRelativeSamplingBand': summary(bands),
              'toleranceRecommendation': {'kind': 'conditioning diagnostic only; NOT a geometric acceptance tolerance',
                  'workingResolution': [1092, 546], 'empiricalAngularErrorRadians': angular_p90,
                  'formula': 'sqrt(2) * (p90 observed sparse bearing residual + half ERP pixel diagonal at equator) / abs(sin(pair triangulation angle))',
                  'interpretation': 'Finite bearing residuals and sampling set a useful error scale, but do not bound pose, correspondence, stitching or learned-depth bias. Report residuals and coverage against this diagnostic scale; do not label fusion geometry PASS from this alone.',
                  'acceptanceStatus': 'NOT RUN: no independent pose/depth truth or validated static-surface tolerance'},
              'inputs': {'frozenSnapshot': BASE.relative(frozen), 'checkedFrozenFiles': len(pinned),
                         'selectedAnchorsSha256': BASE.sha(output / 'selected-panorama.json'),
                         'referenceAnchorsSha256': BASE.sha(frozen / 'selected-panorama.json')},
              'limits': ['Shared tracks are from the same all-nine-panorama SfM, not independent geometry truth.',
                         'Small internal reprojection error does not bound camera pose or depth uncertainty.',
                         'Pair triangulation angle uses the estimated 3D point and is a conditioning diagnostic.',
                         'No ICP, camera refinement, depth fit, generated imagery, fusion or training is performed.'],
              'tracks': tracks}
    BASE.write(output / 'pair-sparse.json', report)
    BASE.write(output / 'tolerance.json', tolerance_record(report))
    common_ids = set(common)
    BASE.write(output / 'common-coverage.json', {
        'schemaVersion': 1, 'sources': [source_name, reference_name],
        'allSharedTracks': {item['panoramaName']: angular_coverage([a for a in item['anchors'] if a['point3DId'] in common_ids])
                            for item in (selected, reference)},
        'heldOutSharedTracks': {item['panoramaName']: angular_coverage([a for a in item['anchors'] if a['point3DId'] in common_ids and held_out(a['point3DId'])])
                                for item in (selected, reference)},
        'limits': 'Angular feature coverage is not a semantic surface mask or independent geometry truth.'})
    print(json.dumps({k: v for k, v in report.items() if k != 'tracks'}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source', default='003_1677293342921360.jpg')
    parser.add_argument('--frozen', type=Path, default=ROOT / 'data/jobs/panoramic-baseline-20261106')
    args = parser.parse_args()
    extract(args.output.resolve(), args.source, args.frozen.resolve())


if __name__ == '__main__':
    main()
