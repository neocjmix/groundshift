#!/usr/bin/env python3
"""Lossless storage for completed new Seine depth jobs; old experiments excluded.

Archive bytes are reversible four-byte shuffle + zlib6, not float quantization.
Every original NPY byte is checked before any raw alias is unlinked. A durable
manifest and SHA-addressed blob retain all aliases; read_npy_bytes and restore_npy
work after interruption. Only data/jobs/seine-full-YYYYMMDD/segment-N-N is allowed.
The coordinator must freeze a completed job before archiving it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import time
import uuid
import zlib


ROOT = Path(__file__).resolve().parents[1]
MAGIC = b'GSNPY\x01\r\n'
CODEC = 'byte-shuffle4-zlib6-v1'
MAX_RAW_BYTES = 16 * 1024 * 1024
MANIFEST = 'archive-manifest.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode_npy(raw):
    if not raw.startswith(b'\x93NUMPY') or not 6 <= len(raw) <= MAX_RAW_BYTES:
        raise ValueError('Require bounded original NPY bytes')
    padded = raw + b'\0' * (-len(raw) % 4)
    shuffled = b''.join(padded[index::4] for index in range(4))
    metadata = json.dumps(dict(codec=CODEC, originalBytes=len(raw), sha256=digest(raw)),
                          sort_keys=True, separators=(',', ':')).encode()
    return MAGIC + struct.pack('<I', len(metadata)) + metadata + zlib.compress(shuffled, 6)


def decode_npy(encoded, *, expected_sha256=None, expected_bytes=None):
    if not encoded.startswith(MAGIC) or len(encoded) < len(MAGIC) + 4:
        raise ValueError('Invalid archive magic or truncated header')
    size = struct.unpack_from('<I', encoded, len(MAGIC))[0]
    start = len(MAGIC) + 4
    if not 1 <= size <= 4096 or len(encoded) <= start + size:
        raise ValueError('Invalid archive metadata length')
    try:
        metadata = json.loads(encoded[start:start + size])
    except (ValueError, UnicodeError) as error:
        raise ValueError('Invalid archive metadata') from error
    if not isinstance(metadata, dict):
        raise ValueError('Invalid archive metadata object')
    count, checksum = metadata.get('originalBytes'), metadata.get('sha256')
    if (metadata.get('codec') != CODEC or type(count) is not int or not 6 <= count <= MAX_RAW_BYTES
            or not isinstance(checksum, str) or not re.fullmatch(r'[0-9a-f]{64}', checksum)
            or expected_sha256 is not None and checksum != expected_sha256
            or expected_bytes is not None and count != expected_bytes):
        raise ValueError('Archive metadata or expected original identity mismatch')
    padded_count = (count + 3) // 4 * 4
    try:
        decoder = zlib.decompressobj()
        shuffled = decoder.decompress(encoded[start + size:], padded_count + 1)
    except zlib.error as error:
        raise ValueError('Corrupt archive zlib payload') from error
    if (not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
            or len(shuffled) != padded_count):
        raise ValueError('Truncated, trailing or oversized archive payload')
    raw = bytearray(padded_count)
    plane_size = padded_count // 4
    for index in range(4):
        raw[index::4] = shuffled[index * plane_size:(index + 1) * plane_size]
    result = bytes(raw[:count])
    if not result.startswith(b'\x93NUMPY') or digest(result) != checksum:
        raise ValueError('Original NPY SHA mismatch after decompression')
    return result


def _ordinary(path, root, *, may_be_absent=False):
    path, root = Path(path).absolute(), Path(root).resolve()
    if '..' in path.parts or not path.is_relative_to(root):
        raise ValueError('Path escapes the authorized new task root')
    current = root
    for component in path.relative_to(root).parts:
        current = current / component
        if current.is_symlink():
            raise ValueError('Symlink archive paths are forbidden')
        if not current.exists() and not may_be_absent:
            raise ValueError('Missing archive path')
    return path


def _job(job, repo):
    repo = Path(repo).resolve()
    job = _ordinary(job, repo)
    relative = job.relative_to(repo)
    if (len(relative.parts) != 4 or relative.parts[:2] != ('data', 'jobs')
            or not re.fullmatch(r'seine-full-\d{8}', relative.parts[2])
            or not re.fullmatch(r'segment-\d+-\d+', relative.parts[3]) or not job.is_dir()):
        raise ValueError('Only new Seine segment jobs may be archived')
    return job


def _stamp(path):
    value = path.stat()
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, stat.S_IMODE(value.st_mode)


def _atomic_bytes(path, data, *, mode=None, mtime_ns=None):
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            temporary.chmod(mode)
        if mtime_ns is not None:
            os.utime(temporary, ns=(mtime_ns, mtime_ns))
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def _manifest(depth):
    path = depth / MANIFEST
    _ordinary(path, depth.parent.parent, may_be_absent=True)
    if not path.exists():
        return dict(schemaVersion=1, codec=CODEC, state='VERIFIED_ARCHIVES', entries={})
    _ordinary(path, depth.parent.parent)
    value = json.loads(path.read_text())
    if (value.get('schemaVersion') != 1 or value.get('codec') != CODEC
            or value.get('state') not in ('VERIFIED_ARCHIVES', 'ARCHIVED')
            or not isinstance(value.get('entries'), dict)):
        raise ValueError('Invalid original-byte archive manifest')
    return value


def _blob(task, entry):
    checksum = entry.get('sha256')
    if not isinstance(checksum, str) or not re.fullmatch(r'[0-9a-f]{64}', checksum):
        raise ValueError('Invalid original SHA in manifest')
    return _ordinary(task / 'depth-archive' / (checksum + '.npy.sz'), task)


def _read_blob(blob):
    if blob.stat().st_size > MAX_RAW_BYTES + 8192:
        raise ValueError('Archive exceeds bounded encoded size')
    return blob.read_bytes()


def _location(path, repo):
    path, repo = Path(path).absolute(), Path(repo).resolve()
    relative = path.relative_to(repo)
    if len(relative.parts) < 6 or relative.parts[4] != 'depth':
        raise ValueError('Require a new Seine depth NPY path')
    job = _job(repo.joinpath(*relative.parts[:4]), repo)
    _ordinary(path, job.parent, may_be_absent=True)
    if not re.fullmatch(r'view-\d+-relative\.npy', path.name):
        raise ValueError('Only relative-depth NPY paths are supported')
    return job, path, path.relative_to(job / 'depth').as_posix()


def read_npy_bytes(path, *, repo=ROOT):
    """Read an existing NPY, or its exact verified bytes from the new-task archive."""
    path = Path(path)
    if path.is_file() and not path.is_symlink():
        # Existing immutable legacy caches remain readable without being mutable
        # archive candidates. Cache callers still validate their original report.
        if path.stat().st_size > MAX_RAW_BYTES:
            raise ValueError('Raw NPY exceeds bounded size')
        raw = path.read_bytes()
        if not raw.startswith(b'\x93NUMPY'):
            raise ValueError('Not original NPY bytes')
        return raw
    job, path, relative = _location(path, repo)
    entry = _manifest(job / 'depth')['entries'].get(relative)
    if not isinstance(entry, dict):
        raise ValueError('No verified archive for this missing NPY')
    blob = _blob(job.parent, entry)
    return decode_npy(_read_blob(blob), expected_sha256=entry['sha256'], expected_bytes=entry['bytes'])


def restore_npy(path, *, repo=ROOT):
    """Materialize one original path without removing its checked archive."""
    job, path, relative = _location(path, repo)
    entry = _manifest(job / 'depth')['entries'].get(relative)
    if not isinstance(entry, dict):
        raise ValueError('No verified archive to restore')
    if path.exists():
        if digest(read_npy_bytes(path, repo=repo)) != entry['sha256']:
            raise ValueError('Existing original differs from archive')
        return path
    raw = read_npy_bytes(path, repo=repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_bytes(path, raw, mode=entry['mode'], mtime_ns=entry['mtimeNs'])
    if digest(path.read_bytes()) != entry['sha256']:
        raise ValueError('Restored original failed SHA check')
    return path


def archive_completed_depth(job, *, repo=ROOT, apply=False):
    job = _job(job, repo)
    native = _ordinary(job / 'training/job.json', job.parent)
    if json.loads(native.read_text()).get('status') != 'PASS':
        raise ValueError('Only a completed PASS native training job may be archived')
    depth = _ordinary(job / 'depth', job.parent)
    expected_files = {}
    for folder in [depth, *([depth / 'computed'] if (depth / 'computed').exists() else [])]:
        model_report = _ordinary(folder / 'report.json', job.parent)
        report = json.loads(model_report.read_text())
        if report.get('status') != 'PASS' or not isinstance(report.get('images'), list) or not report['images']:
            raise ValueError('Require a completed PASS depth job with prediction identities')
        for index, record in enumerate(report['images']):
            checksum = record.get('relativeNpySha256')
            if not isinstance(checksum, str) or not re.fullmatch(r'[0-9a-f]{64}', checksum):
                raise ValueError('Missing original NPY SHA in depth report')
            expected_files[folder / f'view-{index:02d}-relative.npy'] = checksum
    start = time.monotonic()
    free = lambda: os.statvfs(job).f_bavail * os.statvfs(job).f_frsize
    result = dict(status='RUNNING', mode='apply' if apply else 'audit', codec=CODEC,
                  freeBeforeBytes=free(), rawAliases=0, uniqueInodes=0, rawUniqueBytes=0,
                  encodedBytesForUniqueInodes=0, newBlobBytes=0, removedAliases=0, groups=[])
    groups = {}
    for path in sorted(depth.rglob('*-relative.npy')):
        _ordinary(path, job.parent)
        if not path.is_file() or path not in expected_files:
            raise ValueError('Unexpected raw prediction path')
        stamp = _stamp(path)
        groups.setdefault(stamp[:2], []).append((path, stamp))
    manifest = _manifest(depth)
    for path, expected_sha in expected_files.items():
        if digest(read_npy_bytes(path, repo=repo)) != expected_sha:
            raise ValueError('Prediction differs from original inference-report SHA')
    # Existing missing aliases must remain recoverable on retry/idempotent runs.
    for relative, entry in manifest['entries'].items():
        candidate = _ordinary(depth / relative, depth, may_be_absent=True)
        if not candidate.exists():
            read_npy_bytes(candidate, repo=repo)
    destination = _ordinary(job.parent / 'depth-archive', job.parent, may_be_absent=True)
    if apply:
        destination.mkdir(exist_ok=True)
    verified, new_blob_hashes = [], set()
    for aliases in groups.values():
        path, stamp = aliases[0]
        raw = read_npy_bytes(path, repo=repo)
        checksum = digest(raw)
        encoded = encode_npy(raw)
        if decode_npy(encoded, expected_sha256=checksum, expected_bytes=len(raw)) != raw:
            raise ValueError('Archive did not preserve original bytes')
        blob = destination / (checksum + '.npy.sz')
        _ordinary(blob, job.parent, may_be_absent=True)
        if not blob.exists() and checksum not in new_blob_hashes:
            result['newBlobBytes'] += len(encoded)
            new_blob_hashes.add(checksum)
        if apply:
            if blob.exists():
                _ordinary(blob, job.parent)
            else:
                _atomic_bytes(blob, encoded)
            if decode_npy(_read_blob(blob), expected_sha256=checksum, expected_bytes=len(raw)) != raw:
                raise ValueError('Saved archive differs from original')
        for candidate, expected in aliases:
            if _stamp(candidate) != expected:
                raise ValueError('Completed raw prediction changed during archive')
            relative = candidate.relative_to(depth).as_posix()
            entry = dict(sha256=checksum, bytes=len(raw), mode=expected[4], mtimeNs=expected[3])
            if relative in manifest['entries'] and manifest['entries'][relative]['sha256'] != checksum:
                raise ValueError('Original bytes changed since the previous archive')
            manifest['entries'][relative] = entry
        result['groups'].append(dict(sha256=checksum, aliases=len(aliases), originalBytes=len(raw),
            archiveBytes=len(encoded), linksOutsideThisJob=max(0, path.stat().st_nlink - len(aliases))))
        result['rawAliases'] += len(aliases)
        result['rawUniqueBytes'] += len(raw)
        result['encodedBytesForUniqueInodes'] += len(encoded)
        verified.extend(aliases)
    result['uniqueInodes'] = len(groups)
    if apply:
        manifest['state'] = 'VERIFIED_ARCHIVES'
        _atomic_bytes(depth / MANIFEST, (json.dumps(manifest, indent=2) + '\n').encode())
        # All blobs and their complete alias map are durable before unlinking.
        for path, expected in verified:
            if _stamp(path) != expected:
                raise ValueError('Raw prediction changed before unlink')
            path.unlink()
            result['removedAliases'] += 1
        manifest['state'] = 'ARCHIVED'
        _atomic_bytes(depth / MANIFEST, (json.dumps(manifest, indent=2) + '\n').encode())
    result.update(status='PASS', freeAfterBytes=free(), seconds=time.monotonic() - start)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job', type=Path)
    parser.add_argument('--apply', action='store_true', help='Archive verified completed new job and unlink its raw NPY aliases')
    parser.add_argument('--restore', action='store_true', help='Restore all original NPY aliases, retaining archives')
    args = parser.parse_args()
    if args.restore:
        if args.apply:
            parser.error('--restore and --apply are separate operations')
        job = _job(args.job, ROOT)
        for relative in _manifest(job / 'depth')['entries']:
            restore_npy(job / 'depth' / relative)
        print(json.dumps(dict(status='PASS', operation='restore')))
    else:
        print(json.dumps(archive_completed_depth(args.job, apply=args.apply), indent=2))


if __name__ == '__main__':
    main()
