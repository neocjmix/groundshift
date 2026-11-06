#!/usr/bin/env python3
"""Expose only licensed selected diagnostic outputs through the existing lab."""
import argparse
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def metric(label,value,unit='',precision=3):return dict(label=label,value=value,unit=unit,precision=precision)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('job',type=Path);args=parser.parse_args()
    report=read(args.job/'report.json')
    if report['status']!='PASS' or report['inference']['status']!='PASS':raise ValueError('Require actual inference and completed analysis')
    output=PUBLIC/'experiments/perspective-overlap';output.mkdir(parents=True,exist_ok=False)
    source=read(PUBLIC/'experiments/panoramic-pair/summary.json')['sources']
    for item in source:
        if not item['image'].startswith('/'):item['image']='/experiments/panoramic-pair/'+item['image']
    titles={'best':'수평 + 아래쪽 크롭','consensus':'크롭 불일치 제거 후','level':'수평 크롭만','erp':'기존 ERP 깊이 대조군'}
    meanings={'best':'실제 원본을 수평 6개·아래쪽 6개 방향으로 나누고 각각 DAV2 깊이를 보정했습니다. 각 구면 광선에서 가장 중앙을 보는 크롭 하나를 선택합니다. 물리적 촬영 위치는 여전히 두 곳입니다.',
        'consensus':'두 개 이상 크롭이 보며, 크롭 간 거리의 로그 범위가 이전 희소점 참고값 이하인 곳만 남겼습니다. 남은 점의 정확성을 보증하지 않습니다.',
        'level':'기존 수평 6개 크롭씩을 재사용했습니다. 도로 검사 영역을 보지 못하므로 그 영역의 비교는 NOT RUN입니다.',
        'erp':'앞선 공통 784개 특징점으로 보정한 원본 ERP DAV2 깊이입니다. 카메라·작업 해상도·마스크·표시 시점은 이번 대조군과 같습니다.'}
    models=[]
    for key in ['best','consensus','level','erp']:
        folder=output/key;folder.mkdir();result=report['results'][key]
        for name in ['cloud.json','cloud.ply']:shutil.copyfile(args.job/key/name,folder/name)
        directions=[]
        for item in result['directions']:
            ident=item['id'];source_id=int(ident[0]);c=report['coverage'][source_id-4]
            for suffix in ['warp','residual','mask']:shutil.copyfile(args.job/key/f'{ident}-{suffix}.png',folder/f'{ident}-{suffix}.png')
            shutil.copyfile(args.job/f'{key}-{source_id}-range.png',folder/f'{ident}-range.png')
            d=dict(id=ident,title=f'{source_id}번 → {9-source_id}번',source=source[source_id-4]['image'],target=source[5-source_id]['image'],
                depth=f'./{key}/{ident}-range.png',warp=f'./{key}/{ident}-warp.png',residual=f'./{key}/{ident}-residual.png',mask=f'./{key}/{ident}-mask.png',
                metrics=[metric('선택한 출발 샘플',item['selectedSourceSamples']),metric('상대 사진 깊이와 비교 가능',item['candidateSamples']),
                    metric('비교 미지원 샘플',item['unsupportedTargetSamples']),metric('전체 방사 거리 불일치 중앙값',None if item['absoluteRelativeResidual']['median'] is None else item['absoluteRelativeResidual']['median']*100,'%'),
                    metric('RGB 차이 중앙값 · 0–255',item['rgbMeanAbsoluteError255']['median'])],
                notes=['범위 v=.48–.85, stride3. 워프·거리 차이·마스크는 3×3 최근접 표시이며 보간된 증거가 아닙니다.',
                    '거리 차이는 (출발 점의 도착 광선 거리 − 도착 예측 거리) / 도착 예측 거리입니다. ±32.07%에서 색이 포화됩니다. 초록은 참고값 이내, 파랑은 앞, 빨강은 뒤, 회색은 상대 깊이 미지원입니다. 가려짐으로 확정하지 않습니다.',
                    '검은 깊이 영역은 제외·미지원입니다. 거리 색 범위는 촬영 위치별 SfM 학습 거리 P99이며 단계 간 동일합니다. 도로에는 보정용 공통 희소점이 없습니다.'])
            for region,title in [('road','도로'),('facade','벽면·난간')]:
                r=item['regions'][region]
                total='1,881' if region=='road' else '992'
                d['metrics'] += [metric(f'{title} 선택 / ROI 격자 {total}',r['selectedSourceSamples']),metric(f'{title} 비교 가능',r['candidateSamples']),
                    metric(f'{title} 거리 불일치 중앙값',None if r['absoluteRelativeResidual']['median'] is None else r['absoluteRelativeResidual']['median']*100,'%'),
                    metric(f'{title} RGB 차이 중앙값',r['rgbMeanAbsoluteError255']['median'])]
            if key in ['best','consensus']:
                shutil.copyfile(args.job/f'overlap-{source_id}.png',folder/f'{ident}-overlap.png');d['overlap']=f'./{key}/{ident}-overlap.png'
                d['notes'].append(f"같은 중심의 크롭 간 log 거리 범위 참고값 {report['protocol']['logDiagnosticBand']:.6f}. 보정 정확도가 아닌 불일치 검사입니다. 원본 대역 픽셀 {c['bandPixels']:,}개 중 {c['selected'][key]:,}개가 남았습니다.")
            directions.append(d)
        models.append(dict(id=key,title=titles[key],status='PASS',qualityStatus='NOT ACCEPTED',meaning=meanings[key],cloud=f'./{key}/cloud.json',ply=f'./{key}/cloud.ply',directions=directions,
            metrics=[metric('두 출처 표시 점 수',result['points']),*[metric(f'{c["panorama"]}번 대역 픽셀 유지율',c['selected'][key]/c['bandPixels']*100,'%') for c in report['coverage']]],
            notes=['두 점군의 좌표를 겹쳐 표시합니다. 융합·ICP·위치 조정·Gaussian 학습은 실행하지 않았습니다.',
                   '필터를 통과한 벽면도 RGB 불일치가 남으며, 필터 후 일부 비교는 더 나쁩니다. 서로 비슷한 예측도 함께 틀릴 수 있습니다.']))
    summary=dict(heading='원근 사진으로 나누면, 도로까지 이어질까?',intro='같은 두 파노라마를 수평과 아래쪽 원근 사진으로 나눠 깊이를 추정했습니다. 수평만 쓴 경우, 아래쪽을 추가한 경우, 서로 다른 깊이를 말하는 크롭을 제거한 경우를 비교합니다. 원본 사진의 재투영이며 중간 이미지 생성은 없습니다.',
        docHref='https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/PERSPECTIVE_OVERLAP.md',maskCaption='출발 ERP 격자 · 깊이 차이 참고값 분류와 미지원 영역 · 관측된 가려짐이나 정확도 판정 아님',
        completedAt=report['finishedAt'],status='PASS',qualityStatus='NOT ACCEPTED',sources=source,models=models,
        conclusion='아래쪽 크롭으로 도로가 채워졌고, 도로의 두 시점 거리 불일치는 줄었습니다. 그러나 크롭 불일치 필터가 벽면을 많이 지웠고, 남은 영역도 항상 좋아지지는 않았습니다. 거리 전체를 합칠 준비가 끝난 것은 아닙니다.',
        notes=['DAV2 Small을 로컬 M2 Metal/MPS에서 새 아래쪽 크롭 12장에 실제 실행했습니다. 기존 수평 12장 예측·고정 리그 카메라·스쿠터 결과는 보존했습니다.',
            '깊이는 카메라-Z로 보정한 뒤 단위 광선의 Z성분으로 나눠 방사 거리로 바꿨습니다. SfM 임의 단위이며 미터가 아닙니다.',
            '한 촬영 위치의 크롭들은 같은 광선을 공유합니다. 이들 간 깊이 차이는 촬영 위치 이동에 따른 가려짐으로 설명할 수 없습니다. 파노라마 스티칭·모델·보정 오류는 남을 수 있습니다.',
            '도로는 희소 보정점 범위 밖입니다. 내부 비교 개선은 실제 거리의 정확성이나 독립적인 형상 검증을 뜻하지 않습니다.',
            '표시 단계별 대상 픽셀이 다르므로 평균만 비교하지 마세요. 동일 출발 픽셀·양쪽 깊이 유효 샘플 비교도 실행 기록에 남겼습니다.'],
        nextStep='다음은 실제 추가 관측이나 도로·벽면의 다중 시점 대응으로 지역별 보정을 제약하는 작은 실험입니다. 크롭 불일치 제거만으로 9장 융합이나 전체 거리 GS로 확대하지 않습니다.')
    write(output/'summary.json',summary)
    write(output/'measurements.json',{k:report[k] for k in ['status','qualityStatus','startedAt','finishedAt','elapsedSeconds','maxResidentSetBytes','protocolSha256','inferenceReportSha256','coverage','results','pairedBestVersusErp','downwardTrainingCounts']})
    shutil.copyfile(PUBLIC/'experiments/panoramic-calibration/ATTRIBUTION.txt',output/'ATTRIBUTION.txt')
    with (output/'ATTRIBUTION.txt').open('a') as stream:stream.write('Additional changes: downward perspective crops, per-crop camera-Z calibration, spherical selection, disagreement filtering and diagnostic maps.\n')
    timeline=read(PUBLIC/'experiments/lab/timeline.json')
    if any(e['id']=='report-perspective-overlap' for e in timeline['entries']):raise ValueError('Do not overwrite previous experiment')
    timeline['entries'].append(dict(id='report-perspective-overlap',title='원근 깊이 · 도로와 크롭 겹침',description='수평·아래쪽·불일치 제거·ERP 대조군을 같은 좌표에서 비교합니다.',image='/experiments/perspective-overlap/best/4-to-5-range.png',href='/experiments/perspective-overlap/',kind='report',createdAt=report['finishedAt'],detail='두 실제 촬영 위치 · M2 MPS 실행 · 새 GS 없음'))
    write(PUBLIC/'experiments/lab/timeline.json',timeline)
    spec=read(ROOT/'scripts/observation-worlds.json');files=[str(p.relative_to(PUBLIC)) for p in output.rglob('*') if p.is_file()]+['experiments/perspective-overlap/index.html'];spec['files']=list(dict.fromkeys(spec['files']+files));write(ROOT/'scripts/observation-worlds.json',spec)
    print('Published local assets:',len(files),'timeline:',len(timeline['entries']))


if __name__=='__main__':main()
