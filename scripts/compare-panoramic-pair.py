#!/usr/bin/env python3
"""Compare two calibrated ERP jobs without alignment refinement, fusion or training."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import traceback

import numpy as np
from PIL import Image, ImageDraw
from panoramic_pair import compare_direction, summarize_samples
from spherical_depth import backproject_radial

spec = importlib.util.spec_from_file_location('evaluate', Path(__file__).with_name('evaluate-panoramic-depth.py'))
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)


def read(path): return json.loads(path.read_text())
def write(path, data): path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def load_job(path, anchor_path):
    inference, geometry, anchors = read(path/'inference.json'), read(path/'geometry/geometry.json'), read(anchor_path)
    if any(r['status'] != 'PASS' for r in (inference, geometry, anchors)):
        raise ValueError('Require completed inference, calibration and anchors')
    if inference['sourceSha256'] != anchors['source']['sha256'] or geometry['anchorsSha256'] != sha(anchor_path):
        raise ValueError('Job/anchor/source mismatch')
    if sha(path/'raw.npy') != inference['rawSha256']:
        raise ValueError('Raw prediction checksum differs from recorded inference')
    consumed = {str(f.relative_to(path)): sha(f) for f in [path/'raw.npy', path/'source.png', path/'geometry/range-sfm.npy', path/'geometry/filtered.npy', path/'geometry/calibration-samples.json']}
    return dict(path=path, inference=inference, geometry=geometry, anchors=anchors, consumed=consumed,
                radial=np.load(path/'geometry/range-sfm.npy'), mask=np.load(path/'geometry/filtered.npy'),
                rgb=np.array(Image.open(path/'source.png').convert('RGB')), pose=np.array(anchors['worldFromPanorama']))


def diagnostics_images(output, prefix, samples, rgb, regions, relative_band):
    h,w=rgb.shape[:2]; rr,cc=samples['source_rows'],samples['source_columns']; candidate=samples['candidate']
    warped=np.zeros_like(rgb); residual=np.zeros_like(rgb); classes=np.zeros_like(rgb)
    warped[rr[candidate],cc[candidate]]=np.clip(samples['target_rgb'][candidate],0,255).astype(np.uint8)
    # Saturate at the predeclared sparse-only diagnostic band. White=0, blue=front, red=behind.
    v=np.clip(samples['relative_residual'][candidate]/relative_band,-1,1)
    color=np.ones((len(v),3))*255
    color[v<0,:2]*=(1+v[v<0,None]);color[v>=0,1:]*=(1-v[v>=0,None])
    residual[rr[candidate],cc[candidate]]=color.astype(np.uint8)
    classes[rr,cc]=[70,70,70]
    for key,color in [('agreement',[80,210,150]),('in_front',[70,120,255]),('behind',[255,85,70])]:
        selected=samples[key];classes[rr[selected],cc[selected]]=color
    for name,array in [('warp',warped),('residual',residual),('classes',classes)]:Image.fromarray(array).save(output/f'{prefix}-{name}.png')
    roi=Image.fromarray(rgb);draw=ImageDraw.Draw(roi)
    for region in regions:
        box=[int(region['u'][0]*w),int(region['v'][0]*h),int(region['u'][1]*w),int(region['v'][1]*h)]
        draw.rectangle(box,outline='yellow',width=2);draw.text((box[0]+2,box[1]+2),region['id'],fill='black',stroke_width=1,stroke_fill='white')
    roi.save(output/f'{prefix}-regions.png')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['job4','job5','anchors4','anchors5','protocol','output']:p.add_argument(name,type=Path)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();report=dict(status='RUNNING',startedAt=datetime.now(timezone.utc).isoformat())
    try:
        protocol=read(args.protocol);jobs=[load_job(args.job4,args.anchors4),load_job(args.job5,args.anchors5)]
        if jobs[0]['inference']['model']!=jobs[1]['inference']['model']:raise ValueError('Do not silently compare different models')
        if jobs[0]['anchors']['coordinateFrame']!=jobs[1]['anchors']['coordinateFrame']:raise ValueError('Coordinate frames differ')
        if jobs[0]['radial'].shape!=jobs[1]['radial'].shape:raise ValueError('Working grids differ')
        if protocol['sourceHashes'] != [j['anchors']['source']['sha256'] for j in jobs]:raise ValueError('Protocol source mismatch')
        band=protocol['relativeDiagnosticBand'];regions=protocol['regions'];results=[]
        for source,target in [(0,1),(1,0)]:
            a,b=jobs[source],jobs[target];prefix=f'{source+4}-to-{target+4}'
            result=compare_direction(a['radial'],b['radial'],a['rgb'],b['rgb'],a['pose'],b['pose'],
                source_mask=a['mask'],target_mask=b['mask'],stride=1,relative_tolerance=band)
            samples=result['samples'];h,w=a['radial'].shape;u=(samples['source_columns']+.5)/w;v=(samples['source_rows']+.5)/h
            per_region=[]
            for region in regions:
                selected=(u>=region['u'][0])&(u<=region['u'][1])&(v>=region['v'][0])&(v<=region['v'][1])
                per_region.append(dict(id=region['id'],title=region['title'],**summarize_samples(samples,selected)))
            sectors=[]
            for i in range(12):sectors.append(dict(longitudeDegrees=[i*30-180,(i+1)*30-180],**summarize_samples(samples,(u>=i/12)&(u<(i+1)/12))))
            diagnostics_images(args.output,prefix,samples,a['rgb'],regions,band)
            np.savez_compressed(args.output/f'{prefix}-samples.npz',**{k:v for k,v in samples.items() if v is not None})
            results.append(dict(id=prefix,summary=result['summary'],regions=per_region,sectors=sectors))
        xyzs=[];colors=[];source_ids=[];captures=[]
        for index,job in enumerate(jobs):
            xyz,color,_,_=backproject_radial(job['radial'],job['rgb'],job['pose'],mask=job['mask'],stride=3)
            xyzs.append(xyz);colors.append(color);source_ids.extend([index]*len(xyz))
            old=read(job['path']/'geometry/cloud.json');captures.append(dict(id=str(index+4),title=f'Estimated panorama {index+4}',**old['capture']))
        xyz=np.concatenate(xyzs);rgb=np.concatenate(colors)
        evaluate.browser_cloud(args.output/'cloud.json',xyz,rgb,jobs[1]['pose'])
        cloud=read(args.output/'cloud.json');cloud.pop('capture');cloud.update(sourceIds=source_ids,captures=captures)
        write(args.output/'cloud.json',cloud);evaluate.write_ply(args.output/'cloud.ply',xyz,rgb)
        # Only common point IDs can compare the same sparse 3D target. Both keep the global holdout split.
        calibrations=[read(j['path']/'geometry/calibration-samples.json') for j in jobs]
        by_id=[{pid:i for i,pid in enumerate(c['pointIds'])} for c in calibrations];shared=sorted(set(by_id[0])&set(by_id[1]))
        common=[]
        for pid in shared:
            entries=[(c,ids[pid]) for c,ids in zip(calibrations,by_id)]
            if entries[0][0]['heldOut'][entries[0][1]] != entries[1][0]['heldOut'][entries[1][1]]:raise ValueError('Cross-panorama holdout leakage')
            common.append(dict(point3DId=pid,heldOut=entries[0][0]['heldOut'][entries[0][1]],
                calibratedRadial=[c['calibratedRanges'][i] for c,i in entries],sfmRadial=[c['radialSfm'][i] for c,i in entries]))
        write(args.output/'common-calibration-tracks.json',common)
        common_roi=[]
        for index,job in enumerate(jobs):
            anchor_by_id={a['point3DId']:a for a in job['anchors']['anchors']}
            for region in regions:
                ids=[pid for pid in shared if region['u'][0]<=anchor_by_id[pid]['erpNormalizedUv'][0]<=region['u'][1] and region['v'][0]<=anchor_by_id[pid]['erpNormalizedUv'][1]<=region['v'][1]]
                subsets={}
                for held in [False,True]:
                    rows=[row for row in common if row['point3DId'] in ids and row['heldOut']==held]
                    predicted=np.array([row['calibratedRadial'][index] if row['calibratedRadial'][index] is not None else np.nan for row in rows])
                    truth=np.array([row['sfmRadial'][index] for row in rows]); valid=np.isfinite(predicted)&(predicted>0)
                    subsets['heldOut' if held else 'training']={**evaluate.residual_stats(predicted,truth),'medianSignedRelative':float(np.median((predicted[valid]-truth[valid])/truth[valid])) if valid.any() else None}
                common_roi.append(dict(source=str(index+4),region=region['id'],**subsets))

        report.update(status='PASS',model=jobs[0]['inference']['model'],commonSparseRegionResiduals=common_roi,directions=results,cloudPoints=[len(x) for x in xyzs],
            protocol=protocol,protocolSha256=sha(args.protocol),commonCalibrationTracks=len(common),commonWithheldTracks=sum(x['heldOut'] for x in common),
            inputs=[dict(consumedFileSha256=j['consumed'],sourceSha256=j['inference']['sourceSha256'],rawSha256=j['inference']['rawSha256'],
                         geometrySha256=sha(j['path']/'geometry/geometry.json'),calibration=j['geometry']['calibration'],heldOut=j['geometry']['heldOut']) for j in jobs],
            p2Acceptance='NOT RUN: diagnostic comparator is not independently validated geometry tolerance',
            fusion='NOT RUN',gaussianTraining='NOT RUN',surfaceNearestNeighbor='NOT RUN: bounded test uses directional radial discrepancy',
            observations='Unfiltered candidate residuals include possible occlusions, dynamic objects, pose/stitching/calibration/model errors. Classification is diagnostic, not proven visibility. No ICP or alignment changes.')
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(finishedAt=datetime.now(timezone.utc).isoformat(),elapsedSeconds=time.monotonic()-start);write(args.output/'pair.json',report)

if __name__=='__main__':main()
