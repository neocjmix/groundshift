#!/usr/bin/env python3
"""Measure actual matched renders and encode inspectable motion, without pose claims."""
import argparse
from pathlib import Path
import importlib.util
import subprocess
import time
import numpy as np
from PIL import Image,ImageDraw
from spherical_depth import directions_to_erp

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

P=module('prepare','prepare-street.py');C=module('crops','prepare-panoramas.py');G=module('compare','compare-gap.py')


def metrics(reference,rgba,mask):
    reference,rgba,mask=np.asarray(reference),np.asarray(rgba),np.asarray(mask)
    if (reference.dtype!=np.uint8 or rgba.dtype!=np.uint8 or reference.ndim!=3 or reference.shape[2]!=3
            or rgba.shape!=(*reference.shape[:2],4) or mask.shape!=reference.shape[:2] or mask.dtype!=np.bool_):
        raise ValueError('Require matching uint8 RGB/RGBA and boolean selection; no resizing or implicit mask conversion')
    alpha=rgba[:,:,3].astype(float)/255
    composite=np.rint(rgba[:,:,:3].astype(float)*alpha[:,:,None]+127*(1-alpha[:,:,None])).astype(np.uint8)
    result=G.region_metrics(reference,composite,mask)
    result.update(opacityCoverage95=float(np.mean(alpha[mask]>=.95)),meanOpacity=float(np.mean(alpha[mask])),
        meaning='Decoded sRGB RGB error including holes, composited on127 grey. Alpha coverage is not measured visibility or true geometric coverage.')
    return result


def run(job,rendered,output,config_path=None,reference_metrics=None,baseline_model='sparse'):
    output.mkdir(parents=True,exist_ok=False);start=time.monotonic();report=dict(status='RUNNING',startedAt=P.now())
    try:
        config_path=config_path or job/'render-config.json'
        rendering=P.read(rendered/'report.json');config=P.read(config_path);by_id={c['id']:c for c in config['cameras']}
        rows=[];models=[]
        for model in rendering['models']:
            training=P.read(job/('training-'+model['id'])/'job.json')
            native=dict(id=model['id'],status=training['status'],trainingSeconds=training['elapsedSeconds'],maxResidentSetBytes=training.get('maximumResidentSetBytes'),peakMemoryFootprintBytes=training.get('peakMemoryFootprintBytes'),
                adapterEvidence=training.get('adapterEvidence'),initialPoints=None,splats=training.get('artifact',{}).get('splats'),bytes=training.get('artifact',{}).get('bytes'),sha256=training.get('artifact',{}).get('sha256'),steps=training['options']['steps'],renderStatus=model['status'])
            models.append(native)
            if model['status']!='PASS':continue
            for rendered_view in model['renders']:
                camera=by_id[rendered_view['id']]
                if not camera.get('reference'):continue
                reference=np.asarray(Image.open(camera['reference']).convert('RGB'));rgba=np.asarray(Image.open(rendered/model['id']/(camera['id']+'-rgba.png')).convert('RGBA'))
                yy,xx=np.indices(reference.shape[:2]);ray=np.stack([(xx+.5-256)/256,(yy+.5-256)/256,np.ones_like(xx)],axis=-1)
                ray/=np.linalg.norm(ray,axis=-1,keepdims=True);ray=ray@C.crop_rotation(camera['yaw'],camera['pitch']).T
                _,v=directions_to_erp(ray,546,1092);vn=(v+.5)/546
                regions={}
                for name,low,high in [('band',.40,.85),('road-band',.70,.85),('mid-height-band',.43,.68)]:
                    mask=(vn>=low)&(vn<=high)
                    regions[name]=metrics(reference,rgba,mask) if mask.any() else dict(status='NOT RUN',pixelCount=0)
                rows.append(dict(model=model['id'],view=camera['id'],kind=camera['kind'],physical=camera['physicalPanorama'],ring=camera['ring'],yaw=camera['yaw'],regions=regions))
        P.write(output/'view-metrics.json',rows)
        summary=[]
        for native in models:
            selected=[r for r in rows if r['model']==native['id'] and r['kind']=='held' and r['ring']=='level'];native['heldLevelViews']=len(selected)
            if selected:
                native['heldLevelMaeMean']=float(np.mean([r['regions']['band']['mae'] for r in selected]));native['heldLevelCoverage95Mean']=float(np.mean([r['regions']['band']['opacityCoverage95'] for r in selected]))
                native['heldLevelPsnrMean']=float(np.mean([r['regions']['band']['psnrDb'] for r in selected]))
            summary.append(native)
        reference=P.read(reference_metrics) if reference_metrics else rows
        base={r['view']:r for r in reference if r['model']==baseline_model and r['kind']=='held' and r['ring']=='level'}
        if len(base)!=6:raise ValueError('Comparison requires all six actual held level views for baseline '+baseline_model)
        comparisons=[]
        for native in models:
            if native['id']==baseline_model:continue
            candidate={r['view']:r for r in rows if r['model']==native['id'] and r['kind']=='held' and r['ring']=='level'};common=sorted(base.keys()&candidate.keys())
            improved=sum(candidate[v]['regions']['band']['mae']<base[v]['regions']['band']['mae'] for v in common)
            delta=float(np.mean([candidate[v]['regions']['band']['opacityCoverage95']-base[v]['regions']['band']['opacityCoverage95'] for v in common])) if common else None
            comparisons.append(dict(id=native['id'],baseline=baseline_model,views=len(common),maeImprovedViews=improved,meanCoverageDifference=delta,
                comparisonScreen='PASS' if len(common)==6 and improved>=3 and delta>=-.05 else 'FAIL',
                meaning='Predeclared comparative appearance screen, not geometry acceptance. All selected pixels include holes.'))
        (output/'videos').mkdir();video_results=[]
        path_cameras=[c for c in config['cameras'] if c['kind']=='path']
        for native in models:
            ident=native['id']
            if native['renderStatus']!='PASS':continue
            command=['/opt/homebrew/bin/ffmpeg','-v','error','-framerate','6','-i',str(rendered/ident/'path-%03d.png'),'-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(output/'videos'/(ident+'.mp4'))]
            result=subprocess.run(command,capture_output=True,text=True);video_results.append(dict(id=ident,status='PASS' if result.returncode==0 else 'FAIL',exitCode=result.returncode,error=result.stderr,frames=len(path_cameras),fps=6,meaning='Actual GS renders from interpolated recovered cameras; playback rate is encoding, not measured renderer FPS.'))
        completed=[m for m in models if m['renderStatus']=='PASS'];frames=output/'comparison-frames';frames.mkdir()
        for i,camera in enumerate(path_cameras):
            canvas=Image.new('RGB',(768,410*int(np.ceil(len(completed)/2))),(10,16,23));draw=ImageDraw.Draw(canvas)
            for j,m in enumerate(completed):
                x,y=(j%2)*384,(j//2)*410
                im=Image.open(rendered/m['id']/(camera['id']+'.png')).convert('RGB').resize((384,384),Image.Resampling.LANCZOS);canvas.paste(im,(x,y+26));draw.text((x+8,y+7),m['id'].upper(),fill=(235,245,250))
            canvas.save(frames/f'{i:03d}.png')
        if completed:
            r=subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-framerate','6','-i',str(frames/'%03d.png'),'-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(output/'videos/comparison.mp4')],capture_output=True,text=True)
            video_results.append(dict(id='comparison',status='PASS' if r.returncode==0 else 'FAIL',exitCode=r.returncode,error=r.stderr,frames=len(path_cameras),fps=6))
        report.update(status='PASS' if rendering['status']=='PASS' and all(v['status']=='PASS' for v in video_results) else 'FAIL',geometryStatus='NOT ACCEPTED',models=summary,comparisons=comparisons,videos=video_results,
            renderReportSha256=P.sha(rendered/'report.json'),configSha256=P.sha(config_path),metricsSha256=P.sha(output/'view-metrics.json'),referenceMetricsSha256=P.sha(reference_metrics) if reference_metrics else None,
            evaluation='Physical5 RGB excluded from GS optimization and dense initialization. Camera/sparse geometry use all-nine SfM. Actual same-pose photometry, not independent measured geometry.',
            novelGeometryGroundTruth='NOT RUN',diffusion='NOT RUN')
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=P.now(),elapsedSeconds=time.monotonic()-start);P.write(output/'report.json',report)
    print(report['status'],[(m['id'],m.get('heldLevelMaeMean')) for m in report['models']],comparisons)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('renders',type=Path);p.add_argument('output',type=Path);p.add_argument('--config',type=Path);p.add_argument('--reference-metrics',type=Path);p.add_argument('--baseline-model',default='sparse')
    a=p.parse_args();run(a.job.resolve(),a.renders.resolve(),a.output.resolve(),a.config.resolve() if a.config else None,a.reference_metrics.resolve() if a.reference_metrics else None,a.baseline_model)
