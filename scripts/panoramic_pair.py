"""Adjacent ERP diagnostics in an already shared, explicitly calibrated frame.

No alignment, fusion, inferred metric scale, or ground-truth visibility occurs
here. A positive residual places the source prediction behind the target
prediction along the target ray. Either prediction or pose can be wrong.
"""

import numpy as np

from spherical_depth import backproject_radial, directions_to_erp, sample_erp_bilinear


def _pose(value):
    pose = np.asarray(value, dtype=np.float64)
    if (pose.shape != (4, 4) or not np.isfinite(pose).all()
            or not np.allclose(pose[3], [0, 0, 0, 1], atol=1e-8, rtol=0)
            or not np.allclose(pose[:3, :3].T @ pose[:3, :3], np.eye(3), atol=1e-6, rtol=0)
            or not np.isclose(np.linalg.det(pose[:3, :3]), 1, atol=1e-6, rtol=0)):
        raise ValueError("Require a finite right-handed rigid panorama-to-world pose")
    return pose


def _erp(radial, rgb, mask):
    radial, rgb = np.asarray(radial, dtype=np.float64), np.asarray(rgb)
    if radial.ndim != 2 or radial.shape[0] < 2 or radial.shape[1] != 2 * radial.shape[0]:
        raise ValueError("Require a scalar 2:1 ERP radial-range image")
    if rgb.shape != (*radial.shape, 3) or rgb.dtype != np.uint8:
        raise ValueError("Require a matching uint8 RGB image")
    valid = np.isfinite(radial) & (radial > 0)
    if mask is not None:
        mask = np.asarray(mask)
        if mask.shape != radial.shape or mask.dtype != np.bool_:
            raise ValueError("Selection masks must be boolean and match their ERP")
        valid &= mask
    return radial, rgb, valid


def nearest_in_target_pixels(u, v, radial, height, width):
    """Keep nearest projected source samples per target pixel, including ties.

    This is a discrete source-cloud z-buffer diagnostic, not observed occlusion.
    Pixel rounding wraps the horizontal seam and clamps the poles. A bin may
    contain different surfaces; this helper does not establish correspondence.
    """
    if height < 2 or width != 2 * height:
        raise ValueError("Require 2:1 target ERP dimensions")
    u, v, radial = (np.asarray(a, dtype=np.float64) for a in (u, v, radial))
    if u.ndim != 1 or v.shape != u.shape or radial.shape != u.shape:
        raise ValueError("Require paired 1D projected samples")
    if not np.isfinite(u).all() or not np.isfinite(v).all() or not np.isfinite(radial).all() or np.any(radial <= 0):
        raise ValueError("Projected coordinates must be finite and ranges positive")
    columns = np.floor(u + .5).astype(np.int64) % width
    rows = np.clip(np.floor(v + .5).astype(np.int64), 0, height - 1)
    indices = rows * width + columns
    nearest = np.full(height * width, np.inf)
    np.minimum.at(nearest, indices, radial)
    # Floating point roundoff tolerance only, not a geometry acceptance threshold.
    return np.abs(radial - nearest[indices]) <= 1e-10 * np.maximum(1., nearest[indices])


def _stats(values):
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    return dict(samples=int(values.size), mean=float(np.mean(values)) if values.size else None,
                median=float(np.median(values)) if values.size else None,
                p10=float(np.quantile(values, .1)) if values.size else None,
                p90=float(np.quantile(values, .9)) if values.size else None)


def summarize_samples(samples, selection=None):
    """JSON-safe directional/ROI statistics; no survivor-only acceptance claim."""
    selected = np.ones(len(samples["candidate"]), dtype=bool)
    if selection is not None:
        selection = np.asarray(selection)
        if selection.shape != selected.shape or selection.dtype != np.bool_:
            raise ValueError("ROI selection must be a matching boolean sample vector")
        selected &= selection
    candidates = selected & samples["candidate"]
    nearest = candidates & samples["source_nearest_in_target_pixel"]
    count, total = int(candidates.sum()), int(selected.sum())
    result = dict(selectedSourceSamples=total, candidateSamples=count,
                  unsupportedTargetSamples=total - count,
                  candidateFraction=count / total if total else None,
                  signedRangeResidual=_stats(samples["signed_residual"][candidates]),
                  absoluteRangeResidual=_stats(np.abs(samples["signed_residual"][candidates])),
                  signedRelativeResidual=_stats(samples["relative_residual"][candidates]),
                  absoluteRelativeResidual=_stats(np.abs(samples["relative_residual"][candidates])),
                  rgbMeanAbsoluteError255=_stats(samples["rgb_mae"][candidates]),
                  nearestSourceInTargetPixel=dict(samples=int(nearest.sum()),
                      absoluteRelativeResidual=_stats(np.abs(samples["relative_residual"][nearest])),
                      rgbMeanAbsoluteError255=_stats(samples["rgb_mae"][nearest])),
                  residualMeaning="Projected source radial range minus sampled target radial range; positive is behind target prediction, not proven occlusion",
                  rgbMeaning="Observed source RGB versus bilinearly sampled observed target RGB; photos also participated in estimation, not independent appearance truth",
                  classificationStatus="NOT RUN" if samples["tolerance"] is None else "PASS: classified with caller-supplied tolerance; not geometric acceptance")
    if samples["tolerance"] is not None:
        result["classification"] = {
            key: dict(samples=int((candidates & samples[key]).sum()),
                      candidateFraction=float((candidates & samples[key]).sum() / count) if count else None,
                      sourceFraction=float((candidates & samples[key]).sum() / total) if total else None,
                      rgbMeanAbsoluteError255=_stats(samples["rgb_mae"][candidates & samples[key]]))
            for key in ("agreement", "in_front", "behind")}
        result["toleranceRangeUnits"] = _stats(samples["tolerance"][candidates])
    return result


def compare_direction(source_range, target_range, source_rgb, target_rgb,
                      source_pose, target_pose, *, source_mask=None, target_mask=None,
                      stride=3, tolerance=None, relative_tolerance=None):
    """Project one calibrated spherical prediction into another observed ERP.

    Range and both pose translations must already share units/frame. All selected
    positive source samples are retained, including those without target support.
    Bilinear sampling requires every contributing target depth/mask value valid;
    wrapping across the ERP seam is deliberate. Target-center coincidences are
    unsupported. No RGB or residual-based rejection biases the main summary.

    tolerance is optional: scalar, source ERP shaped, or selected-source-sample
    vector, in the shared range units. It must be finite and nonnegative. None
    means no agreement/front/behind classification, never an automatic threshold.
    Alternatively relative_tolerance is an explicit nonnegative scalar multiplied
    by sampled target range per candidate. The two tolerance modes are exclusive.
    """
    if tolerance is not None and relative_tolerance is not None:
        raise ValueError("Specify absolute or relative tolerance, not both")
    if relative_tolerance is not None:
        relative_tolerance = np.asarray(relative_tolerance, dtype=np.float64)
        if relative_tolerance.ndim != 0 or not np.isfinite(relative_tolerance) or relative_tolerance < 0:
            raise ValueError("Relative tolerance must be a finite nonnegative scalar")
        relative_tolerance = float(relative_tolerance)
    source_range, source_rgb, source_valid = _erp(source_range, source_rgb, source_mask)
    target_range, target_rgb, target_valid = _erp(target_range, target_rgb, target_mask)
    source_pose, target_pose = _pose(source_pose), _pose(target_pose)
    xyz, colors, rows, columns = backproject_radial(source_range, source_rgb, source_pose,
                                                   mask=source_valid, stride=stride)
    count, (height, width) = len(xyz), target_range.shape
    target_local = (xyz - target_pose[:3, 3]) @ target_pose[:3, :3]
    projected_range = np.linalg.norm(target_local, axis=1)
    projectable = np.isfinite(projected_range) & (projected_range > 0)
    u, v = np.full(count, np.nan), np.full(count, np.nan)
    u[projectable], v[projectable] = directions_to_erp(target_local[projectable], height, width)
    # Exact pixel-center round trips otherwise retain ~1e-14 interpolation weights
    # on an invalid neighbor. This only corrects numerical roundoff, not a warp.
    for coordinates in (u, v):
        rounded = np.round(coordinates)
        near = np.isfinite(coordinates) & (np.abs(coordinates - rounded) < 1e-10)
        coordinates[near] = rounded[near]
    sampled_range, sampled_rgb = np.full(count, np.nan), np.full((count, 3), np.nan)
    sampled_range[projectable] = sample_erp_bilinear(np.where(target_valid, target_range, np.nan),
                                                   u[projectable], v[projectable])
    sampled_rgb[projectable] = sample_erp_bilinear(target_rgb, u[projectable], v[projectable])
    candidates = projectable & np.isfinite(sampled_range) & (sampled_range > 0)
    nearest = np.zeros(count, dtype=bool)
    nearest[projectable] = nearest_in_target_pixels(u[projectable], v[projectable],
                                                   projected_range[projectable], height, width)
    signed, relative, rgb_mae = np.full(count, np.nan), np.full(count, np.nan), np.full(count, np.nan)
    signed[candidates] = projected_range[candidates] - sampled_range[candidates]
    relative[candidates] = signed[candidates] / sampled_range[candidates]
    rgb_mae[candidates] = np.mean(np.abs(colors[candidates].astype(float) - sampled_rgb[candidates]), axis=1)
    samples = dict(source_rows=rows, source_columns=columns, world_xyz=xyz, source_rgb=colors,
                   target_u=u, target_v=v, target_projected_range=projected_range,
                   target_sampled_range=sampled_range, target_rgb=sampled_rgb,
                   candidate=candidates, source_nearest_in_target_pixel=nearest,
                   signed_residual=signed, relative_residual=relative, rgb_mae=rgb_mae,
                   tolerance=None, agreement=None, in_front=None, behind=None)
    if tolerance is not None:
        tolerance = np.asarray(tolerance, dtype=np.float64)
        if not np.isfinite(tolerance).all() or np.any(tolerance < 0):
            raise ValueError("Tolerance must be finite and nonnegative")
        if tolerance.ndim == 0:
            tolerance = np.full(count, float(tolerance))
        elif tolerance.shape == source_range.shape:
            tolerance = tolerance[rows, columns]
        if tolerance.shape != (count,) or not np.isfinite(tolerance).all() or np.any(tolerance < 0):
            raise ValueError("Tolerance must be finite, nonnegative and scalar, source ERP shaped, or sample shaped")
        samples.update(tolerance=tolerance, agreement=candidates & (np.abs(signed) <= tolerance),
                       in_front=candidates & (signed < -tolerance), behind=candidates & (signed > tolerance))
    elif relative_tolerance is not None:
        tolerance = sampled_range * relative_tolerance
        samples.update(tolerance=tolerance, agreement=candidates & (np.abs(signed) <= tolerance),
                       in_front=candidates & (signed < -tolerance), behind=candidates & (signed > tolerance))
    return dict(samples=samples, summary=summarize_samples(samples))
