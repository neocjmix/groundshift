#!/usr/bin/env python3
"""Publish an explicit one-ERP observation set; keep raw logs/weights/paths local."""
import argparse
import json
from pathlib import Path
import shutil

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'

def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('da2',type=Path);p.add_argument('dav2',type=Path);args=p.parse_args()
    out=PUBLIC/'experiments/panoramic-depth';out.mkdir(parents=True,exist_ok=True)
    source=read(ROOT/'scripts/samples/mapillary-beijing.json');photo=next(x for x in source['images'] if x['image_id']=='679966948337536')
    records=[];times=[]
    for key,title,job in [('da2','DA² · 구면 방사 거리',args.da2),('dav2','Depth Anything V2 Small · ERP 대조군',args.dav2)]:
        inference=read(job/'inference.json');geo=read(job/'geometry/geometry.json')
        if inference['status']!='PASS' or geo['status']!='PASS':raise ValueError('This publisher requires real completed inference and geometry diagnostics')
        dest=out/key;dest.mkdir(exist_ok=True)
        for name in ['range.png','mask.png','cloud.json','cloud-all.json','cloud.ply','cloud-all.ply']:
            shutil.copyfile(job/'geometry'/name,dest/name)
        shutil.copyfile(job/'depth.png',dest/'depth.png');times.append(geo['finishedAt'])
        diagnostics={name:geo[name] for name in ['calibration','heldOut','coverageFraction','solidAngleCoverageFraction','validFraction','points','filteredSeam','anchorCoverage','maskPolicy','selfReprojection']}
        write(dest/'diagnostics.json',diagnostics)
        records.append(dict(id=key,title=title,status='PASS',meaning=inference['outputMeaning'],inferenceSeconds=inference['inferenceSeconds'],
            rawDepth=f'{key}/depth.png',rangeDepth=f'{key}/range.png',mask=f'{key}/mask.png',cloud=f'{key}/cloud.json',fullCloud=f'{key}/cloud-all.json',ply=f'{key}/cloud.ply',diagnostics=diagnostics,
            notes=['미터가 아닌 기존 SfM의 임의 단위로 보정했습니다. 같은 사진들에서 추정한 점들과의 내부 비교입니다.',
                   '보정에 쓴 점 1,195개와 보정에서 제외한 점 326개를 분리했습니다. 독립적인 실제 깊이 정답은 없습니다.',
                   '추론 PASS는 기하 정확도 PASS가 아닙니다. 위·아래 극점은 보정 점이 없고, 좌우 경계에도 불연속이 남습니다.',
                   'DA²는 거리 배율 1개를, DAV2는 역거리의 배율·절편 2개를 맞췄으므로 오차 숫자만으로 모델 우열을 확정할 수 없습니다.']))
    Image.open(args.da2/'source.png').convert('RGB').save(out/'source.jpg',quality=94)
    summary=dict(completedAt=max(times),source=dict(title='Beijing panorama 5 · Cicero101 / Mapillary',sourceUrl=photo['commons_page'],licenseUrl=source['licenseUrl'],originalSize=[7680,3840],workingSize=[1092,546]),
                 baseline=dict(href='/experiments/object-real/'),models=records,p1ReadyForPair='diagnostic-only',
                 notes=['하나의 실제 파노라마에서 구면 전체 깊이 추론을 실행했습니다. 새 GS 학습, 생성 이미지, 여러 파노라마의 융합은 하지 않았습니다.',
                        '상단 하늘 위험 영역과 하단 노란 표식을 보수적으로 제외하므로 위쪽 건물·나무도 일부 사라집니다. 이 마스크는 물체 분할이나 모델 신뢰도가 아닙니다.',
                        '점군은 가로·세로 3픽셀 간격으로 샘플링했습니다. 좌표는 기존 고정 리그의 추정 포즈에서 왔고, 스쿠터 전용 SfM 좌표계와는 다릅니다.',
                        '다음은 인접한 두 파노라마의 표면·재투영 일치 여부를 확인하는 진단입니다. 전역적으로 일관된 거리 점군이나 GS 학습 준비가 검증된 것은 아닙니다.',
                        'PanDA-Small은 코드·체크포인트·인터페이스를 조사했지만 이번 실행에서는 NOT RUN입니다.'])
    write(out/'summary.json',summary)
    timeline=read(PUBLIC/'experiments/lab/timeline.json');timeline['entries']=[e for e in timeline['entries'] if e['id']!='report-panoramic-depth']
    timeline['entries'].append(dict(id='report-panoramic-depth',title='파노라마 한 구 · 전체 방향 깊이와 점군',description='DA²와 DAV2를 같은 실제 360도 사진에 실행. 구면 깊이·보정·색상 점군을 비교합니다.',createdAt=max(times),image='/experiments/panoramic-depth/source.jpg',href='/experiments/panoramic-depth/',kind='report',detail='P0 + P1 · 실제 ERP 1장 · GS 학습 없음'))
    write(PUBLIC/'experiments/lab/timeline.json',timeline)
    spec=read(ROOT/'scripts/observation-worlds.json');files=[str(f.relative_to(PUBLIC)) for f in out.rglob('*') if f.is_file()]+['experiments/panoramic-depth/index.html'];spec['files']=list(dict.fromkeys(spec['files']+files));write(ROOT/'scripts/observation-worlds.json',spec)
    print(json.dumps(dict(report=str(out),files=len(files),models=[x['id'] for x in records],timelineEntries=len(timeline['entries']))))

if __name__=='__main__':main()
