#!/usr/bin/env python3
"""Prepare the single final1024/800k trial from preserved sources and DAV2 seed."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from PIL import Image
import importlib.util

spec=importlib.util.spec_from_file_location('street_prepare',Path(__file__).with_name('prepare-street.py'))
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)


def verify_frames(previous,current,resolution=1024):
    old={Path(f['file_path']).name:f for f in previous}
    new={Path(f['file_path']).name:f for f in current}
    if len(old)!=len(previous) or len(new)!=len(current) or old.keys()!=new.keys():
        raise ValueError('Require the exact same unique training image identities')
    for name,f in new.items():
        before=old[name]
        if f['physicalPanorama']==5 or any(f[k]!=before[k] for k in ['physicalPanorama','ring','yaw','pitch']):
            raise ValueError('Training center or view selection changed')
        if not np.array_equal(f['transform_matrix'],before['transform_matrix']):
            raise ValueError('Camera pose changed')
        if f['w']!=resolution or f['h']!=resolution:
            raise ValueError('Wrong actual training dimensions')
        for key in ['fl_x','fl_y','cx','cy']:
            if f[key]/resolution!=before[key]/before['w']:
                raise ValueError('Normalized camera intrinsics changed')


def prepare(job,baseline):
    start=time.monotonic();high=job/'inputs-hires'
    if not high.exists():P.prepare_inputs(high,1024)
    inputs=P.read(high/'report.json');native=P.read(baseline/'training-dense/job.json')
    if inputs['status']!='PASS' or inputs['resolution']!=1024 or native['status']!='PASS':
        raise ValueError('Require completed real1024 preparation and preserved native baseline')
    if P.sha(baseline/'training-dense/world/scene.ply')!=native['artifact']['sha256']:
        raise ValueError('Baseline native export changed')
    old=P.read(baseline/'inputs/transforms.json');transforms=P.read(high/'transforms.json')
    verify_frames(old['frames'],transforms['frames'])
    if len(transforms['frames'])!=96:raise ValueError('Require exact96 original training views')
    folder=job/'datasets/hires';folder.mkdir(parents=True,exist_ok=False)
    for name in ['images','masks']:(folder/name).mkdir()
    frames=[]
    for frame in transforms['frames']:
        name=Path(frame['file_path']).name
        for kind in ['images','masks']:
            path=high/kind/name
            with Image.open(path) as im:
                if im.size!=(1024,1024):raise ValueError('Image/mask dimensions disagree')
            shutil.copyfile(path,folder/kind/name)
        frames.append(dict(name=name,imageSha256=P.sha(folder/'images'/name),maskSha256=P.sha(folder/'masks'/name)))
    P.write(folder/'transforms.json',transforms)
    provenance=P.read(high/'provenance.json');provenance['notes']+=' Final same-data quality attempt: fresh1024 crops from the same original bytes, exact same camera poses/FOV and calibrated DAV2183124-point initialization. No depth reinference. Brush8k800kSH1seed42. No later same-data quality sweep.'
    P.write(folder/'provenance.json',provenance);shutil.copyfile(high/'LICENSE',folder/'LICENSE')
    seed=baseline/'datasets/dense/init.ply';shutil.copyfile(seed,folder/'init.ply')
    if P.sha(seed)!=P.sha(folder/'init.ply'):raise ValueError('Initialization changed')
    count=None
    with seed.open('rb') as stream:
        for _ in range(100):
            line=stream.readline().decode().strip()
            if line.startswith('element vertex '):count=int(line.split()[-1])
            if line=='end_header':break
    if count!=183124:raise ValueError('Expected the preserved183124-point initialization')
    # Common512 evaluation is deliberately retained. The native1024 data is separate.
    (job/'inputs').symlink_to((baseline/'inputs').resolve(),target_is_directory=True)
    (job/'training-baseline').symlink_to((baseline/'training-dense').resolve(),target_is_directory=True)
    report=dict(status='PASS',finishedAt=P.now(),elapsedSeconds=time.monotonic()-start,
        resolution=1024,trainingImages=96,physicalTrainingCenters=8,heldPhysicalPanorama=5,
        initialPoints=count,initialPlySha256=P.sha(seed),baselineSceneSha256=native['artifact']['sha256'],
        inputReportSha256=P.sha(high/'report.json'),sourceManifestSha256=inputs['sourceManifestSha256'],
        poseDocumentSha256=inputs['poseDocumentSha256'],frames=frames,
        meaning='Same physical sources/poses/FOV/DAV2 seed; fresh native1024 sampling, not upscaled512. No metric depth or independent geometry truth.')
    P.write(job/'preparation.json',report);print('PASS:96 native1024 training views; original seed/poses retained')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('--baseline',type=Path,default=P.ROOT/'data/jobs/street-conclusion-20261106')
    a=p.parse_args();prepare(a.job.resolve(),a.baseline.resolve())
