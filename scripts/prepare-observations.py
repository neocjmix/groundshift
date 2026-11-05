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
# These distinct exports supplement the four existing catalog worlds.
TRIALS = [
 ('beijing-10k', 'mapillary-beijing-rig-baseline-10000/world', 'Beijing · observed 10k', '48 real crops · 150,000 splats · Quality FAIL', 'Real photographs only; fixed panorama rigs. Blurred structures and stretched geometry remain.'),
 ('beijing-generated', 'mapillary-beijing-generated-gs-smoke/world', 'Beijing · generated input', '48 real + 1 generated view · 2,000 steps · Quality FAIL', 'Local diffusion output was included in Metal training. An integration experiment, not evidence of improved reconstruction.'),
 ('beijing-depth', 'mapillary-depth-gs-10000-20261105/world', 'Beijing · depth-guided generated view', '48 real + 1 depth-guided synthetic view · 10,000 Metal steps · Quality FAIL', 'Observed pixels were reprojected with locally calibrated relative depth; masked MPS diffusion supplied the remaining pixels. The generated view has an estimated, reused pose and does not establish new geometry.'),
 ('beijing-20k', 'mapillary-beijing-rig-baseline-20000/world', 'Beijing · capacity 20k', '750,000 splats · 69 MB · Quality FAIL', 'Longer training and larger capacity together; held-view PSNR fell from 14.72 to 12.68 dB.'),
 ('beijing-2k', 'mapillary-beijing-rig-baseline/world', 'Beijing · observed 2k', '48 real crops · 7,015 splats · Quality FAIL', 'The first constrained-rig Gaussian baseline. Training and export worked, while the reconstructed appearance remained blurry.'),
 ('beijing-video-baseline', 'mapillary-video-4to6-20261105/gs-real48-10000/world', 'Beijing · matched real-only baseline', '48 real crops · 10,000 Metal steps · Quality FAIL', 'The matched real-only baseline for the 65-frame panorama experiment. Its rendered building edges remain blurry; target #5 geometry participated in all-image SfM.'),
 ('beijing-video-rife', 'mapillary-video-4to6-20261105/gs-rife6-10000/world', 'Beijing · 65-frame interpolation GS', '48 real + 6 generated crops · Quality FAIL', 'The generated midpoint was added to Metal Gaussian training. It renders but adds streaked geometry and did not improve either inspected target view.'),
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
HISTORY_TRIALS += ['mapillary-depth-stereo-view02-corrected-20261105', 'mapillary-depth-warp-view02-v3-20261105', 'mapillary-depth-warp-comparison-20261105', 'mapillary-depth-inpaint-view02-20261105', 'mapillary-depth-inpaint-vs-real-20261105', 'mapillary-depth-inpaint-vs-gray-20261105', 'mapillary-depth-augmented-view02-20261105', 'mapillary-depth-gs-10000-20261105']
HISTORY_TRIALS += [f'mapillary-depth-render-view{view}-{kind}' for view in ('01', '03')
                   for kind in ('baseline', 'generated', 'comparison')]

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
        elif slug in ('beijing-video-baseline', 'beijing-video-rife'):
            provenance['notes'] = ('Source: Cicero101 / Mapillary 360 photographs mirrored by Wikimedia Commons, CC-BY-SA-4.0. '
                + ('This is the matched 48-real-view baseline for the RIFE interpolation experiment. No synthetic training pixels were used. ' if slug == 'beijing-video-baseline' else
                   'Two 7680x3840 source panoramas numbered 4 and 6 were resized to 2048x1024 and interpolated with Practical-RIFE 4.25 on Apple MLX into 65 frames. The generated midpoint was projected into six 512x512 pinhole views. Training combined 48 observed views with these six generated views. ')
                + 'The target rig camera matrices were copied from all-image SfM of real panorama number 5; generated pixels did not estimate or validate those poses. '
                'This is an appearance experiment with possible pose mismatch and foreground ghosting, not an independently verified 3D camera path. '
                'RIFE is optical-flow frame interpolation, not diffusion. The 65-frame video and failed diffusion acquisition are documented at /experiments/video-4to6/. '
                'Gravity and metric scale are unknown. Asset coordinates preserve the actual Brush export. '
                'Quality FAIL after actual browser rendering: blurry or streaked geometry. Successful Metal execution is recorded separately.')
            credit = ('Source photography: Cicero101 / Mapillary, redistributed by Wikimedia Commons. CC-BY-SA-4.0: https://creativecommons.org/licenses/by-sa/4.0/\n'
                + COMMONS + '\nModifications: ' + ('pinhole reprojection and local Brush Gaussian training from 48 real crops. No generated training pixels.' if slug == 'beijing-video-baseline' else
                'resized equirectangular endpoints, RIFE 4.25 MLX optical-flow interpolation, 64-pixel seam blend, pinhole reprojection and local Brush Gaussian training. RIFE code and converted weights are MIT; see https://huggingface.co/mlx-community/RIFE-4.25. Generated content may be fictional and does not prove place fidelity.') + ' '
                'Per-image source attribution and the interpolated video are at /experiments/video-4to6/.\n')
        elif slug.startswith('beijing-'):
            # Do not retain earlier-stage wording claiming no reconstruction was performed.
            notes = ('Source: nine consecutive 7680x3840 panoramas by Cicero101 on Mapillary, mirrored by Wikimedia Commons; 2025-05-27 05:11:05–13, timezone unspecified. This is a small dense candidate, not a global density maximum. The photos were reprojected into overlapping pinhole views, then world cameras were estimated with fixed co-located spherical rigs. Forty-eight observed crops were used for Brush Metal training. Poses and initialization colors used all nine panoramas: this is only an appearance holdout, not independent geometry validation. Gravity and metric scale are unknown. Coordinates and transforms preserve the measured export. Quality FAIL: blurry, streaked or incomplete geometry. ')
            if slug == 'beijing-generated':
                old = provenance['notes']
                notes += old[old.index('Current augmented dataset:'):]
            elif slug == 'beijing-depth':
                notes += ('One 512x512 generated training view used source photos pano_000004 and pano_000006 view 02, '
                    'Depth Anything V2 Small on MPS, sparse SfM inverse-depth calibration, source-consistency gating, '
                    'and Stable Diffusion 1.5 Inpainting on MPS for 34.31% missing pixels. Its camera is the existing '
                    'all-image SfM pose for pano_000005 view 02, not independently estimated from generated RGB. '
                    'See /experiments/depth-warp/ for real/synthetic labels and matched renders.')
            else:
                notes += 'No diffusion-generated training pixels were used in this variant.'
            provenance['notes'] = notes
            credit = ('Source photography: Cicero101 / Mapillary, redistributed by Wikimedia Commons. CC-BY-SA-4.0: https://creativecommons.org/licenses/by-sa/4.0/\n' + COMMONS + '\nModifications: perspective reprojection, camera estimation, Gaussian reconstruction and rendered preview. Per-image attribution is in /experiments/mapillary/sources.json.\n')
            if slug in ('beijing-generated', 'beijing-depth'):
                credit += 'One synthetic training view used Stable Diffusion 1.5 Inpainting. Model terms: CreativeML OpenRAIL-M, ' + MODEL_LICENSE + '. Generated pixels are hypotheses, not observed geometry.\n'
            if slug == 'beijing-depth':
                credit += 'Source-crop relative depth used Depth Anything V2 Small, Apache-2.0: https://github.com/DepthAnything/Depth-Anything-V2.\n'
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
            stamp = data.get('finishedAt') or data.get('startedAt') or data.get('createdAt')
            if stamp:
                item['recordedAt'] = stamp
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
        dict(trial='Previous generated-view consistency', stage='quality validation', execution='NOT RUN', detail='The earlier one-view diffusion input is an integration test, not validated multi-view novel-view synthesis.'),
    ])
    video_job = ROOT / 'data/jobs/mapillary-video-4to6-20261105'
    rife = read_json(video_job / 'rife-65-periodic/report.json')
    inpaint = read_json(video_job / 'rife-view02-diffusion/report.json')
    baseline = read_json(video_job / 'gs-real48-10000/job.json')
    augmented = read_json(video_job / 'gs-rife6-10000/job.json')
    records.extend([
        dict(trial='Panorama 4→6', stage='RIFE 4.25 MLX 65-frame inference', execution='PASS',
             detail=f"2048x1024; inference {rife['generationSeconds']:.3f} s; optical-flow interpolation, not diffusion."),
        dict(trial='Panorama 4→6', stage='Generated-frame seam blend and MP4 encode', execution=rife['encoding']['status'],
             detail=f"Midpoint edge MAE {rife['seam'][32]['edgeMaeBefore']:.3f} → {rife['seam'][32]['edgeMaeAfter']:.3f}; source endpoints byte-identical."),
        dict(trial='Panorama 4→6', stage='Exploratory bicycle-region MPS inpainting', execution=inpaint['status'],
             detail=f"One 512x512 crop; {inpaint['inferenceSeconds']:.3f} s; distorted bicycle remained, so output was not used for video or GS training."),
        dict(trial='Panorama 4→6', stage='Real-only matched baseline GS', execution=baseline['status'],
             detail=f"48 real photographs; {baseline['options']['steps']:,} Metal steps."),
        dict(trial='Panorama 4→6', stage='RIFE-augmented GS', execution=augmented['status'],
             detail=f"48 real + 6 generated crops at measured target rig pose; {augmented['options']['steps']:,} Metal steps."),
        dict(trial='LTX-2.3 MLX', stage='full-sphere video diffusion candidate', execution='NOT RUN',
             detail='Local code and CLI verified; selected q8 model files total 49,986,854,521 bytes before text encoder. Slow model transfer stopped; no inference.'),
        dict(trial='RIFE generated multi-view consistency', stage='quality validation', execution='NOT RUN',
             detail='Six crops share one measured rig pose; other 64 generated panoramas have no independently estimated camera poses.'),
    ])
    records.sort(key=lambda item: item.get('recordedAt', ''), reverse=True)
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
<div class="links"><a href="/">← 모든 장면</a><a href="/experiments/video-4to6/">65장 구면 보간 실험 ↗</a><a href="#worlds">GS 실험 결과</a><a href="#history">전체 실행 기록</a></div>
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
<h2 id="worlds">내보낸 GS 장면을 모두 열어 보기</h2><p>EXPERIMENT_COUNT개 실험을 기존 4개 장면과 함께 갤러리에서 볼 수 있습니다. 아래 수치는 저장된 실제 실행 결과입니다. 브라우저 미리보기는 실제 GS 렌더링이며 원본 사진을 대신 사용하지 않았습니다.</p>
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
    page = REPORT_HTML.replace('WORLD_ROWS', world_rows).replace('HISTORY_ROWS', ''.join(history_rows)).replace('HISTORY_COUNT', str(len(history))).replace('EXPERIMENT_COUNT', str(len(TRIALS))).replace('COMMONS_URL', html.escape(COMMONS, quote=True)).replace('MODEL_LICENSE_URL', html.escape(MODEL_LICENSE, quote=True))
    assert_public_text(page)
    (out / 'index.html').write_text(page)
    return ['experiments/mapillary/' + x for x in ['index.html', 'summary.json', 'sources.json']] + ['experiments/mapillary/images/' + x for x in IMAGES]


def prepare_video_report(worlds):
    """Publish only selected licensed stills and the generated RIFE clip."""
    from shutil import which
    job = ROOT / 'data/jobs/mapillary-video-4to6-20261105'
    source = job / 'rife-65-periodic'
    generation = read_json(source / 'report.json')
    preparation = read_json(job / 'preparation.json')
    if generation['encoding']['status'] != 'PASS' or generation['frameCount'] != 65 or generation['imageSize'] != [2048, 1024]:
        raise ValueError('Expected completed 65-frame 2048x1024 panorama run')
    if not any(w['id'] == 'beijing-video-rife' and w['execution'] == 'PASS' for w in worlds):
        raise ValueError('Video experiment GS scene has not been exported')
    if sha(source / 'interpolation.mp4') != generation['video']['sha256']:
        raise ValueError('Video hash differs from local generation report')
    if [x['preparedSha256'] for x in preparation['inputs']] != [sha(source / 'frames/frame_000.png'), sha(source / 'frames/frame_064.png')]:
        raise ValueError('Photo endpoints are not byte-identical in the video frame sequence')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise FileNotFoundError('FFmpeg required to strip metadata and prepare licensed public thumbnails')
    out = PUBLIC / 'experiments/video-4to6'
    (out / 'images').mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / 'interpolation.mp4', out / 'interpolation.mp4')
    originals = sorted((ROOT / 'data/samples/mapillary-beijing/images').glob('*.jpg'))
    if len(originals) != 9:
        raise ValueError('Expected the nine acquired source panoramas')
    sample = read_json(ROOT / 'scripts/samples/mapillary-beijing.json')
    for index in (4, 5, 6):
        if sha(originals[index]) != sample['images'][index]['sha256']:
            raise ValueError('Source photograph differs from licensed sample inventory')
    frames = {'start': source / 'frames/frame_000.png',
              'quarter': source / 'frames/frame_016.png',
              'midpoint': source / 'frames/frame_032.png',
              'threequarter': source / 'frames/frame_048.png',
              'finish': source / 'frames/frame_064.png',
              'crossfade': job / 'crossfade.png',
              'observed-middle': originals[5],
              'inpaint-input': job / 'rife-view02-diffusion/reference.png',
              'inpaint-mask': job / 'rife-view02-diffusion/mask.png',
              'inpaint-result': job / 'rife-view02-diffusion/completed.png'}
    inpaint = read_json(job / 'rife-view02-diffusion/report.json')
    if inpaint['status'] != 'PASS' or inpaint['gpuInference'] != 'PASS':
        raise ValueError('Expected completed exploratory MPS inpaint')
    images = []
    for name, src in frames.items():
        dst = out / 'images' / f'{name}.jpg'
        scale = '512:512:flags=lanczos' if name.startswith('inpaint-') else '1024:512:flags=lanczos'
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src),
                        '-vf', 'scale=' + scale, '-map_metadata', '-1',
                        '-frames:v', '1', '-q:v', '2', str(dst)], check=True)
        kind = ('observed-source' if name in ('start', 'finish', 'observed-middle') else
                'simple-blend-control' if name == 'crossfade' else
                'inpaint-mask' if name == 'inpaint-mask' else
                'diffusion-completion' if name == 'inpaint-result' else
                'generated-interpolation')
        images.append({'path': f'images/{name}.jpg', 'bytes': dst.stat().st_size,
                       'sha256': sha(dst), 'kind': kind})
    run_log = (job / 'rife-run.log').read_text()
    peak_match = re.search(r'(\d+)\s+peak memory footprint', run_log)
    peak = int(peak_match.group(1)) if peak_match else None
    comparison = read_json(job / 'midpoint-comparison.json')
    posed = []
    for view in ('02', '04'):
        baseline_render = read_json(job / f'render-real48-view{view}/report.json')
        generated_render = read_json(job / f'render-rife6-view{view}/report.json')
        metrics = read_json(job / f'compare-view{view}/report.json')
        if any(value['status'] != 'PASS' for value in (baseline_render, generated_render, metrics)):
            raise ValueError(f'Expected actual headed-Chrome render and photometric comparison for view {view}')
        full = metrics['regions']['full']
        posed.append({'view': view, 'reference': 'Separately held-out real photo 5 crop',
                      'baselineMae': round(full['baseline']['mae'], 3),
                      'generatedMae': round(full['completed']['mae'], 3),
                      'baselinePsnrDb': round(full['baseline']['psnrDb'], 3),
                      'generatedPsnrDb': round(full['completed']['psnrDb'], 3),
                      'baselineAlphaBelow240Fraction': baseline_render['maskedFraction'],
                      'generatedAlphaBelow240Fraction': generated_render['maskedFraction']})
    preview_evidence = ROOT / 'data/validation/observations/local-previews.json'
    preview_ids = set()
    if preview_evidence.is_file():
        preview_ids = {result['id'] for result in read_json(preview_evidence)['results']
                       if result['render'] == 'PASS' and not result['errors']}
    local_browser = 'PASS' if {'beijing-video-baseline', 'beijing-video-rife'} <= preview_ids else 'NOT RUN'
    world = next(w for w in worlds if w['id'] == 'beijing-video-rife')
    public = {
        'schemaVersion': 1, 'experiment': 'Mapillary panoramas 4→6, 65-frame RIFE interpolation',
        'priority': 'Plausible generated scenery; exact place fidelity is secondary',
        'status': {'frameGeneration': 'PASS', 'seamRepair': 'PASS', 'videoEncoding': 'PASS',
                   'metalGaussianTraining': world['execution'], 'localBrowserRendering': local_browser,
                   'publicBrowserRendering': 'NOT RUN at archive creation; see deployment evidence',
                   'gaussianVisualQuality': 'FAIL', 'LTXVideoDiffusion': 'NOT RUN'},
        'sources': [{'index': index, 'imageId': sample['images'][index]['image_id'],
                     'commonsPage': sample['images'][index]['commons_page'], 'sha256': sample['images'][index]['sha256']}
                    for index in (4, 5, 6)],
        'sourceLicense': {'author': 'Cicero101 / Mapillary', 'license': 'CC-BY-SA-4.0',
                          'licenseUrl': sample['licenseUrl']},
        'generation': {'engine': 'Practical-RIFE 4.25 via MLX', 'isDiffusion': False,
                       'modelRevision': generation['model']['revision'], 'modelWeightsSha256': generation['model']['weightsSha256'],
                       'codeRevision': '764b89be56497fb26243d1de75f2957f3889e5d3',
                       'license': 'MIT', 'frames': 65, 'imageSize': [2048, 1024], 'fps': 24,
                       'gpuInferenceSeconds': generation['generationSeconds'],
                       'wholeProcessPeakFootprintBytes': peak, 'seamBandPixels': generation['seamBandPixels'],
                       'midpointEdgeMaeBefore': generation['seam'][32]['edgeMaeBefore'],
                       'midpointEdgeMaeAfter': generation['seam'][32]['edgeMaeAfter'],
                       'videoBytes': generation['video']['bytes'], 'videoSha256': generation['video']['sha256']},
        'midpointComparison': {'meaning': 'Pixel error against separately loaded observed panorama 5; not a plausibility or geometry score',
                               'maeCrossfade': comparison['results']['crossfade']['mae'],
                               'maeRife': comparison['results']['rife_mid_periodic']['mae'],
                               'psnrCrossfadeDb': comparison['results']['crossfade']['psnrDb'],
                               'psnrRifeDb': comparison['results']['rife_mid_periodic']['psnrDb']},
        'exploratoryDiffusion': {'status': 'PASS for local 2D inference; visual repair not accepted',
                                 'scope': 'One 512x512 crop, foreground bicycle mask only; not used in Gaussian training or panorama video',
                                 'model': inpaint['model']['repository'], 'modelRevision': inpaint['model']['revision'],
                                 'license': inpaint['model']['license'], 'licenseUrl': inpaint['model']['licenseUrl'],
                                 'device': inpaint['device'], 'inferenceSeconds': inpaint['inferenceSeconds'],
                                 'outputSha256': inpaint['output']['sha256'],
                                 'assessment': 'Foreground bicycle remained visibly distorted; no convincing geometry repair'},
        'reconstruction': {'world': world['manifest'], 'trainingImages': world['trainingImages'],
                           'syntheticImages': 6, 'steps': world['steps'], 'splats': world['splats'],
                           'trainingElapsedSeconds': world['trainingSeconds'], 'worldAssetSha256': world['sha256'],
                           'poseProvenance': 'Six locally estimated all-image SfM poses involving the real middle panorama; generated pixels did not estimate or validate pose',
                           'posedViewComparison': posed,
                           'assessment': 'Both worlds rendered in headed Chrome. The generated-view world remained blurry or streaked and had higher pixel error at two inspected target directions. 3D plausibility improvement FAIL.'},
        'LTXVideoDiffusion': {'status': 'NOT RUN', 'reason': 'Selected q8 model weights alone require 49,986,854,521 bytes, plus Gemma; acquisition was stopped after a measured 10 MiB HTTP range transferred only 5,720,941 bytes in 30 seconds. No video diffusion inference took place.',
                              'candidateModel': 'dgrauet/ltx-2.3-mlx-q8', 'candidateRevision': '69f8f11996b7b2ee54e82d0db7a5acad14b8685d',
                              'modelLicense': 'LTX-2 Community License Agreement',
                              'modelLicenseUrl': 'https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2'},
        'limitations': ['RIFE is flow interpolation, not diffusion or new 3D view synthesis.',
                        'The 65 frames are temporal interpolation images, not 65 separately measured camera positions.',
                        'Foreground bicycles show ghosting and the source photographs retain a yellow nadir band.',
                        'All-image SfM used the observed middle photograph for pose and initialization, so there is no independent geometry test.'],
        'publicImages': images,
    }
    assert_public_text(json.dumps(public))
    write_json(out / 'summary.json', public)
    scenic = ''.join(f'<figure><img src="images/{name}.jpg" alt="{label}"><figcaption>{label}</figcaption></figure>'
                     for name, label in [('start','출발 · 실제 사진 #4'), ('quarter','¼ · 생성'),
                                         ('midpoint','½ · 생성 / GS 입력'), ('threequarter','¾ · 생성'),
                                         ('finish','도착 · 실제 사진 #6'), ('crossfade','단순 50% 겹침 기준'),
                                         ('observed-middle','비교 · 실제 사진 #5')])
    source_links = ' · '.join(f'<a href="{html.escape(sample["images"][i]["commons_page"], quote=True)}">원본 #{i}</a>' for i in (4, 5, 6))
    page = f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Groundshift · 65개 구면 프레임 실험</title>
<style>:root{{font-family:system-ui,-apple-system,sans-serif;background:#f4f3ec;color:#223627;color-scheme:light}}*{{box-sizing:border-box}}body{{max-width:1320px;margin:auto;padding:28px}}a{{color:#426534}}h1{{font-size:clamp(30px,5vw,60px);letter-spacing:-.04em;line-height:1.05;max-width:850px;margin:16px 0}}h2{{margin-top:42px}}p{{line-height:1.65;color:#526252;max-width:960px}}nav{{display:flex;gap:16px;flex-wrap:wrap}}.eyebrow{{font-size:12px;letter-spacing:.18em}}.status{{padding:16px 20px;background:#e6e9dc;border-left:4px solid #8da16e;line-height:1.6;margin:20px 0}}video{{display:block;width:100%;max-height:70vh;background:#142018;border-radius:12px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}figure{{margin:0;background:#e5e8df;border-radius:10px;overflow:hidden}}figure img{{display:block;width:100%;aspect-ratio:2/1;object-fit:contain}}figcaption{{padding:12px 16px;font-size:14px}}small{{color:#647164}}@media(max-width:700px){{body{{padding:18px}}.grid{{grid-template-columns:1fr}}}}</style>
<nav><a href="/">← 장면 갤러리</a><a href="/experiments/mapillary/">이전 Mapillary 실험</a><a href="/?world=/worlds/beijing-video-baseline/world.json">실제 사진 GS ↗</a><a href="/?world={world['manifest']}">보간 추가 GS ↗</a></nav>
<div class="eyebrow">GROUNDSHIFT / 360° INTERPOLATION / LOCAL M2 METAL</div><h1>두 장 사이에 65개의 구면 프레임을 만들다.</h1>
<p>연속 촬영된 파노라마 #4와 #6을 양 끝에 놓고, 맥에서 중간 프레임을 생성했습니다. 실제 #5 사진은 생성 입력에서 빼고 나중에 비교용으로만 보여줍니다. 이번에는 장소를 정확히 맞히는 것보다 그럴듯한 풍경과 움직임을 우선 봅니다.</p>
<div class="status"><strong>프레임 생성 PASS</strong> · 65장 / 2048×1024 / 24fps · Apple MLX 추론 {generation['generationSeconds']:.1f}초 · <strong>GS Metal 학습 {world['execution']}</strong><br>영상 확산 모델 LTX는 가중치 다운로드를 완료하지 못해 추론 <strong>NOT RUN</strong>입니다. 이 영상은 <strong>RIFE 광학 흐름 보간</strong> 결과이며 디퓨전 생성물로 표시하지 않습니다.</div>
<video controls playsinline muted preload="metadata" poster="images/midpoint.jpg"><source src="interpolation.mp4" type="video/mp4">브라우저에서 MP4 재생을 지원하지 않습니다.</video>
<p><small>원본 구면 사진을 2048×1024로 축소하고 65프레임을 만든 뒤, 생성 프레임의 좌우 64픽셀 경계를 부드럽게 연결했습니다. 실제 사진인 첫·마지막 프레임은 원본 준비 파일과 바이트 단위로 같습니다. 이 영상의 카메라 경로는 측정되지 않았습니다.</small></p>
<h2>선택한 시점</h2><div class="grid">{scenic}</div>
<p>건물과 보행로는 이어지지만 가까운 자전거는 겹쳐 보이고, 아래 노란 띠는 원본 360 카메라의 바닥 가림입니다. 실제 중간 사진과의 2048×1024 픽셀 비교에서 단순 겹침은 PSNR {comparison['results']['crossfade']['psnrDb']:.3f} dB, RIFE는 {comparison['results']['rife_mid_periodic']['psnrDb']:.3f} dB였습니다. 이 수치는 그럴듯함이나 3D 형상의 점수가 아닙니다.</p>
<h2>3D로 내보낸 결과</h2><p>가운데 생성 파노라마를 여섯 90° 시야로 나누어, 실제 #5 사진의 전체 이미지 SfM에서 얻은 위치·방향을 붙였습니다. 나머지 48장은 실제 관측 사진입니다. 이 포즈는 생성 장면에서 새로 검증한 값이 아니므로 3D 형상의 정확도를 뜻하지 않습니다.</p>
<p><a href="/?world=/worlds/beijing-video-baseline/world.json">48장 실제 사진 GS ↗</a> · <a href="/?world={world['manifest']}">48장 실제 + 6장 생성 GS ↗</a> · 각각 10,000 Metal 단계 · 생성 추가 장면 {world['splats']:,} splats / {world['bytes']/1e6:.2f} MB</p>
<p><strong>3D 품질 개선 FAIL.</strong> 같은 추정 카메라 방향 두 곳을 Chrome에서 렌더링해 실제 #5 사진과 비교했습니다. 02방향 MAE는 실제 사진만 학습한 장면 {posed[0]['baselineMae']:.3f} → 생성 뷰 추가 장면 {posed[0]['generatedMae']:.3f}, 04방향은 {posed[1]['baselineMae']:.3f} → {posed[1]['generatedMae']:.3f}로 모두 커졌습니다. 숫자보다 직접 보이는 흐릿한 건물·자전거 형상이 핵심 한계입니다. 사진과의 오차는 장면의 그럴듯함을 완전히 평가하지 않습니다.</p>
<h2>자전거 부분 2D 확산 보정</h2><p>한 시야의 앞쪽 자전거만 마스킹해 M2의 MPS에서 Stable Diffusion 1.5 인페인팅을 실행했습니다. 입력·마스크·결과를 아래에 그대로 둡니다. 결과에서도 자전거가 찌그러져 보여 3D 학습이나 위 영상에는 사용하지 않았습니다. 한 장의 부분 보정은 구면 전체나 여러 시점의 일관성을 증명하지 않습니다.</p>
<div class="grid">{''.join(f'<figure><img src="images/{name}.jpg" alt="{label}"><figcaption>{label}</figcaption></figure>' for name, label in [('inpaint-input','보정 전 생성 자전거 시야'),('inpaint-mask','흰색 생성 마스크'),('inpaint-result','MPS 확산 보정 결과 · 형상 미수용')])}</div>
<h2>출처와 한계</h2><p>{source_links} · Cicero101 / Mapillary, Wikimedia Commons 재배포 · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC-BY-SA-4.0</a>. 이미지와 비디오는 해당 사진의 수정본입니다. RIFE 코드·변환 가중치 <a href="https://huggingface.co/mlx-community/RIFE-4.25">MIT</a>. 부분 보정 모델은 <a href="{MODEL_LICENSE}">CreativeML OpenRAIL-M</a>입니다. LTX-2 모델은 별도의 <a href="https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2">커뮤니티 라이선스</a> 후보였고 실행 결과는 없습니다.</p>
<p><a href="summary.json">실측값·해시·상태 JSON ↗</a> · 원본 대형 사진, 모델 가중치와 로컬 작업 로그는 배포물에 넣지 않았습니다.</p></html>'''
    assert_public_text(page)
    (out / 'index.html').write_text(page)
    return (['experiments/video-4to6/' + name for name in ['index.html', 'summary.json', 'interpolation.mp4']]
            + ['experiments/video-4to6/' + image['path'] for image in images])


def prepare_depth_report():
    """Publish selected licensed crops and relative-depth previews, never arrays or logs."""
    job = ROOT / 'data/jobs/mapillary-depth-v2-3views-20261105'
    inference, geometry = read_json(job / 'report.json'), read_json(job / 'geometry-check.json')
    if inference['status'] != 'PASS' or geometry['status'] != 'PASS' or len(inference['images']) != 3:
        raise ValueError('Expected completed three-view depth diagnostic')
    sample = read_json(ROOT / 'scripts/samples/mapillary-beijing.json')
    crops = read_json(ROOT / 'data/jobs/mapillary-beijing-crops/crops.json')
    crop_by_name = {Path(crop['file']).name: crop for crop in crops['crops']}
    out = PUBLIC / 'experiments/depth-v2'
    out.mkdir(parents=True, exist_ok=True)
    rows, files = [], ['experiments/depth-v2/index.html', 'experiments/depth-v2/summary.json']
    for index, image in enumerate(inference['images']):
        # Panorama filenames are one-based; source inventory indices are zero-based.
        source_index = index + 3
        source = sample['images'][source_index]
        expected = f'pano_{index + 4:06d}_view_02.png'
        check = geometry['results'][index]
        if Path(image['source']).name != expected or check['image'] != expected:
            raise ValueError('Depth image and SfM observation ordering differ')
        crop = crop_by_name[expected]
        if crop['sourceIndex'] != source_index or source['image_id'] not in crop['sourceId']:
            raise ValueError('Depth crop provenance differs from source inventory')
        expected_source = ROOT / 'data/jobs/mapillary-beijing-rig-poses-v2/dataset/images' / expected
        if Path(image['source']).resolve() != expected_source.resolve() or expected_source.is_symlink():
            raise ValueError('Depth source is not the selected public panorama crop')
        for suffix in ('source', 'visual'):
            name = f'view-{index:02d}-{suffix}.png'
            original = expected_source if suffix == 'source' else job / name
            if suffix == 'source' and sha(original) != image['sourceSha256']:
                raise ValueError('Published depth source differs from observed crop')
            if suffix == 'visual' and sha(original) != image['visualSha256']:
                raise ValueError('Depth visualization hash mismatch')
            shutil.copyfile(original, out / name)
            files.append('experiments/depth-v2/' + name)
        rows.append({'photo': index + 4, 'sourceUrl': source['commons_page'],
                     'imageId': source['image_id'], 'license': source['license'],
                     'cropSourceSha256': image['sourceSha256'],
                     'depthVisualSha256': image['visualSha256'],
                     'inferenceSeconds': image['inferenceSeconds'],
                     'sparseObservations': check['sparseObservations'],
                     'rankCorrelation': check['spearmanRelativeVsInverseSfMZ']})
    summary = {'schemaVersion': 1, 'status': 'PASS for MPS relative-depth inference and observed-point ordering; subsequent reprojection and GS comparison at /experiments/depth-warp/',
               'model': inference['model'], 'revision': inference['revision'],
               'modelLicense': 'Apache-2.0 for Depth Anything V2 Small',
               'sourceLicense': 'CC-BY-SA-4.0; Cicero101 / Mapillary via Wikimedia Commons',
               'device': inference['device'], 'torchVersion': inference['torchVersion'],
               'modelLoadSeconds': inference['modelLoadSeconds'],
               'wholeJobSeconds': inference['elapsedSeconds'],
               'wholeProcessPeakFootprintBytes': 1619919952,
               'interpretation': 'Relative inverse-depth-like values, independently normalized per image; no metric scale, cross-view agreement, novel-view coverage or GS gain established. SfM comparison uses the same observed photos and is not independent ground truth.',
               'images': rows}
    write_json(out / 'summary.json', summary)
    cards = ''.join(f'<article><h2>실제 사진 {r["photo"]}</h2><div class="pair"><figure><img src="view-{i:02d}-source.png" alt="실제 베이징 거리 사진"><figcaption>실제 촬영 시야</figcaption></figure><figure><img src="view-{i:02d}-visual.png" alt="상대 깊이 예측, 밝을수록 가까움"><figcaption>예측 상대 깊이 · 밝을수록 가까움</figcaption></figure></div><p>희소 3D 관측점 {r["sparseObservations"]}개와 앞뒤 순서 상관 {r["rankCorrelation"]:.3f} · MPS 추론 {r["inferenceSeconds"]:.2f}초 · <a href="{html.escape(r["sourceUrl"], quote=True)}">원본 사진/저작자 ↗</a></p></article>' for i, r in enumerate(rows))
    page = f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Groundshift · 사진 깊이 추정 실험</title>
<style>:root{{font-family:system-ui,-apple-system,sans-serif;background:#f4f3ec;color:#24372a}}*{{box-sizing:border-box}}body{{max-width:1150px;margin:auto;padding:28px}}a{{color:#426534}}nav{{display:flex;gap:16px;flex-wrap:wrap}}h1{{font-size:clamp(30px,5vw,58px);letter-spacing:-.04em;line-height:1.05}}p{{line-height:1.65;color:#536254;max-width:950px}}article{{margin:36px 0;padding:20px;background:#e6e9df;border-radius:12px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}figure{{margin:0}}img{{width:100%;display:block;border-radius:7px}}figcaption{{padding:8px 0}}.status{{border-left:4px solid #819b68;padding:12px 18px;background:#e3eadb}}@media(max-width:650px){{.pair{{grid-template-columns:1fr}}body{{padding:16px}}}}</style>
<nav><a href="/">장면 모음 ↗</a><a href="/experiments/video-4to6/">65프레임 실험 ↗</a><a href="/experiments/mapillary/">기존 비교 ↗</a></nav><h1>사진에서 깊이를 추정해 봤다</h1>
<p>실제 360° 사진 4·5·6에서 같은 방향의 512×512 시야를 잘라, Depth Anything V2 Small을 이 맥의 MPS/Metal에서 실행했다. 회색 지도는 사진 속 각 픽셀의 <strong>상대적인 앞뒤</strong>를 예측한다. 각 사진마다 따로 정규화했으므로 회색값을 사진 사이에서 거리처럼 비교할 수 없다.</p>
<div class="status"><strong>깊이 추론 PASS.</strong> 세 사진에서 예측한 앞뒤 순서는 기존 사진 기반 희소 3D 점과 대체로 일치했다. 이는 같은 사진에서 얻은 SfM 추정치와의 내부 비교이지 실제 거리 측정이나 독립 검증이 아니다.</div>
{cards}
<h2>후속 실험</h2><p>사진 4·6의 상대 깊이를 SfM 희소점에 맞춰 보정하고, 관측 RGB를 사진 5의 카메라로 옮긴 뒤 비어 있는 부분을 확산 모델로 채웠다. <a href="/experiments/depth-warp/">투영·생성·3D 결과 비교 ↗</a>. 사진 5의 RGB는 투영·생성 과정에 쓰지 않았지만 전체 이미지 SfM은 사진 5를 사용했다.</p>
<p>사진: Cicero101 / Mapillary, Wikimedia Commons 재배포, <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC-BY-SA-4.0</a>. 수정: 구면→평면 투영 및 상대 깊이 시각화. 모델: <a href="https://github.com/DepthAnything/Depth-Anything-V2">Depth Anything V2 Small</a>, Apache-2.0. <a href="summary.json">측정·해시 JSON ↗</a>. 원본 대형 사진, 깊이 수치 배열, 모델 가중치와 로컬 로그는 배포하지 않는다.</p></html>'''
    assert_public_text(page)
    (out / 'index.html').write_text(page)
    return files


def prepare_depth_warp_report(worlds):
    """Publish an evidence-bound, image-first account of the depth-guided trial."""
    jobs = ROOT / 'data/jobs'
    warp_dir = jobs / 'mapillary-depth-warp-view02-v3-20261105'
    warp = read_json(warp_dir / 'report.json')
    coverage = read_json(jobs / 'mapillary-depth-warp-comparison-20261105/report.json')
    inpaint_dir = jobs / 'mapillary-depth-inpaint-view02-20261105'
    inpaint = read_json(inpaint_dir / 'report.json')
    inpaint_rgb = read_json(jobs / 'mapillary-depth-inpaint-vs-real-20261105/report.json')
    gray_rgb = read_json(jobs / 'mapillary-depth-inpaint-vs-gray-20261105/report.json')
    augmentation = read_json(jobs / 'mapillary-depth-augmented-view02-20261105/augmentation.json')
    training = read_json(jobs / 'mapillary-depth-gs-10000-20261105/job.json')
    world = next((item for item in worlds if item['id'] == 'beijing-depth'), None)
    if any(item['status'] != 'PASS' for item in (warp, coverage, inpaint, inpaint_rgb, gray_rgb, augmentation, training)):
        raise ValueError('Depth-guided report requires completed local stages')
    if world is None or world['execution'] != 'PASS' or warp['targetImagePixelsRead'] is not False:
        raise ValueError('Depth-guided GS export or held-out RGB boundary was not verified')
    if augmentation['targetPhotographPixelsRead'] is not False or augmentation['target'] != 'images/pano_000005_view_02.png':
        raise ValueError('Generated-view augmentation did not preserve target RGB holdout')
    if inpaint['output']['sha256'] != sha(inpaint_dir / 'completed.png'):
        raise ValueError('Generated image differs from MPS inpaint report')
    if inpaint['input']['referenceSha256'] != warp['outputs']['warp-consistent.png']['sha256']:
        raise ValueError('Inpaint input differs from source-consistent warp')
    sample = read_json(ROOT / 'scripts/samples/mapillary-beijing.json')
    crop_report = read_json(jobs / 'mapillary-beijing-crops/crops.json')
    crop_by_name = {Path(item['file']).name: item for item in crop_report['crops']}
    for number, sample_index in ((4, 3), (5, 4), (6, 5)):
        crop = crop_by_name[f'pano_{number:06d}_view_02.png']
        if crop['sourceIndex'] != sample_index or sample['images'][sample_index]['image_id'] not in crop['sourceId']:
            raise ValueError('Depth-guided crop/source attribution mismatch')
    out = PUBLIC / 'experiments/depth-warp'
    image_dir = out / 'images'
    image_dir.mkdir(parents=True, exist_ok=True)
    dataset_images = jobs / 'mapillary-beijing-rig-poses-v2/dataset/images'
    if sha(dataset_images / 'pano_000005_view_02.png') != coverage['inputs']['reference']['sha256']:
        raise ValueError('Published target photo differs from held-out RGB evaluation')
    for source in warp['sources']:
        if sha(dataset_images / source['name']) != source['sourceSha256']:
            raise ValueError('Published endpoint differs from learned-depth warp input')
    stereo_dir = jobs / 'mapillary-depth-stereo-view02-corrected-20261105'
    images = {
        'observed-04': dataset_images / 'pano_000004_view_02.png',
        'observed-05': dataset_images / 'pano_000005_view_02.png',
        'observed-06': dataset_images / 'pano_000006_view_02.png',
        'stereo': stereo_dir / 'warp.png',
        'depth-raw': warp_dir / 'warp.png',
        'depth-consistent': warp_dir / 'warp-consistent.png',
        'depth-mask': warp_dir / 'mask-consistent.png',
        'gray-control': inpaint_dir / 'gray-control.png',
        'diffusion': inpaint_dir / 'completed.png',
    }
    renders = []
    for view in ('01', '03'):
        before_dir = jobs / f'mapillary-depth-render-view{view}-baseline'
        after_dir = jobs / f'mapillary-depth-render-view{view}-generated'
        before = read_json(before_dir / 'report.json')
        after = read_json(after_dir / 'report.json')
        comparison = read_json(jobs / f'mapillary-depth-render-view{view}-comparison/report.json')
        if any(item['status'] != 'PASS' for item in (before, after, comparison)):
            raise ValueError(f'Headed Chrome render/compare missing for view {view}')
        expected = f'images/pano_000005_view_{view}.png'
        if before['frame'] != expected or after['frame'] != expected:
            raise ValueError('Matched render camera mismatch')
        images[f'observed-{view}'] = dataset_images / Path(expected).name
        images[f'gs-baseline-{view}'] = before_dir / 'input.png'
        images[f'gs-generated-{view}'] = after_dir / 'input.png'
        full = comparison['regions']['full']
        renders.append({
            'view': view, 'camera': expected, 'browserGpu': after['gpu'],
            'baselineMae255': full['baseline']['mae'],
            'generatedMae255': full['completed']['mae'],
            'baselinePsnrDb': full['baseline']['psnrDb'],
            'generatedPsnrDb': full['completed']['psnrDb'],
            'baselineLowOpacityFraction': before['maskedFraction'],
            'generatedLowOpacityFraction': after['maskedFraction'],
            'baselinePlySha256': before['assetSha256'],
            'generatedPlySha256': after['assetSha256'],
        })
    inventory = []
    for name, src in images.items():
        dst = image_dir / f'{name}.png'
        shutil.copyfile(src, dst)
        inventory.append({'name': name, 'path': f'images/{name}.png',
                          'sha256': sha(dst), 'bytes': dst.stat().st_size})
    public = {
        'schemaVersion': 1,
        'experiment': 'Depth-calibrated reprojection, masked diffusion, matched Gaussian training',
        'status': {'MPSDepth': 'PASS', 'sparseCalibration': 'PASS',
                   'observedPixelWarp': 'PASS', 'sourceConsistencyGate': 'PASS',
                   'MPSInpainting': 'PASS', 'MetalGaussianTraining': 'PASS',
                   'localHeadedChromeRenders': 'PASS', 'visualQuality': 'FAIL',
                   'independentGeometryValidation': 'NOT RUN',
                   'publicBrowserRendering': 'NOT RUN at archive creation; see deployment evidence'},
        'sourcePhotos': [{'panorama': number, 'imageId': sample['images'][number-1]['image_id'],
                          'commonsPage': sample['images'][number-1]['commons_page'],
                          'license': 'CC-BY-SA-4.0'} for number in (4, 5, 6)],
        'holdout': 'Panorama 5 RGB excluded from warp, inpainting and GS training; all-image SfM used its pixels to estimate pose and sparse initialization.',
        'geometry': {'method': warp['calibration'], 'scale': 'arbitrary SfM units',
                     'sourceSparsePairs': [source['sparsePairs'] for source in warp['sources']],
                     'sourceInternalHoldoutMedianAbsInverseZError': [
                         source['internalHoldoutMedianAbsInverseZError'] for source in warp['sources']]},
        'coverage': {'stereoFraction': coverage['variants']['stereo']['projectedSourceFraction'],
                     'rawDepthWarpFraction': coverage['variants']['learnedRaw']['projectedSourceFraction'],
                     'sourceConsistentDepthWarpFraction': coverage['variants']['learnedSourceConsistent']['projectedSourceFraction'],
                     'consistentUnknownFraction': inpaint['input']['syntheticFraction'],
                     'consistencyRule': warp['coverage']['consistencyRule']},
        'photometric': {
            'warp': coverage['variants'],
            'diffusionFullMae255': inpaint_rgb['regions']['full']['completed']['mae'],
            'grayControlFullMae255': gray_rgb['regions']['full']['baseline']['mae'],
            'diffusionFullPsnrDb': inpaint_rgb['regions']['full']['completed']['psnrDb'],
            'grayControlFullPsnrDb': gray_rgb['regions']['full']['baseline']['psnrDb'],
            'interpretation': 'Different source supports are not directly comparable. On common pixels stereo beats both depth variants. Full-canvas diffusion versus gray is a small MAE gain but lower PSNR.'},
        'generation': {'model': inpaint['model'], 'steps': inpaint['settings']['steps'],
                       'seed': inpaint['settings']['seed'], 'gpuInferenceSeconds': inpaint['inferenceSeconds'],
                       'processPeakRssBytes': inpaint['processPeakRssBytes']},
        'gaussian': {'realTrainingImages': 48, 'generatedTrainingImages': 1,
                     'steps': training['options']['steps'], 'trainingSeconds': training['elapsedSeconds'],
                     'splats': world['splats'], 'sceneBytes': world['bytes'],
                     'worldManifest': world['manifest'], 'matchedRenders': renders},
        'images': inventory,
    }
    assert_public_text(json.dumps(public, ensure_ascii=False))
    write_json(out / 'summary.json', public)
    by_name = {item['name']: item for item in inventory}
    def figure(name, caption):
        return f'<figure><img src="{by_name[name]["path"]}" alt="{html.escape(caption, quote=True)}"><figcaption>{html.escape(caption)}</figcaption></figure>'
    source_links = ' · '.join(
        f'<a href="{html.escape(photo["commonsPage"], quote=True)}">실제 사진 {photo["panorama"]} 원본·저작자 ↗</a>'
        for photo in public['sourcePhotos'])
    render_cards = ''.join(
        f'<section><h3>사진 5 · 방향 {item["view"]}</h3><div class="grid">'
        + figure(f'observed-{item["view"]}', '실제 사진 5 · 학습 RGB 제외')
        + figure(f'gs-baseline-{item["view"]}', '실제 사진 48장만 학습한 GS')
        + figure(f'gs-generated-{item["view"]}', '실제 48장 + 생성 1장 학습한 GS')
        + '</div><p>실제 사진 대비 RGB MAE '
        + f'{item["baselineMae255"]:.2f} → {item["generatedMae255"]:.2f}; '
        + f'PSNR {item["baselinePsnrDb"]:.2f} → {item["generatedPsnrDb"]:.2f} dB. '
        + '같은 추정 카메라로 Chrome에서 렌더했다.</p></section>' for item in renders)
    page = f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Groundshift · 깊이 기반 중간 시점 실험</title>
<style>:root{{font-family:system-ui,-apple-system,sans-serif;background:#f4f3ec;color:#24372a}}*{{box-sizing:border-box}}body{{max-width:1220px;margin:auto;padding:28px}}a{{color:#426534}}nav{{display:flex;gap:16px;flex-wrap:wrap}}h1{{font-size:clamp(31px,5vw,58px);letter-spacing:-.04em;line-height:1.05}}h2{{margin-top:42px}}p{{line-height:1.65;color:#536254;max-width:1040px}}.status{{border-left:4px solid #b06646;padding:12px 18px;background:#f2e5d8}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}}figure{{margin:0}}img{{width:100%;display:block;border-radius:7px;background:#121b14}}figcaption{{padding:8px 0;font-size:14px}}section{{margin:34px 0;padding:20px;background:#e6e9df;border-radius:12px}}@media(max-width:750px){{.grid{{grid-template-columns:1fr 1fr}}body{{padding:16px}}}}@media(max-width:490px){{.grid{{grid-template-columns:1fr}}}}</style>
<nav><a href="/">장면 모음 ↗</a><a href="/experiments/depth-v2/">깊이 예측 지도 ↗</a><a href="/experiments/video-4to6/">65프레임 영상 ↗</a></nav>
<h1>깊이를 이용해 중간 장면 만들기</h1>
<p>실제로 촬영된 구면 사진 4와 6에서 같은 방향을 잘랐다. 각 픽셀의 상대 깊이를 M2에서 추정하고 기존 SfM 희소 3D 점에 맞춘 뒤, 사진 5의 추정 카메라로 두 사진의 <strong>관측 픽셀</strong>을 옮겼다. 두 출처가 서로 맞지 않는 픽셀은 버리고 빈 영역만 확산 모델로 채웠다. 사진 5의 RGB는 생성이나 GS 학습에 쓰지 않았지만, 카메라 위치와 초기 3D 점을 구한 전체 이미지 SfM에는 쓰였다.</p>
<div class="status"><strong>로컬 실행 PASS · 3D 품질 개선 FAIL.</strong> 원본 48장과 생성 이미지 1장을 10,000단계씩 맞춰 비교했다. 아래 결과는 실제 브라우저 렌더이며, 새 장면도 <a href="/?world={world['manifest']}">직접 탐색할 수 있다 ↗</a>. 밝고 그럴듯한 부분은 생성된 가설이지 실제 거리의 측정값이 아니다.</div>
<h2>1 · 관측 원본</h2><div class="grid">{figure('observed-04','실제 사진 4 · 입력')}{figure('observed-05','실제 사진 5 · 결과 평가용 RGB')}{figure('observed-06','실제 사진 6 · 입력')}</div>
<h2>2 · 사진을 중간 카메라로 옮기기</h2><p>동일한 512² 방향에서 스테레오는 {public['coverage']['stereoFraction']*100:.1f}%를 채웠다. 깊이 기반 투영은 {public['coverage']['rawDepthWarpFraction']*100:.1f}%를 채운 것처럼 보였지만 어긋난 물체가 많았다. 두 출처 간 깊이·색 일치 검사 후에는 {public['coverage']['sourceConsistentDepthWarpFraction']*100:.1f}%만 관측 픽셀로 남겼다. 서로 다른 영역의 MAE를 직접 순위 비교하면 안 된다. 양쪽에 공통으로 있는 픽셀에서는 스테레오가 더 정확했다.</p>
<div class="grid">{figure('stereo','스테레오로 옮긴 관측 픽셀 · 나머지 검정')}{figure('depth-raw','깊이 투영 원본 · 높은 채움률, 눈에 띄는 중복')}{figure('depth-consistent','두 출처 일치 검사 후 관측 픽셀')}</div>
<h2>3 · 빈 {public['coverage']['consistentUnknownFraction']*100:.1f}% 생성</h2><p>흰 마스크만 Stable Diffusion 1.5 Inpainting으로 MPS에서 채웠다. 실제 사진 5와의 전체 RGB MAE는 단색 회색 채움 {public['photometric']['grayControlFullMae255']:.2f}, 확산 채움 {public['photometric']['diffusionFullMae255']:.2f}로 작은 차이다. PSNR은 각각 {public['photometric']['grayControlFullPsnrDb']:.2f}, {public['photometric']['diffusionFullPsnrDb']:.2f} dB로 오히려 회색이 높다. 이런 픽셀 점수는 그럴듯함이나 3D 일관성을 판단하지 않는다.</p>
<div class="grid">{figure('depth-mask','흰색 부분만 생성')}{figure('gray-control','단색 채움 비교')}{figure('diffusion','MPS 확산 생성 · 실제 물체 보존 보장 없음')}</div>
<h2>4 · 같은 조건의 GS 렌더</h2><p>원본만 학습한 장면과 생성 1장을 더한 장면을 실제 사진 5의 서로 다른 두 방향에서 렌더했다. 생성 이미지의 포즈는 기존 전체 이미지 SfM에서 가져온 추정값이다. 새로운 시점의 실제 정합이나 미터 단위 위치가 확인된 것은 아니다.</p>{render_cards}
<p><a href="/?world=/worlds/beijing-10k/world.json">실제 48장 GS ↗</a> · <a href="/?world={world['manifest']}">실제 48장 + 생성 1장 GS ↗</a> · <a href="summary.json">측정·해시·상태 JSON ↗</a></p>
<h2>출처와 한계</h2><p>{source_links}. Cicero101 / Mapillary, Wikimedia Commons 재배포, <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC-BY-SA-4.0</a>. 수정: 구면 투영, 깊이 보정, 재투영, 인페인팅 및 GS 렌더. <a href="https://github.com/DepthAnything/Depth-Anything-V2">Depth Anything V2 Small</a> Apache-2.0, <a href="{MODEL_LICENSE}">Stable Diffusion 1.5 Inpainting CreativeML OpenRAIL-M</a>. 원본 대형 사진, 깊이 배열, 모델 가중치와 로컬 학습 로그는 배포하지 않는다.</p></html>'''
    assert_public_text(page)
    (out / 'index.html').write_text(page)
    return ['experiments/depth-warp/index.html', 'experiments/depth-warp/summary.json'] + [
        'experiments/depth-warp/' + item['path'] for item in inventory]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-previews', action='store_true')
    parser.add_argument('--base-url', default='http://127.0.0.1:4317')
    args = parser.parse_args()
    worlds = prepare_worlds()
    history = collect_history()
    files = prepare_report(worlds, history) + prepare_video_report(worlds) + prepare_depth_report() + prepare_depth_warp_report(worlds)
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
