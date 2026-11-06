#!/usr/bin/env python3
"""Publish one explicit provisional/final observation, retaining phase snapshots."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / 'public'
SLUG = 'street-final-hires'
REPORT = 'experiments/final-quality'


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def public_text(value):
    text = json.dumps(value, ensure_ascii=False)
    if re.search(r'file://|/(?:Users|home|private|Volumes|tmp)/|data/jobs/|https?://(?:localhost|127\.0\.0\.1)|icloud\.com', text, re.I):
        raise ValueError('Private/local reference in selected public metadata')


def main(a):
    job = a.job.resolve()
    source = read(a.state)
    phase = source['phase']
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', phase):
        raise ValueError('Phase must be a unique lowercase slug')
    snapshot = job / 'publications' / phase
    if snapshot.exists():
        raise ValueError('Publication phase already recorded; use a fresh phase identifier')
    out = PUBLIC / REPORT
    out.mkdir(parents=True, exist_ok=True)
    summary = {k: deepcopy(source[k]) for k in ['phase', 'updatedAt', 'title', 'summary', 'stages', 'notes']}
    summary['sources'] = read(PUBLIC / 'experiments/street/summary.json')['sources']
    copies = []
    summary['samples'] = []
    for i, sample in enumerate(source.get('samples', [])):
        item = {k: sample[k] for k in ['title', 'caption']}
        for key in ['highres', 'baseline']:
            if sample.get(key):
                src = Path(sample[key]).resolve()
                if not src.is_file() or src.suffix.lower() not in ['.png', '.jpg', '.jpeg']:
                    raise ValueError('Require actual selected comparison image')
                name = f'samples/{i:02d}-{key}{src.suffix.lower()}'
                copies.append((src, out / name)); item[key] = './' + name
        summary['samples'].append(item)
    for key in ['comparisons', 'metrics']:
        if key in source:
            summary[key] = deepcopy(source[key])
    for i, comparison in enumerate(summary.get('comparisons', [])):
        src = Path(comparison['image']).resolve()
        name = f'comparison/{phase}-{i:02d}{src.suffix.lower()}'
        copies.append((src, out / name)); comparison['image'] = './' + name
    if source.get('video'):
        src = Path(source['video']).resolve(); name = f'comparison/{phase}-motion.mp4'
        copies.append((src, out / name)); summary['video'] = './' + name
    catalog = read(PUBLIC / 'worlds/catalog.json')
    timeline = read(PUBLIC / 'experiments/lab/timeline.json')
    allow_path = ROOT / 'scripts/observation-worlds.json'
    allow = read(allow_path)
    world_plan = None
    if source.get('world'):
        selected = source['world']; native_dir = Path(selected['nativeDir']).resolve()
        native = read(native_dir / 'job.json'); ply = native_dir / 'world/scene.ply'
        if native['status'] != 'PASS' or sha(ply) != native['artifact']['sha256']:
            raise ValueError('Require complete native export with matching SHA')
        presentation = Path(selected['presentationDir']).resolve()
        metadata = read(presentation / 'world.json')
        metadata.update(id=SLUG, title=selected['title'])
        metadata['provenance']['notes'] = ('Actual local M2 Metal training,96 real1024px perspective crops from8 of9 existing licensed panoramas. '
            'Same DAV2 calibrated183124-point initialization and estimated camera poses as street-dense. '
            'Panorama5 RGB excluded from optimization; all-nine SfM geometry reused.8000steps,SH1,seed42,max800000splats. '
            'No generated training images or new depth inference. Arbitrary SfM units; no measured floor/collision. '
            'Observation /experiments/final-quality/. Quality: ' + selected['quality'])
        public_text(metadata)
        summary['run'] = dict(status='PASS', splats=native['artifact']['splats'], bytes=native['artifact']['bytes'],
            sha256=native['artifact']['sha256'], seconds=native['elapsedSeconds'], quality=selected['quality'],
            world=f'/worlds/{SLUG}/world.json')
        preview = Path(selected['preview']).resolve() if selected.get('preview') else None
        if preview:
            summary['run']['preview'] = f'/worlds/{SLUG}/preview.jpg'
        world_plan = (native_dir, presentation, metadata, preview, selected, native)
    elif source.get('run'):
        summary['run'] = deepcopy(source['run'])
    public_text(summary)
    for src, dest in copies:
        if not src.is_file():
            raise ValueError('Selected public evidence missing: ' + str(src))
        if dest.exists() and sha(src) != sha(dest):
            raise ValueError('Existing public evidence would be replaced: ' + dest.name)
    if world_plan:
        native_dir, presentation, metadata, preview, selected, native = world_plan
        dest = PUBLIC / 'worlds' / SLUG
        if dest.exists() and sha(dest / 'scene.ply') != native['artifact']['sha256']:
            raise ValueError('Previous exported scene would be overwritten')
        dest.mkdir(exist_ok=True)
        if not (dest / 'scene.ply').exists():
            shutil.copyfile(native_dir / 'world/scene.ply', dest / 'scene.ply')
        write(dest / 'world.json', metadata)
        shutil.copyfile(presentation / 'cameras.json', dest / 'cameras.json')
        shutil.copyfile(job / 'inputs-hires/LICENSE', dest / 'SOURCE_LICENSE')
        if preview:
            from PIL import Image
            Image.open(preview).convert('RGB').save(dest / 'preview.jpg', quality=91)
        elif not (dest / 'preview.jpg').exists():
            # Explicit placeholder: never call this an actual new-scene render.
            shutil.copyfile(PUBLIC / 'worlds/street-dense/preview.jpg', dest / 'preview.jpg')
            summary['run']['quality'] += ' 카드 그림은 이전 DAV2 기준이며 새 장면의 렌더 미리보기는 NOT RUN.'
        curated = job / 'public-worlds' / SLUG / 'world'
        curated.mkdir(parents=True, exist_ok=True)
        for name in ['scene.ply', 'world.json', 'cameras.json', 'SOURCE_LICENSE', 'preview.jpg']:
            if name == 'scene.ply' and (curated / name).exists():
                continue
            shutil.copyfile(dest / name, curated / name)
        entry = dict(id=SLUG, title=metadata['title'], description='같은 실제 거리 사진·DAV2 초기 점군.1024px 학습 입력·80만 Gaussian 상한의 마지막 품질 조합.',
            category='experiment', manifestPath=f'/worlds/{SLUG}/world.json', thumbnailPath=f'/worlds/{SLUG}/preview.jpg',
            createdAt=native['finishedAt'], detail=selected['quality'])
        catalog['scenes'] = [entry if old['id'] == SLUG else old for old in catalog['scenes']]
        if not any(old['id'] == SLUG for old in catalog['scenes']):
            catalog['scenes'].append(entry)
        scene_entry = dict(id=SLUG, title=entry['title'], description=entry['description'], image=entry['thumbnailPath'], href='/?world='+entry['manifestPath'],
            kind='scene', createdAt=entry['createdAt'], detail=entry['detail'])
        timeline['entries'] = [scene_entry if old['id'] == SLUG else old for old in timeline['entries']]
        if not any(old['id'] == SLUG for old in timeline['entries']):
            timeline['entries'].append(scene_entry)
        if not any(old['id'] == SLUG for old in allow['worlds']):
            allow['worlds'].append(dict(id=SLUG, source=str(curated.relative_to(ROOT)), asset='scene.ply', format='ply', credits=['SOURCE_LICENSE']))
    for src, dest in copies:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copyfile(src, dest)
    write(out / 'summary.json', summary)
    (out / 'ATTRIBUTION.txt').write_text('Photographs: Cicero101 / Mapillary via Wikimedia Commons, CC BY-SA4.0. https://creativecommons.org/licenses/by-sa/4.0/\nChanges: actual perspective reprojection from retained original panoramas, calibrated DAV2 initialization reused, local Brush/Metal Gaussian training and marked actual browser renders. No diffusion/generated training RGB. Original full panoramas, private footage, raw logs and weights excluded.\n')
    report = dict(id='report-final-quality', title='같은 데이터의 마지막 품질 실험', description=summary['summary'],
        image=summary.get('run', {}).get('preview', '/worlds/street-dense/preview.jpg'), href='/experiments/final-quality/', kind='report',
        createdAt=summary['updatedAt'], detail=summary['phase']+' · '+summary['title'])
    timeline['entries'] = [report if old['id'] == report['id'] else old for old in timeline['entries']]
    if not any(old['id'] == report['id'] for old in timeline['entries']):
        timeline['entries'].append(report)
    allow['files'] = list(dict.fromkeys(allow['files'] + [REPORT+'/index.html'] + [str(p.relative_to(PUBLIC)) for p in out.rglob('*') if p.is_file()]))
    if world_plan:
        write(PUBLIC / 'worlds/catalog.json', catalog)
    write(PUBLIC / 'experiments/lab/timeline.json', timeline); write(allow_path, allow)
    snapshot.mkdir(parents=True)
    write(snapshot / 'summary.json', summary)
    write(snapshot / 'publication.json', dict(status='PASS', phase=phase, publishedLocallyAt=datetime.now(timezone.utc).isoformat(), files=[dict(path=str(p.relative_to(PUBLIC)), bytes=p.stat().st_size, sha256=sha(p)) for p in out.rglob('*') if p.is_file()]))
    print(json.dumps(dict(status='PASS', phase=phase, publicReport='/experiments/final-quality/', sceneCount=len(catalog['scenes']), timelineCount=len(timeline['entries'])), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path); parser.add_argument('--state', type=Path, required=True)
    main(parser.parse_args())
