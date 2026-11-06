"""Analytic tangent cameras and explicit inverse-Z/radial overlap constraints."""
from itertools import combinations
import numpy as np


def icosahedron_normals():
    phi=(1+np.sqrt(5))/2
    vertices=np.array([(0,a,b*phi) for a in [-1,1] for b in [-1,1]]+
        [(a,b*phi,0) for a in [-1,1] for b in [-1,1]]+
        [(b*phi,0,a) for a in [-1,1] for b in [-1,1]])
    normals=[]
    for face in combinations(range(12),3):
        if all(np.isclose(np.linalg.norm(vertices[a]-vertices[b]),2) for a,b in combinations(face,2)):
            n=vertices[list(face)].sum(axis=0);normals.append(n/np.linalg.norm(n))
    normals=np.array(normals)
    if normals.shape!=(20,3):raise RuntimeError('Icosahedron face construction failed')
    return np.array(sorted(normals.tolist(),key=lambda r:(round(r[1],12),round(r[2],12),round(r[0],12))))


def view_angles(normal):
    n=np.asarray(normal,float)
    if n.shape!=(3,) or not np.isfinite(n).all() or not np.isclose(np.linalg.norm(n),1):
        raise ValueError('Require a finite unit face normal')
    return float(np.degrees(np.arctan2(n[0],n[2]))%360),float(np.degrees(np.arcsin(-n[1])))


def project_rays(rays,rotation,params,size):
    rays,rotation=np.asarray(rays,float),np.asarray(rotation,float)
    if rotation.shape!=(3,3) or not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-8) or not np.isclose(np.linalg.det(rotation),1):
        raise ValueError('Require a right-handed rigid crop rotation')
    if rays.shape[-1]!=3 or not np.isfinite(rays).all() or not np.allclose(np.linalg.norm(rays,axis=-1),1):
        raise ValueError('Require unit finite ERP rays')
    fx,fy,cx,cy=np.asarray(params,float)
    if fx<=0 or fy<=0 or not np.isfinite([fx,fy,cx,cy]).all():raise ValueError('Invalid intrinsics')
    q=rays@rotation
    with np.errstate(divide='ignore',invalid='ignore'):xy=q[...,:2]/q[...,2,None]*[fx,fy]+[cx,cy]
    inside=(q[...,2]>0)&(xy[...,0]>=.5)&(xy[...,0]<=size-.5)&(xy[...,1]>=.5)&(xy[...,1]<=size-.5)
    return xy,q[...,2],inside


def fit_overlap_system(anchor_rows,overlap_rows,initial,overlap_weight=.20,iterations=6):
    """Each row is an already normalized linear inverse-radial constraint.

    Anchors fix SfM scale. Overlap has no independent metric information.
    Weak initial regularization limits noisy affine drift; no held anchors enter.
    """
    initial=np.asarray(initial,float)
    if initial.ndim!=1 or len(initial)%2 or not np.isfinite(initial).all():raise ValueError('Require affine initial coefficients')
    if not anchor_rows:raise ValueError('Overlap alone cannot establish depth scale')
    if not np.isfinite(overlap_weight) or overlap_weight<0:raise ValueError('Invalid overlap weight')
    a=np.asarray([r[0] for r in anchor_rows],float);b=np.asarray([r[1] for r in anchor_rows],float)
    if a.shape!=(len(b),len(initial)) or not np.isfinite(a).all() or not np.isfinite(b).all() or np.any(b<=0):raise ValueError('Invalid anchored inverse-range system')
    groups=[a];targets=[b];weights=[np.full(len(b),1/len(b))]
    if overlap_rows:
        c=np.asarray(overlap_rows,float)
        if c.ndim!=2 or c.shape[1]!=len(initial) or not np.isfinite(c).all():raise ValueError('Invalid overlap rows')
        groups.append(c);targets.append(np.zeros(len(c)));weights.append(np.full(len(c),overlap_weight/len(c)))
    if np.linalg.matrix_rank(np.concatenate(groups))<len(initial):raise ValueError('Unidentifiable affine coefficients; preserve unsupported depth')
    groups.append(np.eye(len(initial)));targets.append(initial);weights.append(np.full(len(initial),1e-5/len(initial)))
    x=np.concatenate(groups);y=np.concatenate(targets);base=np.concatenate(weights);solution=initial.copy()
    for _ in range(iterations):
        error=x@solution-y;scale=max(float(np.median(np.abs(error[:len(b)])))*1.4826,1e-7)
        robust=np.minimum(1,1.5*scale/np.maximum(np.abs(error),1e-12));w=np.sqrt(base*robust)
        solution=np.linalg.lstsq(x*w[:,None],y*w,rcond=None)[0]
    if not np.isfinite(solution).all():raise ValueError('Nonfinite calibrated solution')
    return solution


def shell_mesh(radial,pose,max_ratio=1.25):
    """Build only supported ERP triangles; duplicate seam vertices intentionally."""
    from spherical_depth import erp_unit_rays
    radial,pose=np.asarray(radial,float),np.asarray(pose,float)
    if pose.shape!=(4,4) or not np.isfinite(pose).all() or not np.allclose(pose[3],[0,0,0,1]) or not np.allclose(pose[:3,:3].T@pose[:3,:3],np.eye(3),atol=1e-7) or not np.isclose(np.linalg.det(pose[:3,:3]),1):raise ValueError('Require actual rigid panorama pose')
    if max_ratio<=1 or not np.isfinite(max_ratio):raise ValueError('Require explicit depth discontinuity ratio')
    h,w=radial.shape;rays=erp_unit_rays(h,w);valid=np.isfinite(radial)&(radial>0)
    p=rays*np.where(valid,radial,0)[...,None]@pose[:3,:3].T+pose[:3,3]
    # Wrap the last horizontal cell to column0, duplicating that vertex at u>1.
    p=np.concatenate([p,p[:,:1]],axis=1);d=np.concatenate([radial,radial[:,:1]],axis=1);v=np.concatenate([valid,valid[:,:1]],axis=1)
    u=(np.arange(w+1)+.5)/w;y=1-(np.arange(h)+.5)/h;xx,yy=np.meshgrid(u,y)
    indices=[]
    for row in range(h-1):
        for col in range(w):
            for corners in [[(row,col),(row+1,col),(row,col+1)],[(row,col+1),(row+1,col),(row+1,col+1)]]:
                values=np.array([d[a,b] for a,b in corners])
                if all(v[a,b] for a,b in corners) and values.max()/values.min()<=max_ratio:
                    indices.extend(a*(w+1)+b for a,b in corners)
    return dict(schemaVersion=1,positions=p.reshape(-1,3).ravel().tolist(),uvs=np.stack([xx,yy],axis=-1).ravel().tolist(),indices=indices)


def fill_display_nadir(rgb,start=.85):
    """Presentation-only color extrapolation over known source nadir artwork.

    This creates no depth, camera, training RGB or measured floor. Return a copy
    and leave the observed upper region byte-identical before JPEG encoding.
    """
    from PIL import Image,ImageFilter
    rgb=np.asarray(rgb)
    if rgb.ndim!=3 or rgb.shape[2]!=3 or rgb.dtype!=np.uint8 or not 0<start<1:raise ValueError('Require uint8 RGB and explicit nadir boundary')
    h,w=rgb.shape[:2];edge=int(h*start)
    if edge<2 or edge>=h:raise ValueError('Nadir boundary leaves no observed color')
    row=rgb[max(0,edge-12):edge].astype(float).mean(axis=0)
    # Periodic horizontal blur, preserving the ERP wrap rather than edge clamps.
    strip=np.tile(row.astype(np.uint8),(1,3,1));smooth=np.asarray(Image.fromarray(strip).filter(ImageFilter.GaussianBlur(12)))[0,w:2*w].astype(float)
    blend=np.linspace(0,1,h-edge)[:,None,None];fill=smooth[None]*(1-blend)+smooth.mean(axis=0)[None,None]*blend
    result=rgb.copy();result[edge:]=np.rint(fill).clip(0,255).astype(np.uint8)
    return result
