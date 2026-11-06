"""Fixed-pose pinhole geometry for observed correspondences, not pose recovery."""
import numpy as np


def camera_from_pose(world_from_camera, params):
    pose, params = np.asarray(world_from_camera,float), np.asarray(params,float)
    if (pose.shape!=(4,4) or not np.isfinite(pose).all()
            or not np.allclose(pose[3],[0,0,0,1])
            or not np.allclose(pose[:3,:3].T@pose[:3,:3],np.eye(3),atol=1e-8)
            or not np.isclose(np.linalg.det(pose[:3,:3]),1)):
        raise ValueError('Require right-handed rigid camera-to-world pose')
    if params.shape!=(4,) or not np.isfinite(params).all() or np.any(params[:2]<=0):
        raise ValueError('Require corner-origin fx,fy,cx,cy')
    matrix=np.column_stack([pose[:3,:3].T,-pose[:3,:3].T@pose[:3,3]])
    k=np.array([[params[0],0,params[2]],[0,params[1],params[3]],[0,0,1]])
    return dict(pose=pose,params=params,matrix=matrix,projection=k@matrix)


def triangulate_observed(xy0,xy1,camera0,camera1):
    """Corner-origin float pixels -> homogeneous DLT and explicit diagnostics.

    OpenCV feature coordinates are array-index centers; callers must add .5.
    Projection residual/parallax are diagnostics, not independent depth accuracy.
    """
    xy0,xy1=np.asarray(xy0,float),np.asarray(xy1,float)
    if xy0.ndim!=2 or xy0.shape[1]!=2 or xy1.shape!=xy0.shape or not np.isfinite([xy0,xy1]).all():
        raise ValueError('Require finite paired Nx2 corner-origin pixels')
    if not len(xy0):return dict(xyz=np.empty((0,3)),positive=np.empty(0,bool),errors=np.empty((0,2)),parallax=np.empty(0))
    p0,p1=camera0['projection'],camera1['projection']
    a=np.stack([xy0[:,0,None]*p0[2]-p0[0],xy0[:,1,None]*p0[2]-p0[1],
                xy1[:,0,None]*p1[2]-p1[0],xy1[:,1,None]*p1[2]-p1[1]],axis=1)
    _,_,vh=np.linalg.svd(a)
    with np.errstate(divide='ignore',invalid='ignore'):xyz=vh[:,-1,:3]/vh[:,-1,3,None]
    positive=np.isfinite(xyz).all(axis=1);errors=[];bearings=[]
    for camera,observed in [(camera0,xy0),(camera1,xy1)]:
        q=xyz@camera['matrix'][:,:3].T+camera['matrix'][:,3]
        positive &= q[:,2]>0
        with np.errstate(divide='ignore',invalid='ignore'):projected=q[:,:2]/q[:,2,None]*camera['params'][:2]+camera['params'][2:]
        errors.append(np.linalg.norm(projected-observed,axis=1))
        ray=np.column_stack([(observed-camera['params'][2:])/camera['params'][:2],np.ones(len(observed))])
        ray/=np.linalg.norm(ray,axis=1,keepdims=True);bearings.append(ray@camera['pose'][:3,:3].T)
    parallax=np.degrees(np.arccos(np.clip(np.sum(bearings[0]*bearings[1],axis=1),-1,1)))
    return dict(xyz=xyz,positive=positive,errors=np.stack(errors,axis=1),parallax=parallax)


def angular_separation(a,b):
    a,b=np.asarray(a,float),np.asarray(b,float)
    return np.degrees(np.arccos(np.clip(np.sum(a*b,axis=-1),-1,1)))


def spatial_holdout(uv,width=1092,height=546,block=64):
    """Deterministic source-panorama tiles; not independent camera holdout."""
    uv=np.asarray(uv,float)
    if uv.shape[-1]!=2 or not np.isfinite(uv).all() or np.any(uv<0) or np.any(uv>=1):
        raise ValueError('Require normalized ERP coordinates in [0,1)')
    tiles=np.floor(uv*np.array([width,height])/block).astype(int)
    return ((tiles[...,0]+2*tiles[...,1])%5)==0
