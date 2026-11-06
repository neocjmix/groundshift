#!/usr/bin/env python3
"""Append real model trials to the existing observation catalog; never replace."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import numpy as np
from PIL import Image

spec=importlib.util.spec_from_file_location('prepare',Path(__file__).with_name('prepare-street.py'))
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
read,write=P.read,P.write
ROOT=P.ROOT;PUBLIC=ROOT/'public'
TITLES={'dav2':'DAV2 · 이전 최고 기준','panda':'PanDA-Small · 구면 깊이','da2':'DA² · 구면 깊이','moge':'MoGe-2 Small · 단안 기하','da3':'DA3-Small · 여러 시점 공동 추정','depthmaster':'DepthMaster · 구면 공동 추정'}
TITLES['panda-supported']='PanDA-Small · 초근접 이상점 제외'
MEANINGS={'dav2':'앞선 street-dense의 실제 학습 산출물을 그대로 재사용하고 이번에 같은 카메라에서 다시 렌더했습니다. 재학습하지 않았습니다.',
          'panda':'파노라마 전체의 상대 방사 깊이를 사진별 scale+offset으로 보정했습니다.',
          'da2':'파노라마 전체의 방사 깊이를 사진별 scale로 보정했습니다.',
          'moge':'실제 90° 시야각을 입력한 단안 점 지도로 camera-Z를 얻고 크롭별 scale을 보정했습니다.',
          'da3':'같은 방향을 보는 8개 실제 촬영 위치를 함께 입력했습니다. 기존 카메라 위치를 조건으로 주고, 방향별 공동 scale을 보정했습니다.',
          'depthmaster':'한 촬영 위치의 6개 큐브 면을 함께 처리해 구면 깊이를 얻고, 사진별 scale을 보정했습니다.'}
MEANINGS['panda-supported']=MEANINGS['panda']+' 첫 학습이22분 후 중단돼, 추정 카메라에 극단적으로 가까운 초기 점을 제외한 한 번의 재시도입니다. 같은 모델·원시 깊이·보정·초기 점 수를 사용합니다. 제외 기준은 실측 빈 공간이 아닙니다.'


def main(a):
    job=a.job.resolve();decision=read(a.decision);evaluation=read(job/'evaluation/report.json');config=read(job/'render-config.json');metrics=read(job/'evaluation/view-metrics.json')
    if evaluation['status']!='PASS':raise ValueError('Require actual completed renders and measurements')
    ids=[m['id'] for m in evaluation['models']]
    if decision.get('best') not in ids or not decision.get('completedAt') or any(not decision['modelQuality'].get(i) for i in ids):
        raise ValueError('Require reviewed recommendation, completed time and quality notes before any publication mutation')
    for ident in ids:
        native=read(job/('training-'+ident)/'job.json')
        if ident not in TITLES or native['status']!='PASS' or P.sha(job/('training-'+ident)/'world/scene.ply')!=native['artifact']['sha256']:
            raise ValueError('Unverified native export before publication')
    out=PUBLIC/'experiments/model-selection';out.mkdir(parents=True,exist_ok=False)
    for name in ['renders','reference','videos','initialization','depth']:(out/name).mkdir()
    catalog=read(PUBLIC/'worlds/catalog.json');timeline=read(PUBLIC/'experiments/lab/timeline.json');allow=read(ROOT/'scripts/observation-worlds.json')
    models=[];new_worlds=[]
    for native in evaluation['models']:
        ident=native['id'];baseline=ident=='dav2';slug='street-model-'+ident
        if not baseline and any(m['id']==slug for m in catalog['scenes']):raise ValueError('Existing world would be replaced')
        original=job/('training-'+ident)/'world'
        job_record=read(job/('training-'+ident)/'job.json')
        if job_record['status']!='PASS' or P.sha(original/'scene.ply')!=job_record['artifact']['sha256']:raise ValueError('Native artifact mismatch')
        world_path='/worlds/street-dense/world.json' if baseline else f'/worlds/{slug}/world.json'
        preview='/worlds/street-dense/preview.jpg' if baseline else f'/worlds/{slug}/preview.jpg'
        init='../street/initialization/dense.ply' if baseline else f'./initialization/{ident}.ply'
        title=TITLES[ident];quality=decision['modelQuality'][ident]
        if not baseline:
            src=job/'presentation'/ident;metadata=read(src/'world.json');metadata.update(id=slug,title='거리 모델 · '+title)
            metadata['provenance']['notes']=f'Locally reconstructed from licensed real Mapillary panoramas using {ident} depth initialization and Brush/Metal. Eight training centers,96 real crops. Panorama5 RGB excluded from inference, seed colors and GS training; all-nine SfM geometry reused. No generated intermediate images. Quality: {quality}. Details /experiments/model-selection/. Arbitrary units, no measured metric geometry.'
            dest=PUBLIC/'worlds'/slug;dest.mkdir(parents=True,exist_ok=False)
            shutil.copyfile(original/'scene.ply',dest/'scene.ply');write(dest/'world.json',metadata);shutil.copyfile(src/'cameras.json',dest/'cameras.json');shutil.copyfile(job/'inputs/LICENSE',dest/'SOURCE_LICENSE')
            Image.open(job/'renders'/ident/'held-5-level-300.png').convert('RGB').save(dest/'preview.jpg',quality=91)
            curated=job/'public-worlds'/slug/'world';shutil.copytree(dest,curated)
            new_worlds.append(dict(id=slug,source=str(curated.relative_to(ROOT)),asset='scene.ply',format='ply',credits=['SOURCE_LICENSE']))
            shutil.copyfile(job/'datasets'/ident/'init.ply',out/'initialization'/(ident+'.ply'))
            catalog['scenes'].append(dict(id=slug,title=metadata['title'],description=MEANINGS[ident],category='experiment',manifestPath=world_path,thumbnailPath=preview,createdAt=job_record['finishedAt'],detail=f'8개 실제 위치 · 8,000 Metal 단계 · {quality}'))
            timeline['entries'].append(dict(id=slug,title=metadata['title'],description=MEANINGS[ident],image=preview,href='/?world='+world_path,kind='scene',createdAt=job_record['finishedAt'],detail=f'{title} · {quality}'))
        rendered=out/'renders'/ident;rendered.mkdir()
        for camera in config['cameras']:
            if camera['kind']!='path':shutil.copyfile(job/'renders'/ident/(camera['id']+'.png'),rendered/(camera['id']+'.png'))
        shutil.copyfile(job/'evaluation/videos'/(ident+'.mp4'),out/'videos'/(ident+'.mp4'))
        points=183124 if baseline else read(job/('fusion-'+ident)/'report.json')['points']
        models.append({**native,'title':title,'meaning':MEANINGS[ident],'quality':quality,'world':world_path,'preview':preview,'video':f'./videos/{ident}.mp4','init':init,'points':points})
    if decision['best'] not in [m['id'] for m in models]:raise ValueError('Recommendation must be actually rendered')
    shutil.copyfile(job/'evaluation/videos/comparison.mp4',out/'videos/comparison.mp4')
    if (job/'datasets/panda/init.ply').exists():shutil.copyfile(job/'datasets/panda/init.ply',out/'initialization/panda-original.ply')
    views=[]
    for c in config['cameras']:
        if c['kind']=='path':continue
        item=dict(id=c['id'],kind=c['kind'],title=f'{c["physicalPanorama"]}번 · {c["ring"]} {c["yaw"]}°')
        if c['kind']=='offpath':item['title']='관측 없는 경로 옆 · '+c['id']
        if c.get('reference'):
            shutil.copyfile(c['reference'],out/'reference'/(c['id']+'.png'));item['source']='./reference/'+c['id']+'.png'
        views.append(item)
    evidence=[]
    for ident in ['panda','da3','moge','da2','depthmaster']:
        inference=job/ident/'report.json'
        if not inference.exists() or read(inference)['status']!='PASS':continue
        ir=read(inference);name='p04.png' if ir['convention'].endswith('radial') else 'p04-level-300.png'
        target=out/'depth'/(ident+'.png');shutil.copyfile(job/ident/name,target)
        evidence.append(dict(title=TITLES[ident]+' · 원시 깊이',image='./depth/'+target.name,caption='원시 예측의 이미지별2–98분위 시각화. 모델 간 밝기가 같은 거리라는 뜻이 아닙니다. '+ir['convention']))
    sources=read(PUBLIC/'experiments/street/summary.json')['sources']
    summary=dict(status='PASS',completedAt=decision['completedAt'],best=decision['best'],verdict=decision['verdict'],models=models,views=views,metrics=metrics,stages=decision['stages'],candidates=decision['candidates'],notes=decision['notes'],depthEvidence=evidence,sources=sources,comparisonVideo='./videos/comparison.mp4',comparisons=evaluation['comparisons'])
    write(out/'summary.json',summary)
    (out/'ATTRIBUTION.txt').write_text('Photographs: Cicero101 / Mapillary via Wikimedia Commons, CC BY-SA4.0. https://creativecommons.org/licenses/by-sa/4.0/\nChanges: perspective crops, depth visualizations, locally calibrated initialization, Brush Gaussian training and actual browser renders. No diffusion or generated training images. Model checkpoint/source licenses and actual statuses: docs/MODEL_SELECTION.md. Weights, originals and raw logs remain local.\n')
    timeline['entries'].append(dict(id='report-model-selection',title='거리 모델 비교 · 같은 거리, 다른 모델',description=decision['verdict']['summary'],image=next(m['preview'] for m in models if m['id']==decision['best']),href='/experiments/model-selection/',kind='report',createdAt=decision['completedAt'],detail=f'{len(models)-1}개 새 GS + 이전 최고 기준 · 후보·실패·이동 영상'))
    write(PUBLIC/'worlds/catalog.json',catalog);write(PUBLIC/'experiments/lab/timeline.json',timeline)
    allow['worlds']+=new_worlds;files=[str(p.relative_to(PUBLIC)) for p in out.rglob('*') if p.is_file()]+['experiments/model-selection/index.html']
    allow['files']=list(dict.fromkeys(allow['files']+files));write(ROOT/'scripts/observation-worlds.json',allow)
    print('Published locally',len(new_worlds),'new worlds;',len(files),'report files')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('job',type=Path);parser.add_argument('--decision',type=Path,required=True);main(parser.parse_args())
