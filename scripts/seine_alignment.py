#!/usr/bin/env python3
"""Align overlapping image-derived panorama rigs without GPS or metric claims.

The returned Sim(3) maps source raw SfM coordinates into reference raw SfM
coordinates. Orientations resolve the rotation ambiguity of a straight street;
camera centers determine positive scale and translation. This checks overlap
consistency, not geometry accuracy. Original models and point clouds are read
only. Chain transforms explicitly, then apply the baseline assetToWorld once.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import numpy as np


def _rotation(value):
    value = np.asarray(value, dtype=float)
    if (value.shape != (3, 3) or not np.isfinite(value).all()
            or not np.allclose(value.T @ value, np.eye(3), atol=1e-7, rtol=0)
            or not np.isclose(np.linalg.det(value), 1, atol=1e-7, rtol=0)):
        raise ValueError('Require a finite proper SO(3) rotation, not scale or reflection')
    return value


def _pose(value):
    value = np.asarray(value, dtype=float)
    if (value.shape != (4, 4) or not np.isfinite(value).all()
            or not np.allclose(value[3], [0, 0, 0, 1], atol=1e-9, rtol=0)):
        raise ValueError('Require a finite homogeneous physical camera pose')
    _rotation(value[:3, :3])
    return value


def _angle(rotation):
    # atan2 is stable close to zero, unlike acos(trace) for exact alignments.
    skew = np.array([rotation[2, 1] - rotation[1, 2],
                     rotation[0, 2] - rotation[2, 0],
                     rotation[1, 0] - rotation[0, 1]])
    return float(np.degrees(np.arctan2(np.linalg.norm(skew) / 2,
                                     (np.trace(rotation) - 1) / 2)))


def _mean_rotation(rotations):
    u, _, vt = np.linalg.svd(np.sum(rotations, axis=0))
    return u @ np.diag([1, 1, np.linalg.det(u @ vt)]) @ vt


def _parts(transform):
    scale = float(transform['scale'])
    rotation = _rotation(transform['rotation'])
    translation = np.asarray(transform['translation'], dtype=float)
    if not np.isfinite(scale) or scale <= 0 or translation.shape != (3,) or not np.isfinite(translation).all():
        raise ValueError('Require positive finite scale and finite XYZ translation')
    return scale, rotation, translation


def _record(scale, rotation, translation):
    return dict(scale=float(scale), rotation=rotation.tolist(), translation=translation.tolist())


def transform_points(points, transform):
    """Return source XYZ positions in the reference frame; never edit inputs."""
    scale, rotation, translation = _parts(transform)
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError('Require finite Nx3 points')
    return scale * (points @ rotation.T) + translation


def transform_pose(pose, transform):
    """Scale the camera center, not its orientation basis."""
    pose = _pose(pose)
    _, rotation, _ = _parts(transform)
    result = np.eye(4)
    result[:3, :3] = rotation @ pose[:3, :3]
    result[:3, 3] = transform_points(pose[:3, 3][None, :], transform)[0]
    return result


def compose_alignment(reference_from_middle, middle_from_source):
    """Return reference_from_source. The right transform is applied first."""
    a, ar, at = _parts(reference_from_middle)
    b, br, bt = _parts(middle_from_source)
    return _record(a * b, ar @ br, a * (ar @ bt) + at)


def _baseline(centers, order):
    # Median pair separation per sequence index is robust to one bad center and
    # accounts for the omitted held poses. It is an SfM-unit normalization only.
    spans = [np.linalg.norm(centers[j] - centers[i]) / abs(order[j] - order[i])
             for i in range(len(centers)) for j in range(i + 1, len(centers))]
    baseline = float(np.median(spans))
    resolution = np.finfo(float).eps * max(1, float(np.abs(centers).max())) * 64
    if not np.isfinite(baseline) or baseline <= resolution:
        raise ValueError('Degenerate camera-center baseline; positive scale is unobservable')
    return baseline


def _residuals(source, reference, transform, baseline):
    predicted = [transform_pose(pose, transform) for pose in source]
    position = np.array([np.linalg.norm(a[:3, 3] - b[:3, 3]) for a, b in zip(predicted, reference)])
    angle = np.array([_angle(a[:3, :3] @ b[:3, :3].T) for a, b in zip(predicted, reference)])
    return position, position / baseline, angle


def _fit(source, reference, order, position_limit, angle_limit, fraction):
    n = len(source)
    minimum = max(3, math.ceil(n * fraction))
    candidates = np.array([b[:3, :3] @ a[:3, :3].T for a, b in zip(source, reference)])
    distances = np.array([[_angle(a @ b.T) for b in candidates] for a in candidates])
    medoid = int(np.argmin(np.median(distances, axis=1)))
    orientation_ok = distances[medoid] <= angle_limit
    if int(orientation_ok.sum()) < minimum:
        raise ValueError('Insufficient shared orientation consensus')
    rotation = _mean_rotation(candidates[orientation_ok])
    x, y = source[:, :3, 3], reference[:, :3, 3]
    _baseline(x, order)
    baseline = _baseline(y, order)
    rotated = x @ rotation.T
    best = None
    for i in range(n):
        for j in range(i + 1, n):
            if not orientation_ok[i] or not orientation_ok[j]:
                continue
            delta = rotated[j] - rotated[i]
            denominator = float(delta @ delta)
            if denominator <= np.finfo(float).tiny:
                continue
            scale = float(delta @ (y[j] - y[i]) / denominator)
            if scale <= 0:
                continue
            translation = ((y[i] - scale * rotated[i]) + (y[j] - scale * rotated[j])) / 2
            position = np.linalg.norm(scale * rotated + translation - y, axis=1) / baseline
            inliers = orientation_ok & (position <= position_limit)
            score = (int(inliers.sum()), -float(np.median(position)))
            if best is None or score > best[0]:
                best = score, inliers
    if best is None or best[0][0] < minimum:
        raise ValueError('Insufficient positive-scale camera-center consensus')
    inliers = best[1]
    for _ in range(3):
        rotation = _mean_rotation(candidates[inliers])
        xr, yr = x[inliers] @ rotation.T, y[inliers]
        xc, yc = xr - xr.mean(axis=0), yr - yr.mean(axis=0)
        denominator = float(np.sum(xc * xc))
        if denominator <= np.finfo(float).tiny:
            raise ValueError('Degenerate inlier baseline')
        scale = float(np.sum(xc * yc) / denominator)
        translation = yr.mean(axis=0) - scale * xr.mean(axis=0)
        transform = _record(scale, rotation, translation)
        _, normalized, angles = _residuals(source, reference, transform, baseline)
        refined = (normalized <= position_limit) & (angles <= angle_limit)
        if int(refined.sum()) < minimum:
            raise ValueError('Overlap loses consistency after joint refit')
        if np.array_equal(refined, inliers):
            return transform, inliers, baseline
        inliers = refined
    raise ValueError('Overlap consensus did not stabilize')


def fit_pose_alignment(source_by_id, reference_by_id, *, position_limit=0.25,
                       angle_limit_degrees=3.0, minimum_fraction=0.75):
    """Fit from shared real source identities; all poses are panorama-to-world.

    A deterministic quarter of shared poses is withheld for an independent
    overlap check, then all inliers are used for the final transform. Thresholds
    are explicit engineering gates, not measured-world accuracy. A returned FAIL
    must not be accepted silently by the caller.
    """
    if not (0 < position_limit < 1 and 0 < angle_limit_degrees < 90 and 0.5 < minimum_fraction <= 1):
        raise ValueError('Invalid overlap consistency thresholds')
    ids = sorted(set(source_by_id) & set(reference_by_id))
    if len(ids) < 6:
        raise ValueError('Require at least six distinct shared physical panoramas')
    source = np.array([_pose(source_by_id[key]) for key in ids])
    reference = np.array([_pose(reference_by_id[key]) for key in ids])
    order = np.arange(len(ids))
    held = order % 4 == 1
    transform_train, training_inliers, baseline_train = _fit(
        source[~held], reference[~held], order[~held], position_limit, angle_limit_degrees, minimum_fraction)
    hp, hn, ha = _residuals(source[held], reference[held], transform_train, baseline_train)
    transform, inliers, baseline = _fit(source, reference, order, position_limit, angle_limit_degrees, minimum_fraction)
    p, normalized, angles = _residuals(source, reference, transform, baseline)
    held_pass = bool(np.all(hn <= position_limit) and np.all(ha <= angle_limit_degrees))
    return dict(schemaVersion=1, status='PASS' if held_pass else 'FAIL',
                meaning='Relative alignment of image-derived SfM rigs; arbitrary reference units, not GPS or surveyed accuracy',
                transform=transform, sharedCount=len(ids), inlierCount=int(inliers.sum()),
                referenceStepSfm=baseline,
                thresholds=dict(positionFractionOfReferenceStep=position_limit,
                                orientationDegrees=angle_limit_degrees, minimumInlierFraction=minimum_fraction),
                residuals=[dict(sourceId=key, centerErrorSfm=float(p[i]), centerErrorSteps=float(normalized[i]),
                                orientationErrorDegrees=float(angles[i]), inlier=bool(inliers[i])) for i, key in enumerate(ids)],
                heldCheck=dict(status='PASS' if held_pass else 'FAIL',
                    note='Withheld only from overlap transform fitting; these images participated in their separate SfM jobs',
                    fitSourceIds=[key for i, key in enumerate(ids) if not held[i]],
                    fitInlierCount=int(training_inliers.sum()), transform=transform_train,
                    poses=[dict(sourceId=ids[i], centerErrorSfm=float(a), centerErrorSteps=float(b),
                                orientationErrorDegrees=float(c)) for i, a, b, c in zip(order[held], hp, hn, ha)]))


def load_physical_poses(job):
    """Map local sourceIndex to preserved original sourceId and SHA, not p00."""
    job = Path(job)
    report = json.loads((job / 'sfm/report.json').read_text())
    if report['status'] != 'PASS' or report['fullRegistration'] != 'PASS':
        raise ValueError('Require complete actual fixed-rig SfM registration')
    anchor_report = json.loads((job / 'anchors/report.json').read_text())
    if anchor_report['status'] != 'PASS':
        raise ValueError('Require completed physical-rig anchor extraction')
    crops = json.loads((job / 'sfm-inputs/crops.json').read_text())
    physical = json.loads((job / 'anchors/physical.json').read_text())
    sources = {item['sourceId']: item['sha256'] for item in crops['sourcePanoramas']}
    if len(sources) != len(crops['sourcePanoramas']):
        raise ValueError('Duplicate original source identity')
    if any(not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{64}', value) is None for value in sources.values()):
        raise ValueError('Require SHA-256 pins for every original panorama')
    identities = {}
    for crop in crops['crops']:
        index, key = str(crop['sourceIndex']), crop['sourceId']
        if key not in sources or index in identities and identities[index] != key:
            raise ValueError('Conflicting local panorama identity')
        identities[index] = key
    if (set(identities) != set(physical) or len(set(identities.values())) != len(identities)
            or set(identities.values()) != set(sources)):
        raise ValueError('Physical cameras do not match unique source identities')
    poses = {key: _pose(physical[index]['pose']) for index, key in identities.items()}
    return poses, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_job', type=Path)
    parser.add_argument('reference_job', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output exists; preserve prior alignment evidence')
    result = dict(schemaVersion=1, status='FAIL', startedAt=datetime.now(timezone.utc).isoformat())
    try:
        result['inputDigests'] = {label: {name: hashlib.sha256((job / name).read_bytes()).hexdigest()
            for name in ['sfm/report.json', 'sfm-inputs/crops.json', 'anchors/report.json', 'anchors/physical.json']}
            for label, job in [('source', args.source_job), ('reference', args.reference_job)]}
        source, source_hashes = load_physical_poses(args.source_job)
        reference, reference_hashes = load_physical_poses(args.reference_job)
        for key in set(source) & set(reference):
            if source_hashes[key] != reference_hashes[key]:
                raise ValueError(f'Shared source identity has different original bytes: {key}')
        result.update(fit_pose_alignment(source, reference))
    except (ValueError, KeyError, OSError) as error:
        result['error'] = f'{type(error).__name__}: {error}'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(f"Alignment {result['status']}: {args.output}")
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
