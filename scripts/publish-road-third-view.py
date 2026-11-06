#!/usr/bin/env python3
"""Publish selected CC BY-SA derived evidence; retain raw arrays and logs locally."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import numpy as np
from spherical_depth import sample_erp_bilinear
from PIL import Image

spec=importlib.util.spec_from_file_location('publisher',Path(__file__).with_name('publish-perspective-overlap.py'))
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('job',type=Path);parser.add_argument('evaluation',type=Path);args=parser.parse_args()
    import hashlib
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=P.read(args.job/'report.json');evaluation=P.read(args.evaluation/'report.json')
    if report['status']!='PASS' or evaluation['status']!='PASS' or evaluation['stereoReportSha256']!=sha(args.job/'report.json') or report['tracksSha256']!=sha(args.job/'tracks.json'):
        raise ValueError('Require matching completed experiment and evaluation')
    output=P.PUBLIC/'experiments/road-third-view';output.mkdir(parents=True,exist_ok=False)
    names=['source-4.jpg','source-5.jpg','source-6.jpg','third-overlay.jpg','track-examples.jpg','previous45.ply','observed56.ply']
    for name in names:shutil.copyfile(args.job/name,output/name)
    manifest=P.read(P.ROOT/'scripts/samples/mapillary-beijing.json'); sources=[]
    for n, item in zip([4,5,6],manifest['images'][3:6]):
        sources.append(dict(id=str(n),image=f'./source-{n}.jpg',title=f'{n}번 · 실제 촬영 사진',sourceUrl=item['commons_page'],licenseUrl=manifest['licenseUrl'],sha256=item['sha256'],imageId=item['image_id']))
    tracks=P.read(args.job/'tracks.json');xyz=[];colors=[];kinds=[];common=[]
    with Image.open(args.job/'source-5.jpg') as im:pixels=np.asarray(im.convert('RGB'))
    # Both reconstructions use unchanged world coordinates. No alignment or fusion.
    for kind in [0,1]:
        for row in tracks:
            if kind==1 and row['status']!='supported':continue
            xyz.append(row['oldXyz'] if kind==0 else row['primary']['xyz'])
            uv=row['oldUv'][1]
            color=sample_erp_bilinear(pixels,np.array(uv[0]*pixels.shape[1]-.5),np.array(uv[1]*pixels.shape[0]-.5))
            colors.append(np.clip(color,0,255).astype(int).tolist());kinds.append(kind);common.append(row['status']=='supported')
    P.write(output/'cloud.json',dict(positions=np.asarray(xyz).ravel().tolist(),colors=np.asarray(colors).ravel().tolist(),kinds=kinds,common=common,
        up=(-np.asarray(report['worldFromPanorama']['5'])[:3,1]).tolist(),coordinateFrame='fixed-rig-sfm-20261104',units='SfM arbitrary; not meters',meaning='Old4/5 triangulations and independently matched5/6 triangulations. No pose refinement, fusion or Gaussian training. Overview camera is a display choice.'))
    P.write(output/'summary.json',dict(completedAt=evaluation['finishedAt'],status=report['status'],qualityStatus=report['qualityStatus'],
        heading='도로의 점, 세 번째 사진에서도 이어질까?',
        conclusion=f'{report["totalTracks"]}개 중{report["supportedTracks"]}개를 실제5·6번 사진에서 다시 확인했습니다. 확인된 점은 잘 이어졌지만 나머지{report["unsupportedTracks"]}개는 판단하지 못했습니다. 거리 전체를 합칠 근거로는 부족합니다.',
        sources=sources,stereo=report,evaluation=evaluation,
        notes=['새 매칭은 실제5·6번 RGB와 기존 카메라만 사용합니다. 4·5번의3D 점이나 학습된 깊이는 매칭 입력이 아닙니다.',
               '44개는 전체291개의15.1%입니다. 실패·미지원247개를 제외한 뒤 전체가 잘 맞았다고 해석하면 안 됩니다.',
               '사전에 광선 방향으로 크롭 하나를 선택했습니다. 다른 크롭까지 찾으면86개에서 지원되지만, 좋은 오차를 골라 주 결과를 바꾸지 않았습니다.',
               '세 번째 RGB는 이전 보정에 쓰지 않았지만 카메라 자세는9장 전체에서 함께 추정했습니다. 독립적인 실측 깊이 정답이 아닙니다.',
               '기존·새 보정 모두44개 중5개의 깊이는 마스크 또는 보간 이웃 때문에 무효입니다.39개 공통 유효점과 그중 이전 제외점6개만 별도로 비교합니다.',
               '새 점만 사용한 보정은 이 작은 영역에서 좋아 보여도 앞선 실험의 먼 영역 무효47개 문제가 남습니다. 거리 전체의 최선이라는 뜻이 아닙니다.',
               '새 깊이 추론·보정 학습·위치 수정·융합·Gaussian 학습은 실행하지 않았습니다. 기존 스쿠터와 모든 이전 실험은 보존했습니다.'],
        nextStep='다음은 미지원 도로의 원인과 벽면·먼 영역을 따로 검사하고, 보정이 지원되는 방향·거리만 표시하는 것입니다.9장 전체 융합은 아직 보류합니다.'))
    P.write(output/'track-diagnostics.json',tracks)
    (output/'ATTRIBUTION.txt').write_text('Cicero101 / Mapillary via Wikimedia Commons. CC BY-SA 4.0.\nhttps://creativecommons.org/licenses/by-sa/4.0/\nChanges: resized panorama previews, projected track overlays, deterministic real-image patches, colored stereo point clouds.\nOriginal image URLs, IDs and SHA-256 are in summary.json sources. No generated images.\n')
    timeline=P.read(P.PUBLIC/'experiments/lab/timeline.json')
    if any(e['id']=='report-road-third-view' for e in timeline['entries']):raise ValueError('Preserve previous publication')
    timeline['entries'].append(dict(id='report-road-third-view',title='도로 대응점 · 세 번째 실제 사진 확인',description='291개 중44개 재확인. 기존·새 보정을 제3시점 스테레오와 비교합니다.',image='/experiments/road-third-view/third-overlay.jpg',href='/experiments/road-third-view/',kind='report',createdAt=evaluation['finishedAt'],detail='실제 촬영3곳 · 지원15.1% · GS·융합 없음'))
    P.write(P.PUBLIC/'experiments/lab/timeline.json',timeline)
    spec=P.read(P.ROOT/'scripts/observation-worlds.json');files=[str(p.relative_to(P.PUBLIC)) for p in output.iterdir() if p.is_file()]+['experiments/road-third-view/index.html']
    spec['files']=list(dict.fromkeys(spec['files']+files));P.write(P.ROOT/'scripts/observation-worlds.json',spec)
    print('Published locally',len(files),'allowlisted report files; timeline',len(timeline['entries']))


if __name__=='__main__':main()
