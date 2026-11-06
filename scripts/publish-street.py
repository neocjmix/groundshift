#!/usr/bin/env python3
"""Curate all street worlds and measured evidence into the existing static lab."""
import argparse
from pathlib import Path
import importlib.util
import shutil
import subprocess
import numpy as np
from PIL import Image,ImageDraw

spec=importlib.util.spec_from_file_location('prepare',Path(__file__).with_name('prepare-street.py'))
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
ROOT=P.ROOT;PUBLIC=ROOT/'public';read,write=P.read,P.write


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('job',type=Path);parser.add_argument('--decision',type=Path,required=True);args=parser.parse_args();job=args.job.resolve()
    decision=read(args.decision);base=read(job/'evaluation/report.json');metrics=read(job/'evaluation/view-metrics.json');config=read(job/'render-config.json')
    if base['status']!='PASS':raise ValueError('Require actual completed renders and measurements')
    batches=[(base,job/'renders',job/'evaluation')]
    for suffix in ['sphere','long']:
        if (job/f'evaluation-{suffix}/report.json').exists():
            extra=read(job/f'evaluation-{suffix}/report.json');extra_config=read(job/f'render-config-{suffix}.json')
            if extra['status']!='PASS' or extra_config['cameras']!=config['cameras']:raise ValueError('Repair camera/evaluation mismatch')
            batches.append((extra,job/f'renders-{suffix}',job/f'evaluation-{suffix}'));metrics+=read(job/f'evaluation-{suffix}/view-metrics.json')
    output=PUBLIC/'experiments/street';output.mkdir(parents=True,exist_ok=False)
    for folder in ['renders','reference','videos','initialization','depth']: (output/folder).mkdir()
    models=[];titles={'sparse':'희소점 대조군','dense':'깊이점 추가 · 크롭별 합산','filtered':'크롭별 합산 + 이웃 검사','stereo':'실제 사진 스테레오','sphere':'구면 중복 정리 + 이웃 검사'}
    fusion=read(job/'fusion/report.json');sparse=read(job/'sparse-preparation.json');world_specs=[];catalog=read(PUBLIC/'worlds/catalog.json');timeline=read(PUBLIC/'experiments/lab/timeline.json')
    existing_ids={m['id'] for m in catalog['scenes']};data_sources={}
    for report,renders,evaluation in batches:
        for recorded in report['models']:
            ident=recorded['id'];parent=ident.removesuffix('-long');slug='street-'+ident
            if slug in existing_ids:raise ValueError('Never replace an existing experiment scene')
            native=read(job/('training-'+ident)/'job.json');src=job/('training-'+ident)/'world';metadata=read(job/'presentation'/ident/'world.json')
            if native['status']!='PASS' or P.sha(src/'scene.ply')!=native['artifact']['sha256']:raise ValueError('Native export changed')
            title=titles[parent]+(' · 학습2배' if ident.endswith('-long') else '')
            metadata['id']=slug;metadata['title']='거리 · '+title
            # Curated presentation must describe this run, rather than retaining
            # acquisition-stage text saying no reconstruction has occurred.
            metadata['provenance']['notes']=(f'Locally reconstructed from nine licensed real ERP panoramas, not a downloaded example GS. '
                f'Actual training:96 real512x512 crops from8 physical centers; physical5 RGB excluded from GS optimization and seed colors. '
                f'Camera/SfM geometry includes all9 centers; no independent measured geometry truth. '
                f'Initialization:{parent}. Brush0.3.0,Apple M2 Metal,{native["options"]["steps"]} steps,SH1,seed42,max400000 splats. '
                f'No diffusion or generated intermediate RGB. Coordinates remain arbitrary SfM units; the documented asset rotation only aligns estimated camera-up for display, not measured gravity. '
                f'Route uses9 recovered camera centers; interpolated viewing poses do not imply a measured floor or collision surface. '
                f'Comparison report /experiments/street/. Quality: {decision["modelQuality"].get(ident,"experimental; limitations remain")}. '
                f'Original source bytes, weights and raw logs remain local; licensed derived crops and attribution are in the report.')
            dest=PUBLIC/'worlds'/slug;dest.mkdir(parents=True,exist_ok=False)
            shutil.copyfile(src/'scene.ply',dest/'scene.ply');write(dest/'world.json',metadata);shutil.copyfile(job/'presentation'/ident/'cameras.json',dest/'cameras.json');shutil.copyfile(job/'inputs/LICENSE',dest/'SOURCE_LICENSE')
            shown=next(c['id'] for c in config['cameras'] if c['kind']=='held' and c['ring']=='level' and c['yaw']==300)
            with Image.open(renders/ident/(shown+'.png')) as im:im.convert('RGB').save(dest/'preview.jpg',quality=91)
            folder=output/'renders'/ident;folder.mkdir();data_sources[ident]=renders
            for camera in config['cameras']:
                if camera['kind']=='path':continue
                shutil.copyfile(renders/ident/(camera['id']+'.png'),folder/(camera['id']+'.png'))
            shutil.copyfile(evaluation/'videos'/(ident+'.mp4'),output/'videos'/(ident+'.mp4'))
            initial=output/'initialization'/(parent+'.ply')
            if not initial.exists():shutil.copyfile(job/'datasets'/parent/'init.ply',initial)
            count=sparse['points'] if parent=='sparse' else read(job/'fusion-sphere/report.json')['points'] if parent=='sphere' else fusion['results'][parent]['points']
            meaning={'sparse':'실제 사진에서 추정한 희소점만 초기 위치로 사용했습니다.','dense':'상대 깊이를 보정해 점을 늘렸습니다. 겹치는 크롭은 각각 점을 남기는 첫 비교군입니다.','filtered':'크롭별 깊이점 중 다른 촬영 위치의 깊이·색과 일치하는 후보를 남겼습니다. 정확도나 가려짐의 정답은 아닙니다.','stereo':'학습 사진끼리 직접 매칭해 삼각측량한 점을 추가했습니다. 단안 깊이 점은 사용하지 않습니다.','sphere':'같은 촬영 위치의 같은 방향에는 깊이 하나만 남긴 뒤, 다른 촬영 위치의 구면 깊이·색과 비교했습니다. 가장 중앙을 보는 크롭을 먼저 선택하며 무효를 임의 보충하지 않습니다.'}[parent]
            if ident.endswith('-long'):meaning+=' 같은 입력·초기 점군으로 학습 단계만8,000→16,000으로 늘린 비교입니다.'
            models.append({**recorded,'title':title,'meaning':meaning,'quality':decision['modelQuality'].get(ident,'실험 결과'),'world':f'/worlds/{slug}/world.json','preview':f'/worlds/{slug}/preview.jpg','video':f'./videos/{ident}.mp4','init':f'./initialization/{parent}.ply','points':count})
            world_specs.append(dict(id=slug,source=str(src.relative_to(ROOT)),asset='scene.ply',format='ply',credits=['SOURCE_LICENSE']))
            # Packaging copies explicit source worlds, so keep curated presentation
            # metadata in a separate local artifact directory, never edit native exports.
            curated=job/'public-worlds'/slug/'world';curated.mkdir(parents=True,exist_ok=False)
            for name in ['scene.ply','world.json','cameras.json','SOURCE_LICENSE']:shutil.copyfile(dest/name,curated/name)
            world_specs[-1]['source']=str(curated.relative_to(ROOT))
            detail=f'실제8개 촬영 위치 · {native["options"]["steps"]:,} Metal 단계 · {decision["modelQuality"].get(ident,"실험")}'
            catalog['scenes'].append(dict(id=slug,title=metadata['title'],description=meaning,category='experiment',manifestPath=f'/worlds/{slug}/world.json',thumbnailPath=f'/worlds/{slug}/preview.jpg',detail=detail,createdAt=native['finishedAt']))
            existing_ids.add(slug)
            timeline['entries'].append(dict(id=slug,title=metadata['title'],description=meaning,image=f'/worlds/{slug}/preview.jpg',href=f'/?world=/worlds/{slug}/world.json',kind='scene',createdAt=native['finishedAt'],detail=detail))
    if decision['best'] not in [m['id'] for m in models]:raise ValueError('Recommended model was not actually executed')
    views=[]
    for camera in config['cameras']:
        if camera['kind']=='path':continue
        item=dict(id=camera['id'],title=f'{"학습 제외" if camera["kind"]=="held" else "학습 위치"} · {camera["physicalPanorama"]}번 · {camera["ring"]} {camera["yaw"]}°',kind=camera['kind'])
        if camera['kind']=='offpath':item['title']='관측 없는 경로 옆 · '+camera['id']
        if camera.get('reference'):
            shutil.copyfile(camera['reference'],output/'reference'/(camera['id']+'.png'));item['source']='./reference/'+camera['id']+'.png'
        views.append(item)
    # One synchronized mosaic, using exactly the same saved camera frames.
    frames=job/'publication-comparison-frames';frames.mkdir(exist_ok=False);paths=[c for c in config['cameras'] if c['kind']=='path']
    columns=3 if len(models)>4 else 2
    for i,camera in enumerate(paths):
        canvas=Image.new('RGB',(384*columns,410*int(np.ceil(len(models)/columns))),(10,16,23));draw=ImageDraw.Draw(canvas)
        for n,m in enumerate(models):
            x,y=(n%columns)*384,(n//columns)*410
            with Image.open(data_sources[m['id']]/m['id']/(camera['id']+'.png')) as im:canvas.paste(im.convert('RGB').resize((384,384),Image.Resampling.LANCZOS),(x,y+26))
            draw.text((x+8,y+7),m['id'].upper(),fill=(235,245,250))
        canvas.save(frames/f'{i:03d}.png')
    subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-framerate','6','-i',str(frames/'%03d.png'),'-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(output/'videos/comparison.mp4')],check=True)
    evidence=[]
    for ring in ['level','down']:
        name=f'p04-{ring}-300.png';raw=job/'fusion'/(name+'.relative.png');target=output/'depth'/(ring+'-relative.png');shutil.copyfile(raw,target)
        evidence.append(dict(title=f'4번 · {ring} · 상대 깊이',image=f'./depth/{ring}-relative.png',caption='DAV2 Small의 원시 상대 깊이를 이미지별2–98분위로 표시했습니다. 밝기가 절대 거리나 미터를 뜻하지 않습니다.'))
        depth=np.load(job/'fusion'/(name+'.z.npy'));Image.fromarray(np.isfinite(depth).astype(np.uint8)*255).save(output/'depth'/(ring+'-valid.png'))
        evidence.append(dict(title=f'4번 · {ring} · 보정 깊이 유효 영역',image=f'./depth/{ring}-valid.png',caption='흰색=양의 보정 깊이와 각도·거리 선택 범위를 통과. 깊이 정확도나 실제 가려짐의 정답이 아닙니다.'))
    if (job/'fusion-sphere/report.json').exists():
        for suffix in ['radial','support']:
            shutil.copyfile(job/'fusion-sphere'/f'4-{suffix}.png',output/'depth'/f'sphere-4-{suffix}.png')
        evidence.extend([dict(title='4번 · 방향별 하나의 구면 깊이',image='./depth/sphere-4-radial.png',caption='구면 광선마다 가장 중앙 크롭의 깊이를 선택했습니다. 무효 깊이는 보충하지 않았으며, 밝기는 SfM 학습 거리 P99 기준입니다. 미터 아님.'),dict(title='4번 · 구면 이웃 검사',image='./depth/sphere-4-support.png',caption='격자 샘플 중 초록=다른 실제 촬영 위치에서 깊이·색 일치, 노랑=미지원 또는 불일치. 실제 정확도·가려짐 정답이 아닙니다.')])
    manifest=read(ROOT/'scripts/samples/mapillary-beijing.json');sources=[dict(title=f'사진{i+1} · Cicero101 / Mapillary {s["image_id"]}',url=s['commons_page'],licenseUrl=manifest['licenseUrl']) for i,s in enumerate(manifest['images'])]
    stereo=read(job/'stereo/report.json');inference=read(job/'depth/report.json')
    stages=[dict(title='실제 사진·카메라·학습 제외 구성',status='PASS',detail='9개 실제 촬영 위치 중5번 RGB를 GS 최적화와 조밀 초기 색에서 제외했습니다. 카메라·희소 형상은 전체9장으로 추정했습니다.'),
        dict(title='초기 희소점 색의 학습 제외 검사',status='FAIL',detail='처음 준비한 SfM 평균 색은5번의 기여를 배제할 수 없어 사용하지 않았습니다. 동일한 XYZ를 비5번 실제 관측 색으로 다시 만든3124개 점을 모든 비교군에 공통으로 사용했습니다.'),
        dict(title='DAV2 Small · 로컬 M2 MPS 추론',status=inference['status'],detail=f'실제 학습 크롭{len(inference["images"])}장. 기록된 모델 로드·추론 {inference["elapsedSeconds"]:.3f}초. 상대 깊이를 그대로 미터로 사용하지 않았습니다.'),
        dict(title='실제 RGB 스테레오',status=stereo['status'],detail=f'84개 방향 쌍 중80개 완료,{stereo["points"]:,}개 후보.4개는 보정 지평선 조건으로 실패·제외했습니다. 유효 그룹만 명시적으로 사용했고 실패 상태를 성공으로 바꾸지 않았습니다. 새 매칭에는 사진5를 쓰지 않았습니다.'),
        dict(title='깊이 보정·공통 좌표 점군 통합',status=fusion['status'],detail=f'96장 모두 보정 실행. 깊이와 다른 시점의 색·깊이를 비교했습니다. 같은 모델끼리 일치할 수도 있어 형상 정합 승인으로 보지 않습니다. 완전한 P2 형상 승인은 NOT ACCEPTED입니다.')]
    if (job/'fusion-sphere/report.json').exists():
        sphere=read(job/'fusion-sphere/report.json');stages.append(dict(title='겹치는 크롭의 구면 중복 정리',status=sphere['status'],detail='초기 비교군은 겹치는 크롭을 따로 합산했습니다. 후속 비교는 구면 광선마다 깊이 하나를 먼저 선택하고, 다른 물리적 촬영 위치에서도 방향별 하나의 깊이와만 비교합니다. 초기 결과도 별도 장면으로 남겼습니다.'))
    for m in models:stages.append(dict(title='Metal GS 학습 · '+m['title'],status=m['status'],detail=f'실제 {m["steps"]:,}단계,{m["trainingSeconds"]:.3f}초,{m["splats"]:,} Gaussian. 원시 로그와 자원 측정은 Mac에 보존했습니다.'))
    stages += [dict(title='실제 브라우저 동일 시점 렌더·이동 영상',status='PASS',detail=f'모든{len(models)}개 결과를 실제 headed Chrome/Spark로 렌더했습니다. 사진5의12개 방향, 학습 위치12개, 경로49프레임, 경로 옆2시점입니다. 영상은6fps로 인코딩했으며 측정된 렌더 FPS가 아닙니다.'),
        dict(title='대체 통합 엔진의 실제 추론',status='NOT RUN',detail='InfiniSplat v2·UniTriSplat·GGPS의 공식 설치 경로는 CUDA/NVIDIA를 요구합니다. 라이선스도 별도 조건이 있어 이 Mac에 억지로 포팅하거나 서비스로 대체하지 않았습니다. Brush 공식 최신 릴리스는 검증한0.3.0입니다.'),
        dict(title='독립적인 실측 형상·더 긴 거리 확장',status='NOT RUN',detail='외부 실측 깊이가 없고 자유 이동에서의 품질 문제가 남아, 더 큰 구간 연결·스트리밍으로 확장하지 않았습니다.')]
    summary=dict(status='PASS',completedAt=decision['completedAt'],best=decision['best'],verdict=decision['verdict'],models=models,views=views,metrics=metrics,stages=stages,depthEvidence=evidence,sources=sources,comparisonVideo='./videos/comparison.mp4',repair=decision.get('repair'),matchedBudget=decision.get('matchedBudget'),comparisons=[c for report,_,_ in batches for c in report['comparisons']],
        notes=['동일한96개 RGB·마스크·카메라와 시드42,해상도512,SH1을 사용했습니다. 초기 점 개수는 바뀝니다. 학습2배 비교만8,000→16,000단계입니다.',
            'SfM 임의 단위이며 GPS·중력·미터 깊이를 측정하지 않았습니다. 초기 점군과 Gaussian은 같은 공통 좌표를 유지합니다.',
            '색 오차와 불투명도는 관찰 지표입니다. 모양의 정확도, 실제 가려짐, 안전한 바닥이나 일반적인 거리 재구성 성공을 보장하지 않습니다.',
            '실제 처리 시간은 단일 실행 기록입니다. 일부 CPU 준비·미리보기 작업이 겹쳤고 열 상태를 통제한 반복 성능 벤치마크가 아닙니다.',
            '원본 파노라마·스쿠터·앞선 실패 결과는 모두 보존했습니다. 이번 장면은 사진으로 이 Mac에서 새로 학습한 결과이며, 예제 GS를 내려받아 사용한 것이 아닙니다.'])
    write(output/'summary.json',summary);write(output/'calibration-measurements.json',read(job/'fusion/calibrations.json'))
    (output/'ATTRIBUTION.txt').write_text('Original photographs: Cicero101 / Mapillary via Wikimedia Commons, CC BY-SA4.0. https://creativecommons.org/licenses/by-sa/4.0/\nChanges: actual perspective crops, relative-depth visualization, RGB stereo/calibrated point initialization, local Brush Gaussian training, actual browser renders and rendered motion videos. No diffusion or generated intermediate training images.\nDAV2 Small checkpoint: Apache-2.0; weights/code remain local. Source-photo credits and URLs in summary.json.\n')
    timeline['entries'].append(dict(id='report-street-conclusion',title='거리 GS · 끝까지 실행한 비교와 결론',description=decision['verdict']['summary'],image=f'/worlds/street-{decision["best"]}/preview.jpg',href='/experiments/street/',kind='report',createdAt=decision['completedAt'],detail=f'{len(models)}개 실제 GS · 같은 시점·이동 영상 · 실패 단계 포함'))
    write(PUBLIC/'worlds/catalog.json',catalog);write(PUBLIC/'experiments/lab/timeline.json',timeline)
    spec=read(ROOT/'scripts/observation-worlds.json');spec['worlds']+=world_specs
    files=[str(p.relative_to(PUBLIC)) for p in output.rglob('*') if p.is_file()]+['experiments/street/index.html']
    spec['files']=list(dict.fromkeys(spec['files']+files));write(ROOT/'scripts/observation-worlds.json',spec)
    print('Published locally',len(models),'new worlds;',len(files),'report files;',len(catalog['scenes']),'catalog scenes;',len(timeline['entries']),'timeline entries')


if __name__=='__main__':main()
