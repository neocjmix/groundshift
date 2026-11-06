"""Ray-based third-view diagnostics; all distances remain in the fixed SfM frame."""
import numpy as np


def rectified_ray_pixel(panorama_ray, camera_to_panorama, rectification, k, size):
    """Unit ERP ray -> OpenCV array-index pixel, not corner-origin pixel.

    Rectification maps original-camera column rays with R. It does not move
    the camera center. Behind-camera rays and finite-canvas edges are unsupported.
    """
    ray = np.asarray(panorama_ray, float) @ np.asarray(camera_to_panorama, float)
    rectified = ray @ np.asarray(rectification, float).T
    if not np.isfinite(rectified).all() or ray[2] <= 0 or rectified[2] <= 0:
        return None, None
    pixel = rectified[:2] / rectified[2] * [k[0, 0], k[1, 1]] + [k[0, 2], k[1, 2]]
    if not (0 <= pixel[0] < size[0]-1 and 0 <= pixel[1] < size[1]-1):
        return None, None
    return pixel, float(ray[2] / np.linalg.norm(ray))


def sample_supported_disparity(disparity, valid, xy, max_spread=2.):
    """Bilinear subpixel match only when all contributing neighbors are valid.

    Require a coherent 2px disparity neighborhood to avoid averaging different
    surfaces. Exact integer pixels need only their nonzero-weight neighbors.
    Unsupported samples stay unsupported; no nearest-valid-pixel fallback.
    """
    disparity, valid, xy = np.asarray(disparity), np.asarray(valid), np.asarray(xy, float)
    if disparity.ndim != 2 or valid.shape != disparity.shape or xy.shape != (2,):
        raise ValueError('Require a disparity plane, matching validity and one array-index xy')
    if not np.isfinite(xy).all():
        return None, 'outside-canvas'
    x, y = xy; h, w = disparity.shape
    if not (0 <= x < w-1 and 0 <= y < h-1):
        return None, 'outside-canvas'
    ix, iy = int(np.floor(x)), int(np.floor(y)); dx, dy = x-ix, y-iy
    weights = np.array([(1-dx)*(1-dy), dx*(1-dy), (1-dx)*dy, dx*dy])
    values = disparity[iy:iy+2, ix:ix+2].ravel(); supported = valid[iy:iy+2, ix:ix+2].ravel()
    used = weights > 1e-12
    if not (supported[used] & np.isfinite(values[used])).all():
        return None, 'lr-photo-unsupported'
    if np.ptp(values[used]) > max_spread:
        return None, 'disparity-discontinuity'
    return float(np.sum(values[used]*weights[used]) / weights[used].sum()), 'supported'


def rectified_to_corner(xy, rectification, k, params):
    """Rectified array-index coordinate -> original corner-origin camera xy."""
    xy = np.asarray(xy, float); params = np.asarray(params, float)
    ray = np.r_[(xy-[k[0, 2], k[1, 2]])/[k[0, 0], k[1, 1]], 1.] @ rectification
    if not np.isfinite(ray).all() or ray[2] <= 0:
        return None
    return ray[:2]/ray[2]*params[:2]+params[2:]


def third_view_residual(reference_xyz, observed_xyz, center5, center6):
    """Compare 4/5 and 5/6 triangulations, without calling either ground truth.

    Angle is wrapped seam-safe in 3D; relative radial difference uses the 5/6
    range from shared center5 as denominator. Cross-range in SfM units is
    perpendicular distance to the independently matched center6 ray.
    """
    reference, observed = np.asarray(reference_xyz, float), np.asarray(observed_xyz, float)
    a, b = reference-np.asarray(center6), observed-np.asarray(center6)
    if not np.isfinite([a, b]).all() or min(np.linalg.norm(a), np.linalg.norm(b)) <= 0:
        raise ValueError('Require finite nonzero third-view rays')
    ua, ub = a/np.linalg.norm(a), b/np.linalg.norm(b)
    angle = float(np.degrees(np.arctan2(np.linalg.norm(np.cross(ua, ub)), np.dot(ua, ub))))
    r45, r56 = np.linalg.norm(reference-np.asarray(center5)), np.linalg.norm(observed-np.asarray(center5))
    if min(r45, r56) <= 0:
        raise ValueError('Require positive shared-center ranges')
    return dict(angleDegrees=angle, relativeRangeDifference=float((r45-r56)/r56),
                crossRangeSfm=float(np.linalg.norm(np.cross(a, ub))),
                separationSfm=float(np.linalg.norm(reference-observed)))
