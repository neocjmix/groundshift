"""Small, explicit shared-frame point/depth operations for street experiments."""
import hashlib
import numpy as np
from perspective_sphere import sample_plane


def held_id(value):
    return int(hashlib.sha256(str(value).encode()).hexdigest()[:8],16)%5==0


def validate_stereo_report(report,allow_partial=False):
    """Allow only explicitly diagnosed horizon exclusions; never swallow errors."""
    failed=[g for g in report.get('groups',[]) if g.get('status')!='PASS']
    if report.get('status')=='PASS' and not failed:return False
    if (allow_partial and report.get('status')=='FAIL' and failed
            and any(g.get('status')=='PASS' for g in report['groups'])
            and all(g.get('error')=='ValueError: Stereo optical rays are too close to the rectification horizon' for g in failed)):
        return True
    raise ValueError('Stereo stage failed; only explicit rectification-horizon exclusions may be retained')


def project_world(points,world_from_camera,params):
    points=np.asarray(points,float);pose=np.asarray(world_from_camera,float);params=np.asarray(params,float)
    if points.ndim!=2 or points.shape[1]!=3 or pose.shape!=(4,4) or params.shape!=(4,) or np.any(params[:2]<=0):
        raise ValueError('Require Nx3 points, rigid pose and corner-origin fx,fy,cx,cy')
    if not np.allclose(pose[3],[0,0,0,1]) or not np.allclose(pose[:3,:3].T@pose[:3,:3],np.eye(3),atol=1e-8) or not np.isclose(np.linalg.det(pose[:3,:3]),1):
        raise ValueError('Require right-handed rigid world-from-camera')
    q=(points-pose[:3,3])@pose[:3,:3]
    with np.errstate(divide='ignore',invalid='ignore'):xy=q[:,:2]/q[:,2,None]*params[:2]+params[2:]
    return xy,q[:,2]


def depth_support(points,colors,target_z,target_rgb,world_from_camera,params,relative_tolerance=.10,color_tolerance=45):
    """Depth/RGB agreement is a consistency heuristic, never true visibility."""
    xy,z=project_world(points,world_from_camera,params)
    observed=sample_plane(target_z,xy);rgb=np.stack([sample_plane(target_rgb[:,:,i],xy) for i in range(3)],axis=1)
    supported=np.isfinite(observed)&(observed>0)&(z>0)
    residual=np.full(len(points),np.nan);residual[supported]=(z[supported]-observed[supported])/observed[supported]
    color_error=np.mean(np.abs(rgb-np.asarray(colors,float)),axis=1)
    agree=supported&(np.abs(residual)<=relative_tolerance)&(color_error<=color_tolerance)
    return agree,supported,residual,color_error


def voxel_reduce(points,colors,spacing):
    """One arithmetic XYZ/RGB mean per occupied voxel; no registration correction."""
    p,c=np.asarray(points,float),np.asarray(colors,float)
    if p.ndim!=2 or p.shape[1]!=3 or c.shape!=p.shape or not np.isfinite(p).all() or not np.isfinite(c).all() or not np.isfinite(spacing) or spacing<=0:
        raise ValueError('Require finite Nx3 XYZ/RGB and a positive SfM voxel spacing')
    if not len(p):return p,np.empty((0,3),np.uint8)
    _,inverse=np.unique(np.floor(p/spacing).astype(np.int64),axis=0,return_inverse=True)
    count=np.bincount(inverse);xyz=np.column_stack([np.bincount(inverse,weights=p[:,i])/count for i in range(3)])
    rgb=np.column_stack([np.bincount(inverse,weights=c[:,i])/count for i in range(3)])
    return xyz,np.rint(np.clip(rgb,0,255)).astype(np.uint8)
