#!/usr/bin/env python3
"""Calibrate twenty real tangent depths and build one native dataset/background."""
import argparse
from pathlib import Path
import importlib.util
from itertools import combinations
import shutil
import resource
import time
import numpy as np
from PIL import Image
from spherical_depth import erp_unit_rays,sample_erp_bilinear,backproject_radial
from perspective_sphere import sample_plane
from street_geometry import held_id,voxel_reduce
from tangent_geometry import project_rays,fit_overlap_system,shell_mesh,fill_display_nadir

spec=importlib.util.spec_from_file_location('prepare',Path(__file__).with_name('prepare-street.py'))
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
C=P.module('crop','prepare-panoramas.py');CAL=P.module('calibration','compare-perspective-depth.py')


def stats(pred,target):
    ok=np.isfinite(pred)&(pred>0);e=np.abs(pred[ok]/target[ok]-1)
    return dict(samples=len(target),valid=int(ok.sum()),invalid=int((~ok).sum()),medianAbsRel=float(np.median(e)) if len(e) else None,p90AbsRel=float(np.quantile(e,.9)) if len(e) else None)


def fuse(job):
    out=job/'fusion-tangent';out.mkdir(parents=True,exist_ok=False);start=time.monotonic();report=dict(status='RUNNING',startedAt=P.now(),physical=[])
    try:
        inputs=job/'inputs-tangent';inf=P.read(job/'depth/report.json');frames=P.read(inputs/'transforms.json')['frames']
        if inf['status']!='PASS' or inf['revision']!='5426e4f0f36572d16453bbda7a8389317b1bef99' or inf['device']!='mps' or len(inf['images'])!=160:raise ValueError('Require actual160-image pinned DAV2 MPS inference')
        if len(frames)!=160 or any(f['physicalPanorama']==5 for f in frames):raise ValueError('Withheld RGB entered tangent training')
        indexed={Path(row['source']).name:(i,row) for i,row in enumerate(inf['images'])};anchors=P.read(job/'anchors-training-colors/anchors.json');poses=P.panorama_poses()
        rays=erp_unit_rays(512,1024);sample=erp_unit_rays(80,160).reshape(-1,3)
        sample_v=np.repeat((np.arange(80)+.5)/80,160);sample=sample[(sample_v>=.25)&(sample_v<=.85)]
        original=sorted((P.ROOT/'data/samples/mapillary-beijing/images').glob('*.jpg'));all_xyz=[];all_rgb=[];fits=[]
        rows_v=np.broadcast_to(((np.arange(512)+.5)/512)[:,None],(512,1024));band=(rows_v>=.25)&(rows_v<=.85)
        for physical in [1,2,3,4,6,7,8,9]:
            rows=anchors[str(physical)];anchor_rays=np.array([a['rayPanorama'] for a in rows]);xyz=np.array([a['xyz'] for a in rows]);distance=np.linalg.norm(xyz-poses[physical][:3,3],axis=1);held=np.array([held_id(a['id']) for a in rows]);cap=float(np.quantile(distance[~held],.99))
            crops=[];failed=[]
            for frame in [f for f in frames if f['physicalPanorama']==physical]:
                name=Path(frame['file_path']).name;i,record=indexed[name];raw_path=job/f'depth/view-{i:02d}-relative.npy'
                if P.sha(inputs/'images'/name)!=record['sourceSha256'] or P.sha(raw_path)!=record['relativeNpySha256']:raise ValueError('Depth input/prediction bytes changed')
                raw=np.load(raw_path);rotation=C.crop_rotation(frame['yaw'],frame['pitch']);params=[frame[k] for k in ['fl_x','fl_y','cx','cy']]
                xy,cos,inside=project_rays(anchor_rays,rotation,params,frame['w']);pred=sample_plane(raw,xy);valid=inside&np.isfinite(pred);train=valid&~held
                try:
                    # Range along an observed unit ray -> its camera-Z. Both arbitrary SfM units.
                    independent=CAL.camera_z_fit(pred[train],distance[train]*cos[train])
                    mu=float(np.median(pred[train]));sigma=max(float(np.std(pred[train])),1e-6)
                    sx,sc,sv=project_rays(sample,rotation,params,frame['w']);sp=sample_plane(raw,sx);sv&=np.isfinite(sp)
                    crops.append(dict(frame=frame,raw=raw,rotation=rotation,params=params,mu=mu,sigma=sigma,initial=independent,
                        anchorRaw=pred,anchorCos=cos,training=train,held=valid&held,sampleRaw=(sp-mu)/sigma,sampleCos=sc,sampleValid=sv))
                except ValueError as error:failed.append(dict(file=name,status='FAIL',reason=str(error),usedForGeometry=False))
            if len(crops)<3:raise ValueError('Too few anchored tangent faces at physical'+str(physical))
            count=len(crops);anchor_rows=[];overlap_rows=[];initial=[]
            for k,crop in enumerate(crops):
                initial.extend([crop['initial']['scale']*crop['sigma'],crop['initial']['scale']*crop['mu']+crop['initial']['offset']])
                for a in np.flatnonzero(crop['training']):
                    row=np.zeros(count*2);row[k*2:k*2+2]=crop['anchorCos'][a]*np.array([(crop['anchorRaw'][a]-crop['mu'])/crop['sigma'],1])
                    anchor_rows.append((row,1/distance[a]))
            for i,k in combinations(range(count),2):
                a,b=crops[i],crops[k];valid=a['sampleValid']&b['sampleValid'];take=np.flatnonzero(valid)
                if len(take)>128:take=take[np.linspace(0,len(take)-1,128,dtype=int)]
                for s in take:
                    row=np.zeros(count*2);row[i*2:i*2+2]=a['sampleCos'][s]*np.array([a['sampleRaw'][s],1]);row[k*2:k*2+2]=-b['sampleCos'][s]*np.array([b['sampleRaw'][s],1]);overlap_rows.append(row)
            solution=fit_overlap_system(anchor_rows,overlap_rows,initial)
            values=[];scores=[];before=[];local_fits=[]
            for k,crop in enumerate(crops):
                frame=crop['frame'];name=Path(frame['file_path']).name;alpha,beta=solution[k*2:k*2+2];a=float(alpha/crop['sigma']);b=float(beta-a*crop['mu'])
                if a<=0:
                    failed.append(dict(file=name,status='FAIL',reason='Joint fit nonpositive inverse-Z slope',usedForGeometry=False));continue
                xy,cos,inside=project_rays(rays,crop['rotation'],crop['params'],frame['w']);raw=sample_plane(crop['raw'],xy)
                with np.errstate(divide='ignore',invalid='ignore'):
                    radial=1/(cos*(a*raw+b));prior=1/(cos*(crop['initial']['scale']*raw+crop['initial']['offset']))
                values.append(np.where(inside,radial,np.nan));before.append(np.where(inside,prior,np.nan));scores.append(np.where(inside,cos,-np.inf))
                h=crop['held'];target=distance[h]
                with np.errstate(divide='ignore',invalid='ignore'):
                    hp=1/(crop['anchorCos'][h]*(a*crop['anchorRaw'][h]+b));old=1/(crop['anchorCos'][h]*(crop['initial']['scale']*crop['anchorRaw'][h]+crop['initial']['offset']))
                fit=dict(file=name,physical=physical,status='PASS',scale=a,offset=b,convention='inverse-camera-z',units='sfm-arbitrary',trainingAnchors=int(crop['training'].sum()),heldAnchors=int(h.sum()),
                    initial=crop['initial'],heldBefore=stats(old,target),heldAfter=stats(hp,target),source='Nonheld SfM inverse-radial anchors plus same-center overlap; no physical5 RGB; no metric range claim')
                local_fits.append(fit)
            if len(values)<3:raise ValueError('Joint calibration rejected most faces')
            values=np.array(values);before=np.array(before);scores=np.array(scores);winner=np.argmax(scores,axis=0)
            primary=np.take_along_axis(values,winner[None],axis=0)[0];valid=band&(np.max(scores,axis=0)>0)&np.isfinite(primary)&(primary>0)&(primary<=cap)
            radial=np.where(valid,primary,np.nan);np.savez_compressed(out/f'p{physical:02d}-sphere.npz',radial=radial,winner=winner,valid=valid)
            np.save(out/f'p{physical:02d}-range.npy',radial.astype(np.float32))
            diag=np.zeros((512,1024,3),np.uint8);diag[valid]=[32,214,160];Image.fromarray(diag).save(out/f'p{physical:02d}-valid.png')
            display=np.zeros(radial.shape,np.uint8);display[valid]=np.rint(np.clip(1-radial[valid]/cap,0,1)*255).astype(np.uint8);Image.fromarray(display).save(out/f'p{physical:02d}-radial.png')
            with Image.open(original[physical-1]) as image:rgb=np.asarray(image.convert('RGB').resize((1024,512),Image.Resampling.LANCZOS))
            points,colors,_,_=backproject_radial(radial,rgb,poses[physical],stride=2);all_xyz.append(points);all_rgb.append(colors);fits.extend(local_fits);fits.extend(failed)
            overlap_diag=[]
            for label,vv in [('before',before),('after',values)]:
                available=np.isfinite(vv)&(vv>0)&(vv<=cap);support=available.sum(axis=0);logs=np.log(np.where(available,vv,1));spread=np.max(np.where(available,logs,-np.inf),axis=0)-np.min(np.where(available,logs,np.inf),axis=0);sel=band&(support>=2)
                overlap_diag.append(dict(stage=label,rays=int(sel.sum()),medianLogRangeSpread=float(np.median(spread[sel])) if sel.any() else None,p90LogRangeSpread=float(np.quantile(spread[sel],.9)) if sel.any() else None))
            report['physical'].append(dict(id=physical,calibratedFaces=len(local_fits),failedFaces=len(failed),overlapConstraints=len(overlap_rows),anchorConstraints=len(anchor_rows),validSpherePixels=int(valid.sum()),capSfm=cap,overlap=overlap_diag))
            P.write(out/'report.json',report);P.write(out/'calibrations.json',fits);print('Physical',physical,'faces',len(local_fits),'valid',int(valid.sum()),flush=True)
        spacing=P.read(P.ROOT/'data/jobs/street-conclusion-20261106/fusion/report.json')['results']['dense']['voxelSpacingSfm'];xyz,rgb=voxel_reduce(np.concatenate(all_xyz),np.concatenate(all_rgb),spacing)
        if len(xyz)<5000:raise ValueError('Too few valid calibrated points to train')
        CAL.D.CAL.write_ply(out/'tangent-full.ply',xyz,rgb);sparse=P.read(job/'anchors-training-colors/sparse.json')
        if any(int(r['colorSource'].split('_')[1])==5 for r in sparse):raise ValueError('Withheld RGB sparse colors')
        take=np.linspace(0,len(xyz)-1,min(180000,len(xyz)),dtype=int);seed=np.r_[np.array([r['xyz'] for r in sparse]),xyz[take]];colors=np.r_[np.array([r['rgb'] for r in sparse],np.uint8),rgb[take]]
        dataset=job/'datasets/tangent';dataset.mkdir(parents=True,exist_ok=False)
        for folder in ['images','masks']:
            (dataset/folder).mkdir()
            for frame in frames:shutil.copyfile(inputs/folder/Path(frame['file_path']).name,dataset/folder/Path(frame['file_path']).name)
        for name in ['transforms.json','provenance.json','LICENSE']:shutil.copyfile(inputs/name,dataset/name)
        CAL.D.CAL.write_ply(dataset/'init.ply',seed,colors)
        report.update(status='PASS',geometryStatus='NOT ACCEPTED',points=len(seed),denseFullPoints=len(xyz),sparsePoints=len(sparse),voxelSpacingSfm=spacing,initialPlySha256=P.sha(dataset/'init.ply'),depthReportSha256=P.sha(job/'depth/report.json'),
            coordinateConvention='Calibrated inverse camera-Z converted via actual crop rays to radial range and preserved raw SfM world; arbitrary units.',neuralTensorShapes=sorted({str(r.get('actualModelTensorShape')) for r in inf['images']}))
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=P.now(),elapsedSeconds=time.monotonic()-start,maximumResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);P.write(out/'report.json',report)


def backgrounds(job):
    native_math=P.module('native_math','reconstruct.py')
    native=P.read(job/'training-tangent/world/world.json');out=job/'background-assets';out.mkdir(exist_ok=False)
    transform=native['coordinates']['assetToWorld'];world=np.eye(4);world[:3,:3]=np.array([native_math.rotate(axis,transform['quaternion']) for axis in np.eye(3)]).T*transform['scale'];world[:3,3]=transform['position']
    if transform['scale']!=1:raise ValueError('Background rigid convention requires explicit handling of nonunit scale')
    poses=P.panorama_poses();sources=sorted((P.ROOT/'data/samples/mapillary-beijing/images').glob('*.jpg'));views=[]
    for p in [1,2,3,4,6,7,8,9]:
        image_path=f'p{p:02d}-panorama.jpg';mesh_path=f'p{p:02d}-shell.json';pose=world@poses[p]
        with Image.open(sources[p-1]) as im:display=np.asarray(im.convert('RGB').resize((2048,1024),Image.Resampling.LANCZOS))
        Image.fromarray(fill_display_nadir(display)).save(out/image_path,quality=90)
        radial=np.load(job/f'fusion-tangent/p{p:02d}-range.npy');uu,vv=np.meshgrid(np.arange(128),np.arange(64));u=(uu+.5)/128*1024-.5;v=(vv+.5)/64*512-.5
        small=sample_erp_bilinear(radial,u,v);mesh=shell_mesh(small,pose);P.write(out/mesh_path,mesh)
        views.append(dict(id=f'p{p:02d}',center=pose[:3,3].tolist(),panoramaToWorld=pose.tolist(),imagePath=image_path,meshPath=mesh_path))
    P.write(out/'background.json',dict(schemaVersion=1,views=views,notes='Non5 actual source photographs,2048x1024 derived display copies. Lower15percent known nadir artwork is replaced by smoothed column-color extrapolation fading to a constant, presentation-only nonobserved pixels; not training data or recovered ground. Panorama orientation follows actual rig; backdrop is an infinite-distance appearance approximation. Coarse64x128 calibrated estimated-depth shells reject invalid samples/ratios>1.25; no collision or measured floor. Mesh positions already viewerworldY-up, ERP local+Xright+Ydown+Zforward; UV(u,1-v), wrapS repeat.'))
    P.write(job/'background-report.json',dict(status='PASS',finishedAt=P.now(),physicalSources=[1,2,3,4,6,7,8,9],geometryStatus='NOT ACCEPTED',backgroundSha256=P.sha(out/'background.json'),views=[dict(id=v['id'],imageSha256=P.sha(out/v['imagePath']),meshSha256=P.sha(out/v['meshPath'])) for v in views]))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['fusion','background']);p.add_argument('job',type=Path);a=p.parse_args();fuse(a.job.resolve()) if a.stage=='fusion' else backgrounds(a.job.resolve())
