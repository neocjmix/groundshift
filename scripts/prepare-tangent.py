#!/usr/bin/env python3
"""One twenty-direction real ERP preparation; preserve fixed physical cameras."""
import argparse
from pathlib import Path
import importlib.util
import shutil
import time
import numpy as np
from PIL import Image,ImageDraw
from spherical_depth import erp_unit_rays,directions_to_erp
from tangent_geometry import icosahedron_normals,view_angles,project_rays

spec=importlib.util.spec_from_file_location('prepare',Path(__file__).with_name('prepare-street.py'))
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
C=P.module('crops','prepare-panoramas.py')


def prepare(job):
    out=job/'inputs-tangent';out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    report=dict(status='RUNNING',startedAt=P.now(),heldPhysicalPanorama=5)
    try:
        views=[];size=1024;fov=80;intr=C.intrinsics(size,fov);params=[intr[k] for k in ['fx','fy','cx','cy']]
        for i,n in enumerate(icosahedron_normals()):
            yaw,pitch=view_angles(n);rotation=C.crop_rotation(yaw,pitch)
            if not np.allclose(rotation[:,2],n,atol=1e-10):raise ValueError('Face direction disagrees with crop rotation')
            views.append(dict(id=i,yaw=yaw,pitch=pitch,normal=n.tolist(),rotation=rotation.tolist()))
        rays=erp_unit_rays(270,540);coverage=np.zeros(rays.shape[:2],int)
        for v in views:coverage+=project_rays(rays,v['rotation'],params,size)[2]
        if not np.all(coverage>=1):raise ValueError('Declared layout leaves uncovered sphere rays')
        for name in ['images','masks']:(out/name).mkdir()
        color=np.zeros((*coverage.shape,3),np.uint8);color[...,0]=np.minimum(coverage*30,255);color[...,1]=np.minimum(coverage*65,255);color[...,2]=160
        Image.fromarray(color).save(out/'angular-coverage.png')
        poses=P.panorama_poses();source_manifest=P.read(P.ROOT/'scripts/samples/mapillary-beijing.json')
        originals=sorted((P.ROOT/'data/samples/mapillary-beijing/images').glob('*.jpg'));frames=[];records=[];paths=[]
        yy,xx=np.indices((size,size));local=np.stack([(xx+.5-size/2)/intr['fx'],(yy+.5-size/2)/intr['fy'],np.ones((size,size))],axis=-1);local/=np.linalg.norm(local,axis=-1,keepdims=True)
        for physical,path in enumerate(originals,1):
            if P.sha(path)!=source_manifest['images'][physical-1]['sha256']:raise ValueError('Original panorama bytes changed')
            if physical==5:continue
            with Image.open(path) as im:pixels=np.asarray(im.convert('RGB'))
            for v in views:
                name=f'p{physical:02d}-tangent-{v["id"]:02d}.png';rotation=np.array(v['rotation']);pose=poses[physical].copy();pose[:3,:3]=pose[:3,:3]@rotation
                rgb=C.crop_panorama(pixels,size,fov,v['yaw'],v['pitch']);_,y=directions_to_erp(local@rotation.T,270,540);valid=(y+.5)/270<=.85
                Image.fromarray(rgb).save(out/'images'/name);Image.fromarray(valid.astype(np.uint8)*255).save(out/'masks'/name)
                frame=dict(file_path='images/'+name,w=size,h=size,fl_x=intr['fx'],fl_y=intr['fy'],cx=size/2,cy=size/2,
                    physicalPanorama=physical,face=v['id'],yaw=v['yaw'],pitch=v['pitch'],ring='tangent',transform_matrix=(pose@np.diag([1,-1,-1,1])).tolist())
                frames.append(frame);records.append(dict(**frame,sourceSha256=source_manifest['images'][physical-1]['sha256'],imageSha256=P.sha(out/'images'/name),maskSha256=P.sha(out/'masks'/name)));paths.append(str((out/'images'/name).resolve()))
        if len(frames)!=160 or any(f['physicalPanorama']==5 for f in frames):raise ValueError('Wrong training/withholding identities')
        P.write(out/'transforms.json',dict(camera_model='PINHOLE',ply_file_path='init.ply',frames=frames));P.write(out/'inference-inputs.json',paths);P.write(out/'views.json',views)
        provenance=P.read(P.RIG/'provenance.json');provenance['notes']+=' Explicit user-reopened tangent/background experiment:20co-located real1024px80degree projections per non5 physicalcenter;160trainviews,all-nine SfM reused. No diffusion, no newphysicalcameras. Depth must be explicitly calibrated to arbitrary SfM units.'
        P.write(out/'provenance.json',provenance);shutil.copyfile(P.ROOT/'data/jobs/street-final-quality-20261106/inputs-hires/LICENSE',out/'LICENSE')
        (job/'inputs').symlink_to((P.ROOT/'data/jobs/street-conclusion-20261106/inputs').resolve(),target_is_directory=True)
        (job/'training-baseline').symlink_to((P.ROOT/'data/jobs/street-final-quality-20261106/training-hires').resolve(),target_is_directory=True)
        (job/'anchors-training-colors').symlink_to((P.ROOT/'data/jobs/street-conclusion-20261106/anchors-training-colors').resolve(),target_is_directory=True)
        canvas=Image.new('RGB',(5*256,4*280),(20,27,32));draw=ImageDraw.Draw(canvas)
        for i,v in enumerate(views):
            im=Image.open(out/'images'/f'p04-tangent-{i:02d}.png').convert('RGB').resize((256,256));x,y=(i%5)*256,(i//5)*280;canvas.paste(im,(x,y+24));draw.text((x+4,y+5),f'face{i:02d} yaw{v["yaw"]:.1f} pitch{v["pitch"]:.1f}',fill='white')
        canvas.save(out/'p04-twenty-real-views.jpg',quality=91)
        report.update(status='PASS',trainingImages=len(frames),resolution=size,fovDegrees=fov,viewsPerPhysical=20,trainingPhysical=[1,2,3,4,6,7,8,9],frames=records,
            coverage=dict(sampledRays=int(coverage.size),uncovered=int((coverage==0).sum()),minimum=int(coverage.min()),mean=float(coverage.mean()),maximum=int(coverage.max())),
            sourceManifestSha256=P.sha(P.ROOT/'scripts/samples/mapillary-beijing.json'),poseDocumentSha256=P.sha(P.BASE/'evaluation-cameras.json'),meaning='Full sphere angular coverage is not valid depth coverage or additional physical camera baselines.')
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=P.now(),elapsedSeconds=time.monotonic()-start);P.write(out/'report.json',report)
    print('PASS160real1024crops; coverage',report['coverage'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);a=p.parse_args();prepare(a.job.resolve())
