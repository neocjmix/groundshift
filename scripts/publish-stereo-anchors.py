#!/usr/bin/env python3
"""Publish selected licensed evidence, keeping raw inputs, arrays and logs local."""
import argparse
import importlib.util
from pathlib import Path
import shutil
from PIL import Image,ImageDraw

spec=importlib.util.spec_from_file_location('publish',Path(__file__).with_name('publish-perspective-overlap.py'))
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
read,write,metric=P.read,P.write,P.metric


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('job',type=Path);parser.add_argument('matching',type=Path);parser.add_argument('--sift-control',type=Path,required=True);parser.add_argument('--road',type=Path,required=True);args=parser.parse_args()
    report=read(args.job/'report.json')
    if report['status']!='PASS':raise ValueError('Require completed calibration experiment')
    if report['matchingReportSha256']!=__import__('hashlib').sha256((args.matching/'matching.json').read_bytes()).hexdigest():raise ValueError('Wrong matching job')
    output=P.PUBLIC/'experiments/stereo-anchors';output.mkdir(parents=True,exist_ok=False)
    sources=read(P.PUBLIC/'experiments/perspective-overlap/summary.json')['sources']
    control=read(args.sift_control/'report.json');road=read(args.road/'report.json')
    if control['status']!='PASS' or control['matchingReportSha256']!=report['matchingReportSha256'] or report['roadStereo']!=road or not report['roadStereoUsed']:raise ValueError('Require explicit SIFT-only and used wide stereo evidence')
    models=[];titles={'baseline':'기존 보정 유지','augmented':'기존 점 + SIFT + 도로 스테레오','new-only':'새 대응점만 · 도로 포함','sift-augmented':'대조군 · SIFT만 추가','sift-only':'대조군 · SIFT만 보정'}
    variants=[('augmented',args.job,report,'augmented'),('baseline',args.job,report,'baseline'),('new-only',args.job,report,'new-only'),('sift-augmented',args.sift_control,control,'augmented'),('sift-only',args.sift_control,control,'new-only')]
    for key,job,current,method in variants:
        result=current['results'][method]
        folder=output/key;folder.mkdir()
        for name in ['cloud.json','cloud.ply']:shutil.copyfile(job/method/name,folder/name)
        directions=[]
        for direction in result['directions']:
            ident=direction['id'];source=int(ident[0]);target=9-source
            for suffix in ['warp','residual']:shutil.copyfile(job/method/f'{ident}-{suffix}.png',folder/f'{ident}-{suffix}.png')
            for suffix in ['range','overlap']:shutil.copyfile(job/method/f'{source}-{suffix}.png',folder/f'{ident}-{suffix}.png')
            held=next(h for h in current['held'] if h['direction']==ident and h['region']=='all')['methods'][method]['projection']
            historical=next(h for h in current['historicalHeld'] if h['direction']==ident and h['parallaxMinimum']==0)['methods'][method]
            metrics=[metric('새 제외점 재투영 중앙값 · 512px 크롭',held['medianPixels'],'px'),metric('새 제외점 재투영 P90',held['p90Pixels'],'px'),metric(f'제외점 유효 / 전체{current["newHeldTracks"]}',held['validSamples']),
                metric('선택 출발 샘플',direction['selectedSourceSamples']),metric('상대 깊이 비교 가능',direction['candidateSamples']),
                metric('전체 거리 불일치 중앙값',direction['absoluteRelativeResidual']['median']*100,'%'),metric('전체 거리 불일치 P90',direction['absoluteRelativeResidual']['p90']*100,'%'),
                metric('이전217개 검사점 중 무효',historical['invalidSamples']),metric('이전 검사점 유효값 중앙값',historical['medianPixels'],'px')]
            for region,title in [('road','도로'),('facade','벽면·난간')]:
                r=direction['regions'][region];metrics.extend([metric(f'{title} 선택 샘플',r['selectedSourceSamples']),metric(f'{title} 비교 가능',r['candidateSamples']),metric(f'{title} 거리 불일치 중앙값',r['absoluteRelativeResidual']['median']*100 if r['absoluteRelativeResidual']['median'] is not None else None,'%'),metric(f'{title} RGB 차이 중앙값',r['rgbMeanAbsoluteError255']['median'])])
            directions.append(dict(id=ident,title=f'{source}번 → {target}번',source=sources[source-4]['image'],target=sources[target-4]['image'],depth=f'./{key}/{ident}-range.png',warp=f'./{key}/{ident}-warp.png',residual=f'./{key}/{ident}-residual.png',overlap=f'./{key}/{ident}-overlap.png',metrics=metrics,
                notes=[f'새 제외점은 실제 사진에서 찾은 대응점 중 보정에 쓰지 않은{current["newHeldTracks"]}개입니다. 카메라와 삼각측량도 같은 사진에서 얻었으므로 독립적인 실제 깊이 정답은 아닙니다.',
                    '도로 스테레오 포함 여부에 따라 제외점 집합도 다릅니다. SIFT만 쓴 대조군과 희소점 평균을 바로 비교하지 마세요. 동일 집합 안의 기존·새 보정 비교와 동일 픽셀의 조밀 비교는 실행 기록에 남겼습니다.',
                    '깊이·마스크·stride3·표시 카메라는 이전 실험과 동일합니다. 워프와 거리 차이는 3×3 최근접 표시입니다. 거리 차이 색은 ±32.07%에서 포화되며 가려짐 판정이 아닙니다.']))
        models.append(dict(id=key,title=titles[key],status='PASS',qualityStatus='NOT ACCEPTED',cloud=f'./{key}/cloud.json',ply=f'./{key}/cloud.ply',directions=directions,
            meaning={'baseline':'이전 수평 + 아래쪽 크롭의 깊이와 보정을 그대로 재현했습니다. 두 구면 지도와 마스크가 이전 파일과 일치함을 검사했습니다.',
                     'augmented':f'기존 학습점에 새 학습 대응점{report["newTrainingTracks"]}개를 추가했습니다. SIFT와512픽셀 범위 스테레오로 얻은 도로 근거를 함께 사용합니다. 깊이 모델·사진·카메라 위치는 그대로입니다.',
                     'new-only':'도로를 포함한 새 학습 대응점만 같은 보정식에 사용했습니다. 이번 실행에는 부족한 크롭의 기존 보정 대체가 필요 없었지만, 먼 영역에서 무효 깊이가 늘었습니다.',
                     'sift-augmented':'도로 후보가 부족했던 첫 대조군입니다. 기존 점 + SIFT 학습514개로 보정했습니다. 스테레오256픽셀 검색의 도로7개 후보는 제외했습니다.',
                     'sift-only':'첫 대조군에서 SIFT 학습514개만 보정에 사용했습니다. 도로 근거가 없어서 조밀 점군과 기존 검사점에서 악화가 나타났습니다.'}[key],
            metrics=[metric('표시 점 수',result['points']),*[metric(f'{s+4}번 선택 대역 유지율',pixels/220584*100,'%') for s,pixels in enumerate(result['selectedPixels'])]],
            notes=['SfM 임의 단위입니다. 위치 조정·ICP·점군 융합·새 Gaussian 학습은 실행하지 않았습니다.',
                   '좋은 희소점 지표가 전체 점군의 정확도를 보장하지 않습니다. 도로 근거를 추가해도 벽면과 먼 영역의 문제는 남습니다.']))
    evidence=[];folder=output/'matches';folder.mkdir()
    for group in report['matching']['groups']:
        name=group['id']+'-matches.jpg';shutil.copyfile(args.matching/name,folder/name)
        evidence.append(dict(title=group['id'],image='./matches/'+name,caption='실제 사진4·5번 · 초록=학습, 노랑=제외, 분홍=이전 제외점 근처라 학습 금지. 선이 그어졌다는 것만으로 참 대응이라고 확정하지 않습니다.'))
    road_tracks=read(args.road/'tracks.json')
    for source in [0,1]:
        with Image.open(P.PUBLIC/sources[source]['image'].lstrip('/')) as im:canvas=im.convert('RGB').resize((1092,546),Image.Resampling.LANCZOS)
        draw=ImageDraw.Draw(canvas)
        for row in road_tracks:
            u,v=row['uv'][source];x,y=u*1092-.5,v*546-.5;color=(255,210,40) if row['held'] else (40,240,175)
            draw.ellipse((x-2,y-2,x+2,y+2),fill=color)
        name=f'road-{source+4}-anchors.jpg';canvas.save(folder/name,quality=90)
        evidence.append(dict(title=f'도로 스테레오 후보 · {source+4}번',image='./matches/'+name,caption=f'검색 범위512에서 통과한{road["roadTracks"]}개 후보 · 구면 중복 제거 전 · 초록=학습 후보, 노랑=제외 후보 · 참 깊이 보증 아님'))
    summary=dict(heading='실제 대응점을 늘리면 깊이 보정이 좋아질까?',intro='두 실제 파노라마에서 특징점을 직접 매칭하고, 고정된 카메라 위치로3D 거리를 계산했습니다. 이 근거를 기존 깊이 보정에 추가한 경우와 새 근거만 쓴 경우를 비교합니다. 새 깊이 추론이나 생성 모델은 실행하지 않았습니다.',
        completedAt=report['finishedAt'],status='PASS',qualityStatus='NOT ACCEPTED',sources=sources,models=models,evidence=evidence,
        docHref='https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/STEREO_ANCHORS.md',
        conclusion='SIFT만 늘리는 보정은 충분하지 않았습니다. 도로 스테레오의 검색 범위를256→512픽셀로 늘려 후보291개를 얻은 뒤, 기존 보정에 추가하자 도로4→5 거리 불일치가2.43%→0.45%로 줄었습니다. 반대 방향은 거의 같았고, 벽면과 먼 영역의 문제는 남습니다.',
        notes=['일반 SIFT 검색:667개 고유 대응점,4번 도로0개. 도로 전용 약한 대비 검색을 추가:669개,학습514개·제외140개. 실제 촬영 위치는 두 곳 그대로입니다.',
               'SIFT는1024px 원근 크롭에서 양방향 비율 검사,재투영1px 이하,시차3도 이상,양쪽 양의 깊이 조건을 사용했습니다. 구면 광선 중복을 제거하고 사진4의 공간 타일 단위로 제외점을 나눴습니다.',
               '스테레오256픽셀 검색은 도로 후보7개로 근거 확보 FAIL이었습니다. 이전 깊이 가설로 범위를 진단하니 도로 이동량이대략280–394픽셀이라512로 확대했습니다. 깊이 예측은 매칭 입력이나 후보 거리 정답으로 쓰지 않았습니다.',
               f'검색512에서 도로 후보291개를 얻었습니다. SIFT와 구면 중복 제거 후 전체{report["uniqueTracks"]}개,학습{report["newTrainingTracks"]}개·제외{report["newHeldTracks"]}개입니다. 실제 촬영 위치는 두 곳입니다.',
               '도로 제외점은4번46개·5번13개입니다. 새 점만 보정하면 기존217개 검사점 중 한 방향47개가 무효가 됩니다. 새 점의 가까운 거리 분포가 먼 영역을 충분히 제약하지 못합니다.',
               '기존217개 제외점 근처0.5도 안의 새 점은 학습에서 제외했습니다. 공간적 보호 규칙이며 동일 물체의 정체성을 증명하는 것은 아닙니다.',
               '원본 사진,이전 최고 스쿠터,카메라,모델 예측,이전 실험은 보존했습니다.'],
        nextStep='다음은 제3시점 확인과 보정이 지원되는 거리·방향 구분입니다. 현재는 도로의 국소 개선이며,벽면·먼 영역을 해결하기 전9장 전체나 GS로 확대하지 않습니다.')
    write(output/'summary.json',summary)
    write(output/'measurements.json',{k:report[k] for k in ['status','qualityStatus','startedAt','finishedAt','elapsedSeconds','maxResidentSetBytes','protocolSha256','implementationSha256','uniqueTracks','newTrainingTracks','newHeldTracks','roadStereoUsed','fits','held','historicalHeld','results','paired','depthInference','fusion','gaussianTraining','geometryAcceptance']})
    write(output/'sift-control-measurements.json',{k:control[k] for k in ['status','elapsedSeconds','maxResidentSetBytes','held','historicalHeld','results','paired','newTrainingTracks','newHeldTracks']})
    shutil.copyfile(P.PUBLIC/'experiments/perspective-overlap/ATTRIBUTION.txt',output/'ATTRIBUTION.txt')
    with (output/'ATTRIBUTION.txt').open('a') as stream:stream.write('Additional changes: observed SIFT correspondence overlays and fixed-pose stereo/calibration diagnostics.\n')
    timeline=read(P.PUBLIC/'experiments/lab/timeline.json')
    if any(e['id']=='report-stereo-anchors' for e in timeline['entries']):raise ValueError('Preserve earlier publication')
    timeline['entries'].append(dict(id='report-stereo-anchors',title='실제 대응점 · 도로 검색 범위 교정',description='스테레오 범위256→512로 도로 후보291개 확보. 국소 개선과 실패 대조군을 함께 봅니다.',image='/experiments/stereo-anchors/matches/road-4-anchors.jpg',href='/experiments/stereo-anchors/',kind='report',createdAt=report['finishedAt'],detail='CPU 실행 · 실제 촬영2곳 · 보정 대조군5개 · 새 GS 없음'))
    write(P.PUBLIC/'experiments/lab/timeline.json',timeline)
    spec=read(P.ROOT/'scripts/observation-worlds.json');files=[str(p.relative_to(P.PUBLIC)) for p in output.rglob('*') if p.is_file()]+['experiments/stereo-anchors/index.html'];spec['files']=list(dict.fromkeys(spec['files']+files));write(P.ROOT/'scripts/observation-worlds.json',spec)
    print('Local report files',len(files),'timeline',len(timeline['entries']))


if __name__=='__main__':main()
