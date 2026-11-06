#!/usr/bin/env python3
"""Observed SIFT correspondences in the preserved two-panorama SfM frame.

Local CPU only. Existing depth predictions are reused. No pose optimization,
synthetic imagery, ICP or Gaussian training. Every run uses a new directory.
"""
import argparse
import importlib.util
from pathlib import Path
import resource
import time
import traceback

import numpy as np
from PIL import Image,ImageDraw
from spherical_depth import directions_to_erp
from stereo_tracks import camera_from_pose,triangulate_observed,angular_separation,spatial_holdout

spec=importlib.util.spec_from_file_location('overlap',Path(__file__).with_name('experiment-perspective-overlap.py'))
O=importlib.util.module_from_spec(spec);spec.loader.exec_module(O)
D,C=O.D,O.C
PREVIOUS=D.ROOT/'data/jobs/perspective-overlap-verified-20261106'
PREPARED=D.ROOT/'data/jobs/perspective-overlap-input-20261106'
INFERRED=D.ROOT/'data/jobs/perspective-overlap-inference-20261106'


def bearings(xy,camera):
    ray=np.column_stack([(xy-camera['params'][2:])/camera['params'][:2],np.ones(len(xy))])
    ray/=np.linalg.norm(ray,axis=1,keepdims=True)
    return ray@camera['pose'][:3,:3].T


def match(output,ground=False):
    import cv2
    output.mkdir(parents=True,exist_ok=False);started=time.monotonic()
    report=dict(status='RUNNING',startedAt=D.now(),opencv=cv2.__version__)
    try:
        anchors=[D.read(p) for p in D.anchor_paths()]
        previous=D.read(PREVIOUS/'report.json');split=D.read(O.PARENT/'dav2/calibration.json')
        if previous['status']!='PASS':raise ValueError('Require preserved completed perspective experiment')
        poses=[np.array(a['worldFromPanorama']) for a in anchors]
        files=list(D.anchor_paths())+[PREVIOUS/'report.json',PREVIOUS/'down-calibrations.json',O.CONTROL/'crop-calibrations.json',O.PARENT/'dav2/calibration.json',O.LEVEL/'report.json',INFERRED/'report.json',PREPARED/'protocol.json']
        source_names=['003_1677293342921360.jpg','004_679966948337536.jpg']
        sources=[D.ROOT/'data/samples/mapillary-beijing/images'/n for n in source_names]
        for path,anchor in zip(sources,anchors):
            if D.sha(path)!=anchor['source']['sha256']:raise ValueError('Original panorama hash changed')
        files+=sources
        files += [Path(__file__),Path(__file__).with_name('stereo_tracks.py'),Path(__file__).with_name('prepare-panoramas.py')]
        protocol=dict(schemaVersion=1,declaredAt=D.now(),sourcePhysicalPanoramas=[4,5],source='Observed original licensed ERP images; reprojected level/downward 90-degree crops at1024, not generated views',
            calibration='Existing SfM frame/poses and old predictions fixed; augment original training with new training correspondences, compare new-only where >=30 support. No217 historical holdout IDs in original training; exclude new training within0.5deg of historical held rays in either panorama.',
            matching=dict(detector='SIFT',nfeatures=6000,ratio=.75,mutualRatio=True,size=1024,opencvCornerConversion='+0.5 to SIFT array-index xy before pinhole geometry'),
            geometry=dict(maxReprojectionPixels=1.,minParallaxDegrees=3.,positiveZBoth=True,maxRange='Existing training SfM P99 per panorama',dedupBothRayDegrees=.35,protectedHistoricalHoldoutDegrees=.5),
            split='After dedup: source ERP1092x546 tile64; held when(tile_x+2*tile_y)%5==0. Entire retained correspondence held together in both panoramas. Internal calibration holdout, not independent geometry truth.',
            model='Reuse pinned DAV2 MPS predictions without inference. Inverse camera-Z affine Huber calibration, radial=Z/unit_ray_z. SfM arbitrary units; unknown gravity.',
            controls=['baseline preserved calibration','original training plus new training anchors','new training anchors only with explicit unchanged-fit fallback if unsupported'],
            diagnostics='Same angular band, ranges, ROI rectangles, stride3, central crop selection and pair reference as preceding experiment. Keep all failures, coverage, joint support and old/new residuals. No threshold tuning or pose changes.',
            files=[dict(path=D.local(p),bytes=p.stat().st_size,sha256=D.sha(p)) for p in files])
        protocol['groundFeatureSearch']=dict(enabled=ground,mask='ERP v=.70–.85 in both source crops; all longitudes',nfeatures=3000,contrastThreshold=.01,
            reason='Initial global6000 SIFT search produced zero accepted source4 road tracks. Add a masked low-contrast search without relaxing fixed geometric filters; preserve original run.')
        D.write(output/'protocol.json',protocol)
        cv2.setNumThreads(2);cv2.setRNGSeed(0)
        pixels=[np.array(Image.open(p).convert('RGB')) for p in sources]
        detector=cv2.SIFT_create(nfeatures=6000)
        matcher=cv2.BFMatcher(cv2.NORM_L2)
        def ratio_matches(a,b):
            if a is None or b is None or len(b)<2:return {}
            return {m.queryIdx:(m.trainIdx,float(m.distance/n.distance)) for pair in matcher.knnMatch(a,b,k=2) if len(pair)==2 for m,n in [pair] if n.distance>0 and m.distance<.75*n.distance}
        rows=[];groups=[];caps=[c['rangeCap'] for c in previous['coverage']]
        for ring,pitch in [('level',0),('down',-30)]+([('ground',-30)] if ground else []):
            for yaw in range(0,360,60):
                images=[C.crop_panorama(p,1024,90,yaw,pitch) for p in pixels]
                cameras=[]
                for pose in poses:
                    world=pose.copy();world[:3,:3]=pose[:3,:3]@C.crop_rotation(yaw,pitch)
                    cameras.append(camera_from_pose(world,[512]*4))
                active_detector=detector;mask=None
                if ring=='ground':
                    active_detector=cv2.SIFT_create(nfeatures=3000,contrastThreshold=.01)
                    _,map_y=C.sampling_map(1092,546,1024,90,yaw,pitch)
                    vv=(map_y+.5)/546;mask=((vv>=.70)&(vv<=.85)).astype(np.uint8)*255
                detected=[active_detector.detectAndCompute(cv2.cvtColor(im,cv2.COLOR_RGB2GRAY),mask) for im in images]
                forward=ratio_matches(detected[0][1],detected[1][1]);reverse=ratio_matches(detected[1][1],detected[0][1])
                pairs=[(i,j,ratio) for i,(j,ratio) in sorted(forward.items()) if j in reverse and reverse[j][0]==i]
                xy=[np.array([detected[s][0][p[s]].pt for p in pairs],float).reshape(-1,2)+.5 for s in [0,1]]
                result=triangulate_observed(*xy,*cameras)
                radial=[np.linalg.norm(result['xyz']-pose[:3,3],axis=1) for pose in poses]
                good=result['positive']&(np.max(result['errors'],axis=1)<=1)&(result['parallax']>=3)
                for ranges,cap in zip(radial,caps):good &= (ranges>0)&(ranges<=cap)
                world_rays=[bearings(x,c) for x,c in zip(xy,cameras)]
                group=dict(id=f'{ring}-{yaw:03d}',ring=ring,yaw=yaw,pitch=pitch,keypoints=[len(k[0]) for k in detected],mutualRatioMatches=len(pairs),geometryAccepted=int(good.sum()))
                all_uv=[]
                for s in [0,1]:
                    pano_rays=world_rays[s]@poses[s][:3,:3]
                    u,v=directions_to_erp(pano_rays,546,1092) if len(pano_rays) else (np.array([]),np.array([]))
                    all_uv.append(np.column_stack([(u+.5)/1092,(v+.5)/546]))
                roi=(all_uv[0][:,0]>=.25)&(all_uv[0][:,0]<=.72)&(all_uv[0][:,1]>=.78)&(all_uv[0][:,1]<=.84)
                group['source4RoadRejection']=dict(mutualRatio=int(roi.sum()),positive=int((roi&result['positive']).sum()),
                    reprojection=int((roi&result['positive']&(np.max(result['errors'],axis=1)<=1)).sum()),
                    parallax=int((roi&result['positive']&(np.max(result['errors'],axis=1)<=1)&(result['parallax']>=3)).sum()),accepted=int((roi&good).sum()))
                np.savez_compressed(output/f'{group["id"]}-candidates.npz',xy0=xy[0],xy1=xy[1],uv0=all_uv[0],uv1=all_uv[1],accepted=good,**result)
                for n in np.flatnonzero(good):
                    uv=[];rays=[]
                    for s in [0,1]:
                        ray=poses[s][:3,:3].T@world_rays[s][n];u,v=directions_to_erp(ray,546,1092)
                        uv.append([(float(u)+.5)/1092,(float(v)+.5)/546]);rays.append(ray.tolist())
                    rows.append(dict(group=group['id'],xyz=result['xyz'][n].tolist(),xy=[x[n].tolist() for x in xy],uv=uv,rayPanorama=rays,worldRays=[r[n].tolist() for r in world_rays],
                                     parallaxDegrees=float(result['parallax'][n]),reprojectionPixels=result['errors'][n].tolist(),ratio=pairs[n][2]))
                # Preserve selected input pixels locally; public mosaics use reduced previews only.
                for s,image in enumerate(images):Image.fromarray(image).save(output/f'{group["id"]}-{s+4}.png')
                groups.append(group)
        # Deterministic greedy suppression in both spherical rays, crossing ERP seam.
        kept=[]
        for row in sorted(rows,key=lambda r:(max(r['reprojectionPixels']),r['ratio'],r['group'],r['xy'][0])):
            rays=np.array(row['worldRays'])
            if kept:
                distances=angular_separation(np.array([r['worldRays'] for r in kept]),rays)
                if np.any(np.all(distances<=.35,axis=1)):continue
            kept.append(row)
        held_ids=set(split['withheldPointIds'])
        protected=[np.array([a['rayPanorama'] for a in anchor['anchors'] if a['point3DId'] in held_ids]) for anchor in anchors]
        for i,row in enumerate(kept):
            row['id']=i;row['held']=bool(spatial_holdout(row['uv'][0]));row['protectedHistoricalHoldout']=any(float(np.min(angular_separation(rays,np.array(ray))))<=.5 for rays,ray in zip(protected,row['rayPanorama']))
            row['training']=not row['held'] and not row['protectedHistoricalHoldout']
        D.write(output/'tracks.json',kept)
        for group in groups:
            canvas=Image.new('RGB',(1024,542),(10,15,20));draw=ImageDraw.Draw(canvas)
            for s in [0,1]:
                with Image.open(output/f'{group["id"]}-{s+4}.png') as im:canvas.paste(im.resize((512,512),Image.Resampling.LANCZOS),(s*512,30))
            for row in kept:
                if row['group']!=group['id']:continue
                color=(255,205,60) if row['held'] else (240,85,170) if row['protectedHistoricalHoldout'] else (55,240,170)
                a=np.array(row['xy'][0])/2+[0,30];b=np.array(row['xy'][1])/2+[512,30]
                draw.line([tuple(a),tuple(b)],fill=color,width=1)
                for point in [a,b]:draw.ellipse(tuple(point-2)+tuple(point+2),fill=color)
            draw.text((8,8),group['id']+' | green=train yellow=held pink=protected | line position does not prove correctness',fill='white')
            canvas.save(output/f'{group["id"]}-matches.jpg',quality=88)
        regions=D.read(D.ROOT/'docs/evidence/panoramic-pair-protocol.json')['regions']
        regional=[]
        for s in [0,1]:
            for region in regions:
                chosen=[r for r in kept if region['u'][0]<=r['uv'][s][0]<=region['u'][1] and region['v'][0]<=r['uv'][s][1]<=region['v'][1]]
                regional.append(dict(panorama=s+4,region=region['id'],tracks=len(chosen),training=sum(r['training'] for r in chosen),held=sum(r['held'] for r in chosen),protected=sum(r['protectedHistoricalHoldout'] for r in chosen)))
        report.update(status='PASS',groups=groups,rawAccepted=len(rows),deduplicated=len(kept),training=sum(r['training'] for r in kept),held=sum(r['held'] for r in kept),protected=sum(r['protectedHistoricalHoldout'] for r in kept),regions=regional,protocolSha256=D.sha(output/'protocol.json'),tracksSha256=D.sha(output/'tracks.json'),
            sourceCrops={p.name:dict(bytes=p.stat().st_size,sha256=D.sha(p)) for p in sorted(output.glob('*-[45].png'))})
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(finishedAt=D.now(),elapsedSeconds=time.monotonic()-started,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);D.write(output/'matching.json',report)
    print({k:report[k] for k in ['status','elapsedSeconds','rawAccepted','deduplicated','training','held','regions']})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--ground',action='store_true');args=parser.parse_args();match(args.output,args.ground)
