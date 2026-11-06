#!/usr/bin/env python3
"""Controlled common-track calibration and observed-feature reprojection; no new inference."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import time
import traceback

import numpy as np
from PIL import Image, ImageDraw
from spherical_depth import directions_to_erp, sample_erp_bilinear, backproject_radial
from panoramic_pair import compare_direction

ROOT=Path(__file__).resolve().parents[1]
PAIR=ROOT/'data/jobs/panoramic-pair-20261106'
BASE=ROOT/'data/jobs/panoramic-baseline-20261106'
RIG=ROOT/'data/jobs/mapillary-beijing-rig-poses-v2/dataset'
spec=importlib.util.spec_from_file_location('calibration',Path(__file__).with_name('evaluate-panoramic-depth.py'))
CAL=importlib.util.module_from_spec(spec);spec.loader.exec_module(CAL)


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def local(path):return str(path.relative_to(ROOT))
def job_paths():return {key:[PAIR/f'{key}-4',ROOT/f'data/jobs/panoramic-depth-{key}-20261106'] for key in ['da2','dav2']}
def anchor_paths():return [PAIR/'anchors-4/selected-panorama.json',BASE/'selected-panorama.json']


def unit_bearing(xy,params):
    xy,params=np.asarray(xy,float),np.asarray(params,float)
    if xy.shape!=(2,) or params.shape!=(4,) or not np.isfinite(xy).all() or not np.isfinite(params).all() or np.any(params[:2]<=0):
        raise ValueError('Require finite corner-origin pinhole pixels and fx,fy,cx,cy')
    ray=np.r_[(xy-params[2:])/params[:2],1.]
    return ray/np.linalg.norm(ray)


def select_observation(observations,cameras):
    if not observations:raise ValueError('Missing observed feature, never invent correspondence')
    def rank(o):
        camera=cameras[o['image']];ray=unit_bearing(o['xyCornerOrigin'],camera['params'])
        return (float(np.sum((ray[:2]/ray[2])**2)),o['image'])
    return min(observations,key=rank)


def common_fits(ids,predictions,ranges,kind):
    mappings=[{int(pid):i for i,pid in enumerate(group)} for group in ids]
    if any(len(m)!=len(group) for m,group in zip(mappings,ids)):raise ValueError('Point IDs must be unique per panorama')
    common=np.array(sorted(set(mappings[0])&set(mappings[1])),dtype=np.int64)
    held=CAL.split_ids(common);training=common[~held]
    fits=[]
    for mapping,pred,target in zip(mappings,predictions,ranges):
        indices=np.array([mapping[int(pid)] for pid in training])
        fits.append(CAL.fit_calibration(np.asarray(pred)[indices],np.asarray(target)[indices],kind))
    return common,held,fits


def project_world(point,target_camera,observed):
    point,observed=np.asarray(point,float),np.asarray(observed,float)
    invalid=dict(valid=False,insideImage=False,xy=None,pixelError=None,angularErrorDegrees=None)
    if point.shape!=(3,) or not np.isfinite(point).all():return invalid
    pose=np.asarray(target_camera['camFromWorld'],float);q=pose[:3,:3]@point+pose[:3,3]
    if not np.isfinite(q).all() or np.linalg.norm(q)<=0:return invalid
    ray=unit_bearing(observed,target_camera['params'])
    angle=float(np.degrees(np.arccos(np.clip(np.dot(q/np.linalg.norm(q),ray),-1,1))))
    if q[2]<=0:return {**invalid,'angularErrorDegrees':angle}
    p=np.asarray(target_camera['params']);xy=p[:2]*q[:2]/q[2]+p[2:]
    if not np.isfinite(xy).all():return invalid
    return dict(valid=True,insideImage=bool(0<=xy[0]<target_camera['width'] and 0<=xy[1]<target_camera['height']),xy=xy.tolist(),
                pixelError=float(np.linalg.norm(xy-observed)),angularErrorDegrees=angle)


def evaluate_range(radial,source_ray_world,source_center,target_camera,observed):
    if not np.isfinite(radial) or radial<=0:
        return dict(valid=False,insideImage=False,xy=None,pixelError=None,angularErrorDegrees=None)
    return project_world(np.asarray(source_center)+np.asarray(source_ray_world)*radial,target_camera,observed)


def statistics(rows,method):
    entries=[r['methods'][method] for r in rows];valid=[r for r in entries if r['valid']]
    errors=np.array([r['pixelError'] for r in valid]);angles=np.array([r['angularErrorDegrees'] for r in valid])
    return dict(samples=len(entries),validSamples=len(valid),invalidSamples=len(entries)-len(valid),outOfImageSamples=sum(r['valid'] and not r['insideImage'] for r in entries),
                medianPixels=float(np.median(errors)) if len(errors) else None,p90Pixels=float(np.quantile(errors,.9)) if len(errors) else None,
                medianAngularDegrees=float(np.median(angles)) if len(angles) else None)


def paired_statistics(rows):
    pairs=[r for r in rows if r['methods']['original']['valid'] and r['methods']['common']['valid']]
    delta=np.array([r['methods']['common']['pixelError']-r['methods']['original']['pixelError'] for r in pairs])
    return dict(pairedValidSamples=len(pairs),excludedPairs=len(rows)-len(pairs),improved=sum(float(x)<0 for x in delta),
                medianDeltaPixels=float(np.median(delta)) if len(delta) else None,
                meaning='Common minus original error on the same valid points; not independent geometry truth')


def declare(path):
    files=anchor_paths()+[PAIR/'anchors-4/pair-sparse.json',ROOT/'docs/evidence/panoramic-pair-protocol.json']+list(RIG.joinpath('sparse').glob('*.bin'))
    files += [ROOT/f'public/experiments/panoramic-pair/{key}/cloud.json' for key in ['da2','dav2']]
    files += [p for p in (RIG/'images').glob('pano_*.png') if p.name.startswith(('pano_000004_', 'pano_000005_'))]
    for jobs in job_paths().values():
        for job in jobs:files += [job/name for name in ['inference.json','raw.npy','source.png','geometry/geometry.json','geometry/calibration-samples.json','geometry/filtered.npy']]
    record=dict(schemaVersion=1,declaredAt=now(),hypothesis='Different calibration anchor populations explain some cross-view depth bias',
        training='Same common point IDs in both views; SHA256 point-ID modulo-five holdout unchanged',
        calibration='Same existing DA2 scale-only radial and DAV2 Huber affine inverse-radial fit; SfM-projected ERP sampling unchanged in calibration',
        evaluation='One real crop observation per panorama and shared withheld point, nearest principal point in normalized pinhole coordinates; tie by image name. Evaluate both directions.',
        observedRay='Sample learned depth on the observed source feature bearing, backproject using its estimated camera center, project to the actual observed target crop feature',
        controls=['SfM radial distance along the identical observed source ray','Original triangulated SfM point projected into selected target crop'],
        strata=dict(pairParallaxDegrees=[0,1,3,10,180],longitudeBins=12,regions='Unchanged previous source-ERP road/facade rectangles; not guaranteed matching physical surfaces'),
        acceptance='Diagnostic only. No post-hoc winner selection, nine-way fusion, ICP, pose refinement, generation or GS training.',
        invalidPolicy='Retain all withheld IDs in denominators; nonpositive/behind-camera predictions invalid; positive-Z out-of-image projections remain in pixel statistics; paired improvements disclose excluded invalids',
        cloudPolicy='Freeze previous masks, stride3 and comparison camera for original/common overlays; changed ranges only. Invalid ranges excluded with counts. No fusion.',
        files=[dict(path=local(p),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(set(files))])
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as stream:stream.write(json.dumps(record,indent=2)+'\n')
    print('Declared',path,'input files',len(record['files']))


def diagnostic_mosaic(rows,cameras,output):
    names=sorted({r['targetImage'] for r in rows});canvas=Image.new('RGB',(3*512,2*542),(10,14,20));draw=ImageDraw.Draw(canvas)
    palette={'sfmRay':(255,90,220),'original':(255,100,70),'common':(50,230,210)}
    for index,name in enumerate(names):
        tile=Image.open(RIG/'images'/name).convert('RGB');d=ImageDraw.Draw(tile)
        for row in rows:
            if row['targetImage']!=name:continue
            actual=np.array(row['targetObserved']);d.ellipse(tuple(actual-2)+tuple(actual+2),outline='yellow',width=1)
            for method,color in palette.items():
                item=row['methods'][method]
                if not item['valid']:continue
                delta=(np.array(item['xy'])-actual)*2;length=np.linalg.norm(delta)
                if length>48:delta*=48/length
                tip=actual+delta;d.line([tuple(actual),tuple(tip)],fill=color,width=1);d.ellipse(tuple(tip-1)+tuple(tip+1),fill=color)
        x,y=(index%3)*512,(index//3)*542;canvas.paste(tile,(x,y+30));draw.text((x+5,y+8),name,fill='white')
    canvas.save(output)


def run(output,protocol_path):
    output.mkdir(parents=True,exist_ok=False);started=time.monotonic();report=dict(status='RUNNING',startedAt=now())
    try:
        import pycolmap
        protocol=read(protocol_path)
        for entry in protocol['files']:
            path=ROOT/entry['path']
            if path.stat().st_size!=entry['bytes'] or sha(path)!=entry['sha256']:raise ValueError(f'Pinned input changed: {entry["path"]}')
        anchors=[read(p) for p in anchor_paths()];by_id=[{a['point3DId']:a for a in group['anchors']} for group in anchors]
        if anchors[0]['coordinateFrame']!=anchors[1]['coordinateFrame']:raise ValueError('Coordinate frame mismatch')
        model=pycolmap.Reconstruction(RIG/'sparse');cameras={}
        for image in model.images.values():
            c=model.cameras[image.camera_id]
            if c.model_name!='PINHOLE':raise ValueError('This bounded diagnostic requires actual PINHOLE calibration')
            cameras[image.name]=dict(params=c.params.tolist(),width=c.width,height=c.height,camFromWorld=image.cam_from_world().matrix().tolist())
        poses=[np.asarray(a['worldFromPanorama']) for a in anchors];sparse=read(PAIR/'anchors-4/pair-sparse.json');angles={r['point3DId']:r['pairTriangulationAngleDegrees'] for r in sparse['tracks']}
        previous_protocol=read(ROOT/'docs/evidence/panoramic-pair-protocol.json');results=[]
        for kind,jobs in job_paths().items():
            predictions=[];targets=[];ids=[];raws=[];rgbs=[];masks=[];old_fits=[]
            for job,anchor in zip(jobs,anchors):
                inference=read(job/'inference.json');geometry=read(job/'geometry/geometry.json')
                if inference['status']!='PASS' or geometry['status']!='PASS' or inference['model']!=kind or inference['sourceSha256']!=anchor['source']['sha256'] or sha(job/'raw.npy')!=inference['rawSha256']:raise ValueError('Invalid model/source/inference evidence')
                raw=np.load(job/'raw.npy');h,w=raw.shape;items=anchor['anchors'];uv=np.array([a['erpNormalizedUv'] for a in items])
                values=sample_erp_bilinear(raw,uv[:,0]*w-.5,uv[:,1]*h-.5);point_ids=np.array([a['point3DId'] for a in items]);ranges=np.array([a['radialRangeSfm'] for a in items])
                fit=CAL.fit_calibration(values[~CAL.split_ids(point_ids)],ranges[~CAL.split_ids(point_ids)],kind)
                np.testing.assert_allclose([fit['scale'],fit['offset']],[geometry['calibration']['scale'],geometry['calibration']['offset']],rtol=1e-8,atol=1e-10)
                ids.append(point_ids);predictions.append(values);targets.append(ranges);raws.append(raw);old_fits.append(fit)
                rgbs.append(np.array(Image.open(job/'source.png').convert('RGB')));masks.append(np.load(job/'geometry/filtered.npy'))
            common,held,fits=common_fits(ids,predictions,targets,kind)
            if len(common)!=1001 or int(held.sum())!=217:raise ValueError('Common set changed from declared experiment')
            destination=output/kind;destination.mkdir();write(destination/'calibration.json',dict(trainingPointIds=common[~held].tolist(),withheldPointIds=common[held].tolist(),original=old_fits,common=fits))
            feature_rows=[];directions=[]
            for source,target in [(0,1),(1,0)]:
                rows=[]
                for pid in common[held]:
                    pid=int(pid);a,b=by_id[source][pid],by_id[target][pid];src=select_observation(a['observedSelectedCropPixels'],cameras);dst=select_observation(b['observedSelectedCropPixels'],cameras)
                    cam=cameras[src['image']];R=np.array(cam['camFromWorld'])[:3,:3];t=np.array(cam['camFromWorld'])[:3,3];center=-R.T@t;world_ray=R.T@unit_bearing(src['xyCornerOrigin'],cam['params'])
                    np.testing.assert_allclose(center,poses[source][:3,3],atol=1e-10,rtol=0)
                    pano_ray=poses[source][:3,:3].T@world_ray;u,v=directions_to_erp(pano_ray,*raws[source].shape);raw_value=sample_erp_bilinear(raws[source],u,v)
                    values={name:float(CAL.apply_calibration(raw_value,fit)[0]) for name,fit in [('original',old_fits[source]),('common',fits[source])]}
                    methods={name:evaluate_range(value,world_ray,center,cameras[dst['image']],dst['xyCornerOrigin']) for name,value in {**values,'sfmRay':a['radialRangeSfm']}.items()}
                    methods['sfmPoint']=project_world(a['xyzWorld'],cameras[dst['image']],dst['xyCornerOrigin'])
                    row=dict(point3DId=pid,direction=f'{source+4}-to-{target+4}',sourceImage=src['image'],sourceObserved=src['xyCornerOrigin'],targetImage=dst['image'],targetObserved=dst['xyCornerOrigin'],sourceUv=a['erpNormalizedUv'],pairParallaxDegrees=angles[pid],methods=methods)
                    rows.append(row)
                def summarize(items):return dict(methods={name:statistics(items,name) for name in ['sfmPoint','sfmRay','original','common']},paired=paired_statistics(items))
                strata=[]
                for low,high in zip(protocol['strata']['pairParallaxDegrees'][:-1],protocol['strata']['pairParallaxDegrees'][1:]):
                    strata.append(dict(group='parallax',label=f'{low}-{high} degrees',**summarize([r for r in rows if low<=r['pairParallaxDegrees']<high])))
                for i in range(12):strata.append(dict(group='longitude',label=f'{i*30-180} to {(i+1)*30-180}',**summarize([r for r in rows if i/12<=r['sourceUv'][0]<(i+1)/12])))
                for region in previous_protocol['regions']:strata.append(dict(group='region',label=region['id'],**summarize([r for r in rows if region['u'][0]<=r['sourceUv'][0]<=region['u'][1] and region['v'][0]<=r['sourceUv'][1]<=region['v'][1]])))
                ident=f'{source+4}-to-{target+4}';diagnostic_mosaic(rows,cameras,destination/f'{ident}-features.png')
                directions.append(dict(id=ident,**summarize(rows),strata=strata));feature_rows+=rows
            write(destination/'feature-samples.json',feature_rows)
            common_ranges=[CAL.apply_calibration(raw,fit)[0] for raw,fit in zip(raws,fits)]
            for i,array in enumerate(common_ranges):np.save(destination/f'range-{i+4}.npy',array.astype(np.float32))
            dense=[]
            for source,target in [(0,1),(1,0)]:
                result=compare_direction(common_ranges[source],common_ranges[target],rgbs[source],rgbs[target],poses[source],poses[target],source_mask=masks[source],target_mask=masks[target],stride=1)
                dense.append(dict(id=f'{source+4}-to-{target+4}',summary=result['summary']))
            clouds=[backproject_radial(r,rgb,pose,mask=mask,stride=3)[:2] for r,rgb,pose,mask in zip(common_ranges,rgbs,poses,masks)]
            xyz=np.concatenate([c[0] for c in clouds]);colors=np.concatenate([c[1] for c in clouds]);cloud=read(ROOT/f'public/experiments/panoramic-pair/{kind}/cloud.json')
            cloud.update(positions=np.round(xyz,6).reshape(-1).tolist(),colors=colors.reshape(-1).tolist(),sourceIds=[i for i,c in enumerate(clouds) for _ in c[0]])
            write(destination/'cloud.json',cloud);CAL.write_ply(destination/'cloud.ply',xyz,colors)
            results.append(dict(model=kind,originalFits=old_fits,commonFits=fits,trainingTracks=int((~held).sum()),withheldTracks=int(held.sum()),directions=directions,commonDense=dense,cloudPoints=[len(c[0]) for c in clouds],
                maskMeaning='Frozen previous masks; no rethresholding to favor common fit. Camera/center/radius match previous cloud for direct view comparison.'))
        report.update(status='PASS',protocolSha256=sha(protocol_path),models=results,inference='NOT RUN: reuse pinned prior MPS predictions',poseRefinement='NOT RUN',fusion='NOT RUN',gaussianTraining='NOT RUN',independentGeometry='NOT RUN',sourceLicense='Cicero101 / Mapillary via Wikimedia Commons, CC BY-SA 4.0',limits=['All controls and holdouts are internal to all-image SfM; camera/depth truth is not independent.','One selected real observation per panorama/track avoids duplicate weighting; selection does not use depth/error.','SfM point and ray controls reuse optimized geometry and may share biased poses.','Weak parallax makes small pixel errors compatible with large depth errors.'])
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(finishedAt=now(),elapsedSeconds=time.monotonic()-started,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);write(output/'report.json',report)
    print(json.dumps(dict(status=report['status'],seconds=report['elapsedSeconds'],output=str(output))))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--declare',type=Path);p.add_argument('--protocol',type=Path,default=ROOT/'docs/evidence/panoramic-calibration-protocol.json');p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.declare:declare(args.declare)
    elif args.output:run(args.output,args.protocol)
    else:p.error('Use --declare NEW_PROTOCOL or --output NEW_JOB')

if __name__=='__main__':main()
