#!/usr/bin/env python3
"""Read-only paired overlap and neighboring-center diagnostics, no new fitting."""
import argparse
import importlib.util
from pathlib import Path
import time
import numpy as np
from PIL import Image
from tangent_geometry import project_rays
from perspective_sphere import sample_plane
from spherical_depth import erp_unit_rays,backproject_radial,directions_to_erp,sample_erp_bilinear

spec=importlib.util.spec_from_file_location('tangent',Path(__file__).with_name('reconstruct-tangent.py'))
T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)
P,C=T.P,T.C


def quantiles(values):
    v=np.asarray(values,float);v=v[np.isfinite(v)]
    return dict(samples=len(v),median=float(np.median(v)) if len(v) else None,p90=float(np.quantile(v,.9)) if len(v) else None)


def run(job):
    out=job/'diagnostics';out.mkdir(parents=True,exist_ok=False);start=time.monotonic();report=dict(status='RUNNING',sameCenter=[],neighborCenter=[])
    try:
        frames=P.read(job/'inputs-tangent/transforms.json')['frames'];fits=P.read(job/'fusion-tangent/calibrations.json');inference=P.read(job/'depth/report.json');lookup={Path(v['source']).name:i for i,v in enumerate(inference['images'])}
        rays=erp_unit_rays(128,256);vertical=np.broadcast_to(((np.arange(128)+.5)/128)[:,None],(128,256));band=(vertical>=.25)&(vertical<=.85)
        for physical in [1,2,3,4,6,7,8,9]:
            summary=next(x for x in P.read(job/'fusion-tangent/report.json')['physical'] if x['id']==physical);cap=summary['capSfm'];before=[];after=[]
            for fit in [f for f in fits if f['status']=='PASS' and f['physical']==physical]:
                frame=next(f for f in frames if Path(f['file_path']).name==fit['file']);raw=np.load(job/f'depth/view-{lookup[fit["file"]]:02d}-relative.npy')
                xy,cos,inside=project_rays(rays,C.crop_rotation(frame['yaw'],frame['pitch']),[frame[k] for k in ['fl_x','fl_y','cx','cy']],frame['w']);value=sample_plane(raw,xy)
                with np.errstate(divide='ignore',invalid='ignore'):
                    a=1/(cos*(fit['initial']['scale']*value+fit['initial']['offset']));b=1/(cos*(fit['scale']*value+fit['offset']))
                before.append(np.where(inside,a,np.nan));after.append(np.where(inside,b,np.nan))
            a,b=np.array(before),np.array(after);common=np.isfinite(a)&np.isfinite(b)&(a>0)&(b>0)&(a<=cap)&(b<=cap);select=band&(common.sum(axis=0)>=2)
            def spread(v):
                logs=np.log(np.where(common,v,1));return (np.max(np.where(common,logs,-np.inf),axis=0)-np.min(np.where(common,logs,np.inf),axis=0))[select]
            report['sameCenter'].append(dict(physical=physical,commonRays=int(select.sum()),sameCropMembership=True,before=quantiles(spread(a)),after=quantiles(spread(b)),meaning='Same raw RGB/physical center; internal agreement only. Identical ray and valid crop membership for before/after.'))
        poses=P.panorama_poses();physical=[1,2,3,4,6,7,8,9];ranges={p:np.load(job/f'fusion-tangent/p{p:02d}-range.npy') for p in physical};sources=sorted((P.ROOT/'data/samples/mapillary-beijing/images').glob('*.jpg'));rgb={}
        for p in physical:
            with Image.open(sources[p-1]) as im:rgb[p]=np.array(im.convert('RGB').resize((1024,512),Image.Resampling.LANCZOS))
        for p in physical:
            xyz,color,_,_=backproject_radial(ranges[p],rgb[p],poses[p],stride=4);take=np.linspace(0,len(xyz)-1,min(3000,len(xyz)),dtype=int);xyz,color=xyz[take],color[take]
            for q in sorted([v for v in physical if v!=p],key=lambda v:np.linalg.norm(poses[p][:3,3]-poses[v][:3,3]))[:2]:
                local=(xyz-poses[q][:3,3])@poses[q][:3,:3];distance=np.linalg.norm(local,axis=1);u,v=directions_to_erp(local,512,1024);target=sample_erp_bilinear(ranges[q],u,v);other=sample_erp_bilinear(rgb[q],u,v);valid=np.isfinite(target)&(target>0)
                error=np.abs(distance[valid]/target[valid]-1);color_error=np.mean(np.abs(color[valid].astype(float)-other[valid]),axis=1)
                report['neighborCenter'].append(dict(source=p,target=q,sampled=len(xyz),comparable=int(valid.sum()),invalid=int((~valid).sum()),absRelativeRange=quantiles(error),rgbMae=quantiles(color_error),meaning='Estimated pose/depth cross-view disagreement; occlusion and dynamic objects unresolved. Not independent measured error.'))
        report.update(status='PASS',fusionSha256=P.sha(job/'fusion-tangent/report.json'),calibrationSha256=P.sha(job/'fusion-tangent/calibrations.json'),geometryStatus='NOT ACCEPTED')
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=P.now(),elapsedSeconds=time.monotonic()-start);P.write(out/'report.json',report)
    print(report['status'],'paired overlap',[(r['physical'],r['before']['median'],r['after']['median']) for r in report['sameCenter']])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);a=p.parse_args();run(a.job.resolve())
