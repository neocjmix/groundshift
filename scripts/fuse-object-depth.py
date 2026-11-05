#!/usr/bin/env python3
"""Calibrate relative depth by neighboring feature reprojection, then fuse points.

CPU PyCOLMAP/NumPy. This is experimental geometry, not measured metric depth.
Both originals and generated frames retain their kind in the output report.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import time
import traceback

import numpy as np
from PIL import Image
import pycolmap


def read(path):
    return json.loads(path.read_text())


def write(path,data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def write_ply(path,points,colors):
    dtype=np.dtype([('x','<f4'),('y','<f4'),('z','<f4'),('red','u1'),('green','u1'),('blue','u1')])
    data=np.empty(len(points),dtype=dtype)
    for i,k in enumerate(('x','y','z')): data[k]=points[:,i]
    for i,k in enumerate(('red','green','blue')): data[k]=colors[:,i]
    header=f'ply\nformat binary_little_endian 1.0\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n'
    with path.open('wb') as f:
        f.write(header.encode()); data.tofile(f)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset',type=Path); parser.add_argument('depth',type=Path); parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic(); report=dict(status='RUNNING',startedAt=datetime.now(timezone.utc).isoformat(),calibration=[],metricDepth='NOT RUN',independentValidation='NOT RUN')
    try:
        spec=importlib.util.spec_from_file_location('learned_depth',Path(__file__).with_name('warp-learned-depth.py'))
        helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        model=pycolmap.Reconstruction(args.dataset/'sparse')
        depth_records=read(args.depth/'report.json')['images']
        depth_files={Path(item['source']).name:args.depth/f'view-{i:02d}-relative.npy' for i,item in enumerate(depth_records)}
        images=sorted(model.images.values(),key=lambda im:im.name)
        index={im.image_id:i for i,im in enumerate(images)}
        calibrated={}; matrices={}; rgb={}; cameras={}
        for im in images:
            camera=model.cameras[im.camera_id]; K=camera.calibration_matrix()
            T=im.cam_from_world().matrix(); matrices[im.image_id]=T; cameras[im.image_id]=K
            rgb[im.image_id]=np.asarray(Image.open(args.dataset/'images'/im.name).convert('RGB'))
            pred=np.load(depth_files[im.name])
            try:
                pairs=helper.sparse_pairs(model,im,pred)
                beta=helper.robust_affine(pairs[:,0],pairs[:,1])
            except ValueError as error:
                report['calibration'].append(dict(file=im.name,status='FAIL',reason=str(error),usedForDepthFusion=False))
                continue
            rows=[]
            for obs in im.points2D:
                if not obs.has_point3D(): continue
                value=helper.bilinear(pred,float(obs.xy[0])-.5,float(obs.xy[1])-.5)
                if value is None: continue
                ray=np.linalg.solve(K,np.r_[obs.xy,1.])
                point=model.points3D[obs.point3D_id]
                for element in point.track.elements:
                    if element.image_id==im.image_id or element.image_id not in index: continue
                    if abs(index[element.image_id]-index[im.image_id])>8: continue
                    other=model.images[element.image_id]
                    other_T=other.cam_from_world().matrix()
                    R=other_T[:,:3]@T[:,:3].T
                    t=other_T[:,3]-R@T[:,3]
                    rows.append((value,R@ray,t,other.points2D[element.point2D_idx].xy,model.cameras[other.camera_id].calibration_matrix()))
                    if len(rows)>=2000: break
                if len(rows)>=2000: break
            initial=beta.copy()
            if rows:
                v=np.array([r[0] for r in rows]); a=np.array([r[1] for r in rows]); b=np.array([r[2] for r in rows]); xy=np.array([r[3] for r in rows]); ks=np.array([r[4] for r in rows])
                def error(coeff):
                    inv=coeff[0]*v+coeff[1]
                    xyz=a/np.maximum(inv[:,None],1e-8)+b
                    pix=np.einsum('nij,nj->ni',ks,xyz)
                    uv=pix[:,:2]/np.maximum(pix[:,2:],1e-8)
                    result=np.linalg.norm(uv-xy,axis=1)
                    result[(inv<=0)|(xyz[:,2]<=0)]=1e6
                    return result
                best=error(beta); score=(int((best<3).sum()),-float(np.minimum(best,10).mean()))
                for scale_range in (.25,.07):
                    anchor=beta.copy(); offset=np.median(pairs[:,1])*scale_range
                    for ds in np.linspace(-scale_range,scale_range,9):
                        for db in np.linspace(-offset,offset,9):
                            test=np.array([anchor[0]*(1+ds),anchor[1]+db]); errors=error(test)
                            candidate=(int((errors<3).sum()),-float(np.minimum(errors,10).mean()))
                            if candidate>score: beta,best,score=test,errors,candidate
                reprojection=dict(correspondences=len(rows),inliers3px=int((best<3).sum()),medianPixels=float(np.median(best)),initialMedianPixels=float(np.median(error(initial))))
            else: reprojection=dict(correspondences=0)
            inv=beta[0]*pred+beta[1]
            z=np.where(inv>0,1/np.maximum(inv,1e-8),np.nan)
            calibrated[im.image_id]=z
            np.save(args.output/f'{im.name}.depth.npy',z.astype(np.float32))
            report['calibration'].append(dict(file=im.name,status='PASS',usedForDepthFusion=True,kind='observed' if int(Path(im.name).stem.split('_')[-1])%8==0 else 'synthetic',scale=float(beta[0]),offset=float(beta[1]),sparsePairs=len(pairs),**reprojection))
        # Camera optical axes were centered on the target in the observed crops.
        original_images=[im for im in images if int(Path(im.name).stem.split('_')[-1])%8==0]
        centers=[]; directions=[]
        for im in original_images:
            T=matrices[im.image_id]; centers.append(-T[:,:3].T@T[:,3]); directions.append(T[:,:3].T@np.array([0.,0.,1.]))
        projectors=np.array([np.eye(3)-np.outer(d,d) for d in directions])
        center=np.linalg.lstsq(projectors.sum(0),np.einsum('nij,nj->i',projectors,centers),rcond=None)[0]
        distance=float(np.median(np.linalg.norm(np.array(centers)-center,axis=1)))
        radius=distance*.40
        # Manually observed rectangles enclose the white scooter in three real
        # crops. Their visual-hull intersection isolates it from the black scooter.
        bounds={'frame_0000.png':[150,177,299,288], 'frame_0032.png':[50,115,305,350], 'frame_0064.png':[166,145,329,341]}
        clipping=[]
        for im in original_images:
            if im.name in bounds:
                clipping.append(dict(file=im.name,bounds=bounds[im.name],worldToCamera=matrices[im.image_id].tolist(),intrinsics=cameras[im.image_id].tolist()))
        points,colors=[],[]; fusion=[]
        for im in images:
            if im.image_id not in calibrated: continue
            z=calibrated[im.image_id]; K=cameras[im.image_id]; T=matrices[im.image_id]
            y,x=np.mgrid[0:z.shape[0]:2,0:z.shape[1]:2]; depth=z[y,x]
            pixels=np.stack([x+.5,y+.5,np.ones_like(x)],axis=-1)
            xyz=(pixels@np.linalg.inv(K).T)*depth[...,None]
            world=(xyz.reshape(-1,3)-T[:,3])@T[:,:3]
            color=rgb[im.image_id][y,x].reshape(-1,3)
            valid=np.isfinite(world).all(1)&(depth.reshape(-1)>0)&(np.linalg.norm(world-center,axis=1)<radius)
            ids=np.where(valid)[0]; world=world[ids]; color=color[ids]
            support=np.zeros(len(world),dtype=bool)
            # Prefer real neighboring photographs as support, including for synthetic depths.
            neighbors=sorted([j for j in original_images if j.image_id!=im.image_id and j.image_id in calibrated],key=lambda j:abs(index[j.image_id]-index[im.image_id]))[:2]
            for other in neighbors:
                O=matrices[other.image_id]; ok=cameras[other.image_id]; oz=calibrated[other.image_id]
                camera_xyz=world@O[:,:3].T+O[:,3]
                proj=camera_xyz@ok.T; uv=proj[:,:2]/np.maximum(proj[:,2:],1e-8)-.5
                ix=np.rint(uv[:,0]).astype(int); iy=np.rint(uv[:,1]).astype(int)
                inside=(camera_xyz[:,2]>0)&(ix>=0)&(iy>=0)&(ix<oz.shape[1])&(iy<oz.shape[0])
                n=np.where(inside)[0]; expected=oz[iy[n],ix[n]]
                agreement=np.abs(expected-camera_xyz[n,2])/np.maximum(expected,1e-8)<.15
                color_error=np.abs(rgb[other.image_id][iy[n],ix[n]].astype(float)-color[n]).mean(1)
                support[n]|=agreement&(color_error<50)
            points.append(world[support]); colors.append(color[support])
            fusion.append(dict(file=im.name,candidatePoints=len(world),supportedPoints=int(support.sum())))
        xyz=np.concatenate(points); color=np.concatenate(colors)
        keep=np.ones(len(xyz),dtype=bool)
        for item in clipping:
            T=np.array(item['worldToCamera']);K=np.array(item['intrinsics']); b=item['bounds']
            p=(xyz@T[:,:3].T+T[:,3])@K.T
            uv=p[:,:2]/np.maximum(p[:,2:],1e-8)
            keep&=(p[:,2]>0)&(uv[:,0]>=b[0])&(uv[:,0]<=b[2])&(uv[:,1]>=b[1])&(uv[:,1]<=b[3])
        xyz=xyz[keep]; color=color[keep]
        if len(xyz)<500: raise RuntimeError(f'Only {len(xyz)} supported dense points; inspect input geometry')
        cell=radius/180
        _,indices=np.unique(np.floor(xyz/cell).astype(np.int64),axis=0,return_index=True)
        xyz=xyz[indices];color=color[indices]
        dataset=args.output/'dataset'; dataset.mkdir()
        shutil.copytree(args.dataset/'images',dataset/'images')
        transforms=read(args.dataset/'transforms.json'); transforms['ply_file_path']='init.ply'
        write(dataset/'transforms.json',transforms)
        provenance=read(args.dataset/'provenance.json');provenance['notes']+=' Dense initial points come from relative monocular depth calibrated to neighboring feature reprojection and filtered by depth/color agreement with actual images. This is experimental estimated geometry in arbitrary scale.'
        write(dataset/'provenance.json',provenance)
        write_ply(dataset/'init.ply',xyz,color)
        # A compact browser observation copy; do not publish raw depth or source reports.
        stride=max(1,int(np.ceil(len(xyz)/40000)))
        center=np.median(xyz,axis=0); radius=float(np.quantile(np.linalg.norm(xyz-center,axis=1),.98))
        home_frame=next((f for f in transforms['frames'] if Path(f['file_path']).name=='frame_0032.png'),transforms['frames'][len(transforms['frames'])//2])
        home=np.array(home_frame['transform_matrix'])
        write(args.output/'cloud.json',dict(positions=xyz[::stride].round(5).reshape(-1).tolist(),colors=color[::stride].reshape(-1).tolist(),center=center.tolist(),radius=radius,camera=dict(position=home[:3,3].tolist(),up=home[:3,1].tolist(),fov=45)))
        report.update(status='PASS',calibratedImages=len(calibrated),rejectedDepthImages=len(images)-len(calibrated),points=len(xyz),focus=center.tolist(),radius=radius,clipping=clipping,voxelSize=cell,fusion=fusion,meaning='Relative depth fusion; sparse/SfM correspondence optimization is internal calibration, not external validation. Rejected depth maps do not contribute points; their posed RGB images remain training inputs.')
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(elapsedSeconds=time.monotonic()-started,finishedAt=datetime.now(timezone.utc).isoformat());write(args.output/'report.json',report)


if __name__=='__main__': main()
