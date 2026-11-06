#!/usr/bin/env python3
"""Compare preserved calibration with observed-correspondence calibration."""
import argparse
import importlib.util
from pathlib import Path
import resource
import time
import traceback
import numpy as np
from PIL import Image
from spherical_depth import erp_unit_rays,backproject_radial
from panoramic_pair import compare_direction,summarize_samples
from perspective_sphere import sample_plane,crop_ranges,stitch_ranges
from stereo_tracks import angular_separation

spec=importlib.util.spec_from_file_location('matching',Path(__file__).with_name('experiment-stereo-anchors.py'))
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
D,C,O=M.D,M.C,M.O


def run(matching,output,road=None):
    output.mkdir(parents=True,exist_ok=False);started=time.monotonic();report=dict(status='RUNNING',startedAt=D.now(),qualityStatus='NOT ACCEPTED')
    try:
        protocol=D.read(matching/'protocol.json');matching_report=D.read(matching/'matching.json')
        if matching_report['status']!='PASS' or matching_report['protocolSha256']!=D.sha(matching/'protocol.json') or matching_report['tracksSha256']!=D.sha(matching/'tracks.json'):raise ValueError('Matching evidence changed')
        for entry in protocol['files']:
            path=D.ROOT/entry['path']
            if D.sha(path)!=entry['sha256'] or path.stat().st_size!=entry['bytes']:raise ValueError('Pinned calibration input changed')
        tracks=D.read(matching/'tracks.json');road_report=None;road_used=False
        if road:
            road_report=D.read(road/'report.json')
            road_protocol=D.read(road/'protocol.json')
            if (road_report['status']!='PASS' or road_report['tracksSha256']!=D.sha(road/'tracks.json')
                    or road_report['protocolSha256']!=D.sha(road/'protocol.json')
                    or road_protocol['matchingReportSha256']!=D.sha(matching/'matching.json')):raise ValueError('Road stereo evidence invalid')
            road_used=road_report['roadTracks']>=30
            for row in D.read(road/'tracks.json') if road_used else []:
                if tracks and np.any(np.all(angular_separation(np.array([r['rayPanorama'] for r in tracks]),np.array(row['rayPanorama']))<=.35,axis=1)):continue
                tracks.append(row)
        D.write(output/'tracks.json',tracks)
        new_training=[r for r in tracks if r['training']];new_held=[r for r in tracks if r['held']]
        if any(r['held'] or r['protectedHistoricalHoldout'] for r in new_training):raise ValueError('Holdout leakage')
        anchors=[D.read(p) for p in D.anchor_paths()];poses=[np.array(a['worldFromPanorama']) for a in anchors]
        _,level=O.inference(O.LEVEL);_,down=O.inference(M.INFERRED)
        level_fits=D.read(O.CONTROL/'crop-calibrations.json');down_fits=D.read(M.PREVIOUS/'down-calibrations.json')
        previous=D.read(M.PREVIOUS/'report.json');params=np.array([256.]*4)
        split=D.read(O.PARENT/'dav2/calibration.json');old_held=set(split['withheldPointIds'])
        definitions={};fits={key:{} for key in ['baseline','augmented','new-only']};fit_diagnostics=[]
        for source in [0,1]:
            by_id={a['point3DId']:a for a in anchors[source]['anchors']}
            for ring,pitch in [('level',0),('down',-30)]:
                for index,yaw in enumerate(range(0,360,60)):
                    name=f'pano_{source+4:06d}_view_{index+1:02d}.png' if ring=='level' else f'pano_{source+4:06d}_down_{yaw:03d}.png'
                    raw=level[name] if ring=='level' else down[name]
                    rotation=C.crop_rotation(yaw,pitch);world_rotation=poses[source][:3,:3]@rotation
                    old=level_fits[name] if ring=='level' else down_fits[name]
                    old_fit=old['perspective'] if ring=='level' else old['calibration']
                    if old_held&set(old['trainingPointIds']):raise ValueError('Original holdout leakage')
                    definitions[name]=dict(source=source,ring=ring,yaw=yaw,rotation=rotation,worldRotation=world_rotation,raw=raw)
                    def samples(points):
                        if not len(points):return np.empty(0),np.empty(0)
                        q=(np.array(points)-poses[source][:3,3])@world_rotation
                        with np.errstate(divide='ignore',invalid='ignore'):xy=q[:,:2]/q[:,2,None]*256+256
                        predictions=sample_plane(raw,xy)
                        valid=(q[:,2]>0)&np.isfinite(predictions)
                        return predictions[valid],q[valid,2]
                    old_predictions,old_z=samples([by_id[pid]['xyzWorld'] for pid in old['trainingPointIds']])
                    check=O.P.camera_z_fit(old_predictions,old_z)
                    np.testing.assert_allclose([check['scale'],check['offset']],[old_fit['scale'],old_fit['offset']],rtol=1e-7,atol=1e-9)
                    new_predictions,new_z=samples([r['xyz'] for r in new_training])
                    fits['baseline'][name]=old_fit
                    for method,pred,target in [('augmented',np.r_[old_predictions,new_predictions],np.r_[old_z,new_z]),('new-only',new_predictions,new_z)]:
                        status='PASS';error=None
                        try:fit=O.P.camera_z_fit(pred,target)
                        except ValueError as exception:fit=old_fit;status='NOT RUN';error=str(exception)
                        fits[method][name]=fit
                        fit_diagnostics.append(dict(method=method,crop=name,status=status,fallbackToBaseline=status!='PASS',error=error,oldTrainingSamples=len(old_predictions),newTrainingSamples=len(new_predictions)))
        D.write(output/'calibrations.json',fits);D.write(output/'fit-diagnostics.json',fit_diagnostics)
        held_rows=[]
        for row in new_held:
            ring,yaw=row['group'].split('-');ring='down' if ring=='ground' else ring;yaw=int(yaw)
            names=[f'pano_{s+4:06d}_view_{yaw//60+1:02d}.png' if ring=='level' else f'pano_{s+4:06d}_down_{yaw:03d}.png' for s in [0,1]]
            for source,target in [(0,1),(1,0)]:
                definition=definitions[names[source]];xy=np.array(row['xy'][source])/2
                ray=D.unit_bearing(xy,params);world_ray=definition['worldRotation']@ray
                dst=definitions[names[target]];matrix=np.column_stack([dst['worldRotation'].T,-dst['worldRotation'].T@poses[target][:3,3]])
                camera=dict(params=params.tolist(),width=512,height=512,camFromWorld=matrix.tolist())
                methods={}
                for method in fits:
                    radial=O.P.perspective_radial(float(sample_plane(definition['raw'],xy)),fits[method][names[source]],ray)
                    evaluation=D.evaluate_range(radial,world_ray,poses[source][:3,3],camera,np.array(row['xy'][target])/2)
                    true_range=np.linalg.norm(np.array(row['xyz'])-poses[source][:3,3])
                    evaluation['absoluteRelativeRangeResidual']=float(abs(radial/true_range-1)) if np.isfinite(radial) else None
                    methods[method]=evaluation
                true_range=np.linalg.norm(np.array(row['xyz'])-poses[source][:3,3])
                methods['triangulated']=D.evaluate_range(true_range,world_ray,poses[source][:3,3],camera,np.array(row['xy'][target])/2)
                held_rows.append(dict(track=row['id'],direction=f'{source+4}-to-{target+4}',sourceUv=row['uv'][source],parallaxDegrees=row['parallaxDegrees'],methods=methods))
        D.write(output/'held-samples.json',held_rows)
        held_summary=[]
        regions=D.read(D.ROOT/'docs/evidence/panoramic-pair-protocol.json')['regions']
        for ident in ['4-to-5','5-to-4']:
            for region in [dict(id='all',u=[0,1],v=[0,1])]+regions:
                chosen=[r for r in held_rows if r['direction']==ident and region['u'][0]<=r['sourceUv'][0]<=region['u'][1] and region['v'][0]<=r['sourceUv'][1]<=region['v'][1]]
                held_summary.append(dict(direction=ident,region=region['id'],tracks=len(chosen),methods={k:dict(projection=D.statistics(chosen,k),absoluteRelativeRange=O.stats([r['methods'][k]['absoluteRelativeRangeResidual'] for r in chosen if r['methods'][k]['absoluteRelativeRangeResidual'] is not None])) for k in fits},triangulatedRayControl=D.statistics(chosen,'triangulated')))
        historical=[]
        for row in D.read(O.CONTROL/'feature-samples.json'):
            source=int(row['direction'][0])-4;target=1-source;src=definitions[row['sourceImage']];dst=definitions[row['targetImage']]
            ray=D.unit_bearing(row['sourceObserved'],params);world_ray=src['worldRotation']@ray
            camera=dict(params=params.tolist(),width=512,height=512,camFromWorld=np.column_stack([dst['worldRotation'].T,-dst['worldRotation'].T@poses[target][:3,3]]).tolist())
            methods={}
            for method in fits:
                radial=O.P.perspective_radial(float(sample_plane(src['raw'],row['sourceObserved'])),fits[method][row['sourceImage']],ray)
                methods[method]=D.evaluate_range(radial,world_ray,poses[source][:3,3],camera,row['targetObserved'])
            historical.append(dict(direction=row['direction'],point3DId=row['point3DId'],pairParallaxDegrees=row['pairParallaxDegrees'],methods=methods))
        D.write(output/'historical-held-samples.json',historical)
        historical_summary=[dict(direction=ident,parallaxMinimum=minimum,methods={method:D.statistics([r for r in historical if r['direction']==ident and r['pairParallaxDegrees']>=minimum],method) for method in fits}) for ident in ['4-to-5','5-to-4'] for minimum in [0,10]]
        rays=erp_unit_rays(546,1092);vv=(np.arange(546)+.5)[:,None]/546
        band=np.broadcast_to((vv>=.48)&(vv<=.85),(546,1092))
        rgbs=[np.array(Image.open(j/'source.png').convert('RGB')) for j in D.job_paths()['dav2']]
        reference=D.read(D.ROOT/'public/experiments/perspective-overlap/best/cloud.json')
        results={};maps={}
        pair_protocol=D.read(D.ROOT/'docs/evidence/panoramic-pair-protocol.json')
        for method,calibration in fits.items():
            folder=output/method;folder.mkdir();ranges=[];masks=[];xyzs=[];colors=[];ids=[]
            for source in [0,1]:
                values=[];scores=[]
                for name,definition in definitions.items():
                    if definition['source']!=source:continue
                    radial,score=crop_ranges(definition['raw'],calibration[name],definition['rotation'],rays,params)
                    values.append(radial);scores.append(score)
                stitched=stitch_ranges(values,scores,previous['protocol']['logDiagnosticBand']);radial=stitched['radial'];cap=previous['coverage'][source]['rangeCap']
                mask=band&np.isfinite(radial)&(radial>0)&(radial<=cap)
                if method=='baseline':
                    original=np.load(M.PREVIOUS/f'best-{source+4}.npz')
                    np.testing.assert_allclose(radial,original['radial'],equal_nan=True,rtol=1e-10,atol=1e-10);np.testing.assert_array_equal(mask,original['mask'])
                ranges.append(radial);masks.append(mask);np.savez_compressed(folder/f'{source+4}-map.npz',**stitched,mask=mask)
                O.image_map(radial,mask,folder/f'{source+4}-range.png',limit=cap)
                O.image_map(stitched['log_spread'],band&(stitched['support']>=2),folder/f'{source+4}-overlap.png',limit=previous['protocol']['logDiagnosticBand'])
                xyz,rgb,_,_=backproject_radial(radial,rgbs[source],poses[source],mask=mask,stride=3);xyzs.append(xyz);colors.append(rgb);ids.extend([source]*len(xyz))
            xyz,rgb=np.concatenate(xyzs),np.concatenate(colors)
            cloud={k:reference[k] for k in ['center','radius','camera','captures']};cloud.update(positions=xyz.astype(np.float32).ravel().tolist(),colors=rgb.ravel().tolist(),sourceIds=ids)
            D.write(folder/'cloud.json',cloud);D.CAL.write_ply(folder/'cloud.ply',xyz,rgb)
            directions=[]
            for source,target in [(0,1),(1,0)]:
                ident=f'{source+4}-to-{target+4}';comparison=compare_direction(ranges[source],ranges[target],rgbs[source],rgbs[target],poses[source],poses[target],source_mask=masks[source],target_mask=masks[target],stride=3,relative_tolerance=pair_protocol['relativeDiagnosticBand'])
                samples=comparison['samples'];rows=samples['source_rows'];columns=samples['source_columns'];valid=samples['candidate']
                warp=np.zeros_like(rgbs[source]);warp[rows[valid],columns[valid]]=samples['target_rgb'][valid].clip(0,255).astype(np.uint8)
                Image.fromarray(warp[::3,::3]).resize((1092,546),Image.Resampling.NEAREST).save(folder/f'{ident}-warp.png')
                residual=np.full((546,1092),np.nan);residual[rows,columns]=samples['relative_residual']
                O.image_map(residual,np.isfinite(residual),folder/f'{ident}-residual.png',limit=pair_protocol['relativeDiagnosticBand'],diverging=True)
                with Image.open(folder/f'{ident}-residual.png') as im:Image.fromarray(np.array(im)[::3,::3]).resize((1092,546),Image.Resampling.NEAREST).save(folder/f'{ident}-residual.png')
                regional={}
                for region in regions:
                    selection=((columns+.5)/1092>=region['u'][0])&((columns+.5)/1092<=region['u'][1])&((rows+.5)/546>=region['v'][0])&((rows+.5)/546<=region['v'][1])
                    regional[region['id']]=summarize_samples(samples,selection)
                directions.append(dict(id=ident,**comparison['summary'],regions=regional))
                np.savez_compressed(folder/f'{ident}-samples.npz',**{k:v for k,v in samples.items() if v is not None})
            results[method]=dict(points=len(xyz),selectedPixels=[int(m.sum()) for m in masks],directions=directions)
            maps[method]=[ranges,masks]
        paired=[]
        for method in ['augmented','new-only']:
            for source in [4,5]:
                ident=f'{source}-to-{9-source}';base=np.load(output/f'baseline/{ident}-samples.npz');candidate=np.load(output/f'{method}/{ident}-samples.npz')
                baseline_index={int(r*1092+c):i for i,(r,c) in enumerate(zip(base['source_rows'],base['source_columns']))}
                pairs=[(baseline_index[int(r*1092+c)],i) for i,(r,c) in enumerate(zip(candidate['source_rows'],candidate['source_columns'])) if int(r*1092+c) in baseline_index]
                indices=np.array(pairs);a,b=indices[:,0],indices[:,1];supported=base['candidate'][a]&candidate['candidate'][b]
                for region in [dict(id='all',u=[0,1],v=[0,1])]+regions:
                    u=(candidate['source_columns'][b]+.5)/1092;v=(candidate['source_rows'][b]+.5)/546
                    selected=(u>=region['u'][0])&(u<=region['u'][1])&(v>=region['v'][0])&(v<=region['v'][1]);chosen=selected&supported
                    ae=np.abs(base['relative_residual'][a[chosen]]);be=np.abs(candidate['relative_residual'][b[chosen]])
                    paired.append(dict(method=method,direction=ident,region=region['id'],sharedSelected=int(selected.sum()),jointlySupported=int(chosen.sum()),baseline=O.stats(ae),candidate=O.stats(be),candidateMinusBaseline=O.stats(be-ae)))
        report.update(status='PASS',protocolSha256=D.sha(matching/'protocol.json'),matchingReportSha256=D.sha(matching/'matching.json'),tracksSha256=D.sha(output/'tracks.json'),implementationSha256=D.sha(Path(__file__)),
            matching=matching_report,roadStereo=road_report,roadStereoUsed=road_used,uniqueTracks=len(tracks),newTrainingTracks=len(new_training),newHeldTracks=len(new_held),fits=fit_diagnostics,held=held_summary,historicalHeld=historical_summary,results=results,paired=paired,
            depthInference='NOT RUN: reused hash-checked earlier MPS predictions',fusion='NOT RUN',gaussianTraining='NOT RUN',geometryAcceptance='NOT ACCEPTED')
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(finishedAt=D.now(),elapsedSeconds=time.monotonic()-started,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);D.write(output/'report.json',report)
    print(report['status'],report['elapsedSeconds'],report['uniqueTracks'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('matching',type=Path);p.add_argument('output',type=Path);p.add_argument('--road',type=Path);a=p.parse_args();run(a.matching,a.output,a.road)
