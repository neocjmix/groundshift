#!/usr/bin/env python3
"""Prepare the explicit, user-authorized observation release from local artifacts.

Uses only the Python standard library. --render-previews uses installed
headed Chrome and the local viewer, preserving actual rendered pixels. This
command never copies input footage, source job reports, logs or model weights.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
SPEC = ROOT / 'scripts/observation-worlds.json'
GITHUB = 'https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/'
MODEL_LICENSE = 'https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting/blob/8a4288a76071f7280aedbdb3253bdb9e9d5d84bb/README.md'
COMMONS = 'https://commons.wikimedia.org/wiki/Category:Photographs_of_Beijing_from_Mapillary_(m4ks1Y6pR3fcIjBz9wXxWt)'
# These nine distinct exports supplement the four existing catalog worlds.
TRIALS = [
 ('beijing-10k', 'mapillary-beijing-rig-baseline-10000/world', 'Beijing · observed 10k', '48 real crops · 150,000 splats · Quality FAIL', 'Real photographs only; fixed panorama rigs. Blurred structures and stretched geometry remain.'),
 ('beijing-generated', 'mapillary-beijing-generated-gs-smoke/world', 'Beijing · generated input', '48 real + 1 generated view · 2,000 steps · Quality FAIL', 'Local diffusion output was included in Metal training. An integration experiment, not evidence of improved reconstruction.'),
 ('beijing-20k', 'mapillary-beijing-rig-baseline-20000/world', 'Beijing · capacity 20k', '750,000 splats · 69 MB · Quality FAIL', 'Longer training and larger capacity together; held-view PSNR fell from 14.72 to 12.68 dB.'),
 ('beijing-2k', 'mapillary-beijing-rig-baseline/world', 'Beijing · observed 2k', '48 real crops · 7,015 splats · Quality FAIL', 'The first constrained-rig Gaussian baseline. Training and export worked, while the reconstructed appearance remained blurry.'),
 ('dozer-smoke', 'dozer-smoke/world', 'Dozer · 30-step smoke', '40 supplied cameras · 165,875 splats · early trial', 'Initial native execution test with only 30 training steps. This is a separate exported result, not the accepted 1,500-step scene.'),
 ('dozer-proof', 'dozer-proof-20261104/world', 'Dozer · fresh proof rerun', '40 supplied cameras · 194,871 splats · rerun', 'A fresh local 1,500-step Metal run retained as reconstruction evidence; this PLY differs from the original export.'),
 ('dozer-partial', 'dozer-estimated-1500/world', 'Dozer · partial 16/40 poses', '16 of 40 cameras · 1,048 splats · Quality FAIL', 'The early pose-estimation attempt registered only 16 of 40 photographs. Its sparse Gaussian output is retained for observation.'),
 ('dozer-24', 'dozer-pipeline-24/training/world', 'Dozer · 24-view trial', '24 estimated cameras · 9,662 splats · early trial', 'A small end-to-end local pipeline run using supplied lens calibration and newly estimated camera positions.'),
 ('desk-15s', 'desk-video-15s/training/world', 'My desk · initial 15s trial', '60 estimated cameras · 11,450 splats · early trial', 'The first 15-second crop of the creator recording, with the earlier system HDR conversion. The later full capture is separately available.'),
]
IMAGES = {
 'real-02.png': 'mapillary-beijing-rig-poses-v2/dataset/images/pano_000005_view_02.png',
 'real-04.png': 'mapillary-beijing-rig-poses-v2/dataset/images/pano_000005_view_04.png',
 'stereo-input.png': 'mapillary-beijing-stereo-gap-view04-widefov-v2/warp.png',
 'stereo-mask.png': 'mapillary-beijing-gap-inpaint-stereo-widefov-v2/mask.png',
 'stereo-completed.png': 'mapillary-beijing-gap-inpaint-stereo-widefov-v2/completed.png',
 'stereo-gray.png': 'mapillary-beijing-gap-inpaint-stereo-widefov-v2/gray-control.png',
 'gs-input.png': 'mapillary-beijing-gap-render-10000/input.png',
 'gs-mask.png': 'mapillary-beijing-gap-inpaint-gs10000-v2/mask.png',
 'gs-completed.png': 'mapillary-beijing-gap-inpaint-gs10000-v2/completed.png',
 'gs-gray.png': 'mapillary-beijing-gap-inpaint-gs10000-v2/gray-control.png',
}


# Snapshot of explicitly selected experiment stages; future jobs do not publish metadata silently.
HISTORY_TRIALS = ['desk-video-15s', 'desk-video-full-sdr', 'dozer-1500', 'dozer-estimated-1500', 'dozer-independent-120', 'dozer-pipeline-24', 'dozer-proof-20261104', 'dozer-revisit-export', 'dozer-smoke', 'mapillary-beijing-baseline', 'mapillary-beijing-capacity-comparison', 'mapillary-beijing-crops', 'mapillary-beijing-direction2', 'mapillary-beijing-direction2-poses', 'mapillary-beijing-gap-inpaint-gs10000', 'mapillary-beijing-gap-inpaint-gs10000-v2', 'mapillary-beijing-gap-inpaint-stereo-widefov-v2', 'mapillary-beijing-gap-metrics-gs10000-diffusion', 'mapillary-beijing-gap-metrics-gs10000-gray', 'mapillary-beijing-gap-metrics-stereo-widefov-v2-diffusion', 'mapillary-beijing-gap-metrics-stereo-widefov-v2-gray', 'mapillary-beijing-gap-render', 'mapillary-beijing-gap-render-10000', 'mapillary-beijing-gap-render-20000', 'mapillary-beijing-gap-render-view5', 'mapillary-beijing-generated-augmentation-gs10000', 'mapillary-beijing-generated-augmentation-stereo', 'mapillary-beijing-generated-augmentation-stereo-v2', 'mapillary-beijing-generated-gs-render', 'mapillary-beijing-generated-gs-smoke', 'mapillary-beijing-holdout', 'mapillary-beijing-poses', 'mapillary-beijing-rig-baseline', 'mapillary-beijing-rig-baseline-10000', 'mapillary-beijing-rig-baseline-20000', 'mapillary-beijing-rig-holdout', 'mapillary-beijing-rig-poses', 'mapillary-beijing-rig-poses-v2', 'mapillary-beijing-stereo-gap-v1', 'mapillary-beijing-stereo-gap-view01', 'mapillary-beijing-stereo-gap-view04', 'mapillary-beijing-stereo-gap-view04-padded', 'mapillary-beijing-stereo-gap-view04-relaxed', 'mapillary-beijing-stereo-gap-view04-wide', 'mapillary-beijing-stereo-gap-view04-widefov', 'mapillary-beijing-stereo-gap-view04-widefov-comparison', 'mapillary-beijing-stereo-gap-view04-widefov-repro', 'mapillary-beijing-stereo-gap-view04-widefov-v2', 'mapillary-beijing-stereo-gap-view04-widefov-v2-comparison', 'mapillary-beijing-training-comparison', 'mapillary-beijing-training-view', 'mapillary-beijing-training-view-10000', 'mapillary-beijing-wide-stereo-input', 'mapillary-beijing-wide-stereo-input-repro', 'mapillary-diffusion-smoke', 'mapillary-diffusion-smoke-input']

def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_public_text(text):
    if re.search(r'file:/{2}|/Users/|/private/|/var/folders/|share\.icloud\.com|IMG_\d+\.MOV', text, re.I):
        raise ValueError('Private source reference in prepared public text')


def prepare_worlds():
    result = []
    for slug, source, title, detail, description in TRIALS:
        src = ROOT / 'data/jobs' / source
        out = PUBLIC / 'worlds' / slug
        out.mkdir(parents=True, exist_ok=True)
        world = read_json(src / 'world.json')
        world['id'], world['title'] = slug, title
        provenance = world['provenance']
        if slug == 'desk-15s':
            permission = GITHUB + 'DEPLOYMENT.md#desk-publication-permission'
            provenance.update(sourceUrl=permission, licenseUrl=permission,
                license='All rights reserved; creator-authorized public display',
                attribution='Recorded by the scene creator; public display authorized by the creator',
                notes='Initial 15-second private indoor recording trial; 60 cameras and 9,872 sparse points estimated locally without supplied poses or lens calibration. System HDR-to-SDR conversion preceded 1,500 Metal training steps. Creator authorization covers derived experimental worlds, camera metadata and rendered previews in this observation viewer; no general reuse license is granted. Source footage and extracted frames are not distributed. Asset coordinates preserve Brush output; mean camera up is aligned to world +Y, while gravity and metric scale are unmeasured. This superseded trial is shown as an experiment, not an accepted reconstruction.')
            credit = 'Creator-authorized public display of the derived experimental scene and rendered preview. All rights reserved. No general reuse or redistribution license is granted. Private original footage is not included.\n'
        elif slug.startswith('beijing-'):
            # Do not retain earlier-stage wording claiming no reconstruction was performed.
            notes = ('Source: nine consecutive 7680x3840 panoramas by Cicero101 on Mapillary, mirrored by Wikimedia Commons; 2025-05-27 05:11:05–13, timezone unspecified. This is a small dense candidate, not a global density maximum. The photos were reprojected into overlapping pinhole views, then world cameras were estimated with fixed co-located spherical rigs. Forty-eight observed crops were used for Brush Metal training. Poses and initialization colors used all nine panoramas: this is only an appearance holdout, not independent geometry validation. Gravity and metric scale are unknown. Coordinates and transforms preserve the measured export. Quality FAIL: blurry, streaked or incomplete geometry. ')
            if slug == 'beijing-generated':
                old = provenance['notes']
                notes += old[old.index('Current augmented dataset:'):]
            else:
                notes += 'No diffusion-generated training pixels were used in this variant.'
            provenance['notes'] = notes
            credit = ('Source photography: Cicero101 / Mapillary, redistributed by Wikimedia Commons. CC-BY-SA-4.0: https://creativecommons.org/licenses/by-sa/4.0/\n' + COMMONS + '\nModifications: perspective reprojection, camera estimation, Gaussian reconstruction and rendered preview. Per-image attribution is in /experiments/mapillary/sources.json.\n')
            if slug == 'beijing-generated':
                credit += 'One synthetic training view used Stable Diffusion 1.5 Inpainting. Model terms: CreativeML OpenRAIL-M, ' + MODEL_LICENSE + '. Generated pixels are hypotheses, not observed geometry.\n'
        else:
            credit = (src / 'SOURCE_LICENSE').read_text()
            if slug == 'dozer-24':
                provenance['notes'] = ('Twenty-four chronological source photographs from the licensed NerfBaselines dozer dataset. Supplied OPENCV_FISHEYE lens calibration was fixed; all 24 camera poses and 6,299 sparse points were estimated locally. No supplied poses, sparse geometry or Gaussian checkpoint were used. Camera axes were converted from COLMAP to OpenGL. Asset coordinates preserve Brush output and mean camera up is aligned with world +Y. Gravity and metric scale are unknown. This is an early, superseded local pipeline trial.')
            elif slug == 'dozer-partial':
                provenance['notes'] = ('Early partial camera estimation registered 16 of 40 prepared photographs; supplied camera extrinsics were not used by estimation. Brush completed 1,500 Metal steps on that partial result and exported 1,048 splats. Coverage and visual quality FAIL. COLMAP camera axes were converted to OpenGL; output is Y-up in arbitrary units with no measured gravity or metric scale. This result is retained for observation and is not an accepted scene.')
        world['provenance']['notes'] += ' Observation release: ' + description
        cameras = read_json(src / 'cameras.json')
        if slug == 'desk-15s':
            for i, frame in enumerate(cameras['frames']):
                frame['image'] = f'camera-{i + 1:04d}'
        for value in (world, cameras):
            assert_public_text(json.dumps(value))
        assert_public_text(credit)
        write_json(out / 'world.json', world)
        write_json(out / 'cameras.json', cameras)
        (out / 'SOURCE_LICENSE').write_text(credit)
        shutil.copyfile(src / 'scene.ply', out / 'scene.ply')
        job = read_json(src.parent / 'job.json')
        result.append(dict(id=slug, title=title, sha256=sha(out / 'scene.ply'),
            bytes=(out / 'scene.ply').stat().st_size, splats=job['artifact']['splats'],
            trainingSeconds=job['elapsedSeconds'], trainingImages=job['imageCount'],
            steps=job['options']['steps'], execution=job['status'],
            quality='FAIL' if slug.startswith('beijing-') or slug == 'dozer-partial' else 'NOT ASSESSED FOR ACCEPTANCE',
            manifest=f'/worlds/{slug}/world.json'))
    return result


def collect_history():
    """Whitelist only status/numeric fields; never publish raw job reports."""
    records = []
    for name in HISTORY_TRIALS:
        directory = ROOT / 'data/jobs' / name
        if not directory.is_dir():
            raise FileNotFoundError(directory)
        report_names = ['job.json', 'report.json', 'pipeline.json', 'augmentation.json', 'holdout.json', 'export.json', 'color-validation.json', 'color-validation-correction.json']
        reports = sorted({p for name in report_names for p in directory.glob('**/' + name)})
        if not reports:
            records.append(dict(trial=directory.name, stage='prepared inputs or export reuse', execution='NOT RECORDED', detail=('Synthetic fixture input only; no real-scene or GPU acceptance claim.' if directory.name == 'mapillary-diffusion-smoke-input' else 'No standalone execution-status report; not a successful GPU claim.')))
        for report in reports:
            data = read_json(report)
            stage = str(report.relative_to(directory).parent)
            item = dict(trial=directory.name, stage=(report.stem if stage == '.' else stage + ' / ' + report.stem),
                        execution=data.get('status', 'NOT RECORDED'))
            for key in ['elapsedSeconds', 'inferenceSeconds', 'gpuInference', 'modelDownload', 'multiViewConsistency', 'geometryValidation', 'imageCount', 'registeredImages', 'registeredImageCount', 'trainingImages', 'gpuTraining', 'reconstruction', 'cameraEstimation']:
                value = data.get(key)
                if isinstance(value, (int, float, bool)) or value in ['PASS', 'FAIL', 'NOT RUN', 'CANCELLED']:
                    item[key] = value
            for count_key in ['inputImages', 'registeredImages', 'trainingImages', 'heldOutImages']:
                if isinstance(data.get(count_key), list):
                    item[count_key + 'Count'] = len(data[count_key])
            if isinstance(data.get('coverage'), dict) and 'holeFraction' in data['coverage']:
                item['holePercent'] = data['coverage']['holeFraction'] * 100
            if 'maskedFraction' in data:
                item['holePercent'] = data['maskedFraction'] * 100
            if isinstance(data.get('artifact'), dict):
                item['artifact'] = {k: data['artifact'][k] for k in ['splats', 'bytes', 'sha256'] if k in data['artifact']}
            if directory.name == 'mapillary-beijing-poses':
                item['quality'] = 'FAIL: unconstrained virtual camera centers disagreed'
            if directory.name == 'mapillary-beijing-baseline':
                item['detail'] = 'Cancelled after camera geometry audit; no scene export.'
            if directory.name == 'mapillary-beijing-gap-inpaint-gs10000':
                item['detail'] = 'Failed before GPU inference: removed VAE slicing API; fixed in v2.'
            if directory.name == 'mapillary-diffusion-smoke':
                item['detail'] = 'Synthetic fixture smoke test, cancelled during model acquisition; GPU inference NOT RUN. Not a real-scene result.'
            if directory.name == 'mapillary-beijing-rig-poses':
                item['detail'] = 'Initial rig adapter serialization failed; corrected v2 executed.'
            records.append(item)
    records.append(dict(trial='dozer-revisit-export', stage='duplicate mapping', execution='PASS', detail='Same PLY SHA-256 as dozer-1500 and the supplied-camera catalog scene. Camera-path export reused it; no duplicate scene binary published.'))
    records.extend([
        dict(trial='ViewCrafter', stage='local candidate', execution='NOT RUN', detail='Official example requires CUDA and approximately 23.5 GB; incompatible with this 16 GB M2 path.'),
        dict(trial='SEVA', stage='local candidate', execution='NOT RUN', detail='Gated CUDA model with noncommercial terms; not adopted for this local experiment.'),
        dict(trial='Mapillary direct Graph search', stage='acquisition', execution='FAIL', detail='API access without an authorized token rejected; public Commons mirror used instead.'),
        dict(trial='Commons initial 12-image acquisition', stage='acquisition', execution='FAIL', detail='Rate limit after nine images; nine consecutive licensed panoramas retained. No bypass.'),
        dict(trial='Generated multi-view consistency', stage='quality validation', execution='NOT RUN', detail='One generated input is an integration test, not validated multi-view novel-view synthesis.'),
    ])
    assert_public_text(json.dumps(records))
    return records


def render_previews(base_url, ids):
    js = r'''
import { chromium } from '@playwright/test';
import { writeFile, mkdir } from 'node:fs/promises';
const ids=JSON.parse(process.env.GS_OBSERVATION_IDS);
const browser=await chromium.launch({channel:'chrome',headless:false});
const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
const results=[];
try { for(const id of ids) {
 const errors=[]; const onError=e=>errors.push(e.message);page.on('pageerror',onError);
 await page.goto(process.env.GS_OBSERVATION_BASE+'/?world=/worlds/'+id+'/world.json');
 await page.locator('.scene-shell[data-phase="ready"]').waitFor({timeout:60000});
 await page.locator('.render-details summary').filter({hasText:'fps'}).waitFor({timeout:30000});
 await page.waitForTimeout(500);
 await page.locator('canvas').screenshot({path:'public/worlds/'+id+'/preview.jpg',type:'jpeg',quality:88,style:'.scene-shell > :not(.canvas-mount) { visibility: hidden !important; }'});
 results.push({id,render:'PASS',errors,preview:'actual browser canvas; not a source photograph',details:await page.locator('.render-details').innerText()});
 page.off('pageerror',onError); if(errors.length) throw new Error(errors.join('\n'));
} } finally {await browser.close();}
await mkdir('data/validation/observations',{recursive:true});
await writeFile('data/validation/observations/local-previews.json',JSON.stringify({browser:'headed installed Google Chrome',results},null,2));
'''
    import os
    env = dict(os.environ, GS_OBSERVATION_IDS=json.dumps(ids), GS_OBSERVATION_BASE=base_url)
    subprocess.run(['node', '--input-type=module', '-e', js], cwd=ROOT, env=env, check=True)


REPORT_HTML = r'''<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Groundshift · Mapillary 관측 기록</title>
<style>
:root{font-family:system-ui,-apple-system,sans-serif;color:#213526;background:#f4f3ec;color-scheme:light}*{box-sizing:border-box}body{max-width:1540px;margin:auto;padding:32px}header{display:flex;justify-content:space-between;gap:24px;align-items:center}h1{font-size:36px;letter-spacing:-1.5px;margin:12px 0}h2{font-size:24px;margin:36px 0 12px}p{line-height:1.7;max-width:960px;color:#51604f}a{color:#496333}.eyebrow{font-size:12px;letter-spacing:2px}.badge{padding:10px 14px;border:1px solid #b9ba9c;border-radius:30px;font-size:12px}.status{background:#e7e9dc;padding:14px 20px;border-left:3px solid #78904c;line-height:1.7;margin:20px 0}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}figure{margin:0;background:#e9e9df;border:1px solid #d1d6c5;border-radius:12px;overflow:hidden}figure img{display:block;width:100%;aspect-ratio:1;object-fit:contain;background:#14191b}figcaption{padding:12px;font-size:14px;line-height:1.5}figcaption strong{display:block}nav,.links,.tools{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:20px 0}button{font:inherit;cursor:pointer;border:1px solid #b8c1a8;background:transparent;border-radius:24px;padding:10px 18px;color:#263a28}button[aria-pressed=true]{background:#263c2a;color:white}button:focus-visible,a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #ba701b;outline-offset:3px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px;text-align:left;border-bottom:1px solid #d3d7ca;vertical-align:top}td small{display:block;max-width:600px}caption{text-align:left;line-height:1.7;padding:8px 0}.blend{position:relative;max-width:512px}.blend img+img{position:absolute;inset:0;opacity:.5}.tools input{width:240px}.small{font-size:13px}details{border:1px solid #d1d6c5;border-radius:12px;padding:18px;margin-top:24px}summary{cursor:pointer;font-weight:650}footer{font-size:12px;line-height:1.8;border-top:1px solid #ccd0c1;padding-top:24px;margin-top:44px;color:#596454}code{overflow-wrap:anywhere}.failure{color:#8f3f24}.pass{color:#366738}@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:550px){body{padding:24px 14px}header{display:block}h1{font-size:29px}.grid{grid-template-columns:1fr}.badge{display:inline-block}td,th{padding:9px}}
</style>
<div class="links"><a href="/">← 모든 장면</a><a href="#worlds">GS 실험 결과</a><a href="#history">전체 실행 기록</a></div>
<header><div><div class="eyebrow">GROUNDSHIFT / OBSERVATION / 2026.11.05</div><h1>실제로 본 곳과, 모델이 채운 곳.</h1></div><span class="badge">품질과 상관없이 공개하는 실험 관측면</span></header>
<p>연속 360° 사진 9장으로 카메라를 추정하고 이 Mac의 Metal에서 GS를 학습했습니다. 중간 촬영 위치의 사진을 GS RGB 학습에서 빼고, 빈 영역을 로컬 디퓨전으로 채워 실제 사진과 비교했습니다. 잘못 나온 결과와 중단된 시도도 아래에서 확인할 수 있습니다.</p>
<p class="small">Cicero101 · Mapillary / Wikimedia Commons · 베이징 · 2025-05-27 · 7,680 × 3,840 · CC-BY-SA-4.0. 약 11.3 m 구간의 1초 간격 9장입니다. 전 세계에서 가장 조밀한 지역이라는 주장은 하지 않습니다.</p>
<div class="status"><strong class="pass">GPU 학습·추론·내보내기: PASS</strong> · <strong class="failure">장소 복원 품질: FAIL</strong> · <strong>생성 시점 간 3D 일관성: NOT RUN</strong><br>실행 성공과 품질 판정은 별개입니다. 원본에 없는 사람·간판, 늘어진 형상, 빈 영역이 남아 있습니다.</div>
<nav aria-label="실험 선택"><button id="stereo" aria-pressed="true">사진 사이를 채우기</button><button id="gs" aria-pressed="false">GS의 작은 빈틈 채우기</button></nav>
<p id="description"></p>
<div class="grid">
<figure><img id="real" alt="따로 보관한 실제 타깃 사진"><figcaption><strong>실제 촬영 사진</strong>워핑·디퓨전 입력에는 쓰지 않은 비교 사진. 포즈 추정에는 포함되었습니다.</figcaption></figure>
<figure><img id="input" alt="빈 영역을 채우기 전 입력"><figcaption><strong id="inputTitle"></strong><span id="inputCaption"></span></figcaption></figure>
<figure><img id="mask" alt="흰색이 생성 대상인 마스크"><figcaption><strong>생성 마스크</strong>흰색은 디퓨전 대상입니다. 검증된 3D 빈 공간 지도가 아닙니다.</figcaption></figure>
<figure><img id="completed" alt="로컬 디퓨전으로 채운 결과"><figcaption><strong>로컬 디퓨전 결과</strong><span id="resultCaption"></span></figcaption></figure>
</div><div id="finding" class="status"></div>
<div class="scroll"><table><caption>512 × 512 동일 픽셀 비교. MAE는 낮을수록, PSNR은 높을수록 좋습니다. 이 값만으로 형상이나 사실성을 검증하지 않습니다.</caption><thead><tr><th>처리</th><th>빈 영역 MAE ↓</th><th>전체 PSNR ↑</th></tr></thead><tbody id="rows"></tbody></table></div>
<div class="links"><a id="grayLink" href="images/stereo-gray.png">단순 회색 채우기 이미지 보기 ↗</a></div>
<h2>실제 사진과 겹쳐 보기</h2><p class="small">불투명도를 움직여 생성된 사람·간판과 건물 선의 어긋남을 관찰하세요.</p>
<div class="tools"><label for="opacity">생성 결과 불투명도</label><input id="opacity" type="range" min="0" max="100" value="50"><output id="value" for="opacity">50%</output></div>
<figure class="blend"><img id="under" alt="비교용 실제 사진"><img id="over" alt="겹쳐진 디퓨전 결과"></figure>
<h2 id="worlds">내보낸 GS 장면을 모두 열어 보기</h2><p>9개 신규 실험을 기존 4개 장면과 함께 갤러리에서 볼 수 있습니다. 아래 수치는 저장된 실제 실행 결과입니다. 브라우저 미리보기는 실제 GS 렌더링이며 원본 사진을 대신 사용하지 않았습니다.</p>
<div class="links"><a href="/?world=/worlds/desk/world.json">My desk ↗</a><a href="/?world=/worlds/independent/world.json">Dozer · estimated cameras ↗</a><a href="/?world=/worlds/reconstructed/world.json">Dozer · supplied cameras ↗</a><a href="/?world=/worlds/sample/world.json">Houseplant ↗</a></div>
<div class="scroll"><table><thead><tr><th>장면</th><th>학습</th><th>산출물</th><th>판정</th></tr></thead><tbody>WORLD_ROWS</tbody></table></div>
<p class="small">20,000단계 실험은 학습량과 최대 용량을 함께 바꿨습니다. 10,000단계 대비 PSNR 14.72 → 12.68 dB로 악화했습니다. 실제 48장 + 생성 1장으로 실행한 2,000단계 시험은 통합 동작 확인이며 품질 개선을 입증하는 공정한 비교가 아닙니다.</p>
<h2 id="history">실패와 중단을 포함한 실행 이력</h2>
<div class="status">처음에는 한 파노라마에서 나온 가상 카메라를 독립적으로 추정해 중심이 어긋났습니다. 이 결과는 <strong>형상 FAIL</strong>로 남기고 초기 학습을 중단했습니다. 동일 촬영 위치의 카메라를 고정 리그로 묶은 수정판은 54/54 카메라 추정에 성공했습니다. 첫 디퓨전 실행은 API 변경 때문에 추론 전에 실패했고 수정판에서 MPS 추론이 실제 실행되었습니다.</div>
<p class="small">각 행의 PASS는 해당 명령의 실행·내보내기 또는 계산 성공을 뜻합니다. 전체 품질 PASS가 아닙니다. NOT RECORDED는 독립 상태 보고서가 없는 준비 입력/재사용 디렉터리입니다. CANCELLED는 중단, NOT RUN은 실행하지 않음을 뜻합니다.</p>
<details><summary>HISTORY_COUNT개 단계·시도 기록 펼치기</summary><div class="scroll"><table><thead><tr><th>시도 / 단계</th><th>실행 상태</th><th>실측값 / 한계</th></tr></thead><tbody>HISTORY_ROWS</tbody></table></div></details>
<div class="links"><a href="summary.json">공개 측정값·해시 JSON ↗</a><a href="sources.json">사진별 출처·라이선스 ↗</a><a href="COMMONS_URL">원본 공개 보관함 ↗</a></div>
<footer>원본 사진: Cicero101 / Mapillary, Wikimedia Commons 재배포. <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC-BY-SA-4.0</a>. 비교 사진은 파노라마에서 투영한 수정본이며 GS·워핑·디퓨전 결과는 각각 추가 변형을 거쳤습니다. 이 라이선스는 별도의 비공개 책상 영상에 적용되지 않습니다.<br>
디퓨전: stable-diffusion-v1-5/stable-diffusion-inpainting · revision <code>8a4288a76071f7280aedbdb3253bdb9e9d5d84bb</code> · <a href="MODEL_LICENSE_URL">CreativeML OpenRAIL-M</a>. MPS, 512², seed 41, 설정 20단계 / 실제 19회 denoising. 각 추론 38.26초·39.57초. 모델에는 별도 이용 조건이 있습니다.<br>
포즈와 초기 형상 및 색은 전체 사진으로 추정했습니다. 이것은 외관 홀드아웃이며 독립적인 카메라·형상 검증이 아닙니다. 사진 타깃 한 곳의 픽셀 오차는 여러 생성 시점의 3D 일관성을 증명하지 않습니다. 원본 비공개 영상, 로컬 로그와 모델 가중치는 이 사이트에 포함되지 않습니다.</footer>
<script>
const cases={stereo:{view:'04',description:'앞뒤 두 촬영 위치의 사진을 추정 깊이로 중간 시점에 옮겼습니다. 24.88%가 채워져 나머지 75.12%를 디퓨전 대상으로 삼았습니다.',inputTitle:'관측 사진을 옮긴 결과',inputCaption:'검은 부분은 채우지 못한 영역입니다. 실제 검은 표면이 아닙니다.',resultCaption:'75.12% 생성 마스크 · MPS 39.57초',finding:'빈 공간은 채워졌지만 실제 사진에 없는 사람과 간판도 만들어졌습니다. 단순 회색 채우기보다 MAE는 낮고 PSNR은 조금 나쁩니다. 충실한 장소 복원 품질은 FAIL입니다.',rows:[['검은 빈 영역 유지','104.04','7.542 dB'],['단순 회색 채우기','57.65','12.388 dB'],['디퓨전','50.16','12.371 dB']]},gs:{view:'02',description:'실제 사진 48장으로 10,000단계 학습한 GS를 중간 시점에서 렌더링했습니다. 불투명도가 낮은 2.21% 영역만 채웠습니다.',inputTitle:'GS 렌더링 입력',inputCaption:'새로 촬영한 사진이 아니라 맥에서 학습한 GS를 렌더링한 이미지입니다.',resultCaption:'2.21% 생성 마스크 · MPS 38.26초',finding:'작은 빈틈의 오차는 줄었지만 늘어지는 형상과 잔상은 남았습니다. 낮은 불투명도 마스크는 이미 불투명하게 잘못 생성된 GS 형상을 잡아내지 못합니다.',rows:[['GS 원본','59.43','14.717 dB'],['단순 회색 채우기','68.23','14.653 dB'],['디퓨전','55.47','14.737 dB']]}};
const el=id=>document.getElementById(id);
function select(key){const c=cases[key];['stereo','gs'].forEach(k=>el(k).setAttribute('aria-pressed',String(k===key)));el('real').src=el('under').src='images/real-'+c.view+'.png';['input','mask','completed'].forEach(k=>el(k).src='images/'+key+'-'+k+'.png');el('over').src=el('completed').src;el('grayLink').href='images/'+key+'-gray.png';['description','inputTitle','inputCaption','resultCaption','finding'].forEach(k=>el(k).textContent=c[k]);el('rows').replaceChildren(...c.rows.map(row=>{const tr=document.createElement('tr');row.forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td)});return tr}));}
['stereo','gs'].forEach(k=>el(k).addEventListener('click',()=>select(k)));el('opacity').addEventListener('input',e=>{el('over').style.opacity=e.target.value/100;el('value').value=e.target.value+'%'});select('stereo');
</script></html>'''


def prepare_report(worlds, history):
    out = PUBLIC / 'experiments/mapillary'
    (out / 'images').mkdir(parents=True, exist_ok=True)
    image_inventory = []
    for name, source in IMAGES.items():
        src = ROOT / 'data/jobs' / source
        dst = out / 'images' / name
        shutil.copyfile(src, dst)
        image_inventory.append(dict(path='images/' + name, sha256=sha(dst), bytes=dst.stat().st_size))
    sources = read_json(ROOT / 'scripts/samples/mapillary-beijing.json')
    # Public source attribution contains no need for geographic probe fields.
    sources = {k: sources[k] for k in ['title', 'sequence', 'source', 'author', 'license', 'licenseUrl', 'selection', 'knownLimitations', 'images']}
    for record in sources['images']:
        record.pop('gps', None)
    write_json(out / 'sources.json', sources)
    summary = dict(version=1, observationDate='2026-11-05', machine='Apple M2 / 16 GB unified memory',
        scope='All distinct local world exports plus failed and cancelled experiment summaries; local reconstruction only.',
        quality='Mapillary reconstruction quality FAIL; actual GPU execution PASS; multi-view generated consistency NOT RUN.',
        worlds=worlds, history=history, images=image_inventory,
        model=dict(repository='stable-diffusion-v1-5/stable-diffusion-inpainting', revision='8a4288a76071f7280aedbdb3253bdb9e9d5d84bb', license='CreativeML OpenRAIL-M', licenseUrl=MODEL_LICENSE, seed=41),
        caveat='Appearance holdout only: all panoramas supplied SfM poses and initialization colors. This is not independent geometry validation.')
    assert_public_text(json.dumps(summary))
    write_json(out / 'summary.json', summary)
    world_rows = ''.join('<tr><td><a href="/?world=' + w['manifest'] + '">' + html.escape(w['title']) + ' ↗</a></td><td>' + f"{w['trainingImages']} images · {w['steps']:,} steps<br>{w['trainingSeconds']:.2f} s" + '</td><td>' + f"{w['splats']:,} splats · {w['bytes']/1e6:.2f} MB" + '</td><td>' + w['execution'] + ' execution<br>' + w['quality'] + '</td></tr>' for w in worlds)
    history_rows = []
    for record in history:
        detail = []
        for k, v in record.items():
            if k not in ['trial', 'stage', 'execution', 'artifact']:
                detail.append(f'{k}: {v:.3f}' if isinstance(v, float) else f'{k}: {v}')
        if 'artifact' in record:
            detail.append(f"{record['artifact'].get('splats', '?')} splats")
        history_rows.append('<tr><td>' + html.escape(record['trial']) + '<small>' + html.escape(record['stage']) + '</small></td><td>' + html.escape(str(record['execution'])) + '</td><td>' + '<br>'.join(html.escape(x) for x in detail) + '</td></tr>')
    page = REPORT_HTML.replace('WORLD_ROWS', world_rows).replace('HISTORY_ROWS', ''.join(history_rows)).replace('HISTORY_COUNT', str(len(history))).replace('COMMONS_URL', html.escape(COMMONS, quote=True)).replace('MODEL_LICENSE_URL', html.escape(MODEL_LICENSE, quote=True))
    assert_public_text(page)
    (out / 'index.html').write_text(page)
    return ['experiments/mapillary/' + x for x in ['index.html', 'summary.json', 'sources.json']] + ['experiments/mapillary/images/' + x for x in IMAGES]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-previews', action='store_true')
    parser.add_argument('--base-url', default='http://127.0.0.1:4317')
    args = parser.parse_args()
    worlds = prepare_worlds()
    history = collect_history()
    files = prepare_report(worlds, history)
    definitions = [dict(id=t[0], source='data/jobs/' + t[1], asset='scene.ply', format='ply', credits=['SOURCE_LICENSE']) for t in TRIALS]
    write_json(SPEC, dict(version=1, worlds=definitions, files=files))
    catalog_path = PUBLIC / 'worlds/catalog.json'
    catalog = read_json(catalog_path)
    ids = {t[0] for t in TRIALS}
    catalog['scenes'] = [s for s in catalog['scenes'] if s['id'] not in ids]
    catalog['scenes'] += [dict(id=slug, title=title, description=description, category='experiment', manifestPath=f'/worlds/{slug}/world.json', thumbnailPath=f'/worlds/{slug}/preview.jpg', detail=detail) for slug, _, title, detail, description in TRIALS]
    write_json(catalog_path, catalog)
    if args.render_previews:
        render_previews(args.base_url, [t[0] for t in TRIALS])
    # Ensure every current distinct local world binary is represented in the catalog.
    source_hashes = {sha(p.parent / read_json(p)['assets'][0]['path']) for p in (ROOT / 'data/jobs').glob('**/world/world.json')}
    public_hashes = set()
    for scene in catalog['scenes']:
        manifest = PUBLIC / scene['manifestPath'].lstrip('/')
        world = read_json(manifest)
        public_hashes.add(sha(manifest.parent / world['assets'][0]['path']))
    if source_hashes - public_hashes:
        raise ValueError('Some distinct exported job artifacts are missing from catalog')
    print(json.dumps(dict(preparedWorlds=len(worlds), catalogWorlds=len(catalog['scenes']), distinctJobWorlds=len(source_hashes), publicExperimentFiles=len(files), historyRows=len(history), previews='rendered' if args.render_previews else 'existing previews required'), indent=2))


if __name__ == '__main__':
    main()
