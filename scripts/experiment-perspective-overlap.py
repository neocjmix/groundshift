#!/usr/bin/env python3
"""Bounded two-panorama perspective-depth coverage/overlap experiment.

prepare: OpenCV environment; writes twelve real downward crops and protocol.
run: PyCOLMAP environment; reads actual MPS inference, calibrates and diagnoses.
Outputs are new directories. No model substitution, ICP, fusion, or GS training.
"""
import argparse
import importlib.util
from pathlib import Path
import resource
import time
import traceback

import numpy as np
from PIL import Image
from spherical_depth import erp_unit_rays, backproject_radial
from panoramic_pair import compare_direction, summarize_samples
from perspective_sphere import sample_plane, crop_ranges, stitch_ranges


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


P = module('perspective_control', 'compare-perspective-depth.py')
D = P.D
C = module('panorama_crops', 'prepare-panoramas.py')
LEVEL = D.ROOT/'data/jobs/panoramic-perspective-depth-20261106'
CONTROL = D.ROOT/'data/jobs/panoramic-perspective-control-audited-20261106'
PARENT = D.ROOT/'data/jobs/panoramic-calibration-20261106'
PARAMS = [256., 256., 256., 256.]


def inference(path):
    report = D.read(path/'report.json')
    if (report['status'] != 'PASS' or report['device'] != 'mps'
            or report['model'] != 'depth-anything/Depth-Anything-V2-Small-hf'
            or report['revision'] != '5426e4f0f36572d16453bbda7a8389317b1bef99'
            or len(report['images']) != 12):
        raise ValueError('Require twelve actual pinned native MPS predictions')
    arrays = {}
    for i, item in enumerate(report['images']):
        source = Path(item['source'])
        raw = path/f'view-{i:02d}-relative.npy'
        if D.sha(source) != item['sourceSha256'] or D.sha(raw) != item['relativeNpySha256']:
            raise ValueError('Inference input/output hash mismatch')
        arrays[source.name] = np.load(raw)
        if arrays[source.name].shape != (512,512):raise ValueError('Require original 512-square predictions')
    if len(arrays)!=12:raise ValueError('Duplicate inference source names')
    return report, arrays


def prepare(output):
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    anchors = [D.read(p) for p in D.anchor_paths()]
    _, raw = inference(LEVEL)
    fits = D.read(CONTROL/'crop-calibrations.json')
    errors = []
    for row in D.read(CONTROL/'feature-samples.json'):
        index = int(row['direction'][0])-4
        anchor = next(a for a in anchors[index]['anchors'] if a['point3DId'] == row['point3DId'])
        ray = D.unit_bearing(row['sourceObserved'], PARAMS)
        name = row['sourceImage']
        radial = P.perspective_radial(P.plane_sample(raw[name], row['sourceObserved']),fits[name]['perspective'],ray)
        errors.append(abs(np.log(radial/anchor['radialRangeSfm'])))
    files = list(D.anchor_paths()) + [LEVEL/'report.json', CONTROL/'crop-calibrations.json',
        CONTROL/'feature-samples.json', PARENT/'dav2/calibration.json', D.ROOT/'docs/evidence/panoramic-pair-protocol.json']
    files += sorted((D.RIG/'sparse').glob('*.bin'))
    for job in D.job_paths()['dav2']:
        files += [job/'raw.npy', job/'source.png']
    items = []
    originals = ['003_1677293342921360.jpg', '004_679966948337536.jpg']
    for index, original in enumerate(originals):
        source = D.ROOT/'data/samples/mapillary-beijing/images'/original
        if D.sha(source) != anchors[index]['source']['sha256']:
            raise ValueError('Original panorama hash mismatch')
        files.append(source)
        pixels = np.array(Image.open(source).convert('RGB'))
        for yaw in range(0,360,60):
            name = f'pano_{index+4:06d}_down_{yaw:03d}.png'
            Image.fromarray(C.crop_panorama(pixels,512,90,yaw,-30)).save(output/name)
            items.append(dict(panorama=index+4,name=name,yaw=yaw,pitch=-30,
                              cameraToPanorama=C.crop_rotation(yaw,-30).tolist(),
                              sha256=D.sha(output/name)))
    protocol = dict(schemaVersion=1,declaredAt=D.now(),scope='Two existing physical panoramas; no synthesis, new pose estimation, fusion, voxelization or GS',
        dimensions=[1092,546],params=PARAMS,crops=items,
        geometry='CV +X right +Y down +Z forward; camera-Z affine inverse calibration, then radial=Z/unit_camera_ray_z. Fixed-rig SfM arbitrary units, unknown gravity.',
        calibration='Original level fits preserved. Downward fits use only projected common784 training IDs visible in crop; no217 withheld IDs. Projected features are not newly observed correspondences.',
        selection='Most central positive calibrated crop per spherical ray; stable input-order tie. No depth averaging or cross-panorama alignment.',
        consensus='At least two same-center positive predictions, max(log range)-min(log range) <= prior sparse reference. This rejects disagreement, not proof of correct geometry or occlusion.',
        logDiagnosticBand=float(np.quantile(errors,.9)),referenceSamples=len(errors),
        referenceMeaning='P90 absolute log range error at previous434 withheld directional samples (217 distinct IDs); internal SfM comparator, NOT acceptance/confidence. No new dense predictions used.',
        regionPolicy='Unchanged predeclared road/facade boxes and cross-view relative diagnostic band from previous pair protocol. No geometrical PASS inferred.',
        mask='ERP normalized v in[.48,.85], finite positive range <= per-panorama training SfM P99; raw unmasked arrays retained. No semantic sky/ground confidence.',
        cloudStride=3,qualityGate='NOT ACCEPTED until supported static surfaces agree; road lacks common sparse anchors. Do not equate export or filtering with acceptance.',
        files=[dict(path=D.local(p),bytes=p.stat().st_size,sha256=D.sha(p)) for p in files],
        prepareSeconds=time.monotonic()-started)
    D.write(output/'protocol.json',protocol)
    print('Prepared', len(items), 'observed crops; log reference',protocol['logDiagnosticBand'])


def stats(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    return dict(samples=int(values.size),median=float(np.median(values)) if values.size else None,
                p90=float(np.quantile(values,.9)) if values.size else None)


def image_map(values, mask, path, limit=None, diverging=False):
    values = np.asarray(values,float)
    valid = mask & np.isfinite(values)
    scaled = np.zeros(values.shape)
    if valid.any():
        limit = limit or float(np.quantile(np.abs(values[valid]),.95)) or 1
        scaled[valid] = np.clip(values[valid]/limit,-1,1)
    rgb = np.zeros((*values.shape,3),dtype=np.uint8)
    if diverging:
        for channel in range(3):
            rgb[...,channel] = np.where(valid,255*(1-np.abs(scaled)),0).astype(np.uint8)
        rgb[...,0] = np.where(valid & (scaled>0),255,rgb[...,0])
        rgb[...,2] = np.where(valid & (scaled<0),255,rgb[...,2])
    else:
        rgb[...,0] = np.where(valid,255*np.clip(scaled,0,1),0)
        rgb[...,1] = np.where(valid,255*(1-np.clip(scaled,0,1)),0)
        rgb[...,2] = np.where(valid,100,0)
    Image.fromarray(rgb).save(path)


def run(prepared, inferred, output):
    started = time.monotonic()
    output.mkdir(parents=True,exist_ok=False)
    report = dict(status='RUNNING',startedAt=D.now(),qualityStatus='NOT ACCEPTED')
    try:
        import pycolmap
        protocol = D.read(prepared/'protocol.json')
        for entry in protocol['files']:
            path = D.ROOT/entry['path']
            if path.stat().st_size != entry['bytes'] or D.sha(path) != entry['sha256']:
                raise ValueError(f'Pinned input changed: {path}')
        level_report, level = inference(LEVEL)
        down_report, down = inference(inferred)
        for item in protocol['crops']:
            recorded=next((x for x in down_report['images'] if Path(x['source']).name==item['name']),None)
            if (D.sha(prepared/item['name']) != item['sha256'] or item['name'] not in down
                    or recorded is None or recorded['sourceSha256']!=item['sha256']):
                raise ValueError('Declared downward crop changed/missing')
        anchors = [D.read(p) for p in D.anchor_paths()]
        split = D.read(PARENT/'dav2/calibration.json')
        training, held = set(split['trainingPointIds']), set(split['withheldPointIds'])
        if len(training)!=784 or len(held)!=217 or training & held:
            raise ValueError('Training/holdout split changed')
        poses = [np.array(a['worldFromPanorama']) for a in anchors]
        fits = D.read(CONTROL/'crop-calibrations.json')
        model = pycolmap.Reconstruction(D.RIG/'sparse')
        cameras = {image.name:image.cam_from_world().matrix() for image in model.images.values()}
        rays = erp_unit_rays(546,1092)
        rgbs = [np.array(Image.open(p/'source.png').convert('RGB')) for p in D.job_paths()['dav2']]
        vv = (np.arange(546)+.5)[:,None]/546
        band = np.broadcast_to((vv>=.48)&(vv<=.85),(546,1092))
        stages = {key:[] for key in ['level','best','consensus','erp']}
        coverage, down_fits, crop_records = [], {}, []
        for source, anchor in enumerate(anchors):
            panorama = source+4
            all_ranges, all_scores = [], []
            by_id = {a['point3DId']:a for a in anchor['anchors']}
            cap = float(np.quantile([by_id[pid]['radialRangeSfm'] for pid in training],.99))
            for index, yaw in enumerate(range(0,360,60)):
                name = f'pano_{panorama:06d}_view_{index+1:02d}.png'
                rotation = C.crop_rotation(yaw,0)
                measured = np.asarray(cameras[name])
                np.testing.assert_allclose(measured[:3,:3].T,poses[source][:3,:3]@rotation,atol=1e-9,rtol=0)
                np.testing.assert_allclose(-measured[:3,:3].T@measured[:3,3],poses[source][:3,3],atol=1e-9,rtol=0)
                radial, score = crop_ranges(level[name],fits[name]['perspective'],rotation,rays,PARAMS)
                all_ranges.append(radial);all_scores.append(score)
                crop_records.append(dict(name=name,ring='level',panorama=panorama,sourceSha256=next(x['sourceSha256'] for x in level_report['images'] if Path(x['source']).name==name)))
            level_map = stitch_ranges(all_ranges,all_scores,protocol['logDiagnosticBand'])
            for item in [c for c in protocol['crops'] if c['panorama']==panorama]:
                name = item['name'];rotation = np.array(item['cameraToPanorama'])
                pids, predictions, targets = [], [], []
                world_from_camera = poses[source][:3,:3]@rotation
                for pid in sorted(training):
                    point = np.array(by_id[pid]['xyzWorld'])
                    q = (point-poses[source][:3,3])@world_from_camera
                    if q[2]<=0:continue
                    xy = q[:2]/q[2]*256+256
                    value = float(sample_plane(down[name],xy))
                    if not np.isfinite(value):continue
                    pids.append(pid);predictions.append(value);targets.append(q[2])
                fit = P.camera_z_fit(predictions,targets)
                if set(pids)&held:raise ValueError('Holdout leakage')
                withheld_errors=[]
                for pid in sorted(held):
                    point=np.array(by_id[pid]['xyzWorld'])
                    q=(point-poses[source][:3,3])@world_from_camera
                    if q[2]<=0:continue
                    value=float(sample_plane(down[name],q[:2]/q[2]*256+256))
                    if not np.isfinite(value):continue
                    inverse=fit['scale']*value+fit['offset']
                    withheld_errors.append(dict(point3DId=pid,valid=bool(inverse>0),
                        absoluteLogZError=float(abs(np.log(1/inverse/q[2]))) if inverse>0 else None))
                down_fits[name] = dict(trainingPointIds=pids,calibration=fit,cameraToPanorama=rotation.tolist(),worldFromCameraRotation=world_from_camera.tolist(),cameraCenter=poses[source][:3,3].tolist(),
                    projectedHoldout=withheld_errors,holdoutMeaning='At projected existing SfM locations, not new observed feature correspondences or independent depth truth')
                radial,score = crop_ranges(down[name],fit,rotation,rays,PARAMS)
                all_ranges.append(radial);all_scores.append(score)
                crop_records.append(dict(name=name,ring='down',panorama=panorama,sourceSha256=item['sha256']))
            augmented = stitch_ranges(all_ranges,all_scores,protocol['logDiagnosticBand'])
            erp,_ = D.CAL.apply_calibration(np.load(D.job_paths()['dav2'][source]/'raw.npy'),split['common'][source])
            selected_maps = dict(level=level_map['radial'],best=augmented['radial'],
                consensus=np.where(augmented['consensus'],augmented['radial'],np.nan),erp=erp)
            for key, values in selected_maps.items():
                mask = band & np.isfinite(values) & (values>0) & (values<=cap)
                stages[key].append((values,mask))
                np.savez_compressed(output/f'{key}-{panorama}.npz',radial=values,mask=mask)
                image_map(values,mask,output/f'{key}-{panorama}-range.png',limit=cap)
            np.savez_compressed(output/f'overlap-{panorama}.npz',**augmented)
            np.savez_compressed(output/f'crop-ranges-{panorama}.npz',ranges=np.array(all_ranges),centrality=np.array(all_scores))
            image_map(augmented['log_spread'],band&(augmented['support']>=2),output/f'overlap-{panorama}.png',limit=protocol['logDiagnosticBand'])
            regions = D.read(D.ROOT/'docs/evidence/panoramic-pair-protocol.json')['regions']
            regional = {}
            uu = (np.arange(1092)+.5)[None,:]/1092
            for region in regions:
                region_mask = band & (uu>=region['u'][0]) & (uu<=region['u'][1]) & (vv>=region['v'][0]) & (vv<=region['v'][1])
                regional[region['id']] = dict(pixels=int(region_mask.sum()),
                    selected={k:int((stages[k][source][1]&region_mask).sum()) for k in stages},
                    multipleSupported=int((region_mask&(augmented['support']>=2)).sum()),
                    logSpread=stats(augmented['log_spread'][region_mask&(augmented['support']>=2)]))
            coverage.append(dict(panorama=panorama,bandPixels=int(band.sum()),rangeCap=cap,
                selected={k:int(stages[k][source][1].sum()) for k in stages},
                overlapLogSpread=stats(augmented['log_spread'][band&(augmented['support']>=2)]),regions=regional))
        D.write(output/'down-calibrations.json',down_fits)
        pair_protocol = D.read(D.ROOT/'docs/evidence/panoramic-pair-protocol.json')
        reference = D.read(D.ROOT/'public/experiments/panoramic-calibration/dav2/cloud.json')
        results = {}
        for key, maps in stages.items():
            folder = output/key;folder.mkdir()
            clouds, colors, source_ids = [], [], []
            for source,(values,mask) in enumerate(maps):
                xyz,rgb,_,_ = backproject_radial(values,rgbs[source],poses[source],mask=mask,stride=3)
                clouds.append(xyz);colors.append(rgb);source_ids.extend([source]*len(xyz))
            xyz,rgb = np.concatenate(clouds),np.concatenate(colors)
            cloud = {k:reference[k] for k in ['center','radius','camera','captures']}
            cloud.update(positions=xyz.astype(np.float32).ravel().tolist(),colors=rgb.ravel().tolist(),sourceIds=source_ids)
            D.write(folder/'cloud.json',cloud);D.CAL.write_ply(folder/'cloud.ply',xyz,rgb)
            directions = []
            for source,target in [(0,1),(1,0)]:
                ident=f'{source+4}-to-{target+4}'
                comparison = compare_direction(maps[source][0],maps[target][0],rgbs[source],rgbs[target],poses[source],poses[target],source_mask=maps[source][1],target_mask=maps[target][1],stride=3,relative_tolerance=pair_protocol['relativeDiagnosticBand'])
                samples = comparison['samples'];rows=samples['source_rows'];cols=samples['source_columns'];valid=samples['candidate']
                warp=np.zeros_like(rgbs[source]);warp[rows[valid],cols[valid]]=np.clip(samples['target_rgb'][valid],0,255).astype(np.uint8)
                # Sparse display at stride3; statistics retain all selected samples.
                Image.fromarray(warp[::3,::3]).resize((1092,546),Image.Resampling.NEAREST).save(folder/f'{ident}-warp.png')
                residual=np.full((546,1092),np.nan);residual[rows,cols]=samples['relative_residual']
                image_map(residual,np.isfinite(residual),folder/f'{ident}-residual.png',limit=pair_protocol['relativeDiagnosticBand'],diverging=True)
                mask_image=np.zeros_like(rgbs[source]);mask_image[rows,cols]=[90,90,90]
                for category,color in [('agreement',[70,220,120]),('in_front',[50,100,255]),('behind',[255,80,65])]:
                    chosen=samples[category];mask_image[rows[chosen],cols[chosen]]=color
                Image.fromarray(mask_image[::3,::3]).resize((1092,546),Image.Resampling.NEAREST).save(folder/f'{ident}-mask.png')
                with Image.open(folder/f'{ident}-residual.png') as diagnostic:
                    Image.fromarray(np.array(diagnostic)[::3,::3]).resize((1092,546),Image.Resampling.NEAREST).save(folder/f'{ident}-residual.png')
                regional={}
                for region in pair_protocol['regions']:
                    selection=((cols+.5)/1092>=region['u'][0])&((cols+.5)/1092<=region['u'][1])&((rows+.5)/546>=region['v'][0])&((rows+.5)/546<=region['v'][1])
                    regional[region['id']]=summarize_samples(samples,selection)
                directions.append(dict(id=ident,**comparison['summary'],regions=regional))
                np.savez_compressed(folder/f'{ident}-samples.npz',**{k:v for k,v in samples.items() if v is not None})
            results[key]=dict(points=len(xyz),directions=directions)
        paired=[]
        for source in [4,5]:
            ident=f'{source}-to-{9-source}'
            erp=np.load(output/f'erp/{ident}-samples.npz')
            native=np.load(output/f'best/{ident}-samples.npz')
            erp_indices={int(r*1092+c):i for i,(r,c) in enumerate(zip(erp['source_rows'],erp['source_columns']))}
            pairs=[(erp_indices[int(r*1092+c)],i) for i,(r,c) in enumerate(zip(native['source_rows'],native['source_columns'])) if int(r*1092+c) in erp_indices]
            indices=np.array(pairs);a,b=indices[:,0],indices[:,1]
            jointly_valid=erp['candidate'][a]&native['candidate'][b]
            regions=[dict(id='all',u=[0,1],v=[0,1])]+pair_protocol['regions']
            for region in regions:
                u=(native['source_columns'][b]+.5)/1092;v=(native['source_rows'][b]+.5)/546
                selected=(u>=region['u'][0])&(u<=region['u'][1])&(v>=region['v'][0])&(v<=region['v'][1])
                chosen=selected&jointly_valid
                ae=np.abs(erp['relative_residual'][a[chosen]]);be=np.abs(native['relative_residual'][b[chosen]])
                paired.append(dict(direction=ident,region=region['id'],sharedSelectedSourceSamples=int(selected.sum()),jointlySupportedSamples=int(chosen.sum()),
                    erpAbsoluteRelativeResidual=stats(ae),perspectiveAbsoluteRelativeResidual=stats(be),
                    perspectiveMinusErp=stats(be-ae),fractionPerspectiveLower=float(np.mean(be<ae)) if len(ae) else None))
        report.update(status='PASS',protocolSha256=D.sha(prepared/'protocol.json'),inferenceReportSha256=D.sha(inferred/'report.json'),
            protocol=protocol,coverage=coverage,results=results,crops=crop_records,
            downwardTrainingCounts={k:len(v['trainingPointIds']) for k,v in down_fits.items()},
            pairedBestVersusErp=paired,inference=down_report,geometryAcceptance='NOT ACCEPTED',fusion='NOT RUN',gaussianTraining='NOT RUN')
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(finishedAt=D.now(),elapsedSeconds=time.monotonic()-started,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        D.write(output/'report.json',report)
    print(report['status'],report['elapsedSeconds'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','run']);parser.add_argument('output',type=Path)
    parser.add_argument('--prepared',type=Path);parser.add_argument('--inferred',type=Path)
    args=parser.parse_args()
    if args.action=='prepare':prepare(args.output)
    else:
        if args.prepared is None or args.inferred is None:parser.error('run requires --prepared and --inferred')
        run(args.prepared,args.inferred,args.output)
