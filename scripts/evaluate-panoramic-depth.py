#!/usr/bin/env python3
"""Calibrate one ERP prediction to fixed-rig sparse ranges, retaining uncertainty."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import traceback

import numpy as np
from PIL import Image
from spherical_depth import (sample_erp_bilinear, calibrated_radial, calibrated_inverse_radial,
                             backproject_radial, directions_to_erp, seam_diagnostics)


def write(path, data): path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def split_ids(ids):
    """Deterministic point-ID holdout: no target ranges enter split decisions."""
    return np.array([int(hashlib.sha256(str(int(i)).encode()).hexdigest()[:8],16)%5 == 0 for i in ids])


def fit_calibration(prediction, radial, kind):
    x,y=np.asarray(prediction,float),np.asarray(radial,float)
    if x.ndim != 1 or y.shape != x.shape or len(x)<30 or not np.isfinite(x).all() or not np.isfinite(y).all() or np.any(y<=0):
        raise ValueError('Require >=30 finite paired training values and positive SfM radial ranges')
    if kind=='da2':
        if np.any(x<=0): raise ValueError('DA2 radial predictions must be positive')
        scale=float(np.exp(np.median(np.log(y)-np.log(x))));offset=0.
        convention='ray-range';method='Median log-range ratio on training anchors only; scale-only'
    elif kind=='dav2':
        if np.ptp(x)<1e-8: raise ValueError('Cannot calibrate constant inverse-depth prediction')
        target=1/y;A=np.column_stack([x,np.ones_like(x)]);coef=np.linalg.lstsq(A,target,rcond=None)[0]
        for _ in range(20):
            residual=A@coef-target;mad=1.4826*np.median(np.abs(residual-np.median(residual)))+1e-9
            weights=np.minimum(1,1.345*mad/np.maximum(np.abs(residual),1e-12));root=np.sqrt(weights)
            coef=np.linalg.lstsq(A*root[:,None],target*root,rcond=None)[0]
        scale,offset=map(float,coef);convention='inverse-ray-range';method='Huber IRLS affine inverse-range fit on training anchors only'
        if scale<=0: raise ValueError('Expected closer-is-larger prediction did not give positive inverse-range slope')
    else: raise ValueError('Unknown model; no silent semantic substitution')
    return dict(convention=convention,scale=scale,offset=offset,units='sfm-arbitrary',
                source='Existing fixed-rig SfM observed point anchors; all-image geometry, not independent truth',method=method)


def apply_calibration(prediction, calibration):
    if calibration['convention']=='ray-range': return calibrated_radial(prediction,calibration)
    return calibrated_inverse_radial(prediction,calibration)


def residual_stats(predicted,target):
    predicted,target=np.asarray(predicted,float),np.asarray(target,float)
    if predicted.ndim!=1 or target.shape!=predicted.shape:raise ValueError('Require paired 1D residual samples')
    valid=np.isfinite(predicted)&(predicted>0)&np.isfinite(target)&(target>0)
    delta=np.abs(predicted[valid]-target[valid]);rel=delta/target[valid]
    return dict(samples=len(target),validSamples=int(valid.sum()),invalidSamples=int((~valid).sum()),
                medianAbsRel=float(np.median(rel)) if len(rel) else None,p90AbsRel=float(np.quantile(rel,.9)) if len(rel) else None,
                medianAbsoluteSfmUnits=float(np.median(delta)) if len(delta) else None,
                meaning='Residual to withheld calibration tracks from same SfM, not independent geometry accuracy')


def write_ply(path, xyz, rgb):
    data=np.empty(len(xyz),dtype=[('x','<f4'),('y','<f4'),('z','<f4'),('red','u1'),('green','u1'),('blue','u1')])
    for j,k in enumerate(['x','y','z']):data[k]=xyz[:,j]
    for j,k in enumerate(['red','green','blue']):data[k]=rgb[:,j]
    header=f'ply\nformat binary_little_endian 1.0\ncomment calibrated SfM arbitrary units; estimated geometry, not meters\nelement vertex {len(data)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n'
    with path.open('wb') as f:f.write(header.encode());data.tofile(f)


def browser_cloud(path, xyz, rgb, pose):
    center=np.median(xyz,axis=0);radius=float(np.quantile(np.linalg.norm(xyz-center,axis=1),.90))
    up=pose[:3,:3]@np.array([0.,-1,0]);forward=pose[:3,:3]@np.array([0.,0,1]);side=pose[:3,:3]@np.array([1.,0,0])
    write(path,dict(positions=np.round(xyz,6).reshape(-1).tolist(),colors=rgb.reshape(-1).tolist(),center=center.tolist(),radius=radius,
                   camera=dict(position=(center+up*radius*.8-forward*radius*1.2+side*radius*.4).tolist(),up=up.tolist(),target=center.tolist(),fov=65),
                   capture=dict(position=pose[:3,3].tolist(),up=up.tolist(),target=(pose[:3,3]+forward*radius*.5).tolist())))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('inference',type=Path);p.add_argument('anchors',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();report=dict(status='RUNNING',startedAt=datetime.now(timezone.utc).isoformat())
    try:
        inference=json.loads((args.inference/'inference.json').read_text());anchors=json.loads(args.anchors.read_text())
        if inference['status']!='PASS' or anchors['status']!='PASS':raise ValueError('Require executed inference and preserved pose evidence')
        if inference['sourceSha256']!=anchors['source']['sha256']:raise ValueError('Image differs from SfM anchor source')
        raw=np.load(args.inference/'raw.npy');rgb=np.array(Image.open(args.inference/'source.png').convert('RGB'));h,w=raw.shape
        if list(rgb.shape[:2]) != [h,w]:raise ValueError('RGB and depth shapes differ')
        items=anchors['anchors'];uv=np.array([a['erpNormalizedUv'] for a in items]);target=np.array([a['radialRangeSfm'] for a in items]);ids=np.array([a['point3DId'] for a in items])
        values=sample_erp_bilinear(raw,uv[:,0]*w-.5,uv[:,1]*h-.5);held=split_ids(ids)
        calibration=fit_calibration(values[~held],target[~held],inference['model'])
        ranges,valid=apply_calibration(raw,calibration);anchor_ranges,_=apply_calibration(values,calibration)
        calibration.update(trainingSamples=int((~held).sum()),heldOutSamples=int(held.sum()))
        # Explicit conservative mask, fixed before inspecting model outputs. Loses upper surfaces.
        rows=(np.arange(h)+.5)/h
        band=np.broadcast_to(((rows>=.48)&(rows<=.85))[:,None],raw.shape)
        supported_max=float(np.quantile(target[~held],.99));filtered=valid&band&(ranges<=supported_max)
        np.save(args.output/'range-sfm.npy',ranges.astype(np.float32));np.save(args.output/'valid.npy',valid);np.save(args.output/'filtered.npy',filtered)
        Image.fromarray(filtered.astype(np.uint8)*255).save(args.output/'mask.png')
        if not valid.any():raise ValueError('Calibration has no positive finite full-sphere ranges')
        low,high=np.quantile(ranges[valid],[.02,.98]);high=max(high,low+1e-9);visual=np.zeros(raw.shape,dtype=np.uint8);visual[valid]=(np.clip((ranges[valid]-low)/(high-low),0,1)*255).astype(np.uint8)
        Image.fromarray(visual).save(args.output/'range.png')
        pose=np.array(anchors['worldFromPanorama']);counts={};reprojection={}
        for name,mask in [('cloud-all',valid),('cloud',filtered)]:
            xyz,colors,rr,cc=backproject_radial(ranges,rgb,pose,mask=mask,stride=3)
            if len(xyz)==0:raise ValueError(f'No valid points for {name}')
            write_ply(args.output/f'{name}.ply',xyz,colors);browser_cloud(args.output/f'{name}.json',xyz,colors,pose);counts[name]=len(xyz)
            local=(xyz-pose[:3,3])@pose[:3,:3];pu,pv=directions_to_erp(local,h,w);du=(pu-cc+w/2)%w-w/2
            reprojection[name]=dict(maxPixelError=float(np.max(np.hypot(du,pv-rr))),maxRangeError=float(np.max(np.abs(np.linalg.norm(local,axis=1)-ranges[rr,cc]))),meaning='Algebraic self-reprojection, not an accuracy measurement')
        per_sector=[]
        for sector in range(12):
            selected=held&(uv[:,0]>=sector/12)&(uv[:,0]<(sector+1)/12)
            per_sector.append(dict(longitudeDegrees=[sector*30-180,(sector+1)*30-180],**residual_stats(anchor_ranges[selected],target[selected])))
        lat=(.5-(np.arange(h)+.5)/h)*np.pi;area=np.broadcast_to(np.cos(lat)[:,None],raw.shape)
        report.update(status='PASS',model=inference['model'],sourceSha256=inference['sourceSha256'],anchorsSha256=sha(args.anchors),
                      calibration=calibration,heldOut=residual_stats(anchor_ranges[held],target[held]),training=residual_stats(anchor_ranges[~held],target[~held]),
                      heldOutByLongitude=per_sector,coverageFraction=float(filtered.mean()),solidAngleCoverageFraction=float(area[filtered].sum()/area.sum()),
                      validFraction=float(valid.mean()),points=counts,maskPolicy=dict(rowsNormalized=[.48,.85],maxRangeSfm=supported_max,
                      reason='Conservative upper-sky and bottom branding exclusion plus training-anchor 99th-percentile range support. Not semantic segmentation or model confidence.'),
                      predictionSeam=seam_diagnostics(raw),rangeSeam=seam_diagnostics(ranges),filteredSeam=seam_diagnostics(ranges,filtered),
                      selfReprojection=reprojection,anchorCoverage=anchors['coverage'],worldFromPanorama=pose.tolist(),
                      metricScale='NOT RUN',independentGeometry='NOT RUN',crossPanoramaConsistency='NOT RUN',gaussianTraining='NOT RUN: outside bounded P1 scope')
        write(args.output/'calibration-samples.json',dict(pointIds=ids.tolist(),heldOut=held.tolist(),predictions=values.tolist(),radialSfm=target.tolist(),calibratedRanges=[float(x) if np.isfinite(x) else None for x in anchor_ranges]))
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(finishedAt=datetime.now(timezone.utc).isoformat(),elapsedSeconds=time.monotonic()-started);write(args.output/'geometry.json',report)

if __name__=='__main__':main()
