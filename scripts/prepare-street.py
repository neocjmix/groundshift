#!/usr/bin/env python3
"""Prepare one end-to-end street comparison, using preserved real RGB and poses.

Two explicit environments: `inputs` needs OpenCV; `anchors` needs PyCOLMAP.
Each stage requires a fresh output directory. Originals/previous jobs are read-only.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time
import numpy as np
from PIL import Image
from spherical_depth import directions_to_erp

ROOT=Path(__file__).resolve().parents[1]
RIG=ROOT/'data/jobs/mapillary-beijing-rig-poses-v2/dataset'
BASE=ROOT/'data/jobs/panoramic-baseline-20261106'


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def panorama_poses():
    records=read(BASE/'evaluation-cameras.json')['fixedRigCameras']
    return {int(r['id'].split('-')[1]):np.array(r['worldFromPanorama']) for r in records if r['kind']=='observed'}


def prepare_inputs(output):
    C=module('crops','prepare-panoramas.py'); output.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    report=dict(status='RUNNING',startedAt=now(),heldPhysicalPanorama=5,frames=[])
    try:
        poses=panorama_poses();manifest=read(ROOT/'scripts/samples/mapillary-beijing.json')
        sources=sorted((ROOT/'data/samples/mapillary-beijing/images').glob('*.jpg'))
        for folder in ['images','masks','evaluation']: (output/folder).mkdir()
        frames=[];evaluation=[];inference=[]
        yy,xx=np.indices((512,512));camera_rays=np.stack([(xx+.5-256)/256,(yy+.5-256)/256,np.ones((512,512))],axis=-1)
        camera_rays/=np.linalg.norm(camera_rays,axis=-1,keepdims=True)
        for physical,path in enumerate(sources,1):
            if sha(path)!=manifest['images'][physical-1]['sha256']:raise ValueError('Source provenance hash mismatch')
            pixels=np.asarray(Image.open(path).convert('RGB'))
            for ring,pitch in [('level',0),('down',-30)]:
                for yaw in range(0,360,60):
                    name=f'p{physical:02d}-{ring}-{yaw:03d}.png'
                    rotation=C.crop_rotation(yaw,pitch);world=poses[physical].copy();world[:3,:3]=poses[physical][:3,:3]@rotation
                    frame=dict(file_path='images/'+name,w=512,h=512,fl_x=256,fl_y=256,cx=256,cy=256,
                        physicalPanorama=physical,ring=ring,yaw=yaw,pitch=pitch,transform_matrix=(world@np.diag([1,-1,-1,1])).tolist())
                    rgb=C.crop_panorama(pixels,512,90,yaw,pitch)
                    rays=camera_rays@rotation.T;_,v=directions_to_erp(rays,546,1092);uv_v=(v+.5)/546
                    # Only exclude the known camera/nadir band; do not invent sky geometry.
                    valid=uv_v<=.85
                    Image.fromarray(rgb).save(output/'images'/name)
                    Image.fromarray(valid.astype(np.uint8)*255).save(output/'masks'/name)
                    item=dict(**frame,sourceSha256=sha(path),imageSha256=sha(output/'images'/name),maskSha256=sha(output/'masks'/name),training=physical!=5)
                    report['frames'].append(item);evaluation.append(frame)
                    if physical!=5:frames.append(frame);inference.append(str((output/'images'/name).resolve()))
        write(output/'transforms.json',dict(camera_model='PINHOLE',frames=frames,ply_file_path='init.ply'))
        write(output/'evaluation/transforms.json',dict(camera_model='PINHOLE',frames=evaluation))
        # Reference images live at ../images; evaluation is a render contract, not trainer input.
        for f in evaluation:f['file_path']='../'+f['file_path']
        write(output/'evaluation/transforms.json',dict(camera_model='PINHOLE',frames=evaluation))
        provenance=read(RIG/'provenance.json');provenance['notes']+=' Street comparison: original panorama5 RGB is excluded from GS optimization and dense initialization. Camera/SfM geometry uses all nine panoramas. Real level and downward crops only, no diffusion. Known nadir band ignored by masks.'
        write(output/'provenance.json',provenance)
        (output/'LICENSE').write_text('Original photographs: Cicero101 / Mapillary via Wikimedia Commons. CC BY-SA4.0. https://creativecommons.org/licenses/by-sa/4.0/\nDerived perspective crops, depth diagnostics and reconstruction. Original source URLs/hashes: scripts/samples/mapillary-beijing.json\n')
        write(output/'inference-inputs.json',inference)
        report.update(status='PASS',trainingImages=len(frames),evaluationImages=len(evaluation),physicalTrainingCenters=8,
            maskConvention='Brush v0.3: dataset/masks/same-stem.png, white255 participates, black0 ignored; same angular nadir exclusion for all methods.',
            sourceManifestSha256=sha(ROOT/'scripts/samples/mapillary-beijing.json'),poseDocumentSha256=sha(BASE/'evaluation-cameras.json'))
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=now(),elapsedSeconds=time.monotonic()-start);write(output/'report.json',report)
    print(report['status'],report['trainingImages'],'training images')


def extract_anchors(output):
    import pycolmap
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();report=dict(status='RUNNING',startedAt=now())
    try:
        model=pycolmap.Reconstruction(RIG/'sparse');poses=panorama_poses();groups={p:{} for p in poses}
        cameras={};sparse=[]
        for image in model.images.values():
            physical=int(image.name.split('_')[1]);camera=model.cameras[image.camera_id];matrix=image.cam_from_world().matrix()
            if camera.model_name!='PINHOLE':raise ValueError('Require original PINHOLE rig model')
            params=np.asarray(camera.params);world=np.eye(4);world[:3,:3]=matrix[:3,:3].T;world[:3,3]=-matrix[:3,:3].T@matrix[:,3]
            np.testing.assert_allclose(world[:3,3],poses[physical][:3,3],atol=1e-9)
            cameras[image.name]=dict(physicalPanorama=physical,worldFromCameraCv=world.tolist(),params=params.tolist())
            for observation in image.points2D:
                if not observation.has_point3D():continue
                pid=int(observation.point3D_id);point=model.points3D[pid];xy=np.array(observation.xy)
                ray=np.r_[(xy-params[2:])/params[:2],1.];ray/=np.linalg.norm(ray)
                pano_ray=ray@world[:3,:3].T@poses[physical][:3,:3]
                old=groups[physical].get(pid)
                if old is None or ray[2]>old['centrality']:
                    groups[physical][pid]=dict(id=pid,xyz=point.xyz.tolist(),rayPanorama=pano_ray.tolist(),centrality=float(ray[2]),image=image.name,observedCorner=xy.tolist())
        color_images={}
        for pid,point in model.points3D.items():
            physicals={int(model.images[e.image_id].name.split('_')[1]) for e in point.track.elements}
            # Dense and sparse methods share this geometry. Keep only genuine
            # nonzero-baseline support outside the withheld GS center.
            if len(physicals-{5})>=2:
                # COLMAP point.color can average withheld RGB. Recolor from an
                # actually observed training pixel, never from panorama5.
                choices=[groups[p][int(pid)] for p in physicals-{5} if int(pid) in groups[p]]
                chosen=max(choices,key=lambda row:row['centrality']);name=chosen['image']
                if name not in color_images:color_images[name]=np.asarray(Image.open(RIG/'images'/name).convert('RGB'))
                pixel=np.rint(np.asarray(chosen['observedCorner'])-.5).astype(int)
                h,w=color_images[name].shape[:2];x,y=np.clip(pixel,[0,0],[w-1,h-1])
                sparse.append(dict(id=int(pid),xyz=point.xyz.tolist(),rgb=color_images[name][y,x].tolist(),observedPhysical=sorted(physicals),colorSource=name))
        write(output/'anchors.json',{str(p):list(points.values()) for p,points in groups.items()})
        write(output/'sparse.json',sparse);write(output/'cameras.json',cameras)
        report.update(status='PASS',points=len(sparse),anchorCounts={str(p):len(points) for p,points in groups.items()},
            conventions='True observed corner-origin crop pixels converted to unit panorama rays; 3D positions from all-nine fixed-rig SfM, arbitrary units.',
            sourceFiles=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted((RIG/'sparse').glob('*.bin'))])
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=now(),elapsedSeconds=time.monotonic()-start);write(output/'report.json',report)
    print(report['status'],report['points'],'sparse points',report['anchorCounts'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['inputs','anchors']);p.add_argument('output',type=Path)
    a=p.parse_args();(prepare_inputs if a.stage=='inputs' else extract_anchors)(a.output.resolve())
