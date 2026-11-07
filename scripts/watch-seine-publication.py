#!/usr/bin/env python3
"""Publish completed local Seine exports through the existing branch-follow service.

Requires a verified Git-push rollout or an explicit connector queue. The latter
cannot trigger Railway itself. Never reads provider
credentials, runs reconstruction, or claims browser/GPU acceptance. Run one owner
only; stop this process before any manual publication or branch push.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
GIT = '/Library/Developer/CommandLineTools/usr/bin/git'
BRANCH = 'feat/local-viewer-reconstruction'
REPO = 'neocjmix/groundshift'
ORIGIN = 'https://groundshift-viewer-production.up.railway.app'
IMAGE = 'caddy:2.11.7-alpine@sha256:e70b164da81ef698b3ad19af799ea6086ce6d9e48ed4079eb9fe26f6fbf14ee5'
spec = importlib.util.spec_from_file_location('seine_publication', ROOT / 'scripts/publish-seine-route.py')
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


def now():
    return datetime.now(timezone.utc).isoformat()


def run(command, log, timeout=1800):
    env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GH_PROMPT_DISABLED': '1'}
    with log.open('ab') as output:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=output, timeout=timeout, check=False)
        output.write(result.stdout)
    if result.returncode:
        raise RuntimeError(f'{Path(command[0]).name} exited {result.returncode}; see private attempt log')
    return result.stdout.decode()


def runtime_revision(log):
    paths = ['src', 'build', 'scripts/package-viewer.mjs', 'scripts/package-viewer-overlay.py',
             'scripts/publish-seine-route.py', 'vite.config.ts', 'package.json', 'package-lock.json',
             'tsconfig.json', 'tsconfig.app.json', 'tsconfig.node.json']
    if run([GIT, 'status', '--porcelain', '--', *paths], log).strip():
        raise RuntimeError('Committed runtime source required; native jobs may continue independently')
    tracked = run([GIT, 'ls-files', '-z', '--', *paths], log).split('\0')
    record = hashlib.sha256()
    for name in sorted(filter(None, tracked)):
        record.update(name.encode() + b'\0' + (ROOT / name).read_bytes())
    return record.hexdigest()


def next_export(coordinator, submitted):
    state = coordinator / 'route-run.json'
    if not state.exists():
        return None
    exports = sorted(publication.read(state).get('exports', []), key=lambda item: item['segments'])
    return next((item for item in exports if item.get('status') == 'PASS'
                 and str(item['segments']) not in submitted
                 and not (coordinator / 'publication-receipts' / f'{item["segments"]:03d}.json').exists()), None)


def records(inventory):
    result = {}
    for item in inventory['files']:
        name = item['path']
        if name in result or name.startswith('/') or '..' in Path(name).parts:
            raise ValueError('Unsafe or duplicate local inventory path')
        result[name] = item
    return result


def retain_inert(current_path, base_path):
    """Only archived background files are allowed absent from fresh live curation."""
    current, base = publication.read(current_path), publication.read(base_path)
    selected = records(current)
    for name, item in records(base).items():
        if not name.startswith('www/') or name in selected or name.startswith('www/assets/'):
            continue
        if not re.fullmatch(r'www/worlds/street-tangent20/background/[A-Za-z0-9._-]+', name):
            raise ValueError('Prior observation absent from fresh curation: ' + name)
        source = Path(base['output']) / name
        if source.stat().st_size != item['bytes'] or publication.digest(source) != item['sha256']:
            raise ValueError('Historical background integrity mismatch')
        target = Path(current['output']) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, target)
        current['files'].append(item)
    publication.atomic_json(current_path, current)


def add_pointer(text, stage, tag, archive, sha):
    if not re.fullmatch(r'seine_snapshot_\d{3}', stage) or not re.fullmatch(r'[a-f0-9]{64}', sha):
        raise ValueError('Unsafe deployment pointer')
    if f' AS {stage}\n' in text:
        if f"'{sha}  /tmp/{stage}.tar.gz'" not in text:
            raise ValueError('Existing snapshot pointer differs')
        return text
    marker = f'FROM {IMAGE}\nCOPY deploy/Caddyfile'
    if text.count(marker) != 1 or text.count('COPY --from=') >= 90:
        raise ValueError('Deployment checkpoint consolidation required before adding layers')
    addition = (f'# Immutable completed route snapshot; new boundary GPU acceptance remains NOT RUN.\n'
                f'FROM {IMAGE} AS {stage}\n'
                f'RUN wget -q -O /tmp/{stage}.tar.gz https://github.com/{REPO}/releases/download/{tag}/{archive} \\\n'
                f" && echo '{sha}  /tmp/{stage}.tar.gz' | sha256sum -c - \\\n"
                f' && mkdir /out \\\n && tar -xzf /tmp/{stage}.tar.gz -C /out\n\n')
    result = text.replace(marker, addition + marker)
    return result.replace('EXPOSE 8080\n', f'COPY --from={stage} /out/www /srv\nEXPOSE 8080\n')


def public_hash(item):
    name = item['path'].removeprefix('www/')
    request = urllib.request.Request(ORIGIN + '/' + name, headers={'Accept-Encoding': 'identity', 'Cache-Control': 'no-cache'})
    size, digest = 0, hashlib.sha256()
    with urllib.request.urlopen(request, timeout=45) as response:
        if response.status != 200 or response.headers.get('Content-Encoding') not in (None, 'identity'):
            raise ValueError('Unexpected public response encoding/status')
        while data := response.read(1024 * 1024):
            size += len(data)
            digest.update(data)
    if size != item['bytes'] or digest.hexdigest() != item['sha256']:
        raise ValueError('Public bytes not ready: ' + name)
    return {'path': item['path'], 'bytes': size, 'sha256': digest.hexdigest()}


def verify_archive(url, archive):
    size, sha = 0, hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(url, headers={'Accept-Encoding': 'identity'}), timeout=120) as response:
        while data := response.read(1024 * 1024):
            size += len(data)
            sha.update(data)
    if size != archive.stat().st_size or sha.hexdigest() != publication.digest(archive):
        raise ValueError('Anonymous release archive readback mismatch')
    return dict(status='PASS', bytes=size, sha256=sha.hexdigest(), checkedAt=now())


def advance(coordinator, state, state_path):
    active = state['active']
    attempt = Path(active['attempt'])
    log = attempt / 'commands.log'

    def checkpoint(phase, **values):
        active.update(phase=phase, updatedAt=now(), **values)
        publication.atomic_json(state_path, state)

    if active['phase'] == 'NEW':
        prepared = publication.prepare(ROOT, coordinator, Path(active['snapshot']))
        checkpoint('PREPARED', prepared=prepared)
    if active['phase'] == 'PREPARED':
        revision = runtime_revision(log)
        run(['npm', 'run', 'build'], log)
        if runtime_revision(log) != revision:
            raise RuntimeError('Runtime source changed during build; retry before publication')
        output = json.loads(run(['node', 'scripts/package-viewer.mjs', '--include-reconstruction',
                                '--include-independent', '--include-desk', '--include-experiments',
                                '--reuse-inventory', state['baseInventory']], log))
        inventory = Path(output['output'] + '.inventory.json')
        if runtime_revision(log) != revision:
            raise RuntimeError('Runtime source changed during curation; retry before publication')
        retain_inert(inventory, Path(state['baseInventory']))
        archive = attempt / f'groundshift-seine-route-{active["segments"]:03d}-{time.time_ns()}.tar.gz'
        run(['python3', 'scripts/package-viewer-overlay.py', str(inventory), state['baseInventory'], str(archive)], log)
        overlay = publication.read(archive.with_suffix('.json'))
        checkpoint('PACKAGED', inventory=str(inventory), archive=str(archive), overlay=overlay, runtimeRevision=revision)
    if active['phase'] == 'PACKAGED':
        tag = f'viewer-seine-route-{active["segments"]:03d}-{active["nonce"]}'
        archive = Path(active['archive'])
        notes = attempt / 'release-notes.md'
        notes.write_text(f'Completed immutable local route snapshot {active["segments"]:03d}.\n\n'
                         f'SHA-256: {publication.digest(archive)}\n'
                         'New route boundary/browser acceptance NOT RUN; global geometry NOT ACCEPTED.\n'
                         'Selected licensed derived GS assets only; raw inputs/logs/weights remain local.\n')
        # A crash after upload is recovered by reading the same unique release; no clobber.
        exists = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO], cwd=ROOT,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        if not exists:
            run(['gh', 'release', 'create', tag, str(archive), '--repo', REPO, '--target',
                 run([GIT, 'rev-parse', 'HEAD'], log).strip(), '--title', f'Seine route snapshot {active["segments"]:03d}',
                 '--notes-file', str(notes)], log)
        url = f'https://github.com/{REPO}/releases/download/{tag}/{archive.name}'
        checkpoint('UPLOADED', tag=tag, anonymousArchive=verify_archive(url, archive))
    if active['phase'] == 'UPLOADED':
        docker = ROOT / 'deploy/Dockerfile.github'
        sha = active['overlay']['sha256']
        publication.atomic_bytes(docker, add_pointer(docker.read_text(), f'seine_snapshot_{active["segments"]:03d}',
                                                    active['tag'], Path(active['archive']).name, sha).encode())
        doc = ROOT / 'docs/DEPLOYMENT.md'
        marker = f'<!-- seine-snapshot-{active["segments"]:03d} -->'
        if marker not in doc.read_text():
            doc.write_text(doc.read_text() + f'\n{marker}\n\n### Automated route snapshot {active["segments"]:03d}\n\n'
                           f'Release `{active["tag"]}`, archive `{Path(active["archive"]).name}`, '
                           f'{active["overlay"]["bytes"]:,}bytes, SHA-256 `{sha}`. '
                           f'Apply after every previously pinned archive, in Docker COPY order. '
                           f'Explicit curation, complete base/overlay/composed checks and anonymous full archive readback PASS. '
                           f'{active["overlay"]["overlayFiles"]} changed files; '
                           f'{active["overlay"]["assembledFiles"]} composed files. '
                           'Git push dispatches the verified branch-follow service asynchronously. '
                           'Provider status, public hashes and new GPU boundary/browser checks are NOT RUN at this source commit; '
                           'private publication receipts record later actual readback without inventing acceptance.\n')
        paths = ['deploy/Dockerfile.github', 'docs/DEPLOYMENT.md', 'scripts/observation-worlds.json', 'public/worlds/catalog.json']
        diff = run([GIT, 'diff', '--name-only', 'HEAD', '--', *paths], log).strip()
        if diff:
            run([GIT, 'add', '--', *paths], log)
            run([GIT, 'commit', '--only', '-m', f'deploy: publish immutable Seine snapshot {active["segments"]:03d}', '--', *paths], log)
        checkpoint('COMMITTED', commit=run([GIT, 'rev-parse', 'HEAD'], log).strip())
    if active['phase'] == 'COMMITTED':
        run([GIT, 'push', 'origin', f'HEAD:refs/heads/{BRANCH}'], log, timeout=180)
        active.update(phase='PUSHED', pushedAt=now(), railwayProviderStatus='NOT RUN by background worker',
                      browserRendering='NOT RUN', globalGeometry='NOT ACCEPTED')
        if state.get('deliveryMode') == 'CONNECTOR QUEUE':
            active['status'] = 'DISPATCH_PENDING'
            publication.atomic_json(coordinator / 'publication-dispatch' / f'{active["segments"]:03d}.json',
                {**active, 'requiredNextAction': 'Healthy Railway connector must trigger this exact pointer, then verify actual rollout and public hashes. Git push alone is not Railway dispatch.',
                 'target': dict(link_id='link_6aa0e4f20e58819184c9a6f6974fcfaa',
                                projectId='db649cd6-49db-4750-b86d-c3c4d14b213d',
                                serviceId='2c6ac4d5-37bb-4ea8-aee0-1e75a1abdf69',
                                environmentId='43346592-217f-414e-b2ad-334e09b37599', repo=REPO, branch=BRANCH),
                 'heartbeatMaximumPlannedMinutes': 5})
        state['submissions'][str(active['segments'])] = dict(active)
        state['baseInventory'] = active['overlay']['assembledInventory']
        state['active'] = None
        publication.atomic_json(state_path, state)


def check_submissions(coordinator, state, state_path):
    # Check the canonical coverage first; avoid re-downloading large files until ready.
    for key, submission in state['submissions'].items():
        if submission.get('publicHashes') == 'PASS' or submission.get('status') == 'SUPERSEDED BY LATER VERIFIED SNAPSHOT':
            continue
        changed = submission['overlay']['changedFiles']
        coverage = next(item for item in changed if item['path'] == 'www/worlds/seine-full-route/coverage.json')
        try:
            public_hash(coverage)
            with ThreadPoolExecutor(max_workers=4) as executor:
                verified = list(executor.map(public_hash, changed))
        except (OSError, ValueError) as error:
            submission['lastPublicCheck'] = dict(at=now(), status='NOT READY', errorType=type(error).__name__)
            later = [value for other, value in state['submissions'].items()
                     if int(other) > int(key) and value.get('publicHashes') == 'PASS']
            if later:
                # Cumulative later publication retains these immutable segments.
                # Do not pretend superseded canonical metadata was observed live.
                immutable = [item for item in changed if item['path'].startswith('www/worlds/seine-full-route/route/segments/')]
                with ThreadPoolExecutor(max_workers=4) as executor:
                    verified = list(executor.map(public_hash, immutable))
                submission.update(status='SUPERSEDED BY LATER VERIFIED SNAPSHOT',
                                  immutablePublicFiles=verified, canonicalPublicHashes='NOT RUN before supersession',
                                  supersededBy=max(item['segments'] for item in later), deliveredAt=now())
                publication.atomic_json(coordinator / 'publication-receipts' / f'{int(key):03d}.json', submission)
            continue
        submission.update(publicHashes='PASS', publicFiles=verified, deliveredAt=now())
        receipt = {**submission, 'status': 'DELIVERED PUBLIC HASHES',
                   'meaning': 'Git push plus exact anonymous public bytes; provider status/GPU/browser acceptance remain separate.'}
        publication.atomic_json(coordinator / 'publication-receipts' / f'{int(key):03d}.json', receipt)
    publication.atomic_json(state_path, state)


def main(args):
    coordinator = args.coordinator.resolve()
    if not coordinator.is_relative_to(ROOT / 'data/jobs'):
        raise ValueError('Coordinator must remain in local job boundary')
    coordinator.mkdir(parents=True, exist_ok=True)
    with (coordinator / '.static-publication.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        proof = publication.read(args.autodeploy_proof)
        target_matches = (proof.get('branch') == BRANCH
                          and proof.get('serviceId') == '2c6ac4d5-37bb-4ea8-aee0-1e75a1abdf69')
        verified = proof.get('status') == 'PASS' and proof.get('sourceCommitSha') is None and proof.get('trigger') == 'git-push-observed'
        fallback = args.connector_fallback and proof.get('status') == 'BLOCKED' and proof.get('trigger') == 'connector-heartbeat-queue'
        if not target_matches or not (verified or fallback):
            raise ValueError('Require actual branch-follow push/rollout verification')
        worker = coordinator / 'static-publication'
        worker.mkdir(exist_ok=True)
        state_path = worker / 'state.json'
        log = worker / 'worker-commands.log'
        if run([GIT, 'branch', '--show-current'], log).strip() != BRANCH:
            raise ValueError('Wrong publication branch')
        if not run([GIT, 'remote', 'get-url', 'origin'], log).strip().removesuffix('.git').endswith('github.com/' + REPO):
            raise ValueError('Wrong publication repository')
        state = publication.read(state_path) if state_path.exists() else dict(baseInventory=str(args.base_inventory.resolve()), submissions={}, active=None)
        if args.adopt_base_inventory:
            if state.get('active') is not None:
                raise ValueError('Cannot adopt a manual publication base during an unfinished transaction')
            base = publication.read(args.base_inventory)
            for name, item in records(base).items():
                source = Path(base['output']) / name
                if not source.is_file() or source.is_symlink() or source.stat().st_size != item['bytes'] or publication.digest(source) != item['sha256']:
                    raise ValueError('Adopted composed inventory integrity mismatch')
            state['baseInventory'] = str(args.base_inventory.resolve())
        state['deliveryMode'] = 'CONNECTOR QUEUE' if fallback else 'VERIFIED GIT AUTODEPLOY'
        while True:
            try:
                check_submissions(coordinator, state, state_path)
                if state['active'] is None:
                    export = next_export(coordinator, state['submissions'])
                    if export:
                        nonce = str(time.time_ns())
                        attempt = worker / f'snapshot-{export["segments"]:03d}-{nonce}'
                        attempt.mkdir()
                        state['active'] = dict(phase='NEW', snapshot=export['path'], segments=export['segments'], nonce=nonce, attempt=str(attempt))
                        publication.atomic_json(state_path, state)
                if state['active']:
                    advance(coordinator, state, state_path)
                status = 'WAITING FOR COMPLETED NATIVE EXPORT' if state['active'] is None else state['active']['phase']
                error = None
            except Exception as failure:
                status, error = 'RETRYABLE PUBLICATION BLOCKER', str(failure)
            publication.atomic_json(worker / 'heartbeat.json', dict(pid=os.getpid(), at=now(), status=status,
                error=error, pollSeconds=args.poll_seconds, baseInventory=state['baseInventory'],
                submittedSegments=sorted(map(int, state['submissions'])), active=state['active'],
                deliveryMode=state['deliveryMode'],
                publicBrowser='NOT RUN by worker', railwayStatus='NOT RUN by worker; public hashes checked independently'))
            if args.once:
                break
            time.sleep(args.poll_seconds)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('coordinator', type=Path)
    parser.add_argument('--base-inventory', type=Path, required=True)
    parser.add_argument('--autodeploy-proof', type=Path, required=True)
    parser.add_argument('--connector-fallback', action='store_true', help='Upload/push immediately; queue DISPATCH_PENDING for the separately running connector heartbeat.')
    parser.add_argument('--adopt-base-inventory', action='store_true', help='After stopping for manual metadata publication, verify and adopt its latest composed inventory.')
    parser.add_argument('--poll-seconds', type=float, default=5)
    parser.add_argument('--once', action='store_true')
    main(parser.parse_args())
