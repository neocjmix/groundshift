#!/usr/bin/env python3
"""Compare unchanged calibrated depth maps to actual third-view stereo support."""
import argparse
import importlib.util
from pathlib import Path
import resource
import time
import numpy as np
from spherical_depth import sample_erp_bilinear
from third_view_geometry import third_view_residual

spec=importlib.util.spec_from_file_location('third',Path(__file__).with_name('check-road-third-view.py'))
T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T);D=T.D


def run(job, calibration, output):
    job, calibration = job.resolve(), calibration.resolve()
    output.mkdir(parents=True,exist_ok=False); started=time.monotonic()
    report=dict(status='RUNNING',startedAt=D.now())
    try:
        previous=D.read(job/'report.json'); saved=D.read(calibration/'report.json')
        if previous['status']!='PASS' or saved['status']!='PASS':raise ValueError('Require completed evidence')
        if D.sha(job/'tracks.json')!=previous['tracksSha256']:raise ValueError('Third-view tracks changed')
        variants=['baseline','augmented','new-only']
        files=[job/'report.json',job/'tracks.json',calibration/'report.json',Path(__file__),Path(__file__).with_name('third_view_geometry.py')]
        files += [calibration/v/'5-map.npz' for v in variants]
        D.write(output/'protocol.json',dict(declaredAt=D.now(),variants=variants,physicalSource=5,target=6,
            measurement='Sample frozen5 radial maps at the exact shared panorama5 bearing. Compare to supported preferred5/6 stereo, retaining invalid predictions. Same support set for all variants. No fitting, thresholds or camera changes.',
            split='Report all previously supported tracks and previous training/held separately. RGB6 was withheld from calibration; its SfM pose was not. Old training observations are not independent geometry truth.',
            units='SfM arbitrary units. Relative range difference uses new5/6 stereo range as denominator; angle measured at center6.',
            files=[dict(path=D.local(p),bytes=p.stat().st_size,sha256=D.sha(p)) for p in files]))
        tracks=[r for r in D.read(job/'tracks.json') if r['status']=='supported']
        poses={n:np.asarray(previous['worldFromPanorama'][str(n)]) for n in [5,6]}
        results={}; samples=[]
        for variant in variants:
            with np.load(calibration/variant/'5-map.npz') as arrays:
                radial=arrays['radial'].copy(); mask=arrays['mask'];radial[~mask]=np.nan
            uv=np.array([r['oldUv'][1] for r in tracks]); rays=np.array([r['oldXyz'] for r in tracks])-poses[5][:3,3]
            rays/=np.linalg.norm(rays,axis=1,keepdims=True)
            ranges=sample_erp_bilinear(radial,uv[:,0]*radial.shape[1]-.5,uv[:,1]*radial.shape[0]-.5)
            xyz=poses[5][:3,3]+ranges[:,None]*rays
            rows=[]
            for i,track in enumerate(tracks):
                row=dict(id=track['id'],variant=variant,heldInPrevious=track['heldInPrevious'],trainingInPrevious=track['trainingInPrevious'],valid=bool(np.isfinite(ranges[i]) and ranges[i]>0))
                if row['valid']:row.update(**third_view_residual(xyz[i],track['primary']['xyz'],poses[5][:3,3],poses[6][:3,3]))
                rows.append(row)
            def summarize(selected):
                valid=[r for r in selected if r['valid']]
                return dict(total=len(selected),valid=len(valid),invalid=len(selected)-len(valid),
                    angularResidualDegrees=T.stats([r['angleDegrees'] for r in valid]),
                    absoluteRelativeRangeDifference=T.stats([abs(r['relativeRangeDifference']) for r in valid]))
            results[variant]={name:summarize([r for r in rows if name=='all' or (r['heldInPrevious'] if name=='previous-held' else r['trainingInPrevious'])]) for name in ['all','previous-held','previous-training']}
            samples.extend(rows)
        paired=[]
        for reference in ['baseline','new-only']:
            a={r['id']:r for r in samples if r['variant']==reference};b={r['id']:r for r in samples if r['variant']=='augmented'}
            for name in ['all','previous-held','previous-training']:
                ids=[t['id'] for t in tracks if name=='all' or
                     (name=='previous-held' and t['heldInPrevious']) or
                     (name=='previous-training' and t['trainingInPrevious'])]
                common=[i for i in ids if a[i]['valid'] and b[i]['valid']]
                paired.append(dict(reference=reference,comparison='augmented',subset=name,total=len(ids),commonValid=len(common),
                    referenceAngleDegrees=T.stats([a[i]['angleDegrees'] for i in common]),augmentedAngleDegrees=T.stats([b[i]['angleDegrees'] for i in common]),
                    referenceAbsoluteRelativeRange=T.stats([abs(a[i]['relativeRangeDifference']) for i in common]),
                    augmentedAbsoluteRelativeRange=T.stats([abs(b[i]['relativeRangeDifference']) for i in common]),
                    angleImproved=sum(b[i]['angleDegrees']<a[i]['angleDegrees'] for i in common),
                    rangeImproved=sum(abs(b[i]['relativeRangeDifference'])<abs(a[i]['relativeRangeDifference']) for i in common)))
        D.write(output/'samples.json',samples)
        report.update(status='PASS',qualityStatus='NOT ACCEPTED',stereoReportSha256=D.sha(job/'report.json'),calibrationReportSha256=D.sha(calibration/'report.json'),
            supportedTracks=len(tracks),results=results,paired=paired,protocolSha256=D.sha(output/'protocol.json'),samplesSha256=D.sha(output/'samples.json'),
            calibration='NOT RUN; frozen maps only',depthInference='NOT RUN',gaussianTraining='NOT RUN')
    except Exception as error:report.update(status='FAIL',error=f'{type(error).__name__}: {error}');raise
    finally:
        report.update(finishedAt=D.now(),elapsedSeconds=time.monotonic()-started,maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);D.write(output/'report.json',report)
    print(report['results'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('calibration',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.job,a.calibration,a.output)
