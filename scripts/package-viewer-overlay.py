#!/usr/bin/env python3
"""Checksum an explicit viewer package and archive only changes to a pinned base."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import time


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def records(inventory):
    result = {}
    for item in inventory['files']:
        name = item['path']; p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or str(p) != name or name in result:
            raise ValueError('Unsafe or duplicate inventory path')
        if name.startswith('www/'):
            result[name] = item
    return result


def main(args):
    start = time.perf_counter()
    current = json.loads(args.inventory.read_text()); base = json.loads(args.base.read_text())
    selected = records(current); previous = records(base)
    stage = Path(current['output']).resolve(); base_stage = Path(base['output']).resolve()
    if args.archive.exists() or args.archive.with_suffix('.json').exists():
        raise ValueError('Archive/evidence already exists')
    for folder, entries in [(stage, selected), (base_stage, previous)]:
        for name, item in entries.items():
            p = folder / name
            if not p.is_file() or p.is_symlink() or p.stat().st_size != item['bytes'] or digest(p) != item['sha256']:
                raise ValueError('Inventory/disk mismatch: ' + name)
            if not p.resolve().is_relative_to(folder):
                raise ValueError('Source escapes explicit package')
    # Keep every prior dataset/report path. Old compiled assets may remain in base.
    missing = [name for name in previous if name not in selected and not name.startswith('www/assets/')]
    if missing:
        raise ValueError('Prior observation absent from new curated package: ' + repr(missing))
    changed = [name for name, item in selected.items() if previous.get(name) != item]
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    assembled_dir = args.archive.with_suffix('.assembled')
    assembled_dir.mkdir(exist_ok=False)
    for name in previous:
        target = assembled_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(base_stage / name, target)
    with tarfile.open(args.archive, 'x:gz', format=tarfile.PAX_FORMAT) as archive:
        for name in sorted(changed):
            archive.add(stage / name, arcname=name, recursive=False)
    with tarfile.open(args.archive) as archive:
        members = archive.getmembers()
        if sorted(m.name for m in members) != sorted(changed) or any(not m.isfile() for m in members):
            raise ValueError('Archive member mismatch')
        assembled = dict(previous)
        for member in members:
            data = archive.extractfile(member).read()
            item = dict(path=member.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            if item != selected[member.name]:
                raise ValueError('Archive readback mismatch')
            assembled[member.name] = item
            target = assembled_dir / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()  # Never modify the hard-linked immutable base.
            target.write_bytes(data)
    if any(assembled.get(name) != item for name, item in selected.items()):
        raise ValueError('Base plus overlay does not reconstruct new inventory')
    for name, item in assembled.items():
        target = assembled_dir / name
        if target.stat().st_size != item['bytes'] or digest(target) != item['sha256']:
            raise ValueError('Physically assembled target mismatch: ' + name)
    assembled_inventory = assembled_dir.with_suffix('.inventory.json')
    assembled_inventory.write_text(json.dumps(dict(output=str(assembled_dir.resolve()), files=list(assembled.values())), indent=2)+'\n')
    report = dict(status='PASS', archive=str(args.archive.resolve()), bytes=args.archive.stat().st_size,
        sha256=digest(args.archive), baseInventory=str(args.base.resolve()), inventory=str(args.inventory.resolve()),
        targetFiles=len(selected), overlayFiles=len(changed), retainedBaseOnlyCompiledFiles=[n for n in previous if n not in selected],
        assembledFiles=len(assembled), assembledPublicBytes=sum(item['bytes'] for item in assembled.values()),
        assembledInventory=str(assembled_inventory.resolve()), assembledDirectory=str(assembled_dir.resolve()),
        elapsedSeconds=time.perf_counter()-start,
        assemblyMeaning='Every base/current file checksummed on disk; every overlay member checksummed after decompression; physical hard-linked base plus separately written overlay matches every assembled file and every new target. Old compiled public assets may remain.',
        changedFiles=[selected[n] for n in sorted(changed)])
    args.archive.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','bytes','sha256','targetFiles','overlayFiles','assembledFiles','elapsedSeconds']}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path); parser.add_argument('base', type=Path); parser.add_argument('archive', type=Path)
    main(parser.parse_args())
