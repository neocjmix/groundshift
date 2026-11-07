#!/usr/bin/env python3
"""Reuse byte-verified DAV2 predictions; run the existing MPS backend for misses.

Local evidence only: sources, origins and execution logs may contain local paths.
No metric depth, model substitution or new MPS execution is claimed for cache hits.
Hardlinks require one filesystem and all inference artifacts remain immutable.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import numpy as np
from PIL import Image


BACKEND = Path(__file__).with_name('infer-relative-depth.py')
SPEC = importlib.util.spec_from_file_location('seine_depth_backend', BACKEND)
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
MODEL, REVISION = BASE.MODEL, BASE.REVISION
MEANING = 'Relative inverse-depth-like prediction; not meters, calibrated distance, measured depth or a reconstructed world'
TENSOR_SHAPE = [1, 3, 518, 518]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordinary(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Require an existing ordinary file: {path}')
    return path


def digest_value(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def image_input(path):
    path = ordinary(path)
    with Image.open(path) as source:
        source.load()
        size = list(source.size)
        if source.mode not in ('RGB', 'RGBA', 'L'):
            raise ValueError(f'Unsupported source image mode: {source.mode}')
    if size[0] != size[1]:
        raise ValueError('This route runner requires square tangent crops with the default 518 tensor')
    return dict(source=str(path.resolve()), sourceSha256=sha(path), size=size)


def load_cache(folder):
    folder = Path(folder)
    path = ordinary(folder / 'report.json')
    report = json.loads(path.read_text())
    if (report.get('schemaVersion') != 1 or report.get('status') != 'PASS'
            or report.get('model') != MODEL or report.get('revision') != REVISION
            or report.get('device') != 'mps' or report.get('outputMeaning') != MEANING
            or 'requestedInputSize' not in report or report['requestedInputSize'] is not None
            or not isinstance(report.get('images'), list) or not report['images']):
        raise ValueError(f'Cache must be a complete pinned default DAV2 MPS result: {folder}')
    report_sha = sha(path)
    entries = []
    for index, record in enumerate(report['images']):
        size = record.get('size')
        if (record.get('actualModelTensorShape') != TENSOR_SHAPE
                or not isinstance(size, list) or len(size) != 2 or size[0] != size[1]
                or any(type(value) is not int or value <= 0 for value in size)
                or any(not digest_value(record.get(key)) for key in ['sourceSha256', 'relativeNpySha256', 'visualSha256'])):
            raise ValueError(f'Invalid cached image metadata/default 518 tensor: {folder}, index {index}')
        entries.append(dict(folder=folder, index=index, record=record, reportSha256=report_sha,
                            torchVersion=report.get('torchVersion')))
    return report, entries


def verify_entry(entry, requested):
    """Read actual chosen bytes, not merely the cached PASS label."""
    record, folder, index = entry['record'], entry['folder'], entry['index']
    source = ordinary(record['source'])
    if (sha(source) != record['sourceSha256'] or record['sourceSha256'] != requested['sourceSha256']
            or record['size'] != requested['size']):
        raise ValueError('Cached original source bytes or dimensions differ')
    stem = f'view-{index:02d}'
    paths = {kind: ordinary(folder / f'{stem}-{suffix}') for kind, suffix in
             [('relative', 'relative.npy'), ('visual', 'visual.png'), ('source', 'source.png')]}
    for kind, field in [('relative', 'relativeNpySha256'), ('visual', 'visualSha256')]:
        if sha(paths[kind]) != record[field]:
            raise ValueError(f'Cached {kind} checksum differs')
    if record.get('sourcePreviewSha256') and sha(paths['source']) != record['sourcePreviewSha256']:
        raise ValueError('Cached source preview checksum differs')
    values = np.load(paths['relative'], allow_pickle=False)
    expected_shape = tuple(reversed(requested['size']))
    if (values.dtype != np.dtype('float32') or values.shape != expected_shape
            or not np.isfinite(values).all() or float(values.max()) <= float(values.min())
            or float(values.min()) != record.get('predictionMin') or float(values.max()) != record.get('predictionMax')):
        raise ValueError('Cached prediction must be finite varying float32 with exact source shape/range')
    with Image.open(paths['visual']) as visual:
        visual.load()
        if visual.mode != 'L' or list(visual.size) != requested['size']:
            raise ValueError('Cached depth visualization dimensions/mode differ')
    with Image.open(source) as original, Image.open(paths['source']) as preview:
        original.load()
        preview.load()
        if not np.array_equal(np.array(original.convert('RGB')), np.array(preview.convert('RGB'))):
            raise ValueError('Cached source preview pixels differ from its source')
    return paths


def invoke_backend(output, inputs):
    # This is always the existing pinned executable, with its ordinary default
    # neural size. Test code may patch this function; the CLI has no fake backend.
    command = [sys.executable, str(BACKEND), str(output), *[item['source'] for item in inputs]]
    with (output.parent / 'execution.log').open('x') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)


def run(output, inputs_json, reuse=()):
    output, inputs_json = Path(output), ordinary(inputs_json)
    if output.exists() or output.is_symlink():
        raise ValueError('Output exists; preserve prior execution evidence')
    raw = json.loads(inputs_json.read_text())
    if not isinstance(raw, list) or not raw or any(not isinstance(path, str) for path in raw):
        raise ValueError('Input JSON must be a nonempty list of image paths')
    if len(set(raw)) != len(raw):
        raise ValueError('Input paths must be unique')
    output.mkdir(parents=True)
    started = time.monotonic()
    report = dict(schemaVersion=1, status='RUNNING', startedAt=datetime.now(timezone.utc).isoformat(),
        model=MODEL, revision=REVISION, device='mps', outputMeaning=MEANING, requestedInputSize=None,
        deviceMeaning='Device of the original prediction evidence; see execution for whether this run invokes MPS',
        inputManifestSha256=sha(inputs_json), images=[], newlyInferred=0, reused=0,
        execution=dict(backendInvoked=False, backendStatus='NOT RUN', device=None, newInferenceElapsedSeconds=None),
        torchVersion=None, modelLoadSeconds=None)

    def save():
        report['elapsedSeconds'] = time.monotonic() - started
        temporary = output / 'report.json.tmp'
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        temporary.replace(output / 'report.json')

    save()
    try:
        inputs = [image_input(path) for path in raw]
        cache = {}
        for folder in reuse:
            _, entries = load_cache(folder)
            for entry in entries:
                record = entry['record']
                cache.setdefault((record['sourceSha256'], tuple(record['size'])), entry)
        chosen, misses = [], []
        for requested in inputs:
            entry = cache.get((requested['sourceSha256'], tuple(requested['size'])))
            if entry is not None:
                verify_entry(entry, requested)
            else:
                misses.append(requested)
            chosen.append(entry)
        if misses:
            report['execution'].update(backendInvoked=True, backendStatus='RUNNING', device='mps')
            save()
            invoke_backend(output / 'computed', misses)
            computed, entries = load_cache(output / 'computed')
            if len(entries) != len(misses):
                raise ValueError('Backend returned a different number of predictions')
            for entry, requested in zip(entries, misses):
                verify_entry(entry, requested)
            iterator = iter(entries)
            chosen = [entry if entry is not None else next(iterator) for entry in chosen]
            report['execution'].update(backendStatus='PASS', newInferenceElapsedSeconds=computed['elapsedSeconds'],
                                      modelLoadSeconds=computed['modelLoadSeconds'])
            report['torchVersion'] = computed['torchVersion']
            report['modelLoadSeconds'] = computed['modelLoadSeconds']
        for index, (requested, entry) in enumerate(zip(inputs, chosen)):
            paths = verify_entry(entry, requested)
            computed_this_run = entry['folder'] == output / 'computed'
            # Only this run's generated previews are changed, and only when
            # every encoded byte is identical to its immutable tangent crop.
            # Prior cache evidence and arbitrary input-image encodings stay put.
            if computed_this_run and sha(paths['source']) == requested['sourceSha256']:
                temporary = paths['source'].with_suffix('.link')
                os.link(requested['source'], temporary)
                temporary.replace(paths['source'])
            stem = f'view-{index:02d}'
            for kind, suffix in [('relative', 'relative.npy'), ('visual', 'visual.png'), ('source', 'source.png')]:
                os.link(paths[kind], output / f'{stem}-{suffix}')
            origin = dict(report=str((entry['folder'] / 'report.json').resolve()), reportSha256=entry['reportSha256'],
                          imageIndex=entry['index'], torchVersion=entry['torchVersion'],
                          inferenceSeconds=entry['record'].get('inferenceSeconds'),
                          previousOrigin=entry['record'].get('originEvidence'))
            record = {**entry['record'], **requested, 'computedThisRun': computed_this_run,
                      'inferenceSeconds': entry['record']['inferenceSeconds'] if computed_this_run else None,
                      'sourcePreviewSha256': sha(paths['source']), 'originEvidence': origin}
            report['images'].append(record)
            report['newlyInferred' if computed_this_run else 'reused'] += 1
            save()
        report['status'] = 'PASS'
    except Exception as error:
        report['status'] = 'FAIL'
        report['error'] = f'{type(error).__name__}: {error}'
        if report['execution']['backendStatus'] == 'RUNNING':
            report['execution']['backendStatus'] = 'FAIL'
        raise
    finally:
        report['finishedAt'] = datetime.now(timezone.utc).isoformat()
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('inputs_json', type=Path)
    parser.add_argument('--reuse', action='append', type=Path, default=[])
    args = parser.parse_args()
    try:
        report = run(args.output, args.inputs_json, args.reuse)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{type(error).__name__}: {error}\n')
    print(f"Depth PASS: {report['newlyInferred']} newly inferred, {report['reused']} reused; {args.output}")


if __name__ == '__main__':
    main()
