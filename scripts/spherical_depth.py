"""Small ERP geometry helpers; no model assumptions or automatic metric scale.

Matches prepare-panoramas.py: right-handed +X right, +Y down, +Z toward
the ERP image center. Longitude increases right; latitude increases up.
Array index (u, v) denotes pixel center (u + 0.5, v + 0.5). The horizontal
seam is +/-pi. Poles clamp vertically; they must never wrap to each other.
"""

import numpy as np


PANORAMA_AXES = "+X right, +Y down, +Z toward ERP image center; right-handed"


def _dimensions(height, width):
    if (not isinstance(height, (int, np.integer)) or isinstance(height, bool)
            or not isinstance(width, (int, np.integer)) or isinstance(width, bool)
            or height < 2 or width != 2 * height):
        raise ValueError("Require a full 2:1 ERP with integer height >= 2")


def erp_pixel_rays(u, v, height, width):
    """Unit rays at array-index coordinates, allowing fractional pixel centers."""
    _dimensions(height, width)
    u, v = np.broadcast_arrays(np.asarray(u, dtype=np.float64), np.asarray(v, dtype=np.float64))
    if not np.isfinite(u).all() or not np.isfinite(v).all():
        raise ValueError("ERP coordinates must be finite")
    if np.any((v < -0.5) | (v > height - 0.5)):
        raise ValueError("ERP vertical coordinates must lie between the poles")
    lon = ((u + 0.5) / width - 0.5) * (2 * np.pi)
    lat = (0.5 - (v + 0.5) / height) * np.pi
    return np.stack((np.cos(lat) * np.sin(lon), -np.sin(lat), np.cos(lat) * np.cos(lon)), axis=-1)


def erp_unit_rays(height, width):
    """H x W x 3 rays at every ERP pixel center, in the declared local axes."""
    _dimensions(height, width)
    v, u = np.indices((height, width), dtype=np.float64)
    return erp_pixel_rays(u, v, height, width)


def directions_to_erp(directions, height, width):
    """Project nonzero directions to (u,v); norms do not affect projection.

    At a pole, longitude is arbitrary and does not encode extra information.
    Returned horizontal coordinates may touch either representation of the seam.
    """
    _dimensions(height, width)
    rays = np.asarray(directions, dtype=np.float64)
    if rays.ndim < 1 or rays.shape[-1] != 3 or not np.isfinite(rays).all():
        raise ValueError("Require finite directions with final dimension 3")
    norms = np.linalg.norm(rays, axis=-1)
    if np.any(norms <= 0):
        raise ValueError("Cannot project zero directions")
    lon = np.arctan2(rays[..., 0], rays[..., 2])
    lat = np.arcsin(np.clip(-rays[..., 1] / norms, -1, 1))
    return (lon / (2 * np.pi) + 0.5) * width - 0.5, (0.5 - lat / np.pi) * height - 0.5


def sample_erp_bilinear(values, u, v):
    """Sample a scalar/color ERP, wrapping X and clamping Y independently.

    Nonfinite source samples propagate only when their interpolation weight is
    nonzero. Query coordinates must be finite; output uses float64.
    """
    values = np.asarray(values)
    if values.ndim not in (2, 3) or not np.issubdtype(values.dtype, np.number):
        raise ValueError("Require a numeric scalar or multichannel ERP")
    height, width = values.shape[:2]
    _dimensions(height, width)
    u, v = np.broadcast_arrays(np.asarray(u, dtype=np.float64), np.asarray(v, dtype=np.float64))
    if not np.isfinite(u).all() or not np.isfinite(v).all():
        raise ValueError("ERP sampling coordinates must be finite")
    x, y = np.mod(u, width), np.clip(v, 0, height - 1)
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    x1, y1 = (x0 + 1) % width, np.minimum(y0 + 1, height - 1)
    dx, dy = x - x0, y - y0
    result = np.zeros((*u.shape, *values.shape[2:]), dtype=np.float64)
    for xx, yy, weight in ((x0, y0, (1 - dx) * (1 - dy)), (x1, y0, dx * (1 - dy)),
                            (x0, y1, (1 - dx) * dy), (x1, y1, dx * dy)):
        if values.ndim == 3:
            weight = weight[..., None]
        contribution = np.zeros_like(result)
        np.multiply(values[yy, xx], weight, out=contribution, where=weight != 0)
        result += contribution
    return result


def _calibration(calibration, convention):
    if not isinstance(calibration, dict) or calibration.get("convention") != convention:
        raise ValueError(f"Explicit calibration with convention {convention!r} is required")
    if calibration.get("units") not in ("sfm-arbitrary", "meters"):
        raise ValueError("Calibration units must be sfm-arbitrary or meters")
    if not isinstance(calibration.get("source"), str) or not calibration["source"].strip():
        raise ValueError("Calibration requires its evidence source; units alone are not calibration")
    try:
        scale, offset = float(calibration["scale"]), float(calibration["offset"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Calibration requires explicit numeric scale and offset") from error
    if not np.isfinite([scale, offset]).all() or scale == 0:
        raise ValueError("Calibration requires a finite nonzero scale and finite offset")
    return scale, offset


def calibrated_radial(prediction, calibration):
    """Apply an evidenced affine ray-range fit, never guessed normalization.

    Caller supplies calibration evidence and units; this helper cannot establish
    their accuracy. Meters are only valid if the evidence established metric scale.
    Invalid/nonpositive distances become NaN and are excluded by the valid mask.
    """
    scale, offset = _calibration(calibration, "ray-range")
    prediction = np.asarray(prediction, dtype=np.float64)
    with np.errstate(invalid="ignore", over="ignore"):
        radial = scale * prediction + offset
    valid = np.isfinite(prediction) & np.isfinite(radial) & (radial > 0)
    return np.where(valid, radial, np.nan), valid


def calibrated_inverse_radial(prediction, calibration):
    """Apply 1/range = scale * prediction + offset from explicit calibration.

    This is inverse radial range, NOT inverse pinhole camera-Z. The distinction
    is mandatory in calibration metadata. No default conversion is supplied.
    """
    scale, offset = _calibration(calibration, "inverse-ray-range")
    prediction = np.asarray(prediction, dtype=np.float64)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        inverse = scale * prediction + offset
        radial = 1 / inverse
    valid = np.isfinite(prediction) & np.isfinite(inverse) & (inverse > 0) & np.isfinite(radial)
    return np.where(valid, radial, np.nan), valid


def camera_z_to_radial(camera_z, unit_rays):
    """Convert positive pinhole camera-Z to ray range: range = Z / ray_z.

    Rays must be expressed in that same pinhole camera frame. Rear-facing and
    tangent rays have no positive pinhole depth and are invalid, not flipped.
    """
    z, rays = np.asarray(camera_z, dtype=np.float64), np.asarray(unit_rays, dtype=np.float64)
    if rays.shape != (*z.shape, 3):
        raise ValueError("Camera-Z and unit rays must have matching dimensions")
    finite = np.isfinite(rays).all(axis=-1)
    if not np.allclose(np.linalg.norm(rays[finite], axis=-1), 1, atol=1e-7, rtol=1e-7):
        raise ValueError("Camera-Z conversion requires unit rays")
    valid = np.isfinite(z) & (z > 0) & finite & (rays[..., 2] > 1e-12)
    radial = np.full(z.shape, np.nan)
    np.divide(z, rays[..., 2], out=radial, where=valid)
    valid &= np.isfinite(radial)
    return np.where(valid, radial, np.nan), valid


def backproject_radial(radial, rgb, panorama_to_world, *, mask=None, stride=1):
    """Backproject calibrated ranges with an explicitly supplied rigid pose.

    Return (world_xyz, rgb, rows, columns). Translation and range must already
    share units. The caller owns measured-pose provenance; identity is not inferred.
    Mask/stride are sample selection only, never new estimated observations.
    """
    radial, rgb, pose = np.asarray(radial, dtype=np.float64), np.asarray(rgb), np.asarray(panorama_to_world, dtype=np.float64)
    if radial.ndim != 2:
        raise ValueError("Require a scalar ERP radial-range image")
    height, width = radial.shape
    _dimensions(height, width)
    if rgb.shape != (height, width, 3) or rgb.dtype != np.uint8:
        raise ValueError("Require matching uint8 RGB image; convert other encodings explicitly")
    if (pose.shape != (4, 4) or not np.isfinite(pose).all()
            or not np.allclose(pose[3], [0, 0, 0, 1], atol=1e-8, rtol=0)):
        raise ValueError("Require a finite homogeneous 4x4 panorama-to-world pose")
    rotation = pose[:3, :3]
    if (not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1, atol=1e-6, rtol=0)):
        raise ValueError("Pose rotation must be orthonormal and right-handed; no implicit scale")
    if not isinstance(stride, (int, np.integer)) or isinstance(stride, bool) or stride < 1:
        raise ValueError("Stride must be a positive integer")
    valid = np.isfinite(radial) & (radial > 0)
    if mask is not None:
        mask = np.asarray(mask)
        if mask.shape != radial.shape or mask.dtype != np.bool_:
            raise ValueError("Selection mask must be boolean and match the ERP")
        valid &= mask
    grid = np.zeros(radial.shape, dtype=bool)
    grid[::stride, ::stride] = True
    rows, columns = np.nonzero(valid & grid)
    rays = erp_pixel_rays(columns, rows, height, width)
    local = rays * radial[rows, columns, None]
    return local @ rotation.T + pose[:3, 3], rgb[rows, columns], rows, columns


def seam_diagnostics(values, mask=None):
    """Compare neighboring edge columns with ordinary horizontal neighbors.

    These are raw array discontinuities, not geometry accuracy or a quality gate.
    The seam joins distinct pixel centers, so exact edge equality is not expected.
    """
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("Seam diagnostics require a scalar ERP")
    _dimensions(*values.shape)
    valid = np.isfinite(values)
    if mask is not None:
        mask = np.asarray(mask)
        if mask.shape != values.shape or mask.dtype != np.bool_:
            raise ValueError("Seam mask must be boolean and match the ERP")
        valid &= mask
    seam = np.abs(values[:, -1] - values[:, 0])[valid[:, -1] & valid[:, 0]]
    interior = np.abs(np.diff(values, axis=1))[valid[:, :-1] & valid[:, 1:]]
    def stats(data):
        return {"pairs": int(data.size), "medianAbs": float(np.median(data)) if data.size else None,
                "p90Abs": float(np.quantile(data, .9)) if data.size else None,
                "maxAbs": float(np.max(data)) if data.size else None}
    a, b = stats(seam), stats(interior)
    ratio = a["medianAbs"] / b["medianAbs"] if a["pairs"] and b["pairs"] and b["medianAbs"] > 0 else None
    return {"seam": a, "interior": b, "medianSeamToInteriorRatio": ratio,
            "meaning": "Neighbor difference diagnostic only; no independent depth truth or pass threshold"}
