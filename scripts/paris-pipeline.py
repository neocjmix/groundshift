#!/usr/bin/env python3
"""Bounded Paris ERP -> actual fixed-rig SfM -> calibrated DAV2 seed.

Stages deliberately use existing local tools. No GPS poses, generated RGB,
metric depth, source-photo backdrop or hidden fallback model is introduced.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import time
import numpy as np
from PIL import Image
from tangent_geometry import icosahedron_normals, view_angles
from perspective_sphere import sample_plane
from street_geometry import voxel_reduce


def module(name, filename):
    s = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


C = module('paris_crop', 'prepare-panoramas.py')
CAL = module('paris_calibration', 'compare-perspective-depth.py')
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'data/jobs/tourist-streaming-20261107/hd-initial'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    C.write_json(path, value)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def immutable_image_copy(source, target):
    """Generated crops/masks are immutable; preserve bytes without another copy."""
    try:os.link(source,target)
    except OSError:shutil.copy2(source,target)
    return target


def acquisition(source):
    record = read(source/'acquisition.json')
    if record['status'] != 'PASS' or not 3 <= len(record['frames']) <= 64:
        raise ValueError('Require a complete pinned acquisition of 3..64 panoramas')
    ranks = [frame['rank'] for frame in record['frames']]
    if ranks != list(range(ranks[0], ranks[0] + len(ranks))):
        raise ValueError('Require consecutive ordered source ranks')
    return record


def prepare(job, source=SOURCE):
    out = job/'tangent-inputs'; out.mkdir(exist_ok=False); start = time.monotonic()
    report = dict(status='RUNNING', stage='real20direction768crop', sources=[])
    try:
        for k in ['images', 'masks']:(out/k).mkdir()
        acquired = acquisition(source)
        size, fov = 768, 80
        intr = C.intrinsics(size, fov); views=[]; frames=[]; paths=[]
        for i, normal in enumerate(icosahedron_normals()):
            yaw,pitch=view_angles(normal)
            views.append(dict(id=i,yaw=yaw,pitch=pitch,rotation=C.crop_rotation(yaw,pitch).tolist()))
        for index, frame_source in enumerate(acquired['frames']):
            path=source/frame_source['file']
            if sha(path)!=frame_source['sha256']:raise ValueError('Original source checksum mismatch')
            with Image.open(path) as im:rgb=np.array(im.convert('RGB'))
            for view in views:
                name=f'p{index:02d}-t{view["id"]:02d}.png'
                image=C.crop_panorama(rgb,size,fov,view['yaw'],view['pitch'])
                _,v=C.sampling_map(rgb.shape[1],rgb.shape[0],size,fov,view['yaw'],view['pitch'])
                # Source roof/black nadir excluded; mask is preprocessing, not ground.
                mask=(v+.5)/rgb.shape[0]<.78
                Image.fromarray(image).save(out/'images'/name)
                Image.fromarray(mask.astype(np.uint8)*255).save(out/'masks'/name)
                frame=dict(file_path='images/'+name,w=size,h=size,fl_x=intr['fx'],fl_y=intr['fy'],cx=size/2,cy=size/2,
                    physical=index,rank=frame_source['rank'],view=view['id'],rotation=view['rotation'])
                frames.append(frame);paths.append(str((out/'images'/name).resolve()))
            report['sources'].append(dict(rank=frame_source['rank'],sha256=frame_source['sha256'],file=Path(frame_source['file']).name))
            write(out/'report.json',report);print('Cropped',frame_source['rank'],flush=True)
        write(out/'frames.json',frames);write(out/'inference-inputs.json',paths)
        shutil.copyfile(job/'provenance.json',out/'provenance.json')
        report.update(status='PASS',images=len(frames),size=size,fovDegrees=fov,viewsPerPhysical=20,generatedRgb=False)
    except Exception as error:report.update(status='FAIL',error=str(error));raise
    finally:report['seconds']=time.monotonic()-start;write(out/'report.json',report)


def anchors(job):
    import pycolmap
    out=job/'anchors';out.mkdir(exist_ok=False);start=time.monotonic()
    report=dict(status='RUNNING')
    try:
        sfm=read(job/'sfm/report.json')
        if sfm['status']!='PASS' or sfm['fullRegistration']!='PASS':
            raise ValueError('Require every physical center in the same actual rig reconstruction')
        model=pycolmap.Reconstruction(job/'sfm/dataset/sparse')
        crops=read(job/'sfm-inputs/crops.json')['crops'];by_name={Path(c['file']).name:c for c in crops}
        groups={};poses={}
        for image in model.images.values():
            crop=by_name[image.name];p=crop['sourceIndex']
            pose=np.eye(4);pose[:3]=image.cam_from_world().inverse().matrix()
            pose[:3,:3]=pose[:3,:3]@np.array(crop['relativeCameraToPanoramaRotation']).T
            if p in poses and not np.allclose(poses[p],pose,atol=1e-7):raise ValueError('Rig centers disagree')
            poses[p]=pose;ids=groups.setdefault(p,set())
            for point in image.points2D:
                if point.has_point3D():ids.add(int(point.point3D_id))
        result={};sparse=[]
        for pid,point in model.points3D.items():
            if point.error<=3 and point.track.length()>=3:
                sparse.append(dict(id=int(pid),xyz=point.xyz.tolist(),rgb=point.color.tolist()))
        indexed={r['id']:r for r in sparse}
        for p,ids in groups.items():
            result[str(p)]=dict(pose=poses[p].tolist(),points=[indexed[i] for i in sorted(ids) if i in indexed])
        write(out/'physical.json',result);write(out/'sparse.json',sparse)
        report.update(status='PASS',physicalCenters=len(poses),sparsePoints=len(sparse),anchorsPerPhysical={p:len(r['points']) for p,r in result.items()},
            semantics='Actual image-derived SfM in arbitrary units, fixed analytic crop rig; not GPS or measured metric truth')
    except Exception as error:report.update(status='FAIL',error=str(error));raise
    finally:report['seconds']=time.monotonic()-start;write(out/'report.json',report)


def fusion(job):
    out=job/'fusion';out.mkdir(exist_ok=False);start=time.monotonic()
    report=dict(status='RUNNING',fits=[],rejected=[])
    try:
        inf=read(job/'depth/report.json');frames=read(job/'tangent-inputs/frames.json')
        if inf['status']!='PASS' or inf['model']!='depth-anything/Depth-Anything-V2-Small-hf' or inf['revision']!='5426e4f0f36572d16453bbda7a8389317b1bef99' or inf['device']!='mps' or len(inf['images'])!=len(frames):
            raise ValueError('Require complete pinned DAV2 MPS execution')
        records={Path(r['source']).name:(i,r) for i,r in enumerate(inf['images'])}
        physical=read(job/'anchors/physical.json');points=[];colors=[];posed=[]
        # Numerical seed-thinning size from the preserved SfM record order.
        # This is not a physical/GPS interval or a calibrated metric voxel size.
        centers=np.array([p['pose'] for p in physical.values()])[:,:3,3]
        baseline=float(np.median(np.linalg.norm(np.diff(centers,axis=0),axis=1)))
        if baseline<=0:raise ValueError('No reconstructed baseline')
        for frame in frames:
            pose=np.array(physical[str(frame['physical'])]['pose']);rotation=np.array(frame['rotation']);pose[:3,:3]=pose[:3,:3]@rotation
            name=Path(frame['file_path']).name;index,record=records[name];raw_path=job/f'depth/view-{index:02d}-relative.npy'
            if sha(job/'tangent-inputs'/frame['file_path'])!=record['sourceSha256'] or sha(raw_path)!=record['relativeNpySha256']:raise ValueError('Depth checksum mismatch')
            raw=np.load(raw_path);rows=physical[str(frame['physical'])]['points'];xyz=np.array([r['xyz'] for r in rows]);local=(xyz-pose[:3,3])@pose[:3,:3]
            with np.errstate(divide='ignore',invalid='ignore'):xy=local[:,:2]/local[:,2,None]*[frame['fl_x'],frame['fl_y']]+[frame['cx'],frame['cy']]
            predictions=sample_plane(raw,xy);valid=np.isfinite(predictions)&(local[:,2]>0)
            held=np.array([r['id']%5==0 for r in rows]);train=valid&~held
            converted=pose@np.diag([1,-1,-1,1]);posed.append({**{k:v for k,v in frame.items() if k not in ['rotation','rank','view','physical']},'transform_matrix':converted.tolist()})
            try:
                fit=CAL.camera_z_fit(predictions[train],local[train,2])
                if fit['scale']<=0:raise ValueError('Nonpositive inverse-Z slope')
            except ValueError as error:
                report['rejected'].append(dict(file=name,reason=str(error),depthGeometryUsed=False));continue
            yy,xx=np.indices(raw.shape);ray=np.stack([(xx+.5-frame['cx'])/frame['fl_x'],(yy+.5-frame['cy'])/frame['fl_y'],np.ones(raw.shape)],axis=-1)
            with np.errstate(divide='ignore',invalid='ignore'):z=1/(fit['scale']*raw+fit['offset'])
            radial=z*np.linalg.norm(ray,axis=-1);cap=float(np.quantile(np.linalg.norm(xyz-pose[:3,3],axis=1),.98))
            mask=(np.array(Image.open(job/'tangent-inputs/masks'/name))>0)&np.isfinite(z)&(z>0)&(radial<=cap)
            z=np.where(mask,z,np.nan);q=(ray[::5,::5]*z[::5,::5,None]).reshape(-1,3)@pose[:3,:3].T+pose[:3,3]
            rgb=np.array(Image.open(job/'tangent-inputs/images'/name).convert('RGB'))[::5,::5].reshape(-1,3);ok=np.isfinite(q).all(axis=1)
            points.append(q[ok]);colors.append(rgb[ok])
            h=valid&held
            with np.errstate(divide='ignore',invalid='ignore'):hp=1/(fit['scale']*predictions[h]+fit['offset'])
            good=np.isfinite(hp)&(hp>0)
            report['fits'].append(dict(file=name,trainingAnchors=int(train.sum()),heldAnchors=int(h.sum()),validHeld=int(good.sum()),heldMedianAbsRel=float(np.median(np.abs(hp[good]/local[h,2][good]-1))) if good.any() else None,fit=fit,seedCandidates=int(ok.sum())))
            if len(report['fits'])%20==0:write(out/'report.json',report);print('Depth fits',len(report['fits']),flush=True)
        xyz,rgb=voxel_reduce(np.concatenate(points),np.concatenate(colors),baseline/100)
        sparse=read(job/'anchors/sparse.json');take=np.linspace(0,len(xyz)-1,min(180000,len(xyz)),dtype=int)
        seed=np.r_[np.array([r['xyz'] for r in sparse]),xyz[take]];color=np.r_[np.array([r['rgb'] for r in sparse],np.uint8),rgb[take]]
        dataset=job/'dataset';dataset.mkdir(exist_ok=False)
        for folder in ['images','masks']:shutil.copytree(job/'tangent-inputs'/folder,dataset/folder,copy_function=immutable_image_copy)
        write(dataset/'transforms.json',dict(camera_model='PINHOLE',ply_file_path='init.ply',frames=posed))
        shutil.copyfile(job/'provenance.json',dataset/'provenance.json')
        (dataset/'LICENSE').write_text('Source: Immergis pour la Ville de Paris / Panoramax IGN, Open Licence2.0 (etalab-2.0). Captured2025-05-08, accessed2026-11-07. https://github.com/etalab/licence-ouverte/blob/master/open-licence.md\n')
        CAL.D.CAL.write_ply(dataset/'init.ply',seed,color)
        report.update(status='PASS',trainingImages=len(posed),calibratedImages=len(report['fits']),initialPoints=len(seed),densePoints=len(xyz),voxelSpacingSfm=baseline/100,initialSha256=sha(dataset/'init.ply'),geometryStatus='NOT ACCEPTED',depthSemantics='Per-crop robust affine inverse-camera-Z calibrated to observed SfM points; no arbitrary meters; point seeds converted with actual pinhole rays')
    except Exception as error:report.update(status='FAIL',error=str(error));raise
    finally:report['seconds']=time.monotonic()-start;write(out/'report.json',report)


def finalize(job, source=SOURCE):
    """Separate presentation derivative: keep all original native exports intact."""
    R=module('paris_native','reconstruct.py');native=job/'training/world'
    status=read(job/'training/job.json')
    if status['status']!='PASS':raise ValueError('Require completed actual native export')
    out=job/'view-world';out.mkdir(exist_ok=False)
    world=read(native/'world.json');physical=read(job/'anchors/physical.json')
    acquired=acquisition(source);count=len(acquired['frames']);ranks=[f['rank'] for f in acquired['frames']]
    if set(physical) != {str(i) for i in range(count)}:raise ValueError('Acquisition and estimated physical centers disagree')
    quaternion=world['coordinates']['assetToWorld']['quaternion'];frames=[]
    for p in range(count):
        pose=np.array(physical[str(p)]['pose'])@np.diag([1,-1,-1,1]);columns=[R.rotate(pose[:3,k].tolist(),quaternion) for k in range(4)]
        matrix=[[columns[k][i] for k in range(4)] for i in range(3)]+[[0,0,0,1]]
        frames.append(dict(image=f'panorama-rank-{ranks[p]}',cameraToWorld=matrix,componentId=world['id']+'-rig',continuousFromPrevious=p>0))
    first=np.array(frames[0]['cameraToWorld']);camera=world['navigation']['camera'];camera.update(position=first[:3,3].tolist(),target=(first[:3,3]-first[:3,2]*5).tolist(),up=first[:3,1].tolist(),fov=80)
    world['navigation']['mode']='camera-path'
    fusion_report=read(job/'fusion/report.json')
    world['provenance']['notes']+=f' Viewer camera path selects one analytic ERP-center direction at each of the {count} actual registered physical centers in source rank order {ranks[0]}-{ranks[-1]}. Same component; source prev adjacency verified at acquisition. Straight interpolation is presentation, not a recovered road or collision surface. 20-direction 768px actual RGB, calibrated {fusion_report["calibratedImages"]} of {fusion_report["trainingImages"]} DAV2 depth maps; rejected depths never used as metric geometry. No source-photo backdrop.'
    write(out/'world.json',world)
    write(out/'cameras.json',dict(schemaVersion=1,cameraConvention='OpenGL: +X right, +Y up, -Z forward',worldConvention='right-handed Y-up, arbitrary units',frames=frames,
        sequenceNotes=f'One shared image-derived rig reconstruction of {count} consecutive Panoramax captures, ranks {ranks[0]}-{ranks[-1]}. Provider adjacency verified at acquisition. Source GPS length is approximate; world scale arbitrary. Straight viewing interpolation, not surveyed path/floor.'))
    for name in ['scene.ply','SOURCE_LICENSE']:shutil.copyfile(native/name,out/name)
    write(job/'view-export.json',dict(status='PASS',nativeSceneSha256=sha(native/'scene.ply'),viewerSceneSha256=sha(out/'scene.ply'),physicalPathPoses=count,background=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=['prepare','anchors','fusion','finalize']);p.add_argument('job',type=Path)
    p.add_argument('--source',type=Path,default=SOURCE,help='Complete verified acquisition; originals remain unchanged')
    a=p.parse_args()
    if a.stage in ('prepare','finalize'):globals()[a.stage](a.job.resolve(),a.source.resolve())
    else:globals()[a.stage](a.job.resolve())
