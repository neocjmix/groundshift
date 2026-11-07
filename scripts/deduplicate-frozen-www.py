#!/usr/bin/env python3
"""Share identical immutable publication copies while retaining every path.

Only explicitly listed frozen WWW trees are eligible. Originals, native jobs,
live public/dist, active restores, archives and logs are outside this utility.
Hardlinks share future writes: the caller must freeze every listed tree first.
Default is an audit. --apply requires equal bytes, permissions, owner, flags and
extended attributes, and rechecks files before atomic replacement. Never use it
on a tree that a packager, archive extractor or browser fixture may mutate.
"""
import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import uuid


CHUNK = 4 * 1024 * 1024
MAX_XATTR = 1024 * 1024


def _stamp(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
            stat.S_IMODE(value.st_mode), value.st_uid, value.st_gid, getattr(value, 'st_flags', 0))


def _attrs(path):
    if hasattr(os, 'listxattr'):
        return tuple((name, os.getxattr(path, name, follow_symlinks=False))
                     for name in sorted(os.listxattr(path, follow_symlinks=False)))
    if sys.platform != 'darwin':
        raise RuntimeError('Cannot verify extended attributes on this platform')
    # macOS CPython does not expose os.*xattr. Use the SDK sys/xattr.h API;
    # never assume an unavailable metadata API means there are no attributes.
    libc = ctypes.CDLL(None, use_errno=True)
    libc.listxattr.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    libc.listxattr.restype = ctypes.c_ssize_t
    libc.getxattr.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                             ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int]
    libc.getxattr.restype = ctypes.c_ssize_t
    encoded = os.fsencode(path)
    nofollow = 1  # XATTR_NOFOLLOW: never inspect a redirected target.

    def read(call):
        size = call(None, 0)
        if size < 0:
            raise OSError(ctypes.get_errno(), 'Cannot inspect frozen extended attributes', path)
        if size > MAX_XATTR:
            raise ValueError('Extended attribute exceeds bounded inspection limit')
        if size == 0:
            return b''
        buffer = ctypes.create_string_buffer(size)
        actual = call(buffer, size)
        if actual != size:
            raise OSError(ctypes.get_errno(), 'Extended attributes changed during inspection', path)
        return buffer.raw

    names = read(lambda buffer, size: libc.listxattr(encoded, buffer, size, nofollow))
    attributes = tuple((os.fsdecode(name), read(lambda buffer, size: libc.getxattr(
        encoded, name, buffer, size, 0, nofollow))) for name in sorted(names.split(b'\0')) if name)
    # Darwin ACLs are not returned by listxattr. A permission-equivalent link
    # must preserve these too (sys/acl.h ACL_TYPE_EXTENDED).
    libc.acl_get_file.argtypes = [ctypes.c_char_p, ctypes.c_int]
    libc.acl_get_file.restype = ctypes.c_void_p
    libc.acl_to_text.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ssize_t)]
    libc.acl_to_text.restype = ctypes.c_void_p
    libc.acl_free.argtypes = [ctypes.c_void_p]
    libc.acl_free.restype = ctypes.c_int
    acl = libc.acl_get_file(encoded, 0x100)
    if not acl:
        if ctypes.get_errno() == errno.ENOENT and path.is_file() and not path.is_symlink():
            return attributes  # Ordinary file without an extended ACL.
        raise OSError(ctypes.get_errno(), 'Cannot inspect frozen ACL', path)
    text = None
    try:
        length = ctypes.c_ssize_t()
        text = libc.acl_to_text(acl, ctypes.byref(length))
        if not text or not 0 <= length.value <= MAX_XATTR:
            raise ValueError('Cannot inspect bounded frozen ACL')
        return attributes + (('\0darwin-acl', ctypes.string_at(text, length.value)),)
    finally:
        if text:
            libc.acl_free(text)
        libc.acl_free(acl)


def _digest(path):
    value = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b''):
            value.update(chunk)
    return value.hexdigest()


def _safe_root(repo, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or '.' in path.parts or not path.parts:
        raise ValueError('Require explicit repository-relative frozen WWW paths')
    parts = path.parts
    allowed = (len(parts) >= 4 and parts[0] == 'data' and parts[-1] == 'www'
        and ((parts[1] == 'deploy' and len(parts) == 4 and re.fullmatch(r'viewer-\d+', parts[2]))
             or (parts[1] in ('jobs', 'validation') and ('publications' in parts or 'restore-smoke' in parts))))
    if not allowed:
        raise ValueError(f'Only frozen publication WWW trees are eligible: {relative}')
    current = repo
    for part in parts:
        current = current / part
        if current.is_symlink() or not current.is_dir():
            raise ValueError(f'Frozen root must contain only ordinary directories: {relative}')
    return current


def _files(root):
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in dirs:
            if Path(folder, name).is_symlink():
                raise ValueError('Symlink directory inside frozen WWW tree')
        for name in sorted(files):
            path = Path(folder, name)
            if not stat.S_ISREG(path.lstat().st_mode):
                raise ValueError('Non-regular file inside frozen WWW tree')
            yield path


def _identical(first, second):
    with first.open('rb') as a, second.open('rb') as b:
        while True:
            left, right = a.read(CHUNK), b.read(CHUNK)
            if left != right:
                return False
            if not left:
                return True


def replace_verified(canonical, destination, expected_source, expected_destination, digest):
    """Bounded memory; return only after byte/metadata checked atomic linking."""
    if (canonical.is_symlink() or destination.is_symlink()
            or _stamp(canonical.stat()) != expected_source or _stamp(destination.stat()) != expected_destination):
        raise ValueError('Frozen file changed since audit')
    if expected_source[0] != expected_destination[0] or expected_source[4:] != expected_destination[4:]:
        raise ValueError('Device, mode, owner or flags differ')
    attributes = _attrs(canonical)
    if attributes != _attrs(destination) or not _identical(canonical, destination):
        raise ValueError('Frozen bytes or extended attributes differ')
    temporary = destination.with_name(destination.name + '.gs-hardlink-' + uuid.uuid4().hex)
    try:
        os.link(canonical, temporary, follow_symlinks=False)
        if (_digest(temporary) != digest or _attrs(temporary) != attributes
                or _stamp(canonical.stat()) != expected_source or _stamp(destination.stat()) != expected_destination):
            raise ValueError('Frozen file changed during link verification')
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def deduplicate(repo, plan, *, apply=False, progress=None):
    repo = Path(repo).resolve()
    if (plan.get('schemaVersion') != 1 or plan.get('kind') != 'frozen-www-hardlinks'
            or plan.get('immutableAcknowledged') is not True):
        raise ValueError('Require explicit frozen WWW plan and immutable acknowledgment')
    sources, destinations = plan.get('sources'), plan.get('destinations')
    if (not isinstance(sources, list) or not sources or not isinstance(destinations, list) or not destinations
            or any(not isinstance(path, str) for path in sources + destinations)
            or len(set(destinations)) != len(destinations)):
        raise ValueError('Require unique explicit source and destination lists')
    minimum = plan.get('minBytes', 1024 * 1024)
    if type(minimum) is not int or minimum < 1024 * 1024:
        raise ValueError('Only files at least one MiB may be deduplicated')
    excluded = [repo / value for value in plan.get('excluded', [])]
    roots = [_safe_root(repo, value) for value in sources + destinations]
    if any(root == item or root.is_relative_to(item) or item.is_relative_to(root) for root in roots for item in excluded):
        raise ValueError('A selected root overlaps an explicitly excluded active tree')
    free = lambda: os.statvfs(repo).f_bavail * os.statvfs(repo).f_frsize
    report = dict(schemaVersion=1, status='RUNNING', mode='apply' if apply else 'audit',
        policy='Only frozen WWW copies; preserve every path and unique byte; share SHA/byte/mode/owner/flag/xattr-identical files',
        freeBeforeBytes=free(), replacements=[], scannedFiles=0, hashedInodes=0, skippedSameInode=0)
    start = time.monotonic()
    canonical, hashes = {}, {}
    source_roots = set(roots[:len(sources)])
    try:
        for root in roots:
            for path in _files(root):
                old = path.stat()
                if old.st_size < minimum:
                    continue
                stamp, attrs = _stamp(old), _attrs(path)
                report['scannedFiles'] += 1
                if stamp not in hashes:
                    hashes[stamp] = _digest(path)
                    report['hashedInodes'] += 1
                digest = hashes[stamp]
                if _stamp(path.stat()) != stamp or _attrs(path) != attrs:
                    raise ValueError('Frozen file changed during audit')
                key = (old.st_dev, old.st_size, digest, *stamp[4:], attrs)
                prior = canonical.get(key)
                if prior is None:
                    canonical[key] = path
                    continue
                if root in source_roots:
                    continue  # Anchor roots are read-only, even if internally duplicated.
                source_stamp = _stamp(prior.stat())
                if source_stamp[:2] == stamp[:2]:
                    report['skippedSameInode'] += 1
                    continue
                if apply:
                    replace_verified(prior, path, source_stamp, stamp, digest)
                report['replacements'].append(dict(path=str(path.relative_to(repo)), canonical=str(prior.relative_to(repo)),
                    bytes=old.st_size, sha256=digest, oldLinks=old.st_nlink, oldMtimeNs=old.st_mtime_ns))
            report.update(logicalBytesMatched=sum(row['bytes'] for row in report['replacements']),
                          freeAfterBytes=free(), elapsedSeconds=time.monotonic() - start)
            if progress:
                progress(report)
        report['status'] = 'PASS'
    except BaseException as error:
        report.update(status='FAIL', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report.update(logicalBytesMatched=sum(row['bytes'] for row in report['replacements']),
                      freeAfterBytes=free(), elapsedSeconds=time.monotonic() - start)
        if progress:
            progress(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('report', type=Path)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.report.exists() or args.report.is_symlink():
        parser.error('Report exists; preserve previous audit evidence')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    def save(value):
        temporary = args.report.with_suffix(args.report.suffix + '.tmp')
        temporary.write_text(json.dumps(value, indent=2) + '\n')
        temporary.replace(args.report)
    result = deduplicate(args.repo, json.loads(args.plan.read_text()), apply=args.apply, progress=save)
    print(json.dumps({key: value for key, value in result.items() if key != 'replacements'}))


if __name__ == '__main__':
    main()
