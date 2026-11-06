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
SLUG = 'street-tangent20'
REPORT = 'experiments/tangent-background'


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
    evidence_phase = source.get('evidencePhase', phase)
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', evidence_phase):
        raise ValueError('Reused evidence phase must be an explicit safe slug')
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
        name = f'comparison/{evidence_phase}-{i:02d}{src.suffix.lower()}'
        copies.append((src, out / name)); comparison['image'] = './' + name
    if 'comparisonOrder' in source:
        order = source['comparisonOrder']
        count = len(summary.get('comparisons', []))
        if not isinstance(order, list) or any(type(i) is not int for i in order) or sorted(order) != list(range(count)):
            raise ValueError('Comparison order must be an exact index permutation')
        summary['comparisons'] = [summary['comparisons'][i] for i in order]
    if source.get('video'):
        src = Path(source['video']).resolve(); name = f'comparison/{evidence_phase}-motion.mp4'
        copies.append((src, out / name)); summary['video'] = './' + name
    catalog = read(PUBLIC / 'worlds/catalog.json')
    timeline = read(PUBLIC / 'experiments/lab/timeline.json')
    allow_path = ROOT / 'scripts/observation-worlds.json'
    allow = read(allow_path)
    world_plan = None
    if source.get('world'):
        selected = source['world']
        if selected.get('backgroundDir'):
            raise ValueError('Background completion was rejected; publish GS only, not backgroundDir')
        native_dir = Path(selected['nativeDir']).resolve()
        native = read(native_dir / 'job.json'); ply = native_dir / 'world/scene.ply'
        if native['status'] != 'PASS' or sha(ply) != native['artifact']['sha256']:
            raise ValueError('Require complete native export with matching SHA')
        presentation = Path(selected['presentationDir']).resolve()
        metadata = read(presentation / 'world.json')
        metadata.update(id=SLUG, title=selected['title'])
        # Presentation manifests can come from the historical background trial.
        # Never silently reactivate its rejected presentation in a later release.
        metadata.pop('background', None)
        metadata['provenance']['notes'] = ('Actual local M2 Metal training,160 real1024px tangent perspective crops from8 of9 existing licensed panoramas. '
            '20 icosahedron face-normal directions,FOV80. DAV2 crop inference, SfM and overlap calibration, arbitrary units. '
            'Panorama5 RGB excluded from optimization and background; all-nine SfM geometry reused.8000steps,SH1,seed42,max800000splats. '
            'No generated training images. GS-only display: photo panorama and estimated-depth backgrounds were rejected by the user because translated views misalign. Historical comparisons remain evidence, not enabled presentation. '
            'Observation /experiments/tangent-background/. Quality: ' + selected['quality'])
        public_text(metadata)
        summary['run'] = dict(status='PASS', splats=native['artifact']['splats'], bytes=native['artifact']['bytes'],
            sha256=native['artifact']['sha256'], seconds=native['elapsedSeconds'], quality=selected['quality'],
            world=f'/worlds/{SLUG}/world.json')
        preview = Path(selected['preview']).resolve() if selected.get('preview') else None
        if preview or (PUBLIC / 'worlds' / SLUG / 'preview.jpg').is_file():
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
        source_license = Path(selected['sourceLicense']).resolve() if selected.get('sourceLicense') else job / 'inputs-tangent/LICENSE'
        shutil.copyfile(source_license, dest / 'SOURCE_LICENSE')
        if preview:
            from PIL import Image
            Image.open(preview).convert('RGB').save(dest / 'preview.jpg', quality=91)
        elif not (dest / 'preview.jpg').exists():
            # Export immediately: a clearly labeled neutral placeholder avoids
            # presenting another world's render as this new scene.
            from PIL import Image, ImageDraw
            image = Image.new('RGB', (640, 400), '#17242d')
            draw = ImageDraw.Draw(image)
            draw.text((36, 150), 'NATIVE GS EXPORT READY', fill='#d8f2ee', font_size=26)
            draw.text((36, 205), 'Browser preview: NOT RUN', fill='#b4c9d4', font_size=22)
            image.save(dest / 'preview.jpg', quality=91)
            summary['run']['quality'] += ' 카드 그림은 NOT RUN 임시표시이며 실제 새 장면 렌더는 후속 공개합니다.'
        curated = job / 'public-worlds' / SLUG / 'world'
        curated.mkdir(parents=True, exist_ok=True)
        for name in ['scene.ply', 'world.json', 'cameras.json', 'SOURCE_LICENSE', 'preview.jpg']:
            if name == 'scene.ply' and (curated / name).exists():
                continue
            shutil.copyfile(dest / name, curated / name)
        entry = dict(id=SLUG, title=metadata['title'], description='이십면체20방향·160실제 크롭·DAV2 깊이 보정. 전방위 GS만 표시하며 이동 불일치가 생긴 사진/깊이 배경은 폐기.',
            category='experiment', manifestPath=f'/worlds/{SLUG}/world.json', thumbnailPath=f'/worlds/{SLUG}/preview.jpg',
            createdAt=native['finishedAt'], detail=summary['run']['quality'])
        catalog['scenes'] = [entry if old['id'] == SLUG else old for old in catalog['scenes']]
        if not any(old['id'] == SLUG for old in catalog['scenes']):
            catalog['scenes'].append(entry)
        scene_entry = dict(id=SLUG, title=entry['title'], description=entry['description'], image=entry['thumbnailPath'], href='/?world='+entry['manifestPath'],
            kind='scene', createdAt=entry['createdAt'], detail=entry['detail'])
        timeline['entries'] = [scene_entry if old['id'] == SLUG else old for old in timeline['entries']]
        if not any(old['id'] == SLUG for old in timeline['entries']):
            timeline['entries'].append(scene_entry)
        allowed_world = dict(id=SLUG, source=str(curated.relative_to(ROOT)), asset='scene.ply', format='ply', credits=['SOURCE_LICENSE'])
        allow['worlds'] = [allowed_world if old['id'] == SLUG else old for old in allow['worlds']]
        if not any(old['id'] == SLUG for old in allow['worlds']):
            allow['worlds'].append(allowed_world)
    for src, dest in copies:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copyfile(src, dest)
    write(out / 'summary.json', summary)
    (out / 'ATTRIBUTION.txt').write_text('Photographs: Cicero101 / Mapillary via Wikimedia Commons, CC BY-SA4.0. https://creativecommons.org/licenses/by-sa/4.0/\nChanges: actual 20-direction tangent reprojection from retained original panoramas, DAV2 crop depth inference and calibrated initialization, local Brush/Metal Gaussian training; historical rejected source-photo/estimated-depth background comparisons; current scene is GS only. No diffusion/generated training RGB. Original full panoramas, private footage, raw logs and weights excluded. Historical background processing/modified regions remain documented in preserved evidence; they were rejected for translation misalignment and are not current geometry or display.\n')
    report = dict(id='report-tangent-background', title='이십면체20방향 GS · 배경 방식 폐기', description=summary['summary'],
        image=summary.get('run', {}).get('preview', '/worlds/street-final-hires/preview.jpg'), href='/experiments/tangent-background/', kind='report',
        createdAt=summary['updatedAt'], detail=summary['phase']+' · '+summary['title'])
    timeline['entries'] = [report if old['id'] == report['id'] else old for old in timeline['entries']]
    if not any(old['id'] == report['id'] for old in timeline['entries']):
        timeline['entries'].append(report)
    allow['files'] = list(dict.fromkeys(allow['files'] + [REPORT+'/index.html'] + [str(p.relative_to(PUBLIC)) for p in out.rglob('*') if p.is_file()]))
    if world_plan:
        (PUBLIC / 'worlds/catalog.json').write_text(json.dumps(catalog, indent=2) + '\n')
    write(PUBLIC / 'experiments/lab/timeline.json', timeline); write(allow_path, allow)
    snapshot.mkdir(parents=True)
    write(snapshot / 'summary.json', summary)
    write(snapshot / 'publication.json', dict(status='PASS', phase=phase, publishedLocallyAt=datetime.now(timezone.utc).isoformat(), files=[dict(path=str(p.relative_to(PUBLIC)), bytes=p.stat().st_size, sha256=sha(p)) for p in out.rglob('*') if p.is_file()]))
    print(json.dumps(dict(status='PASS', phase=phase, publicReport='/experiments/tangent-background/', sceneCount=len(catalog['scenes']), timelineCount=len(timeline['entries'])), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path); parser.add_argument('--state', type=Path, required=True)
    main(parser.parse_args())
