#!/usr/bin/env python3
"""Publish explicit adjacent-pair diagnostics, preserving earlier experiments."""
import argparse
import json
from pathlib import Path
import shutil
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def metric(label,value,unit='',precision=2):return dict(label=label,value=value,unit=unit,precision=precision)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('job',type=Path);parser.add_argument('--comparisons',type=Path);args=parser.parse_args();comparisons=args.comparisons or args.job
    out=PUBLIC/'experiments/panoramic-pair';out.mkdir(parents=True,exist_ok=False)
    provenance=read(ROOT/'scripts/samples/mapillary-beijing.json');models=[];times=[]
    jobs5={key:ROOT/f'data/jobs/panoramic-depth-{key}-20261106' for key in ['da2','dav2']}
    for key,title in [('da2','DA² · 구면 방사 거리'),('dav2','Depth Anything V2 Small · ERP 대조군')]:
        pair=read(comparisons/key/'pair.json');job4=args.job/f'{key}-4';job5=jobs5[key]
        if pair['status']!='PASS':raise ValueError('Require actually executed pair diagnostics')
        if pair['protocol'] != read(ROOT/'docs/evidence/panoramic-pair-protocol.json') or pair['commonCalibrationTracks']!=1001 or pair['commonWithheldTracks']!=217:
            raise ValueError('Narrative is audited for this fixed protocol only; update it for a new experiment')
        times.append(pair['finishedAt']);dest=out/key;dest.mkdir()
        for file in (comparisons/key).iterdir():
            if file.suffix in ['.png','.ply'] or file.name in ['cloud.json','pair.json']:shutil.copyfile(file,dest/file.name)
        for number,job in [('4',job4),('5',job5)]:shutil.copyfile(job/'geometry/range.png',dest/f'range-{number}.png')
        inf4=read(job4/'inference.json');inf5=read(job5/'inference.json');directions=[]
        for direction in pair['directions']:
            ident=direction['id'];first,second=ident.split('-to-');s=direction['summary'];regions={r['id']:r for r in direction['regions']}
            metrics=[metric('마스크 내 점 중 상대 사진의 유효 깊이가 있는 비율',s['candidateFraction']*100,'%'),
                metric('비교 표본 수',s['candidateSamples'],precision=0),
                metric('거리 차이 중앙값 / 상대 사진의 예측 거리',s['absoluteRelativeResidual']['median']*100,'%'),
                metric('거리 차이 상위 10% 경계',s['absoluteRelativeResidual']['p90']*100,'%'),
                metric('RGB 평균 절대 차이 · 0–255',s['rgbMeanAbsoluteError255']['mean']),
                metric('도로 후보 영역 · 상대 깊이 지원율',regions['road']['candidateFraction']*100,'%'),
                metric('건물·난간 후보 영역 · 상대 깊이 지원율',regions['facade']['candidateFraction']*100,'%'),
                metric('도로 후보 영역 · 거리 차이 중앙값',regions['road']['absoluteRelativeResidual']['median']*100,'%'),
                metric('건물·난간 후보 영역 · 거리 차이 중앙값',regions['facade']['absoluteRelativeResidual']['median']*100,'%')]
            notes=['거리 차이는 출발 점을 상대 카메라에서 본 방사 거리에서 상대 깊이 예측을 뺀 값입니다. 두 추정 간의 비교이며 실제 깊이 정답 오차가 아닙니다.',
                   f'{second}번의 실제 RGB를 기하 대응 위치에서 읽어 {first}번 사진의 픽셀 격자에 표시했습니다. 새 시점 사진을 생성한 것이 아닙니다. 검은 부분은 마스크 제외 또는 상대 깊이 미지원입니다.',
                   '거리 차이 그림: 흰색 0, 파랑은 상대 예측보다 앞, 빨강은 뒤. 사전 계산한 진단 기준 ±32.07%에서 색이 포화됩니다. 작은 차이도 중요할 수 있으므로 숫자와 함께 보세요.',
                   '분류 그림: 초록은 이 진단 범위 안, 파랑/빨강은 앞/뒤, 회색은 상대 깊이 미지원. 실제 가려짐이 확인됐다는 뜻은 아닙니다. 범위 밖 표본도 전체 오차 통계에 포함했습니다.',
                   '32.07% 기준은 공통 SfM 특징점의 약한 시차와 샘플링에서 계산한 진단용 값입니다. 너무 넓어서 정확도 합격선으로 쓸 수 없습니다.',
                   '같은 ERP 사각형을 두 사진에 적용하므로 같은 물리 표면만 비교한다는 보장은 없습니다. 영역별 상대 깊이 지원율도 함께 확인하세요.',
                   '도로·건물 영역은 결과를 보기 전 원본 사진에서 골랐습니다. 도로 영역에는 공통 SfM 점이 0개입니다. 건물·난간 영역은 4번 11개 / 5번 8개뿐이며 각각 약 3.86% / 4.64%의 진단 기준을 가집니다.']
            directions.append(dict(id=ident,title=f'{first}번 → {second}번 대응 검사',source=f'source-{first}.jpg',target=f'source-{second}.jpg',depth=f'{key}/range-{first}.png',warp=f'{key}/{ident}-warp.png',residual=f'{key}/{ident}-residual.png',mask=f'{key}/{ident}-classes.png',metrics=metrics,notes=notes))
        models.append(dict(id=key,title=title,status='PASS',qualityStatus='NOT ACCEPTED',meaning=inf4['outputMeaning'],cloud=f'{key}/cloud.json',ply=f'{key}/cloud.ply',
            metrics=[metric('새 4번 사진 · MPS 추론',inf4['inferenceSeconds'],' s',3),metric('5번 사진 · 앞선 실행 재사용',inf5['inferenceSeconds'],' s',3),metric('4번 점 수',pair['cloudPoints'][0],precision=0),metric('5번 점 수',pair['cloudPoints'][1],precision=0)],directions=directions,
            notes=['각 사진을 기존 SfM의 방사 거리 특징점으로 따로 보정했습니다. 두 점군은 좌표만 공유하며 ICP 정합, 평균화, 융합, 새 GS 학습은 하지 않았습니다.',
                   '공통 특징점 1,001개 중 217개는 두 사진의 보정에서 모두 제외했습니다. 그래도 같은 9장 사진으로 만든 SfM이므로 독립 검증 자료는 아닙니다.',
                   '하늘 위험 영역과 하단 표식을 제거한 앞선 마스크를 그대로 사용했습니다. 마스크의 일부가 실제 유효 건물과 나무를 제외합니다.',
                   '공통 건물·난간 특징점의 보정 제외점은 각 사진 1개뿐입니다. DAV2도 이 영역의 보정용 특징점과는 약 +42~46%의 거리 편향을 보입니다. 두 사진의 깊이가 비슷해도 맞는 거리라는 뜻은 아닙니다.',
                   '가까운 건물과 도로의 불일치를 따로 진단해야 합니다. 두 추정이 함께 틀리는 경우는 이번 비교로 찾지 못합니다.']))
    sources=[]
    for number,image_id,job in [('4','1677293342921360',args.job/'da2-4'),('5','679966948337536',jobs5['da2'])]:
        photo=next(x for x in provenance['images'] if x['image_id']==image_id)
        Image.open(job/'source.png').convert('RGB').save(out/f'source-{number}.jpg',quality=94)
        sources.append(dict(id=number,title=f'Beijing panorama {number} · Cicero101 / Mapillary',image=f'source-{number}.jpg',sourceUrl=photo['commons_page'],licenseUrl=provenance['licenseUrl']))
    summary=dict(completedAt=max(times),status='PASS',qualityStatus='NOT ACCEPTED',sources=sources,models=models,
        conclusion='두 파노라마의 공통 좌표 비교가 실행됐습니다. 전체 거리 차이는 중앙값 약 3.6–5.1%이지만, 도로·건물의 일치와 실제 정확도는 아직 검증되지 않았습니다. 아홉 장 융합이나 GS 학습으로 넘어가지 않습니다.',
        notes=['두 원본은 7680×3840, 작업 ERP는 1092×546입니다. 이전과 같은 모델·해상도·포즈·마스크를 유지했고 5번 추론은 재사용했습니다.',
               '공통 특징점의 두 카메라 간 시차 중앙값은 약 1.94°입니다. 1,001개 중 371개는 1° 미만이어서, 작은 화면 차이로 깊이를 정확히 구분하기 어렵습니다.',
               'DA²의 건물·난간 영역 불일치는 중앙값 약 10–14%, DAV2는 약 3.9–4.6%입니다. 이 한 쌍의 내부 결과만으로 모델 우열을 확정하지 않습니다.',
               '단일 파노라마 깊이 추론과 양방향 재투영 실행 PASS. 독립 기하 검증, 표면 최근접 거리 검사, 융합, GS 학습은 NOT RUN입니다.',
               '좌표·원본 해시·보정 기준·공통 보정 제외점·방향별 전체 통계는 모델별 pair.json에 기록했습니다. PLY는 출처별 점을 단순 연결한 일반 색상 점군입니다.'],
        nextStep='다음은 이 두 사진의 건물·도로를 대상으로 방향별 보정 편향과 카메라·파노라마 스티칭 오차를 분리하는 진단입니다. 같은 784개 공통 보정점만 사용한 대조군과 217개 제외점의 실제 특징점 재투영을 먼저 비교합니다. 이후 더 큰 시차나 원근 크롭 대조를 결정합니다.')
    write(out/'summary.json',summary)
    timeline=read(PUBLIC/'experiments/lab/timeline.json')
    if any(e['id']=='report-panoramic-pair' for e in timeline['entries']):raise ValueError('Report already published; preserve prior release')
    timeline['entries'].append(dict(id='report-panoramic-pair',title='파노라마 두 구 · 거리와 표면은 일치할까?',description='연속 사진 4·5의 깊이 점군을 공통 좌표에서 비교. 양방향 거리 차이·실제 RGB 재투영·출처별 표시.',createdAt=max(times),image='/experiments/panoramic-pair/source-4.jpg',href='/experiments/panoramic-pair/',kind='report',detail='P1 → P2 진단 · 실제 사진 2장 · 융합·GS 없음'))
    write(PUBLIC/'experiments/lab/timeline.json',timeline)
    spec=read(ROOT/'scripts/observation-worlds.json');files=[str(f.relative_to(PUBLIC)) for f in out.rglob('*') if f.is_file()]+['experiments/panoramic-pair/index.html'];spec['files']=list(dict.fromkeys(spec['files']+files));write(ROOT/'scripts/observation-worlds.json',spec)
    print(json.dumps(dict(report=str(out),files=len(files),timelineEntries=len(timeline['entries']))))

if __name__=='__main__':main()
