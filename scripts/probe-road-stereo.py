#!/usr/bin/env python3
"""Bounded classical stereo alternative for the SIFT-empty source4 road ROI."""
import argparse
import importlib.util
from pathlib import Path
import resource
import time
import traceback
import numpy as np
from PIL import Image
from stereo_tracks import camera_from_pose,triangulate_observed,angular_separation,spatial_holdout


def module(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


M=module('anchors','experiment-stereo-anchors.py');D,C=M.D,M.C
W=module('warp','warp-panorama-gap.py')


def run(matching,output,max_disparity=256):
    import cv2
    output.mkdir(parents=True,exist_ok=False);started=time.monotonic();report=dict(status='RUNNING',startedAt=D.now())
    try:
        prior=D.read(matching/'matching.json')
        if prior['status']!='PASS':raise ValueError('Require completed SIFT evidence')
        for name,item in prior['sourceCrops'].items():
            if D.sha(matching/name)!=item['sha256']:raise ValueError('Recorded observed crop changed')
        protocol=dict(declaredAt=D.now(),matchingReportSha256=D.sha(matching/'matching.json'),
            method='Existing fixed-pose stereo rectification and CPU SGBM_3WAY. No learned-depth prior, camera refinement or new RGB.',
            settings=dict(size=1024,rectifiedScale=2,maxDisparity=max_disparity,blockSize=5,uniquenessRatio=10,lrTolerance=.5,photoTolerance255=15,rectifiedStride=16,minParallaxDegrees=3,minimumCandidateRoadAnchors=30),
            selection='Both positive ranges <= previous training SfM P99; source4 predeclared road ROI only. No relaxed geometry thresholds. Spatial holdout/protected historical rays as SIFT run.',
            caveat='LR/photo consistency and triangulation are internal to same two RGB images/poses, not proven correspondence or independently accurate depth.')
        if max_disparity==512:
            protocol['changedSearchReason']='Initial256-disparity probe inadequate. Previous depth maps (hypotheses, not truth or matcher input) imply road disparities p10~277–335, median~314–340, p90~348–394 in overlapping crops. Increase only search range, not LR/photo/geometry filters.'
        protocol['implementation']={p.name:D.sha(p) for p in [Path(__file__),Path(__file__).with_name('warp-panorama-gap.py'),Path(__file__).with_name('stereo_tracks.py')]}
        D.write(output/'protocol.json',protocol);cv2.setNumThreads(2)
        anchors=[D.read(p) for p in D.anchor_paths()];poses=[np.array(a['worldFromPanorama']) for a in anchors]
        caps=[c['rangeCap'] for c in D.read(M.PREVIOUS/'report.json')['coverage']]
        protected_ids=set(D.read(M.O.PARENT/'dav2/calibration.json')['withheldPointIds'])
        protected=[np.array([a['rayPanorama'] for a in anchor['anchors'] if a['point3DId'] in protected_ids]) for anchor in anchors]
        tracks=[];groups=[]
        for yaw in range(0,360,60):
            frames=[];cameras=[]
            for s,pose in enumerate(poses):
                world=pose.copy();world[:3,:3]=pose[:3,:3]@C.crop_rotation(yaw,-30)
                cameras.append(camera_from_pose(world,[512]*4))
                frames.append(dict(id=s+4,w=1024,h=1024,fl_x=512,fl_y=512,cx=512,cy=512,transform_matrix=(world@np.diag([1,-1,-1,1])).tolist()))
            group=dict(yaw=yaw,status='RUNNING')
            try:
                left,right,r1,r2,k,size,axis,baseline,swapped=W.rectification(*frames,scale=2)
                images=[cv2.imread(str(matching/f'down-{yaw:03d}-{f["id"]}.png')) for f in [left,right]]
                if any(x is None for x in images):raise ValueError('Missing recorded observed crop')
                a,av=W.rectify_image(images[0],left,r1,k,size,5);b,bv=W.rectify_image(images[1],right,r2,k,size,5)
                dl,dr=W.stereo_disparities(a,b,axis,max_disparity,5)
                valid=W.valid_matches(dl,dr,av,bv,a,b,axis,1,max_disparity,.5,15)
                yy,xx=np.indices(valid.shape);sampled=valid&(yy%16==0)&(xx%16==0)
                points,y,x=W.depth_points(dl,sampled,k,baseline,axis,1)
                world=points@r1@W.camera(left)[:3,:3].T+W.camera(left)[:3,3]
                rectxy=[np.column_stack([x,y]).astype(float),np.column_stack([x-dl[y,x] if axis==0 else x,y-dl[y,x] if axis==1 else y])]
                observed={}
                for f,rotation,xy in zip([left,right],[r1,r2],rectxy):
                    ray=np.column_stack([(xy[:,0]-k[0,2])/k[0,0],(xy[:,1]-k[1,2])/k[1,1],np.ones(len(xy))])@rotation
                    observed[f['id']]=ray[:,:2]/ray[:,2,None]*512+512
                result=triangulate_observed(observed[4],observed[5],*cameras)
                np.testing.assert_allclose(result['xyz'],world,atol=1e-5,rtol=1e-6)
                ranges=[np.linalg.norm(world-p[:3,3],axis=1) for p in poses]
                good=result['positive']&(result['parallax']>=3)&(np.max(result['errors'],axis=1)<=1)
                for radial,cap in zip(ranges,caps):good&=(radial>0)&(radial<=cap)
                rays=[];uv=[]
                for s in [0,1]:
                    ray=M.bearings(observed[s+4],cameras[s])@poses[s][:3,:3]
                    u,v=D.directions_to_erp(ray,546,1092) if len(ray) else (np.array([]),np.array([]))
                    rays.append(ray);uv.append(np.column_stack([(u+.5)/1092,(v+.5)/546]))
                roi=(uv[0][:,0]>=.25)&(uv[0][:,0]<=.72)&(uv[0][:,1]>=.78)&(uv[0][:,1]<=.84)
                good&=roi
                for n in np.flatnonzero(good):
                    protected_ray=any(float(np.min(angular_separation(p,rays[s][n])))<=.5 for s,p in enumerate(protected))
                    held=bool(spatial_holdout(uv[0][n]))
                    tracks.append(dict(id=f'sgbm-{yaw}-{n}',method='SGBM',group=f'down-{yaw:03d}',xyz=world[n].tolist(),xy=[observed[s+4][n].tolist() for s in [0,1]],
                        uv=[u[n].tolist() for u in uv],rayPanorama=[r[n].tolist() for r in rays],parallaxDegrees=float(result['parallax'][n]),reprojectionPixels=result['errors'][n].tolist(),held=held,protectedHistoricalHoldout=protected_ray,training=not held and not protected_ray))
                group.update(status='PASS',axis=axis,swapped=swapped,validRectifiedPixels=int((av&bv).sum()),lrPhotoAcceptedPixels=int(valid.sum()),gridSamples=int(sampled.sum()),source4RoadBeforeGeometry=int(roi.sum()),acceptedRoadAnchors=int(good.sum()))
                cv2.imwrite(str(output/f'{yaw:03d}-rectified-left.jpg'),a);cv2.imwrite(str(output/f'{yaw:03d}-rectified-right.jpg'),b)
                cv2.imwrite(str(output/f'{yaw:03d}-valid.png'),valid.astype(np.uint8)*255)
                np.savez_compressed(output/f'{yaw:03d}-stereo.npz',leftDisparity=dl,rightDisparity=dr,valid=valid,selected=sampled,world=world,roadAccepted=good)
            except Exception as error:
                group.update(status='FAIL',error=f'{type(error).__name__}: {error}',traceback=traceback.format_exc())
            groups.append(group)
        D.write(output/'tracks.json',tracks)
        report.update(status='PASS' if any(g['status']=='PASS' for g in groups) else 'FAIL',groups=groups,roadTracks=len(tracks),training=sum(r['training'] for r in tracks),held=sum(r['held'] for r in tracks),
            roadCalibrationStatus='PASS: candidate anchors only, not geometry accuracy' if len(tracks)>=30 else 'FAIL: fewer than30 candidate road anchors',protocolSha256=D.sha(output/'protocol.json'),tracksSha256=D.sha(output/'tracks.json'))
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(finishedAt=D.now(),elapsedSeconds=time.monotonic()-started,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);D.write(output/'report.json',report)
    print({k:report[k] for k in ['status','elapsedSeconds','roadTracks','training','held']})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('matching',type=Path);p.add_argument('output',type=Path);p.add_argument('--max-disparity',type=int,choices=[256,512],default=256);a=p.parse_args();run(a.matching,a.output,a.max_disparity)
