#!/usr/bin/env python3
"""Calibrate actual alternative predictions and make matched real-image GS input."""
import argparse
import importlib.util
from pathlib import Path
import time
import numpy as np
from PIL import Image
from model_depth import fit_depth,apply_depth,range_to_z,outside_camera_proximity
from perspective_sphere import sample_plane
from spherical_depth import directions_to_erp,sample_erp_bilinear
from street_geometry import held_id,project_world,voxel_reduce,validate_stereo_report


def module(name,file):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


R=module('reconstruct_street','reconstruct-street.py');P=R.P
BASE=P.ROOT/'data/jobs/street-conclusion-20261106'


def main(a):
    import re
    variant=a.variant or a.model
    if not re.fullmatch('[a-z][a-z0-9-]*',variant) or not np.isfinite(a.proximity_floor) or a.proximity_floor<0:raise ValueError('Require safe local variant and nonnegative SfM proximity floor')
    job=a.job.resolve();out=job/('fusion-'+variant);out.mkdir(parents=True,exist_ok=False)
    before=time.monotonic();report=dict(status='RUNNING',startedAt=P.now(),model=a.model)
    try:
        folder=job/a.model;inference=P.read(folder/'report.json')
        if inference['status']!='PASS' or inference['physicalCenters']!=[1,2,3,4,6,7,8,9]:raise ValueError('Require complete actual non5 inference')
        kind=inference['convention'];erp=kind.endswith('radial');records={r['id']:r for r in inference['images']}
        for ident,row in records.items():
            if P.sha(folder/(ident+'.npy'))!=row['rawSha256']:raise ValueError('Raw prediction changed')
        frames=P.read(job/'inputs/transforms.json')['frames'];anchors=P.read(job/'anchors-training-colors/anchors.json');poses=P.panorama_poses()
        stereo=BASE/'stereo';validate_stereo_report(P.read(stereo/'report.json'),allow_partial=True)
        if P.sha(stereo/'tracks.npz')!=P.read(stereo/'report.json')['tracksSha256']:raise ValueError('Stereo tracks changed')
        sd=dict(np.load(stereo/'tracks.npz'))
        if np.any(sd['physical']==5):raise ValueError('Withheld stereo leakage')
        calibration_samples={};held_samples={};maps={};camera={}
        for frame in frames:
            name=Path(frame['file_path']).name;p=frame['physicalPanorama'];pose=np.array(frame['transform_matrix'])@np.diag([1,-1,-1,1]);rotation=R.C.crop_rotation(frame['yaw'],frame['pitch'])
            key=f'p{p:02d}' if erp else Path(name).stem
            raw=np.load(folder/(key+'.npy'));row=records[key]
            expected=P.read(P.ROOT/'scripts/samples/mapillary-beijing.json')['images'][p-1]['sha256'] if erp else P.sha(job/'inputs'/frame['file_path'])
            if row['sourceSha256']!=expected:raise ValueError('Source image changed')
            # Sphere uses one fit per physical center. DA3 uses one shared scale
            # per multi-view inference group, preserving its relative depths.
            group=key if erp else row.get('group',key)
            if group not in calibration_samples:calibration_samples[group]=[];held_samples[group]=[]
            if not erp or group not in maps:
                rows=anchors[str(p)];xyz=np.array([r['xyz'] for r in rows]);held=np.array([held_id(r['id']) for r in rows])
                if erp:
                    rays=np.array([r['rayPanorama'] for r in rows]);u,v=directions_to_erp(rays,*raw.shape);x=sample_erp_bilinear(raw,u,v);target=np.linalg.norm(xyz-poses[p][:3,3],axis=-1)
                    valid=np.isfinite(x)&(target>0)
                else:
                    xy,target=project_world(xyz,pose,[256]*4);x=sample_plane(raw,xy);valid=np.isfinite(x)&(target>0)
                tx,ty=x[valid&~held],target[valid&~held];n=len(tx)
                select=np.any(sd['physical']==p,axis=1)&sd['training'];sx=sd['xyz'][select]
                if erp:
                    local=(sx-poses[p][:3,3])@poses[p][:3,:3];u,v=directions_to_erp(local,*raw.shape);sv=sample_erp_bilinear(raw,u,v);st=np.linalg.norm(local,axis=-1)
                else:
                    xy,st=project_world(sx,pose,[256]*4);sv=sample_plane(raw,xy)
                good=np.isfinite(sv)&(st>0);sv,st=sv[good],st[good]
                take=np.linspace(0,len(sv)-1,min(n,len(sv)),dtype=int) if len(sv) else np.empty(0,int)
                tx=np.r_[tx,sv[take]];ty=np.r_[ty,st[take]]
                calibration_samples[group].append((tx,ty));held_samples[group].append((x[valid&held],target[valid&held]))
            maps[group]=True;camera[name]=(frame,pose,rotation,key,group)
        fits={};residuals=[]
        for group,pairs in calibration_samples.items():
            x=np.concatenate([r[0] for r in pairs]);y=np.concatenate([r[1] for r in pairs]);fit=fit_depth(x,y,kind);fits[group]=fit
            hx=np.concatenate([r[0] for r in held_samples[group]]);hy=np.concatenate([r[1] for r in held_samples[group]]);pred=apply_depth(hx,fit,kind);valid=np.isfinite(pred)
            residual=np.abs(pred[valid]/hy[valid]-1)
            residuals.append(dict(group=group,training=len(x),held=len(hx),heldValid=int(valid.sum()),heldInvalid=int((~valid).sum()),heldAbsRelMedian=float(np.median(residual)) if len(residual) else None,heldAbsRelP90=float(np.quantile(residual,.9)) if len(residual) else None,fit=fit))
        P.write(out/'calibrations.json',residuals)
        points=[];colors=[];coverage=[];yy,xx=np.indices((512,512));ray=np.stack([(xx+.5-256)/256,(yy+.5-256)/256,np.ones((512,512))],axis=-1);unit=ray/np.linalg.norm(ray,axis=-1,keepdims=True)
        for name,(frame,pose,rotation,key,group) in camera.items():
            p=frame['physicalPanorama'];raw=np.load(folder/(key+'.npy'))
            if erp:
                u,v=directions_to_erp(unit@rotation.T,*raw.shape);raw=sample_erp_bilinear(raw,u,v)
                z=range_to_z(apply_depth(raw,fits[group],kind),unit)
            else:z=apply_depth(raw,fits[group],kind)
            _,v=directions_to_erp(unit@rotation.T,546,1092)
            cap=np.quantile(np.linalg.norm(np.array([r['xyz'] for r in anchors[str(p)]])-poses[p][:3,3],axis=-1),.99)
            mask=(np.asarray(Image.open(job/'inputs/masks'/name))>0)&((v+.5)/546>=.40)&np.isfinite(z)&(z>0)&(z/unit[:,:,2]<=cap)
            z=np.where(mask,z,np.nan);np.save(out/(name+'.z.npy'),z.astype(np.float32))
            xyz=(ray[::3,::3]*z[::3,::3,None]).reshape(-1,3)@pose[:3,:3].T+pose[:3,3];rgb=np.array(Image.open(job/'inputs/images'/name).convert('RGB'))[::3,::3].reshape(-1,3);valid=np.isfinite(xyz).all(axis=1)
            points.append(xyz[valid]);colors.append(rgb[valid]);coverage.append(dict(file=name,validPixels=int(mask.sum()),candidates=int(valid.sum())))
        spacing=float(np.median([np.linalg.norm(poses[p+1][:3,3]-poses[p][:3,3]) for p in range(1,9)]))/120
        xyz,rgb=voxel_reduce(np.concatenate(points),np.concatenate(colors),spacing)
        rejected=0
        if a.proximity_floor:
            centers=np.array([poses[p][:3,3] for p in [1,2,3,4,6,7,8,9]])
            keep=outside_camera_proximity(xyz,centers,a.proximity_floor)
            rejected=int((~keep).sum());xyz,rgb=xyz[keep],rgb[keep]
        R.CAL.D.CAL.write_ply(out/'full.ply',xyz,rgb)
        take=np.linspace(0,len(xyz)-1,min(len(xyz),180000),dtype=int);old_xyz,old_rgb=R.sparse_seed(job)
        dest=R.dataset(job,variant,np.r_[old_xyz,xyz[take]],np.r_[old_rgb,rgb[take]],f'Actual {a.model} {kind}; explicit {len(fits)} calibration groups; common sparse points and real non5 RGB. Numerical proximity exclusion {a.proximity_floor} SfM units, not measured free space. No independent geometric accuracy or measured metric claim.')
        report.update(status='PASS',qualityStatus='NOT ACCEPTED',variant=variant,convention=kind,calibrationGroups=len(fits),points=len(old_xyz)+len(take),fullDensePoints=len(xyz),voxelSpacingSfm=spacing,coverage=coverage,proximityFloorSfm=a.proximity_floor,proximityRejected=rejected,initialPlySha256=P.sha(dest/'init.ply'),sourceInferenceSha256=P.sha(folder/'report.json'))
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:report.update(finishedAt=P.now(),elapsedSeconds=time.monotonic()-before);P.write(out/'report.json',report)
    print(a.model,report['status'],report['points'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('model',choices=['panda','da2','moge','da3','depthmaster']);p.add_argument('--variant');p.add_argument('--proximity-floor',type=float,default=0);main(p.parse_args())
