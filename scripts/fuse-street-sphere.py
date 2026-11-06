#!/usr/bin/env python3
"""One calibrated radial range per physical-sphere ray, then cross-center fusion.

This is an explicit procedural comparison to per-crop concatenation. Reuses
the same96 actual predictions/fits/RGB/cameras, without new inference or poses.
"""
import argparse
from pathlib import Path
import importlib.util
import resource
import time
import numpy as np
from PIL import Image
from spherical_depth import erp_unit_rays,directions_to_erp,sample_erp_bilinear,backproject_radial
from perspective_sphere import crop_ranges
from street_geometry import voxel_reduce

def module(name,file):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

F=module('fusion','reconstruct-street.py');P,C=F.P,F.C


def run(job):
    out=job/'fusion-sphere';out.mkdir(parents=True,exist_ok=False);start=time.monotonic();report=dict(status='RUNNING',startedAt=P.now())
    try:
        frames=P.read(job/'inputs/transforms.json')['frames'];inference=P.read(job/'depth/report.json');calibrations=P.read(job/'fusion/calibrations.json')
        if inference['status']!='PASS' or P.read(job/'fusion/report.json')['status']!='PASS':raise ValueError('Require completed preserved inference/calibration')
        files=[Path(__file__),job/'depth/report.json',job/'fusion/calibrations.json',job/'inputs/transforms.json']
        P.write(out/'protocol.json',dict(declaredAt=P.now(),procedure='Select one primary crop per ERP ray by geometric centrality BEFORE inspecting depth. Invalid primary remains unsupported. No most-agreeable target crop search.',
            settings=dict(width=1092,height=546,band=[.40,.85],stride=2,relativeTolerance=.10,rgbTolerance255=45,neighbors=2,voxel='Same median estimated baseline/120',maxDenseSeed=180000),
            reason='Initial variants concatenate overlapping crops and accept any agreeing target crop. This can retain conflicting depth shells from one physical center. Test a true spherical map per center without changing the fitted model.',
            files=[dict(path=str(p.relative_to(P.ROOT)),sha256=P.sha(p)) for p in files]))
        indexed={Path(r['source']).name:(i,r) for i,r in enumerate(inference['images'])};fits={r['file']:r for r in calibrations if r['status']=='PASS'}
        poses=P.panorama_poses();physical=[1,2,3,4,6,7,8,9];anchors=P.read(job/'anchors-training-colors/anchors.json')
        rays=erp_unit_rays(546,1092);v=(np.arange(546)+.5)/546;band=np.broadcast_to(((v>=.40)&(v<=.85))[:,None],(546,1092))
        maps={};rgb={};coverage=[]
        originals=sorted((P.ROOT/'data/samples/mapillary-beijing/images').glob('*.jpg'))
        for p in physical:
            candidates=[];scores=[]
            for frame in [f for f in frames if f['physicalPanorama']==p]:
                name=Path(frame['file_path']).name
                if name not in fits:continue
                i,entry=indexed[name];path=job/f'depth/view-{i:02d}-relative.npy'
                if P.sha(path)!=entry['relativeNpySha256']:raise ValueError('Prediction changed')
                raw=np.load(path);rotation=C.crop_rotation(frame['yaw'],frame['pitch'])
                radial,_=crop_ranges(raw,fits[name]['fit'],rotation,rays,[256]*4)
                q=rays@rotation
                with np.errstate(divide='ignore',invalid='ignore'):xy=q[:,:,:2]/q[:,:,2,None]*256+256
                inside=(q[:,:,2]>0)&(xy[:,:,0]>=.5)&(xy[:,:,0]<=511.5)&(xy[:,:,1]>=.5)&(xy[:,:,1]<=511.5)
                scores.append(np.where(inside,q[:,:,2],-np.inf));candidates.append(radial)
            values=np.array(candidates);score=np.array(scores);winner=np.argmax(score,axis=0)
            primary=np.take_along_axis(values,winner[None],axis=0)[0];geometric=np.max(score,axis=0)>0
            cap=float(np.quantile(np.linalg.norm(np.array([a['xyz'] for a in anchors[str(p)]])-poses[p][:3,3],axis=1),.99))
            valid=band&geometric&np.isfinite(primary)&(primary>0)&(primary<=cap);primary=np.where(valid,primary,np.nan)
            available=np.isfinite(values)&(values>0);logs=np.log(np.where(available,values,1));support=available.sum(axis=0)
            spread=np.max(np.where(available,logs,-np.inf),axis=0)-np.min(np.where(available,logs,np.inf),axis=0)
            overlap=band&(support>=2);spreads=spread[overlap]
            coverage.append(dict(physical=p,bandPixels=int(band.sum()),geometryCovered=int((band&geometric).sum()),validPrimary=int(valid.sum()),invalidPrimary=int((band&geometric&~valid).sum()),overlappingValidPixels=int(overlap.sum()),
                overlapLogSpreadMedian=float(np.median(spreads)) if len(spreads) else None,overlapLogSpreadP90=float(np.quantile(spreads,.9)) if len(spreads) else None,
                overlapMoreThan10Percent=int((spreads>np.log(1.10)).sum()),invalidPrimaryFallback=False))
            with Image.open(originals[p-1]) as im:rgb[p]=np.asarray(im.convert('RGB').resize((1092,546),Image.Resampling.LANCZOS))
            maps[p]=primary;np.savez_compressed(out/f'{p}-map.npz',radial=primary,winner=winner,support=support,logSpread=spread,mask=valid)
            show=np.clip(np.nan_to_num(primary,nan=0)/cap,0,1)*255;Image.fromarray(show.astype(np.uint8)).save(out/f'{p}-radial.png')
        points=[];colors=[];comparisons=[]
        for p in physical:
            xyz,color,rows,cols=backproject_radial(maps[p],rgb[p],poses[p],stride=2)
            good=np.zeros(len(xyz),bool);compared=np.zeros(len(xyz),bool);near=sorted([q for q in physical if q!=p],key=lambda q:np.linalg.norm(poses[q][:3,3]-poses[p][:3,3]))[:2]
            pair_records=[]
            for q in near:
                local=(xyz-poses[q][:3,3])@poses[q][:3,:3];distance=np.linalg.norm(local,axis=1);u,v=directions_to_erp(local,546,1092)
                observed=sample_erp_bilinear(maps[q],u,v);other_rgb=sample_erp_bilinear(rgb[q],u,v)
                valid=np.isfinite(observed)&(observed>0)&(distance>0)
                residual=np.full(len(xyz),np.nan);residual[valid]=(distance[valid]-observed[valid])/observed[valid]
                error=np.mean(np.abs(color.astype(float)-other_rgb),axis=1);agree=valid&(np.abs(residual)<=.10)&(error<=45)
                good|=agree;compared|=valid
                pair_records.append(dict(target=q,compared=int(valid.sum()),accepted=int(agree.sum()),absRelativeMedian=float(np.median(np.abs(residual[valid]))) if valid.any() else None))
            points.append(xyz[good]);colors.append(color[good]);comparisons.append(dict(physical=p,candidates=len(xyz),compared=int(compared.sum()),accepted=int(good.sum()),unsupported=int((~compared).sum()),contradictory=int((compared&~good).sum()),pairs=pair_records))
            diagnostic=np.zeros((546,1092,3),np.uint8);diagnostic[rows,cols]=[255,205,45];diagnostic[rows[good],cols[good]]=[30,225,170];Image.fromarray(diagnostic).save(out/f'{p}-support.png')
        spacing=P.read(job/'fusion/report.json')['results']['dense']['voxelSpacingSfm'];xyz,color=voxel_reduce(np.concatenate(points),np.concatenate(colors),spacing)
        F.CAL.D.CAL.write_ply(out/'sphere-full.ply',xyz,color)
        if len(xyz)<5000:raise RuntimeError('Too few supported spherical points; preserve failure instead of inventing depths')
        selected=np.linspace(0,len(xyz)-1,min(len(xyz),180000),dtype=int);old,old_rgb=F.sparse_seed(job);seed=np.r_[old,xyz[selected]];seed_rgb=np.r_[old_rgb,color[selected]]
        dest=F.dataset(job,'sphere',seed,seed_rgb,'One geometrically selected crop per panorama ray; invalid primaries unsupported. Cross-view radial/RGB support in two distinct neighboring physical centers. Reuses exact prior fits; no ICP, pose change or new inference. Estimated geometry, not measured depth.')
        report.update(status='PASS',qualityStatus='NOT ACCEPTED',points=len(seed),fullDensePoints=len(xyz),sparseRetained=len(old),voxelSpacingSfm=spacing,coverage=coverage,comparisons=comparisons,
            initialPlySha256=P.sha(dest/'init.ply'),protocolSha256=P.sha(out/'protocol.json'),calibrationsReusedSha256=P.sha(job/'fusion/calibrations.json'))
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=P.now(),elapsedSeconds=time.monotonic()-start,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);P.write(out/'report.json',report)
    print(report['status'],report['points'],'spherical initialization points')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);a=p.parse_args();run(a.job.resolve())
