#!/usr/bin/env python3
"""Prepare one completed Seine snapshot for the existing static release workflow.

No deployment, training or private source directory is uploaded by this command.
The deployment owner curates/builds the prepared public files, publishes an
incremental archive and writes publication-receipts/NNN.json after dispatch.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
IDENT = 'seine-full-route'
PRIVATE = re.compile(r'file://|/(?:Users|home|private|Volumes|tmp)/|\bdata/jobs/|https?://(?:localhost|127\.0\.0\.1|\[::1\])|https?://[^\s"\\]*icloud\.com', re.I)


def read(path):
    def invalid(value):
        raise ValueError('Non-finite JSON constant: ' + value)
    return json.loads(path.read_text(), parse_constant=invalid)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def public_text(data):
    if PRIVATE.search(data.decode('utf8')):
        raise ValueError('Private reference in selected publication metadata')


def relative(value):
    path = PurePosixPath(value)
    if not value or not path.parts or path.is_absolute() or str(path) != value or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', part) for part in path.parts):
        raise ValueError('Unsafe snapshot reference')
    return path


def ordinary(source, name):
    rel = relative(name)
    path = source
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError('Symlink in snapshot')
    if not path.is_file():
        raise ValueError('Missing selected snapshot file: ' + name)
    return path


def selected_files(source):
    """Follow declared world/RAD references, never walk a native job directory."""
    match = re.fullmatch(r'route-world-(\d{3})', source.name)
    if not match or source.is_symlink():
        raise ValueError('Require an atomically completed route-world-NNN directory')
    coverage = read(ordinary(source, 'coverage.json'))
    world = read(ordinary(source, 'world.json'))
    if coverage.get('status') != 'PASS' or coverage['segments'] != int(match[1]) or world['id'] != IDENT:
        raise ValueError('Require completed matching snapshot coverage')
    if coverage['firstRank'] < 808 or coverage['lastRank'] > 1683 or coverage['targetSourceCount'] != 876:
        raise ValueError('Snapshot is outside the selected source route')
    if world.get('paging') or world.get('streaming') or world.get('background') or world['route']['path'] != 'route/index.json':
        raise ValueError('Require the declared GS-only route world')
    files = {'world.json', 'cameras.json', 'coverage.json', 'SOURCE_LICENSE', 'scene.spz', 'route/index.json'}
    index = read(ordinary(source, 'route/index.json'))
    if len(index['segments']) != coverage['segments']:
        raise ValueError('Segment count differs from completed coverage')
    ids = set()
    for segment in index['segments']:
        if segment['id'] in ids:
            raise ValueError('Duplicate segment')
        ids.add(segment['id'])
        manifest = PurePosixPath('route') / relative(segment['world'])
        child = read(ordinary(source, str(manifest)))
        if child.get('route') or child.get('streaming') or child.get('background') or not child.get('paging') or child['assets'][0]['format'] != 'spz' or child['coordinates']['unit'] != world['coordinates']['unit']:
            raise ValueError('Require standalone RAD/SPZ child in matching units')
        base = manifest.parent
        metadata = ['SOURCE_LICENSE']
        if child['navigation'].get('camerasPath'):
            metadata.append(child['navigation']['camerasPath'])
        files.add(str(manifest))
        files.update(str(base / relative(name)) for name in metadata)
        files.add(str(base / relative(child['assets'][0]['path'])))
        paged_name = base / relative(child['paging']['path'])
        paged = read(ordinary(source, str(paged_name)))
        if paged.get('kind') != 'spark-rad' or paged['root'] not in [x['path'] for x in paged['files']] or len({x['path'] for x in paged['files']}) != len(paged['files']):
            raise ValueError('Invalid or duplicate native paging declarations')
        files.add(str(paged_name))
        for item in paged['files']:
            name = str(paged_name.parent / relative(item['path']))
            if not name.endswith(('.rad', '.radc')):
                raise ValueError('Unexpected native paging asset')
            path = ordinary(source, name)
            if path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
                raise ValueError('Declared RAD integrity mismatch')
            files.add(name)
    frames = read(ordinary(source, 'cameras.json'))['frames']
    ranks = [int(frame['image'].removeprefix('panorama-rank-')) for frame in frames]
    if ranks != list(range(coverage['firstRank'], coverage['lastRank'] + 1)) or len(ranks) != coverage['sourceCount']:
        raise ValueError('Camera path does not match consecutive completed coverage')
    for name in files:
        path = ordinary(source, name)
        if path.suffix == '.json' or path.name == 'SOURCE_LICENSE':
            public_text(path.read_bytes())
    return coverage, sorted(files)


def atomic_bytes(path, data):
    """Replace the directory entry, never write through an immutable hardlink."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.publication-' + str(time.time_ns()))
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())


def prepare(repo, coordinator, snapshot, preview=None):
    repo, coordinator = repo.resolve(), coordinator.resolve()
    source = snapshot.resolve()
    if snapshot.is_symlink() or not source.is_relative_to(coordinator.resolve()) or not coordinator.resolve().is_relative_to(repo / 'data/jobs'):
        raise ValueError('Require an ordinary snapshot within the selected local coordinator')
    coverage, names = selected_files(source)
    selected = [dict(path=name, bytes=(source / name).stat().st_size, sha256=digest(source / name)) for name in names]
    state = read(coordinator / 'route-run.json')
    if not any(Path(export['path']).resolve() == source and export.get('status') == 'PASS' and export['segments'] == coverage['segments'] for export in state['exports']):
        raise ValueError('Snapshot is not a completed coordinator export')
    destination = repo / 'public/worlds' / IDENT
    if (destination / 'coverage.json').exists():
        old = read(destination / 'coverage.json')
        if old['firstRank'] < coverage['firstRank'] or old['lastRank'] > coverage['lastRank'] or old['segments'] > coverage['segments']:
            raise ValueError('Refuse regression of published source coverage')
    pending = coordinator / 'publication-pending' / f'{coverage["segments"]:03d}.json'
    if pending.exists():
        report = read(pending)
        if report['snapshot'] != str(source) or report['selectedFiles'] != selected or not Path(report['sourceWorld']).is_dir():
            raise ValueError('Pending publication lineage mismatch')
        return report
    # A selected original baseline render is an explicit placeholder, not proof
    # that the new route rendered. Later actual browser evidence replaces it.
    preview = preview or repo / 'public/worlds/paris-58m-lod-compact/preview.jpg'
    if not preview.is_file():
        raise ValueError('Require an explicitly selected licensed preview')
    publication = coordinator / ('publication-' + source.name + '-' + str(time.time_ns()))
    frozen = publication / 'world'
    frozen.mkdir(parents=True)
    for name in names:
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(source / name, target)
        except OSError:
            shutil.copyfile(source / name, target)
    shutil.copyfile(preview, frozen / 'preview.jpg')
    now = datetime.now(timezone.utc).isoformat()
    count, meters = coverage['sourceCount'], coverage['sourceGpsCoverageMeters']
    finding = f'{coverage["segments"]} trained segments, {count}/876 source cameras, source GPS coverage {meters:.2f}m/2185.31m. New route browser/boundary rendering NOT RUN; global geometry NOT ACCEPTED. Preview is the retained baseline GS render, not new-route rendering proof.'
    catalog_path = repo / 'public/worlds/catalog.json'
    catalog = read(catalog_path)
    previous = next((x for x in catalog['scenes'] if x['id'] == IDENT), None)
    entry = dict(id=IDENT, title=f'Seine · {meters:.0f}m of 2.185km', description=f'{coverage["segments"]}개 실제 GS · {count}/876소스 · 새 경계 GPU검증 NOT RUN', category='experiment', manifestPath=f'/worlds/{IDENT}/world.json', thumbnailPath=f'/worlds/{IDENT}/preview.jpg', createdAt=previous['createdAt'] if previous else now, detail=finding)
    catalog['scenes'] = [x for x in catalog['scenes'] if x['id'] != IDENT] + [entry]
    timeline_path = repo / 'public/experiments/lab/timeline.json'
    timeline = read(timeline_path)
    observation_id = f'report-seine-route-{coverage["segments"]:03d}'
    if not any(x['id'] == observation_id for x in timeline['entries']):
        timeline['entries'].append(dict(id=observation_id, kind='scene', title=entry['title'], description=entry['description'], image=entry['thumbnailPath'], href='/?world=' + entry['manifestPath'], createdAt=coverage['exportedAt'], detail=finding))
    summary_path = repo / 'public/experiments/tourist-streaming/summary.json'
    summary = read(summary_path)
    summary.update(updatedAt=now, phase='seine-route-native-export', summary=f'{coverage["segments"]}개 실제 GS 구간과 {count}개 소스 시점이 공통 좌표로 연결된 부분 결과입니다. 소스 GPS 약{meters:.2f}m이며 기하 실측 길이가 아닙니다. 새 구간 경계·연속탐색 GPU 검증은 NOT RUN입니다. 전체876소스/2.185km 목표는 진행 중이며 이전 장면·실패·사용자 Safari 확인을 보존합니다.', result=dict(worldPath=entry['manifestPath'], poster=entry['thumbnailPath'], label='현재 연결된 구간 탐색', detail=finding))
    stage_id = 'Seine snapshot ' + f'{coverage["segments"]:03d}'
    if not any(x['title'] == stage_id for x in summary['stages']):
        summary['stages'].insert(0, dict(title=stage_id, status='PASS native export / NOT RUN new route GPU boundary', detail=finding))
    expansion = summary.setdefault('expansion', {})
    expansion.update(status='RUNNING' if count < 876 else 'NATIVE EXPORT COMPLETE / BROWSER NOT RUN', currentReconstructedSourceRecords=count, currentApproximateReconstructedGpsLengthM=meters, fullRouteExportStatus='PASS' if count == 876 else 'NOT RUN full target; partial export PASS', fullRouteBrowserAcceptance='NOT RUN')
    snapshots = expansion.setdefault('snapshots', [])
    if not any(x['segments'] == coverage['segments'] for x in snapshots):
        snapshots.append({**coverage, 'coverageSha256': digest(source / 'coverage.json'), 'routeIndexSha256': digest(source / 'route/index.json')})
    spec_path = repo / 'scripts/observation-worlds.json'
    spec = read(spec_path)
    spec['worlds'] = [x for x in spec['worlds'] if x['id'] != IDENT] + [dict(id=IDENT, source=str(frozen.relative_to(repo)), asset='scene.spz', format='spz', credits=['SOURCE_LICENSE', 'coverage.json'])]
    for value in (catalog, timeline, summary):
        public_text(json.dumps(value, ensure_ascii=False).encode())
    for name in names:
        current = destination / name
        if name.startswith('route/segments/') and current.exists() and digest(current) != digest(frozen / name):
            raise ValueError('An already published immutable segment changed')
    # Metadata has passed preflight; expose files only through atomic replacement.
    for name in names + ['preview.jpg']:
        path = frozen / name
        current = destination / name
        if current.is_file() and current.stat().st_size == path.stat().st_size and digest(current) == digest(path):
            continue
        atomic_bytes(current, path.read_bytes())
    for path, value in [(catalog_path, catalog), (timeline_path, timeline), (summary_path, summary), (spec_path, spec)]:
        atomic_json(path, value)
    copies = (repo / 'deploy/Dockerfile.github').read_text().count('COPY --from=')
    report = dict(status='PREPARED', snapshot=str(source), sourceWorld=str(frozen), coverage=coverage, selectedFiles=selected, metadataFiles=[str(x.relative_to(repo)) for x in (catalog_path, timeline_path, summary_path, spec_path)], previewKind='retained baseline GS placeholder; new-route GPU NOT RUN', preparedAt=now, currentFinalCopyLayers=copies, consolidatePinnedLayersSoon=copies >= 90, next='Fresh build/full explicit curation, existing incremental overlay, release/checksum/pointer/connector dispatch, then public checks; preserve rollback layers.')
    atomic_json(publication / 'prepared.json', report)
    atomic_json(pending, report)
    return report


def main(args):
    coordinator = args.coordinator.resolve()
    snapshot = args.snapshot
    if snapshot is None:
        if not (coordinator / 'route-run.json').is_file():
            print(json.dumps(dict(status='WAITING FOR COORDINATOR STATE')))
            return
        exports = sorted(read(coordinator / 'route-run.json')['exports'], key=lambda x: x['segments'])
        snapshot = next((Path(x['path']) for x in exports if not (coordinator / 'publication-receipts' / f'{x["segments"]:03d}.json').exists()), None)
        if snapshot is None:
            print(json.dumps(dict(status='NO NEW COMPLETED SNAPSHOT')))
            return
    print(json.dumps(prepare(ROOT, coordinator, snapshot), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('coordinator', type=Path)
    parser.add_argument('--snapshot', type=Path)
    main(parser.parse_args())
