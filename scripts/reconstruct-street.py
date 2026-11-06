#!/usr/bin/env python3
"""Build matched sparse/dense/filtered datasets; train with existing native adapter."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import time
import resource
import numpy as np
from PIL import Image
from perspective_sphere import sample_plane
from spherical_depth import directions_to_erp
from street_geometry import held_id,project_world,depth_support,voxel_reduce,validate_stereo_report

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

P=module('prepare','prepare-street.py');C=module('crop','prepare-panoramas.py');CAL=module('calibration','compare-perspective-depth.py')
read,write,sha,now=P.read,P.write,P.sha,P.now


def dataset(job,variant,xyz,rgb,notes):
    out=job/'datasets'/variant;out.mkdir(parents=True,exist_ok=False)
    source=job/'inputs';transforms=read(source/'transforms.json');training=[f for f in transforms['frames'] if f['physicalPanorama']!=5]
    if len(training)!=96 or len(training)!=len(transforms['frames']):raise ValueError('Withheld RGB entered trainer frames')
    for folder in ['images','masks']:
        (out/folder).mkdir()
        for f in training:shutil.copyfile(source/folder/Path(f['file_path']).name,out/folder/Path(f['file_path']).name)
    transforms['ply_file_path']='init.ply';write(out/'transforms.json',transforms)
    provenance=read(source/'provenance.json');provenance['notes']+=' '+notes
    write(out/'provenance.json',provenance);shutil.copyfile(source/'LICENSE',out/'LICENSE')
    CAL.D.CAL.write_ply(out/'init.ply',xyz,rgb)
    return out


def sparse_seed(job):
    rows=read(job/'anchors-training-colors/sparse.json')
    if any(int(r['colorSource'].split('_')[1])==5 for r in rows):raise ValueError('Withheld RGB point color leakage')
    return np.array([r['xyz'] for r in rows]),np.array([r['rgb'] for r in rows],np.uint8)


def baseline(job):
    xyz,rgb=sparse_seed(job);out=dataset(job,'sparse',xyz,rgb,'Sparse SfM seed, recolored from actual non5 training pixels. No learned depth initialization.')
    write(job/'sparse-preparation.json',dict(status='PASS',points=len(xyz),initialPlySha256=sha(out/'init.ply'),finishedAt=now()))
    print('Sparse seed',len(xyz))


def fuse(job,stereo=None,allow_partial=False):
    out=job/'fusion';out.mkdir(parents=True,exist_ok=False);start=time.monotonic();report=dict(status='RUNNING',startedAt=now())
    try:
        inference=read(job/'depth/report.json')
        if inference['status']!='PASS' or inference['device']!='mps' or inference['revision']!='5426e4f0f36572d16453bbda7a8389317b1bef99':raise ValueError('Require actual pinned DAV2 MPS inference')
        frames=read(job/'inputs/transforms.json')['frames'];anchors=read(job/'anchors-training-colors/anchors.json');poses=P.panorama_poses()
        depths={};rgbs={};definitions={};fits=[];old_xyz,old_rgb=sparse_seed(job)
        spacing=float(np.median([np.linalg.norm(poses[p+1][:3,3]-poses[p][:3,3]) for p in range(1,9)]))/120
        cap={p:float(np.quantile(np.linalg.norm(np.array([a['xyz'] for a in anchors[str(p)]])-poses[p][:3,3],axis=1),.99)) for p in poses}
        indexed={Path(r['source']).name:(i,r) for i,r in enumerate(inference['images'])}
        partial=False
        if stereo:
            stereo_report=read(stereo/'report.json');partial=validate_stereo_report(stereo_report,allow_partial)
            if sha(stereo/'tracks.npz')!=stereo_report['tracksSha256']:raise ValueError('Stereo points changed')
        stereodata=dict(np.load(stereo/'tracks.npz')) if stereo else None
        if stereodata is not None and np.any(stereodata['physical']==5):raise ValueError('Withheld RGB entered new stereo initialization')
        for frame in frames:
            name=Path(frame['file_path']).name;p=frame['physicalPanorama'];rotation=C.crop_rotation(frame['yaw'],frame['pitch'])
            pose=np.array(frame['transform_matrix'])@np.diag([1,-1,-1,1]);i,record=indexed[name]
            if record['sourceSha256']!=sha(job/'inputs/images'/name) or record['relativeNpySha256']!=sha(job/f'depth/view-{i:02d}-relative.npy'):raise ValueError('Depth input/output changed')
            raw=np.load(job/f'depth/view-{i:02d}-relative.npy');rows=anchors[str(p)];rays=np.array([a['rayPanorama'] for a in rows])@rotation
            with np.errstate(divide='ignore',invalid='ignore'):xy=rays[:,:2]/rays[:,2,None]*256+256
            prediction=sample_plane(raw,xy);xyz=np.array([a['xyz'] for a in rows]);z=((xyz-pose[:3,3])@pose[:3,:3])[:,2]
            held=np.array([held_id(a['id']) for a in rows]);valid=(rays[:,2]>0)&(z>0)&np.isfinite(prediction)
            px,zz=prediction[valid&~held],z[valid&~held];sfm_count=len(px);stereo_count=0
            if stereodata is not None:
                select=np.any(stereodata['physical']==p,axis=1)&stereodata['training']
                sxy,sz=project_world(stereodata['xyz'][select],pose,[256]*4);sx=sample_plane(raw,sxy);ok=np.isfinite(sx)&(sz>0)
                sx,sz=sx[ok],sz[ok]
                # Balance nearby dense correspondences against original SfM
                # evidence, rather than letting road matches erase far anchors.
                take=np.linspace(0,len(sx)-1,min(len(sx),sfm_count),dtype=int) if len(sx) else np.empty(0,int)
                px=np.r_[px,sx[take]];zz=np.r_[zz,sz[take]];stereo_count=len(take)
            item=dict(file=name,physical=p,sfmTrainingSamples=sfm_count,stereoTrainingSamples=stereo_count,heldSamples=int((valid&held).sum()),status='RUNNING')
            try:
                fit=CAL.camera_z_fit(px,zz);inverse=fit['scale']*raw+fit['offset']
                with np.errstate(divide='ignore',invalid='ignore'):depth=1/inverse
                mask=np.asarray(Image.open(job/'inputs/masks'/name))>0
                yy,xx=np.indices(raw.shape);ray=np.stack([(xx+.5-256)/256,(yy+.5-256)/256,np.ones(raw.shape)],axis=-1)
                unit=ray/np.linalg.norm(ray,axis=-1,keepdims=True);pano=unit@rotation.T;_,v=directions_to_erp(pano,546,1092)
                radial=depth*np.linalg.norm(ray,axis=-1)
                good=mask&((v+.5)/546>=.40)&np.isfinite(depth)&(depth>0)&(inverse>0)&(radial<=cap[p])
                depth=np.where(good,depth,np.nan)
                held_pred=1/(fit['scale']*prediction[valid&held]+fit['offset'])
                target=z[valid&held];hv=np.isfinite(held_pred)&(held_pred>0)
                residual=np.abs(held_pred[hv]/target[hv]-1)
                item.update(status='PASS',fit=fit,validPixels=int(good.sum()),heldValid=int(hv.sum()),heldInvalid=int((~hv).sum()),heldAbsRelMedian=float(np.median(residual)) if len(residual) else None,heldAbsRelP90=float(np.quantile(residual,.9)) if len(residual) else None)
                depths[name]=depth;rgbs[name]=np.asarray(Image.open(job/'inputs/images'/name).convert('RGB'));definitions[name]=(frame,pose)
                np.save(out/(name+'.z.npy'),depth.astype(np.float32))
                # Comparable inverse-depth visualization; not metric depth.
                lo,hi=np.quantile(raw,[.02,.98]);show=np.clip((raw-lo)/max(hi-lo,1e-9),0,1)*255
                Image.fromarray(show.astype(np.uint8)).save(out/(name+'.relative.png'))
            except ValueError as error:item.update(status='FAIL',error=str(error),usedForDenseInitialization=False)
            fits.append(item)
        write(out/'calibrations.json',fits)
        dense_points=[];dense_colors=[];filtered_points=[];filtered_colors=[];coverage=[]
        for name,depth in depths.items():
            frame,pose=definitions[name];p=frame['physicalPanorama'];y,x=np.mgrid[0:512:3,0:512:3];z=depth[y,x]
            ray=np.stack([(x+.5-256)/256,(y+.5-256)/256,np.ones_like(x)],axis=-1)
            xyz=(ray*z[:,:,None]).reshape(-1,3)@pose[:3,:3].T+pose[:3,3];color=rgbs[name][y,x].reshape(-1,3)
            valid=np.isfinite(xyz).all(axis=1)&(z.ravel()>0);xyz=xyz[valid];color=color[valid]
            supported=np.zeros(len(xyz),bool);compared=np.zeros(len(xyz),bool);consistency=[]
            # Different physical centers only. Same-sphere crops provide no
            # stereo baseline. Depth/RGB agreement is a diagnostic heuristic.
            neighbors=sorted([q for q in poses if q!=p and q!=5],key=lambda q:np.linalg.norm(poses[q][:3,3]-poses[p][:3,3]))[:2]
            for other,other_depth in depths.items():
                f,o=definitions[other]
                if f['physicalPanorama'] not in neighbors:continue
                agree,seen,residual,_=depth_support(xyz,color,other_depth,rgbs[other],o,[256]*4,.10,45)
                supported|=agree;compared|=seen;consistency.extend(np.abs(residual[seen]).tolist())
            dense_points.append(xyz);dense_colors.append(color);filtered_points.append(xyz[supported]);filtered_colors.append(color[supported])
            coverage.append(dict(file=name,candidates=len(xyz),compared=int(compared.sum()),accepted=int(supported.sum()),unsupported=int((~compared).sum()),contradictory=int((compared&~supported).sum()),comparisonAbsRelMedian=float(np.median(consistency)) if consistency else None))
        results={}
        for variant,points,colors in [('dense',dense_points,dense_colors),('filtered',filtered_points,filtered_colors)]:
            xyz,rgb=voxel_reduce(np.concatenate(points),np.concatenate(colors),spacing)
            # Dense source rows are sampled/limited deterministically for M2;
            # preserve the complete unthinned cloud locally as diagnostic PLY.
            CAL.D.CAL.write_ply(out/(variant+'-full.ply'),xyz,rgb)
            take=np.linspace(0,len(xyz)-1,min(len(xyz),180000),dtype=int)
            seed=np.concatenate([old_xyz,xyz[take]]);color=np.concatenate([old_rgb,rgb[take]])
            dest=dataset(job,variant,seed,color,f'{variant} calibrated DAV2 inverse camera-Z initialization, voxel spacing derived from SfM baselines. Consistency filtering is not proven visibility or geometric accuracy. Sparse seed retained unchanged.')
            results[variant]=dict(points=len(seed),fullDensePoints=len(xyz),sparseRetained=len(old_xyz),voxelSpacingSfm=spacing,initialPlySha256=sha(dest/'init.ply'))
        if stereo is not None:
            xyz,rgb=voxel_reduce(stereodata['xyz'],stereodata['rgb'],spacing)
            dest=dataset(job,'stereo',np.r_[old_xyz,xyz],np.r_[old_rgb,rgb],'Observed RGB stereo triangulation plus common sparse seed. No monocular depth points. All new matching uses non5 physical centers; all-nine SfM poses remain estimated geometry.')
            results['stereo']=dict(points=len(old_xyz)+len(xyz),stereoPoints=len(xyz),sparseRetained=len(old_xyz),initialPlySha256=sha(dest/'init.ply'))
        report.update(status='PASS',qualityStatus='NOT ACCEPTED',calibratedImages=len(depths),failedFits=len(frames)-len(depths),results=results,coverage=coverage,
            conventions='Calibrated camera-Z -> pinhole rays -> shared fixed SfM world. Distances arbitrary; no ICP or pose modification.',stereoCalibrationUsed=stereo is not None,partialStereoExplicitlyAccepted=partial)
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=now(),elapsedSeconds=time.monotonic()-start,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);write(out/'report.json',report)
    print(report['status'],report['calibratedImages'],'calibrated',results)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['baseline','fusion']);p.add_argument('job',type=Path);p.add_argument('--stereo',type=Path);p.add_argument('--allow-partial-stereo',action='store_true')
    a=p.parse_args();job=a.job.resolve();baseline(job) if a.stage=='baseline' else fuse(job,a.stereo.resolve() if a.stereo else None,a.allow_partial_stereo)
