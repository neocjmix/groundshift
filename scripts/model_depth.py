"""Explicit alternative-depth calibration, without inventing metric scale."""
import numpy as np


def fit_depth(prediction, target, convention):
    x,y=np.asarray(prediction,float),np.asarray(target,float)
    if x.ndim!=1 or x.shape!=y.shape or len(x)<30 or not np.isfinite([x,y]).all() or np.any(y<=0):
        raise ValueError('Require >=30 finite training pairs and positive target distances')
    if convention in ('scale-camera-z','scale-radial'):
        if np.any(x<=0): raise ValueError('Scale-only depths must be positive')
        scale=float(np.exp(np.median(np.log(y)-np.log(x))));offset=0.
    elif convention=='affine-radial':
        if np.ptp(x)<1e-8: raise ValueError('Constant relative radial depth cannot be calibrated')
        a=np.c_[x,np.ones_like(x)];coef=np.linalg.lstsq(a,y,rcond=None)[0]
        for _ in range(20):
            residual=a@coef-y;mad=1.4826*np.median(np.abs(residual-np.median(residual)))+1e-9
            weights=np.minimum(1,1.345*mad/np.maximum(np.abs(residual),1e-12));root=np.sqrt(weights)
            coef=np.linalg.lstsq(a*root[:,None],y*root,rcond=None)[0]
        scale,offset=map(float,coef)
        if scale<=0: raise ValueError('Farther-is-larger radial prediction has nonpositive fitted slope')
    else: raise ValueError('Unknown depth convention; no implicit inverse or radial conversion')
    return dict(convention=convention,scale=scale,offset=offset,units='sfm-arbitrary',
                evidence='Original SfM plus count-balanced observed non5 stereo training tracks; not independent geometry truth')


def apply_depth(raw, fit, expected):
    if fit.get('convention')!=expected or fit.get('units')!='sfm-arbitrary' or not fit.get('evidence'):
        raise ValueError('Explicit matching calibration convention/evidence required')
    scale,offset=fit['scale'],fit['offset']
    if not np.isfinite([scale,offset]).all() or scale<=0: raise ValueError('Invalid calibration')
    result=np.asarray(raw,float)*scale+offset
    return np.where(np.isfinite(result)&(result>0),result,np.nan)


def range_to_z(radial, unit_crop_rays):
    radial,rays=np.asarray(radial,float),np.asarray(unit_crop_rays,float)
    if rays.shape!=(*radial.shape,3) or not np.isfinite(rays).all() or not np.allclose(np.linalg.norm(rays,axis=-1),1,atol=1e-7):
        raise ValueError('Range conversion requires matching unit camera rays')
    return np.where(np.isfinite(radial)&(radial>0)&(rays[...,2]>0),radial*rays[...,2],np.nan)
