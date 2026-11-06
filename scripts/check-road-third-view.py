#!/usr/bin/env python3
"""Check frozen 4/5 road tracks against independently matched real RGB5/6.

No learned depth, pose fitting, generated views, or Gaussian training. Third RGB
was withheld from road calibration, but all camera poses share the earlier SfM.
"""
import argparse
from collections import Counter
import importlib.util
from pathlib import Path
import resource
import time
import traceback
import numpy as np
from PIL import Image, ImageDraw
from spherical_depth import directions_to_erp, sample_erp_bilinear
from stereo_tracks import camera_from_pose, triangulate_observed
from third_view_geometry import (rectified_ray_pixel, sample_supported_disparity,
                                 rectified_to_corner, third_view_residual)


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result); return result


M = module('anchors', 'experiment-stereo-anchors.py'); D, C = M.D, M.C
W = module('warp', 'warp-panorama-gap.py')
PRIOR = D.ROOT/'data/jobs/road-stereo-wide-20261106'


def stats(values):
    a = np.asarray(values, float)
    return dict(samples=len(a), median=float(np.median(a)) if len(a) else None,
                p90=float(np.percentile(a, 90)) if len(a) else None,
                maximum=float(np.max(a)) if len(a) else None)


def pose_inputs():
    """Only observed camera records; never use baseline's virtual target poses."""
    poses = {int(row['id'].split('-')[1]): np.asarray(row['worldFromPanorama'], float)
             for row in D.read(D.BASE/'evaluation-cameras.json')['fixedRigCameras']
             if row['kind'] == 'observed'}
    crops = {Path(c['file']).name: c for c in D.read(D.ROOT/'data/jobs/mapillary-beijing-crops/crops.json')['crops']}
    for frame in D.read(D.RIG/'transforms.json')['frames']:
        crop = crops[Path(frame['file_path']).name]
        physical = int(Path(frame['file_path']).name.split('_')[1])
        derived = np.asarray(frame['transform_matrix']) @ np.diag([1, -1, -1, 1])
        derived[:3, :3] = derived[:3, :3] @ np.asarray(crop['relativeCameraToPanoramaRotation']).T
        np.testing.assert_allclose(derived, poses[physical], atol=1e-10)
    for physical, path in zip([4, 5], D.anchor_paths()):
        np.testing.assert_allclose(poses[physical], D.read(path)['worldFromPanorama'], atol=1e-10)
    return poses


def frame(pose, physical, yaw, pitch):
    world = pose.copy(); world[:3, :3] = pose[:3, :3] @ C.crop_rotation(yaw, pitch)
    return dict(id=physical, w=1024, h=1024, fl_x=512, fl_y=512, cx=512, cy=512,
                transform_matrix=(world @ np.diag([1, -1, -1, 1])).tolist())


def run(output, pitch):
    import cv2
    output.mkdir(parents=True, exist_ok=False); started = time.monotonic()
    report = dict(status='RUNNING', startedAt=D.now(), opencv=cv2.__version__)
    try:
        manifest = D.read(D.ROOT/'scripts/samples/mapillary-beijing.json')
        sources = sorted((D.ROOT/'data/samples/mapillary-beijing/images').glob('*.jpg'))[3:6]
        for path, provenance in zip(sources, manifest['images'][3:6]):
            if D.sha(path) != provenance['sha256']:raise ValueError('Original source hash changed')
        prior = D.read(PRIOR/'report.json')
        if prior['status'] != 'PASS' or D.sha(PRIOR/'tracks.json') != prior['tracksSha256']:
            raise ValueError('Require frozen completed 291-track stereo run')
        tracks = D.read(PRIOR/'tracks.json'); poses = pose_inputs()
        files = sources+[PRIOR/'report.json', PRIOR/'tracks.json', D.BASE/'evaluation-cameras.json',
            D.RIG/'transforms.json', D.ROOT/'data/jobs/mapillary-beijing-crops/crops.json',
            Path(__file__), Path(__file__).with_name('third_view_geometry.py'),
            Path(__file__).with_name('warp-panorama-gap.py'), Path(__file__).with_name('stereo_tracks.py'),
            Path(__file__).with_name('prepare-panoramas.py')]
        protocol = dict(schemaVersion=1, declaredAt=D.now(), physicalPanoramas=[4, 5, 6],
            operation='Match actual RGB5/6 without using 4/5 XYZ or any depth prediction. Then compare frozen 4/5 road tracks at the same observed panorama5 ray.',
            poseCaveat='RGB6 withheld from preceding depth calibration and 4/5 stereo; cameras jointly estimated using all nine images. Not independent camera/depth ground truth.',
            settings=dict(size=1024, hfovDegrees=90, pitchDegrees=pitch, yaws=list(range(0, 360, 60)), rectifiedScale=2,
                maxDisparity=512, blockSize=5, lrTolerancePixels=.5, photoTolerance255=15, subpixelMaxDisparitySpread=2,
                minParallaxDegrees=3, maxReprojectionPixels=1),
            selection='Choose one preferred crop per old panorama5 ray BEFORE matching, highest original-camera ray Z among own-valid finite rectified canvases. No best-residual or nearest-valid selection; retain all other crop trials diagnostically.',
            diagnosticGate=dict(minSupportedTracks=30, angleDegrees=1, absoluteRelativeRange=.05, minimumStableFractionAmongSupported=.8,
                meaning='Predeclared internal repeatability screen, not calibrated street accuracy or fusion acceptance. Unsupported tracks remain in total denominator.'),
            range='5/6 radial ranges from positive fixed-pose triangulation, SfM arbitrary units. No learned-depth/range prior or cap in new matcher.',
            files=[dict(path=D.local(p), bytes=p.stat().st_size, sha256=D.sha(p)) for p in files])
        D.write(output/'protocol.json', protocol)
        cv2.setNumThreads(2); cv2.setRNGSeed(0)
        pixels = {n: np.asarray(Image.open(path).convert('RGB')) for n, path in zip([4, 5, 6], sources)}
        for n in [4, 5, 6]:Image.fromarray(pixels[n]).resize((1092, 546), Image.Resampling.LANCZOS).save(output/f'source-{n}.jpg', quality=90)
        setups = []; preferred = [[] for _ in tracks]; groups = []
        # Choose crops with geometry and own image support only, before disparity inference.
        for yaw in range(0, 360, 60):
            group = dict(yaw=yaw, status='RUNNING'); groups.append(group)
            try:
                frames = [frame(poses[n], n, yaw, pitch) for n in [5, 6]]
                left, right, r1, r2, k, size, axis, baseline, swapped = W.rectification(*frames, scale=2)
                crops = {n: C.crop_panorama(pixels[n], 1024, 90, yaw, pitch) for n in [5, 6]}
                for n in [5, 6]:Image.fromarray(crops[n]).save(output/f'{yaw:03d}-{n}.png')
                a, av = W.rectify_image(crops[left['id']][:, :, ::-1], left, r1, k, size, 5)
                b, bv = W.rectify_image(crops[right['id']][:, :, ::-1], right, r2, k, size, 5)
                own_rotation = r1 if left['id'] == 5 else r2; own_valid = av if left['id'] == 5 else bv
                for index, track in enumerate(tracks):
                    xy, rank = rectified_ray_pixel(track['rayPanorama'][1], C.crop_rotation(yaw, pitch), own_rotation, k, size)
                    if xy is not None:
                        x, y = np.floor(xy).astype(int)
                        if own_valid[y:y+2, x:x+2].all():preferred[index].append((rank, yaw, xy.tolist()))
                setups.append((group, left, right, r1, r2, k, size, axis, baseline, a, av, b, bv))
                group.update(axis=axis, swapped=swapped, baselineSfm=baseline, leftPhysical=left['id'])
            except Exception as error:group.update(status='FAIL', error=f'{type(error).__name__}: {error}')
        selected = [max(items, key=lambda x: (x[0], -x[1])) if items else None for items in preferred]
        D.write(output/'preferred-crops.json', selected)
        candidates = [[] for _ in tracks]
        for group, left, right, r1, r2, k, size, axis, baseline, a, av, b, bv in setups:
            yaw = group['yaw']; stage_started = time.monotonic()
            try:
                dl, dr = W.stereo_disparities(a, b, axis, 512, 5)
                vl = W.valid_matches(dl, dr, av, bv, a, b, axis, 1, 512, .5, 15)
                vr = W.valid_matches(dr, dl, bv, av, b, a, axis, -1, 512, .5, 15)
                own_d, own_v = (dl, vl) if left['id'] == 5 else (dr, vr)
                cameras = {f['id']:camera_from_pose(W.camera(f), [512]*4) for f in [left, right]}
                for i, items in enumerate(preferred):
                    matches = [entry for entry in items if entry[1] == yaw]
                    if not matches:continue
                    _, _, xy = matches[0]; disparity, status = sample_supported_disparity(own_d, own_v, xy)
                    row = dict(yaw=yaw, status=status, ownRectifiedXy=xy)
                    if disparity is not None:
                        other = np.asarray(xy).copy(); other[axis] -= disparity
                        rectified = {5:xy, 6:other}
                        observed = {f['id']:rectified_to_corner(rectified[f['id']], rotation, k, [512]*4) for f, rotation in [(left, r1), (right, r2)]}
                        if any(o is None for o in observed.values()):row['status']='behind-original-camera'
                        elif any(np.any(o<.5) or np.any(o>1023.5) for o in observed.values()):row['status']='outside-source-crop'
                        else:
                            result = triangulate_observed(np.array([observed[5]]), np.array([observed[6]]), cameras[5], cameras[6])
                            if not result['positive'][0] or result['parallax'][0]<3 or np.max(result['errors'])>1:row['status']='geometry-rejected'
                            else:
                                xyz=result['xyz'][0]; row.update(xyz=xyz.tolist(), xy6=observed[6].tolist(),
                                    parallaxDegrees=float(result['parallax'][0]), disparity=float(disparity),
                                    reprojectionPixels=result['errors'][0].tolist(),
                                    **third_view_residual(tracks[i]['xyz'], xyz, poses[5][:3, 3], poses[6][:3, 3]))
                                ray6=(xyz-poses[6][:3, 3])@poses[6][:3, :3]; u,v=directions_to_erp(ray6[None],546,1092)
                                row['uv6']=[float((u[0]+.5)/1092),float((v[0]+.5)/546)]
                                row['stable']=row['angleDegrees']<=1 and abs(row['relativeRangeDifference'])<=.05
                    candidates[i].append(row)
                np.savez_compressed(output/f'{yaw:03d}-stereo.npz', leftDisparity=dl, rightDisparity=dr, leftValid=vl, rightValid=vr,
                    r1=r1, r2=r2, k=k, leftWorldFromCamera=W.camera(left), rightWorldFromCamera=W.camera(right))
                cv2.imwrite(str(output/f'{yaw:03d}-rectified-left.jpg'),a);cv2.imwrite(str(output/f'{yaw:03d}-rectified-right.jpg'),b)
                cv2.imwrite(str(output/f'{yaw:03d}-valid.png'),own_v.astype(np.uint8)*255)
                group.update(status='PASS', lrPhotoPixels5=int(own_v.sum()), elapsedSeconds=time.monotonic()-stage_started)
            except Exception as error:group.update(status='FAIL',error=f'{type(error).__name__}: {error}',traceback=traceback.format_exc())
        rows=[]
        for i, track in enumerate(tracks):
            pick=selected[i]; primary=next((c for c in candidates[i] if c['yaw']==pick[1]),None) if pick else None
            rows.append(dict(id=track['id'], heldInPrevious=track['held'], trainingInPrevious=track['training'],
                oldXyz=track['xyz'], oldUv=track['uv'], preferredYaw=pick[1] if pick else None,
                status=primary['status'] if primary else ('matching-stage-failed' if pick else 'outside-crop-coverage'),
                primary=primary, alternatives=candidates[i]))
        supported=[r for r in rows if r['status']=='supported']; stable=[r for r in supported if r['primary']['stable']]
        gate=len(supported)>=30 and len(stable)>=.8*len(supported)
        D.write(output/'tracks.json',rows)
        report.update(status='PASS' if all(g['status']=='PASS' for g in groups) else 'FAIL', qualityStatus='NOT ACCEPTED',
            totalTracks=len(rows), supportedTracks=len(supported), stableTracks=len(stable), unsupportedTracks=len(rows)-len(supported),
            supportFraction=len(supported)/len(rows), stableFractionOfAll=len(stable)/len(rows),
            stableFractionOfSupported=len(stable)/len(supported) if supported else None,
            statuses=dict(Counter(r['status'] for r in rows)),
            angularResidualDegrees=stats([r['primary']['angleDegrees'] for r in supported]),
            absoluteRelativeRangeDifference=stats([abs(r['primary']['relativeRangeDifference']) for r in supported]),
            crossRangeSfm=stats([r['primary']['crossRangeSfm'] for r in supported]),
            alternativeSupportedTracks=sum(any(c['status']=='supported' for c in r['alternatives']) for r in rows),
            diagnosticGate='PASS' if gate else 'FAIL', groups=groups, protocolSha256=D.sha(output/'protocol.json'), tracksSha256=D.sha(output/'tracks.json'),
            worldFromPanorama={str(n):poses[n].tolist() for n in [4,5,6]},
            depthInference='NOT RUN', poseEstimation='NOT RUN; existing jointly estimated poses', calibration='NOT RUN; unchanged', fusion='NOT RUN', gaussianTraining='NOT RUN')
        # Third observed image: green stable, red inconsistent, yellow unsupported.
        canvas=Image.open(output/'source-6.jpg').convert('RGB'); draw=ImageDraw.Draw(canvas)
        for row in rows:
            ray=(np.asarray(row['oldXyz'])-poses[6][:3,3])@poses[6][:3,:3]
            u,v=directions_to_erp(ray[None],546,1092); x,y=float(u[0]),float(v[0]); row['projectedUv6']=[(x+.5)/1092,(y+.5)/546]
            color=(255,210,40) if row['status']!='supported' else ((40,240,175) if row['primary']['stable'] else (255,70,95))
            draw.ellipse((x-2,y-2,x+2,y+2),fill=color)
            if row['status']=='supported':
                actual=np.asarray(row['primary']['uv6'])*[1092,546]-.5
                if abs(actual[0]-x)<546:draw.line((x,y,*actual),fill=color,width=1)
        canvas.save(output/'third-overlay.jpg',quality=94)
        # Deterministic evenly spaced track examples, never select only successful matches.
        examples=np.linspace(0,len(rows)-1,min(24,len(rows)),dtype=int)
        sheet=Image.new('RGB',(576,len(examples)*148),(15,20,27)); pen=ImageDraw.Draw(sheet)
        for j,index in enumerate(examples):
            row=rows[index]; origins=[row['oldUv'][0],row['oldUv'][1],row['projectedUv6']]
            for col,(n,uv) in enumerate(zip([4,5,6],origins)):
                # Wrap X only; clamp vertical samples, preserving actual observed RGB.
                grid_y,grid_x=np.indices((112,176)); h,w=pixels[n].shape[:2]
                cx,cy=np.asarray(uv)*[w,h]-.5
                patch=sample_erp_bilinear(pixels[n],cx+(grid_x-88)*2,cy+(grid_y-56)*2)
                sheet.paste(Image.fromarray(np.uint8(np.clip(patch,0,255))), (col*192,j*148+24))
                pen.line((col*192+84,j*148+80,col*192+92,j*148+80),fill=(255,255,255),width=1)
                pen.line((col*192+88,j*148+76,col*192+88,j*148+84),fill=(255,255,255),width=1)
            label=f'{index}: {row["status"]}'
            if row['status']=='supported':label+=f' | {row["primary"]["angleDegrees"]:.3f}deg | range {row["primary"]["relativeRangeDifference"]*100:.2f}%'
            pen.text((3,j*148+4),label,fill=(235,240,245))
        sheet.save(output/'track-examples.jpg',quality=92)
        # Standard colored point clouds for inspecting the two triangulations.
        for name, xyz, uv in [('previous45',[r['oldXyz'] for r in rows],[r['oldUv'][1] for r in rows]),
                              ('observed56',[r['primary']['xyz'] for r in supported],[r['oldUv'][1] for r in supported])]:
            xyz=np.asarray(xyz,float).reshape(-1,3); uv=np.asarray(uv,float).reshape(-1,2)
            colors=sample_erp_bilinear(pixels[5],uv[:,0]*pixels[5].shape[1]-.5,uv[:,1]*pixels[5].shape[0]-.5).astype(np.uint8)
            D.CAL.write_ply(output/f'{name}.ply',xyz,colors)
        D.write(output/'tracks.json',rows);report['tracksSha256']=D.sha(output/'tracks.json')
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}',traceback=traceback.format_exc());raise
    finally:
        report.update(finishedAt=D.now(),elapsedSeconds=time.monotonic()-started,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        D.write(output/'report.json',report)
    print({k:report[k] for k in ['status','totalTracks','supportedTracks','stableTracks','diagnosticGate','elapsedSeconds']})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    parser.add_argument('--pitch',type=float,default=-30);args=parser.parse_args();run(args.output,args.pitch)
