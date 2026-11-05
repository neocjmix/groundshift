#!/usr/bin/env python3
"""Publish the no-learned-depth trial alongside existing observation results."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT/'public'
spec = importlib.util.spec_from_file_location('object_publication', ROOT/'scripts/publish-object-focus.py')
helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
read, write = helper.read, helper.write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path); parser.add_argument('--finish', action='store_true')
    args = parser.parse_args(); job = args.job.resolve()
    run = read(job/'ablation.json'); training = read(job/'training/job.json')
    if run['status'] != 'PASS' or training['status'] != 'PASS':
        raise ValueError('Native execution must complete before publication')
    export = job/'training/world'; object_world = job/'object/world'
    if not args.finish:
        raw = read(export/'world.json'); cameras = read(export/'cameras.json')
        previous = read(PUBLIC/'worlds/scooter-real-object/world.json')
        if raw['coordinates'] != previous['coordinates']:
            raise ValueError('Display coordinate transforms differ; cannot copy the comparison camera')
        # Only the display camera is reused. It does not enter training or point initialization.
        raw['navigation']['camera'] = previous['navigation']['camera']
        raw['provenance']['license'] = 'CC-BY-SA-4.0 source images'
        raw['provenance']['attribution'] = 'Original photographs: Cicero101 / Mapillary via Wikimedia Commons. Perspective crops and reconstruction: Groundshift.'
        raw['provenance']['notes'] = ('Nine real images, byte-identical training RGB and camera matrices to the preceding real-only trial. '
            'No intermediate generation, learned monocular depth, depth calibration or depth fusion. '
            f"Initialization: {run['initialPoints']} triangulated SfM points inside the same three observed object rectangles, from {run['sfmPoints']} recovered points. "
            'Brush 0.3.0 on Apple M2 Metal, 5000 steps, max resolution 512, max splats 150000, SH degree 1, seed 42. '
            'Arbitrary scale. The previous display camera is reused only to present comparable views; it is not a reconstruction input. Independent quality measurement NOT RUN.')
        cameras['sequenceNotes'] = 'Nine observed images only, with reused original-image SfM cameras. No generated training views.'
        header, data = helper.ply(export/'scene.ply')
        xyz = np.column_stack([data[k] for k in ['x', 'y', 'z']]); keep = np.isfinite(xyz).all(1)
        for clip in run['clipping']:
            T = np.array(clip['worldToCamera']); K = np.array(clip['intrinsics']); b = clip['bounds']
            projected = (xyz@T[:, :3].T+T[:, 3])@K.T
            uv = projected[:, :2]/np.maximum(projected[:, 2:], 1e-8)
            keep &= ((projected[:, 2] > 0) & (uv[:, 0] >= b[0]) & (uv[:, 0] <= b[2]) & (uv[:, 1] >= b[1]) & (uv[:, 1] <= b[3]))
        selected = data[keep]
        if not len(selected): raise ValueError('No trained Gaussians inside the observed object selection')
        object_world.mkdir(parents=True, exist_ok=False)
        header = [f'element vertex {len(selected)}' if line.startswith('element vertex ') else line for line in header]
        with (object_world/'scene.ply').open('wb') as handle:
            handle.write(('\n'.join(header)+'\n').encode()); selected.tofile(handle)
        for slug, title, folder in [('scooter-nodepth-context', '스쿠터 · 단안 깊이 없이 · 전체', export),
                                    ('scooter-nodepth-object', '스쿠터 · 단안 깊이 없이', object_world)]:
            manifest = json.loads(json.dumps(raw)); manifest.update(id=slug, title=title)
            write(folder/'world.json', manifest); write(folder/'cameras.json', cameras)
            (folder/'SOURCE_LICENSE').write_text('Original photographs: Cicero101 / Mapillary via Wikimedia Commons. CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/\nDerived perspective images and reconstruction. No generated intermediate images or learned monocular depth.\n')
            dest = PUBLIC/'worlds'/slug; dest.mkdir(exist_ok=True)
            for filename in ['world.json', 'cameras.json', 'scene.ply', 'SOURCE_LICENSE']:
                shutil.copyfile(folder/filename, dest/filename)
        write(job/'object/report.json', dict(status='PASS', finishedAt=datetime.now(timezone.utc).isoformat(),
              inputSplats=len(data), outputSplats=len(selected), operation='Same three-rectangle Gaussian-center selection'))
    selected = read(job/'object/report.json')
    out = PUBLIC/'experiments/object-nodepth'; (out/'images').mkdir(parents=True, exist_ok=True)
    for image in sorted((job/'dataset/images').glob('*.png')): shutil.copyfile(image, out/'images'/image.name)
    shutil.copyfile(job/'originals-contact.jpg', out/'originals-contact.jpg')
    shutil.copyfile(job/'cloud.json', out/'cloud.json')
    shutil.copyfile(PUBLIC/'experiments/object-real/cloud.json', out/'previous-cloud.json')
    summary = dict(completedAt=training['finishedAt'], realImages=9, generatedImages=0, depthMaps=0,
        sfmPoints=run['sfmPoints'], initialPoints=run['initialPoints'], exportSplats=training['artifact']['splats'],
        objectSplats=selected['outputSplats'], trainingSeconds=training['elapsedSeconds'], steps=training['options']['steps'],
        images=[dict(file='images/'+record['file'], kind='observed') for record in run['images']],
        sameTrainingImageBytes=all(item['sha256'] == item['referenceSha256'] for item in run['images']),
        sameCameraBytes=run['cameraSha256'] == run['referenceCameraSha256'],
        notes=['실제 사진 9장과 카메라 행렬은 직전 실험과 바이트 단위로 같습니다. 512 해상도, 5,000단계, 최대 150,000 splat, SH 1, 시드 42도 유지했습니다.',
               '단안 깊이 추론·보정·점군 융합을 전부 제거했습니다. 같은 사진 사이의 특징점 대응으로 삼각측량한 희소 점만 초기 위치로 사용합니다.',
               '동일한 세 사진의 물체 선택 영역을 초기 점과 학습 후 Gaussian 중심에 적용했습니다. 사진 자체는 이전과 같이 배경을 포함합니다.',
               '이전과 같은 화면 카메라를 사용해 결과를 나란히 보여줍니다. 이 표시용 카메라는 학습에 들어가지 않습니다. 정량적 품질 비교와 독립적인 형상 정확도 측정은 NOT RUN입니다.'])
    write(out/'summary.json', summary)
    if args.finish:
        shutil.copyfile(PUBLIC/'worlds/scooter-nodepth-object/preview.jpg', out/'gs-preview.jpg')
        shutil.copyfile(PUBLIC/'worlds/scooter-nodepth-context/preview.jpg', out/'context-preview.jpg')
    catalog = read(PUBLIC/'worlds/catalog.json'); publication = read(ROOT/'scripts/observation-worlds.json')
    timeline = read(PUBLIC/'experiments/lab/timeline.json')
    ids = {'scooter-nodepth-object', 'scooter-nodepth-context'}
    catalog['scenes'] = [s for s in catalog['scenes'] if s['id'] not in ids]
    publication['worlds'] = [s for s in publication['worlds'] if s['id'] not in ids]
    timeline['entries'] = [s for s in timeline['entries'] if s['id'] not in ids | {'report-object-nodepth'}]
    for slug, title, folder in [('scooter-nodepth-object', '스쿠터 · 단안 깊이 없이', object_world),
                                ('scooter-nodepth-context', '스쿠터 · 단안 깊이 없이 · 전체', export)]:
        item = dict(id=slug, title=title, description='실제 사진 9장 그대로. 단안 깊이를 빼고 사진 정합의 희소 점으로 시작한 GS.',
            category='experiment', manifestPath=f'/worlds/{slug}/world.json', thumbnailPath=f'/worlds/{slug}/preview.jpg',
            detail=f"9 real images · {run['initialPoints']} SfM initial points · no learned depth · 5,000 Metal steps", createdAt=selected['finishedAt'])
        catalog['scenes'].append(item)
        publication['worlds'].append(dict(id=slug, source=str(folder.relative_to(ROOT)), asset='scene.ply', format='ply', credits=['SOURCE_LICENSE']))
        timeline['entries'].append(dict(id=slug, title=title, description=item['description'], image=item['thumbnailPath'],
            href='/?world='+item['manifestPath'], kind='scene', detail=item['detail'], createdAt=item['createdAt']))
    timeline['entries'].append(dict(id='report-object-nodepth', title='단안 깊이도 제거 · 실제 9장 + SfM',
        description='직전 9장 실험과 같은 입력·카메라·학습 설정으로 깊이 모델의 기여를 빼봅니다.',
        image='/experiments/object-nodepth/originals-contact.jpg', href='/experiments/object-nodepth/',
        kind='report', detail='깊이 사용 / 미사용 결과 비교', createdAt=selected['finishedAt']))
    files = [str(path.relative_to(PUBLIC)) for path in out.rglob('*') if path.is_file()]
    files += ['experiments/object-nodepth/index.html', 'experiments/object-nodepth/gs-preview.jpg', 'experiments/object-nodepth/context-preview.jpg']
    publication['files'] = list(dict.fromkeys(publication['files']+files))
    write(PUBLIC/'worlds/catalog.json', catalog); write(PUBLIC/'experiments/lab/timeline.json', timeline)
    write(ROOT/'scripts/observation-worlds.json', publication)
    print(json.dumps(dict(worlds=len(catalog['scenes']), initialPoints=run['initialPoints'], objectSplats=selected['outputSplats'])))


if __name__ == '__main__': main()
