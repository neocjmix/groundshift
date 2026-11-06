"""Explicit camera-Z to spherical range reprojection; no alignment or fusion.

Crop rotations map camera (+X right, +Y down, +Z forward) into panorama axes.
Pixel coordinates use corner origin, so array sampling subtracts one half.
"""
import numpy as np


def sample_plane(array, xy):
    array, xy = np.asarray(array, float), np.asarray(xy, float)
    if array.ndim != 2 or xy.shape[-1] != 2:
        raise ValueError('Require scalar perspective prediction and paired pixel coordinates')
    x, y = xy[..., 0] - .5, xy[..., 1] - .5
    h, w = array.shape
    valid = np.isfinite(x) & np.isfinite(y) & (x >= 0) & (x <= w-1) & (y >= 0) & (y <= h-1)
    x, y = np.where(valid, x, 0), np.where(valid, y, 0)
    x0, y0 = x.astype(int), y.astype(int)
    x1, y1 = np.minimum(x0+1, w-1), np.minimum(y0+1, h-1)
    dx, dy = x-x0, y-y0
    value = np.zeros_like(x)
    finite = valid.copy()
    for xx, yy, weight in [(x0,y0,(1-dx)*(1-dy)), (x1,y0,dx*(1-dy)),
                           (x0,y1,(1-dx)*dy), (x1,y1,dx*dy)]:
        samples = array[yy, xx]
        finite &= (weight == 0) | np.isfinite(samples)
        value += np.where(weight == 0, 0, samples) * weight
    return np.where(finite, value, np.nan)


def crop_ranges(prediction, calibration, rotation, rays, params):
    """Return radial range and centrality for front-facing supported sphere rays."""
    rotation, rays, params = np.asarray(rotation,float), np.asarray(rays,float), np.asarray(params,float)
    if (rotation.shape != (3,3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-8)
            or not np.isclose(np.linalg.det(rotation), 1)):
        raise ValueError('Require right-handed camera-to-panorama rotation')
    if rays.shape[-1] != 3 or not np.isfinite(rays).all() or not np.allclose(np.linalg.norm(rays,axis=-1),1):
        raise ValueError('Require unit panorama bearings')
    if params.shape != (4,) or not np.isfinite(params).all() or np.any(params[:2] <= 0):
        raise ValueError('Require fx,fy,cx,cy')
    if (calibration.get('convention') != 'inverse-camera-z'
            or calibration.get('units') != 'sfm-arbitrary'
            or not np.isfinite([calibration['scale'],calibration['offset']]).all()
            or calibration['scale'] <= 0):
        raise ValueError('Require explicit calibrated inverse camera-Z in shared SfM units')
    q = rays @ rotation
    with np.errstate(divide='ignore',invalid='ignore'):
        xy = q[...,:2] / q[...,2,None] * params[:2] + params[2:]
        raw = sample_plane(prediction, xy)
        inverse = calibration['scale'] * raw + calibration['offset']
        radial = 1 / inverse / q[...,2]
    valid = (q[...,2] > 0) & (inverse > 0) & np.isfinite(radial) & (radial > 0)
    return np.where(valid,radial,np.nan), np.where(valid,q[...,2],-np.inf)


def stitch_ranges(ranges, centrality, log_band):
    """Select most central supported crop; keep disagreement and coverage evidence.

    Selection is angular sampling policy, not learned confidence. Consensus only
    tests same-center predictions; it is not an occlusion test or depth accuracy.
    A log-band is explicitly supplied by the experiment, never inferred here.
    """
    ranges, centrality = np.asarray(ranges,float), np.asarray(centrality,float)
    if ranges.ndim != 3 or ranges.shape != centrality.shape or ranges.shape[0] < 1:
        raise ValueError('Require matching crop x height x width arrays')
    if not np.isfinite(log_band) or log_band < 0:
        raise ValueError('Require explicit finite nonnegative log disagreement band')
    valid = np.isfinite(ranges) & (ranges > 0) & np.isfinite(centrality) & (centrality > 0)
    support = valid.sum(axis=0)
    winner = np.argmax(np.where(valid,centrality,-np.inf),axis=0)
    best = np.take_along_axis(ranges,winner[None],axis=0)[0]
    best = np.where(support > 0,best,np.nan)
    logs = np.log(np.where(valid,ranges,1))
    spread = np.max(np.where(valid,logs,-np.inf),axis=0)-np.min(np.where(valid,logs,np.inf),axis=0)
    spread = np.where(support > 0,spread,np.nan)
    consensus = (support >= 2) & (spread <= log_band)
    return dict(radial=best, winner=np.where(support>0,winner,-1),support=support,
                log_spread=spread,consensus=consensus)
