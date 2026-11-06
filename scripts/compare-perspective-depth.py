#!/usr/bin/env python3
"""Compare crop-local ERP radial and perspective camera-Z depth on fixed withheld tracks."""
import argparse
from datetime import datetime,timezone
import importlib.util
from pathlib import Path
import resource
import time
import traceback
import numpy as np

spec=importlib.util.spec_from_file_location('diagnose',Path(__file__).with_name('diagnose-pair-calibration.py'))
D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)


def plane_sample(array,xy):
    """Corner-origin camera pixel -> array sample; no wrap on a perspective crop."""
    x,y=np.asarray(xy,float)-.5;h,w=array.shape
    if not np.isfinite([x,y]).all() or not (0<=x<=w-1 and 0<=y<=h-1):return np.nan
    x0,y0=int(x),int(y);x1,y1=min(x0+1,w-1),min(y0+1,h-1);dx,dy=x-x0,y-y0
    return float(array[y0,x0]*(1-dx)*(1-dy)+array[y0,x1]*dx*(1-dy)+array[y1,x0]*(1-dx)*dy+array[y1,x1]*dx*dy)


def camera_z_fit(prediction,camera_z):
    # Reuse the identical robust affine solver; explicitly relabel its actual target.
    fit=D.CAL.fit_calibration(prediction,camera_z,'dav2')
    fit.update(convention='inverse-camera-z',source='Existing SfM pinhole camera-Z at shared training tracks; not radial or metric',method='Same Huber IRLS affine inverse fit, target=1/camera-Z')
    return fit


def perspective_radial(prediction,calibration,observed_camera_ray):
    ray=np.asarray(observed_camera_ray,float)
    if calibration.get('convention')!='inverse-camera-z':raise ValueError('Explicit inverse camera-Z calibration required')
    if ray.shape!=(3,) or not np.isfinite(ray).all() or not np.isclose(np.linalg.norm(ray),1,atol=1e-7) or ray[2]<=0:raise ValueError('Require front-facing unit camera bearing')
    inverse=calibration['scale']*prediction+calibration['offset']
    return float(1/inverse/ray[2]) if np.isfinite(inverse) and inverse>0 else np.nan


def run(output,inference_job,parent,protocol_path):
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();report=dict(status='RUNNING',startedAt=D.now())
    try:
        import pycolmap
        protocol=D.read(protocol_path)
        parent_protocol=D.ROOT/'docs/evidence/panoramic-calibration-protocol.json'
        if D.sha(parent_protocol)!=protocol['parentProtocolSha256']:raise ValueError('Parent protocol changed')
        inherited=D.read(parent_protocol)
        for entry in protocol['files']+inherited['files']:
            path=D.ROOT/entry['path']
            if path.stat().st_size!=entry['bytes'] or D.sha(path)!=entry['sha256']:raise ValueError('Pinned perspective control input changed')
        inference=D.read(inference_job/'report.json')
        if inference['status']!='PASS' or inference['device']!='mps' or inference['model']!=protocol['model'] or inference['revision']!=protocol['revision'] or len(inference['images'])!=12:raise ValueError('Require actual audited MPS predictions for all twelve crops')
        predicted={}
        for i,item in enumerate(inference['images']):
            source=Path(item['source']);path=inference_job/f'view-{i:02d}-relative.npy'
            if D.sha(source)!=item['sourceSha256'] or D.sha(path)!=item['relativeNpySha256']:raise ValueError('Perspective inference hash mismatch')
            predicted[source.name]=np.load(path)
        parent_rows=D.read(parent/'dav2/feature-samples.json');calibrations=D.read(parent/'dav2/calibration.json');training=set(calibrations['trainingPointIds']);held=set(calibrations['withheldPointIds'])
        if len(training)!=784 or len(held)!=217 or training&held:raise ValueError('Declared calibration split changed')
        anchors=[D.read(path) for path in D.anchor_paths()];by_id=[{a['point3DId']:a for a in group['anchors']} for group in anchors];poses=[np.array(a['worldFromPanorama']) for a in anchors]
        raw=[np.load(path/'raw.npy') for path in D.job_paths()['dav2']]
        model=pycolmap.Reconstruction(D.RIG/'sparse');cameras={}
        for image in model.images.values():
            cam=model.cameras[image.camera_id]
            if cam.model_name!='PINHOLE':raise ValueError('Require actual PINHOLE crop calibration')
            cameras[image.name]=dict(params=cam.params.tolist(),width=cam.width,height=cam.height,camFromWorld=image.cam_from_world().matrix().tolist())
        fits={}
        for source in [0,1]:
            names=sorted(name for name in predicted if name.startswith(f'pano_00000{source+4}_'))
            for name in names:
                c=cameras[name];m=np.asarray(c['camFromWorld']);center=-m[:3,:3].T@m[:3,3];pairs=[];rejected=[]
                for pid in sorted(training):
                    a=by_id[source][pid]
                    if not any(o['image']==name for o in a['observedSelectedCropPixels']):continue
                    point=np.asarray(a['xyzWorld']);q=m[:3,:3]@point+m[:3,3]
                    if q[2]<=0:rejected.append(pid);continue
                    xy=np.asarray(c['params'])[:2]*q[:2]/q[2]+np.asarray(c['params'])[2:]
                    perspective=plane_sample(predicted[name],xy)
                    u,v=D.directions_to_erp(poses[source][:3,:3].T@(point-center),*raw[source].shape)
                    erp=float(D.sample_erp_bilinear(raw[source],u,v));radial=float(np.linalg.norm(point-center))
                    if not np.isfinite([perspective,erp,radial]).all():rejected.append(pid);continue
                    pairs.append((pid,erp,perspective,radial,float(q[2])))
                if len(pairs)<30:raise ValueError(f'Insufficient common training tracks for {name}: {len(pairs)}')
                values=np.array(pairs);fits[name]=dict(trainingPointIds=[int(x) for x in values[:,0]],rejectedTrainingIds=rejected,
                    erpLocal=D.CAL.fit_calibration(values[:,1],values[:,3],'dav2'),perspective=camera_z_fit(values[:,2],values[:,4]))
                if held&set(fits[name]['trainingPointIds']):raise ValueError('Holdout leakage')
        D.write(output/'crop-calibrations.json',fits)
        rows=[]
        for old in parent_rows:
            source=int(old['direction'][0])-4;target=1-source;src=old['sourceImage'];dst=old['targetImage'];cam=cameras[src];m=np.array(cam['camFromWorld']);center=-m[:3,:3].T@m[:3,3];ray=D.unit_bearing(old['sourceObserved'],cam['params']);world_ray=m[:3,:3].T@ray
            u,v=D.directions_to_erp(poses[source][:3,:3].T@world_ray,*raw[source].shape);erp=D.sample_erp_bilinear(raw[source],u,v)
            radial=float(D.CAL.apply_calibration(erp,fits[src]['erpLocal'])[0]);persp=perspective_radial(plane_sample(predicted[src],old['sourceObserved']),fits[src]['perspective'],ray)
            methods=dict(sfmRay=old['methods']['sfmRay'],sfmPoint=old['methods']['sfmPoint'],erpGlobal=old['methods']['common'],
                erpLocal=D.evaluate_range(radial,world_ray,center,cameras[dst],old['targetObserved']),perspective=D.evaluate_range(persp,world_ray,center,cameras[dst],old['targetObserved']))
            rows.append({**old,'methods':methods})
        D.write(output/'feature-samples.json',rows)
        def summary(items):
            paired=D.paired_statistics([{**r,'methods':{'original':r['methods']['erpGlobal'],'common':r['methods']['perspective']}} for r in items]);paired['meaning']='Perspective local minus global ERP error on same valid points; not independent truth'
            return dict(methods={key:D.statistics(items,key) for key in ['sfmRay','sfmPoint','erpGlobal','erpLocal','perspective']},pairedVersusGlobal=paired)
        directions=[]
        for ident in ['4-to-5','5-to-4']:
            selected=[r for r in rows if r['direction']==ident];strata=[]
            for low,high in [(0,1),(1,3),(3,10),(10,180)]:strata.append(dict(group='parallax',label=f'{low}-{high} degrees',**summary([r for r in selected if low<=r['pairParallaxDegrees']<high])))
            for i in range(12):strata.append(dict(group='longitude',label=f'{i*30-180} to {(i+1)*30-180}',**summary([r for r in selected if i/12<=r['sourceUv'][0]<(i+1)/12])))
            draw_rows=[{**r,'methods':{'original':r['methods']['erpLocal'],'common':r['methods']['perspective'],'sfmRay':r['methods']['sfmRay']}} for r in selected]
            D.diagnostic_mosaic(draw_rows,cameras,output/f'{ident}-features.png');directions.append(dict(id=ident,**summary(selected),strata=strata))
        report.update(status='PASS',protocolSha256=D.sha(protocol_path),parentReportSha256=D.sha(parent/'report.json'),directions=directions,
            cropTrainingCounts={name:len(value['trainingPointIds']) for name,value in fits.items()},
            uniqueTrainingIdsByPanorama={str(i):len({pid for name,value in fits.items() if name.startswith(f'pano_00000{i}_') for pid in value['trainingPointIds']}) for i in [4,5]},
            inferenceReportSha256=D.sha(inference_job/'report.json'),featureSamplesSha256=D.sha(parent/'dav2/feature-samples.json'),cropCalibrationsSha256=D.sha(output/'crop-calibrations.json'),inference=dict(device=inference['device'],model=inference['model'],revision=inference['revision'],modelLoadSeconds=inference['modelLoadSeconds'],elapsedSeconds=inference['elapsedSeconds'],inferenceSeconds=[i['inferenceSeconds'] for i in inference['images']],relativeNpySha256=[i['relativeNpySha256'] for i in inference['images']]),
            conventions=protocol['depthConventions'],confounders=protocol['confounders'],scope=protocol['scope'])
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(finishedAt=D.now(),elapsedSeconds=time.monotonic()-start,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);D.write(output/'report.json',report)
    print(report['status'],report['elapsedSeconds'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('inference',type=Path);p.add_argument('parent',type=Path);p.add_argument('output',type=Path);p.add_argument('--protocol',type=Path,default=D.ROOT/'docs/evidence/panoramic-perspective-control-protocol.json');a=p.parse_args();run(a.output,a.inference,a.parent,a.protocol)
