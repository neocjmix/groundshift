#!/usr/bin/env python3
"""Observed non5 RGB stereo across the street; no learned-depth prior in matching."""
import argparse
from pathlib import Path
import time
import resource
import traceback
import numpy as np
from PIL import Image
from street_geometry import held_id
from spherical_depth import directions_to_erp
import importlib.util


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


P=module('prepare','prepare-street.py');W=module('warp','warp-panorama-gap.py')
C=module('crop','prepare-panoramas.py')


def run(job,output):
    import cv2
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();report=dict(status='RUNNING',startedAt=P.now(),groups=[])
    try:
        cv2.setNumThreads(2);cv2.setRNGSeed(0)
        poses=P.panorama_poses();anchors=P.read(job/'anchors-training-colors/anchors.json')
        caps={p:float(np.quantile(np.linalg.norm(np.array([a['xyz'] for a in anchors[str(p)]])-poses[p][:3,3],axis=1),.99)) for p in poses}
        frames=P.read(job/'inputs/transforms.json')['frames'];lookup={(f['physicalPanorama'],f['ring'],f['yaw']):f for f in frames}
        physical=[1,2,3,4,6,7,8,9];points=[];colors=[];sources=[];ids=[]
        P.write(output/'protocol.json',dict(declaredAt=P.now(),physicalTrainingCenters=physical,withheld5UsedInNewMatching=False,
            matcher='Existing OpenCV CPU SGBM_3WAY; no learned depth or prior XYZ in matcher.',
            settings=dict(sourceSize=512,rectifiedScale=2,adjacentDisparity=256,gap4to6Disparity=512,blockSize=5,lrTolerancePixels=.5,photoTolerance255=15,stride=8,minParallaxDegrees=3),
            selection='Both radial ranges within existing per-physical SfM P99; both ERP v=.40–.85. Keep original subpixel stereo results and counters. Training split hashes stable point IDs.',
            implementation={p.name:P.sha(p) for p in [Path(__file__),Path(__file__).with_name('warp-panorama-gap.py')]}))
        for p0,p1 in zip(physical,physical[1:]):
            for ring in ['level','down']:
                for yaw in range(0,360,60):
                    g=dict(physical=[p0,p1],ring=ring,yaw=yaw,status='RUNNING');before=time.monotonic()
                    try:
                        pair=[lookup[p,ring,yaw] for p in [p0,p1]]
                        left,right,r1,r2,k,size,axis,baseline,swapped=W.rectification(*pair,scale=2)
                        im=[cv2.imread(str(job/'inputs'/f['file_path'])) for f in [left,right]]
                        a,av=W.rectify_image(im[0],left,r1,k,size,5);b,bv=W.rectify_image(im[1],right,r2,k,size,5)
                        maximum=512 if p1-p0>1 else 256
                        dl,dr=W.stereo_disparities(a,b,axis,maximum,5)
                        valid=W.valid_matches(dl,dr,av,bv,a,b,axis,1,maximum,.5,15)
                        yy,xx=np.indices(valid.shape);selected=valid&(yy%8==0)&(xx%8==0)
                        rect,y,x=W.depth_points(dl,selected,k,baseline,axis,1)
                        pose=W.camera(left);xyz=rect@r1@pose[:3,:3].T+pose[:3,3]
                        good=np.isfinite(xyz).all(axis=1);world_rays=[]
                        for p in [p0,p1]:
                            delta=xyz-poses[p][:3,3];radial=np.linalg.norm(delta,axis=1);unit=delta/np.maximum(radial[:,None],1e-9);world_rays.append(unit)
                            pano=unit@poses[p][:3,:3];_,v=directions_to_erp(pano,546,1092);vn=(v+.5)/546
                            good&=(radial>0)&(radial<=caps[p])&(vn>=.40)&(vn<=.85)
                        angle=np.degrees(np.arccos(np.clip(np.sum(world_rays[0]*world_rays[1],axis=1),-1,1)));good&=angle>=3
                        take=np.flatnonzero(good);points.append(xyz[take]);colors.append(a[y[take],x[take]][:,::-1]);sources.append(np.tile([p0,p1],(len(take),1)))
                        ids.extend(f'{p0}-{p1}-{ring}-{yaw}-{y[i]}-{x[i]}' for i in take)
                        g.update(status='PASS',axis=axis,swapped=swapped,maxDisparity=maximum,lrPhotoPixels=int(valid.sum()),gridCandidates=len(xyz),accepted=len(take),parallaxMedian=float(np.median(angle[good])) if len(take) else None)
                        # Preserve disparity and validity diagnostic evidence. No originals in Git/public.
                        np.savez_compressed(output/f'{p0}-{p1}-{ring}-{yaw:03d}.npz',leftDisparity=dl,rightDisparity=dr,valid=valid,selected=selected,r1=r1,r2=r2,k=k)
                    except Exception as error:g.update(status='FAIL',error=f'{type(error).__name__}: {error}',traceback=traceback.format_exc())
                    g['elapsedSeconds']=time.monotonic()-before;report['groups'].append(g)
                    P.write(output/'report.json',report)
        if not points:raise RuntimeError('No observed stereo results; inspect stage failures')
        xyz=np.concatenate(points);rgb=np.concatenate(colors);physical=np.concatenate(sources);training=~np.array([held_id(i) for i in ids])
        np.savez_compressed(output/'tracks.npz',xyz=xyz,rgb=rgb,physical=physical,training=training,ids=np.array(ids))
        report.update(status='PASS' if all(g['status']=='PASS' for g in report['groups']) else 'FAIL',qualityStatus='NOT ACCEPTED',points=len(xyz),training=int(training.sum()),held=int((~training).sum()),tracksSha256=P.sha(output/'tracks.npz'),protocolSha256=P.sha(output/'protocol.json'),
            limitation='LR/photo/triangulation are correlated estimated-geometry checks. No independent measured depth; all-camera SfM includes panorama5, but new RGB matching excludes it.')
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=P.now(),elapsedSeconds=time.monotonic()-start,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);P.write(output/'report.json',report)
    print(report['status'],report['points'],'observed stereo points')
    return report['status']=='PASS'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('output',type=Path);a=p.parse_args();raise SystemExit(0 if run(a.job.resolve(),a.output.resolve()) else 1)
