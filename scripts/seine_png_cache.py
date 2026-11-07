#!/usr/bin/env python3
"""Prove and restore exact generated PNG caches in completed new Seine jobs.

The ERP JPEGs, depth visualizations/archives, poses, databases, logs and native
exports are never eviction candidates. Every candidate has an exact-byte proof
from a retained original ERP and a saved projection recipe before eviction.
Eviction is explicit; the caller must name the retained reference frontier.
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import resource
import stat
import time
import uuid

import cv2
import numpy as np
import PIL
from PIL import Image, features


ROOT = Path(__file__).resolve().parents[1]
ALLOWED = re.compile(r'(?:tangent-inputs|dataset)/(?:images|masks)/p\d+-t\d+\.png|'
                     r'(?:sfm-inputs|sfm/dataset)/images/pano_\d+_view_\d+\.png|'
                     r'sfm/rig-images/view_\d+/pano_\d+\.png|'
                     r'depth/(?:computed/)?view-\d+-source\.png')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def safe(path, root, *, absent=False):
    path, root = Path(path).absolute(), Path(root).resolve()
    if '..' in path.parts or not path.is_relative_to(root):
        raise ValueError('Path escapes retained job/source scope')
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink() or not absent and not current.exists():
            raise ValueError('Require ordinary retained paths without symlinks')
    return path


def completed(job, repo, *, new_only):
    job = safe(job, repo)
    parts = job.relative_to(Path(repo).resolve()).parts
    if new_only and (len(parts) != 4 or parts[:2] != ('data', 'jobs')
                    or not re.fullmatch(r'seine-full-\d{8}', parts[2])
                    or not re.fullmatch(r'segment-\d+-\d+', parts[3])):
        raise ValueError('Only new Seine segment caches may be changed')
    for relative in ['training/job.json', 'tangent-inputs/report.json', 'depth/report.json', 'sfm/report.json']:
        if read(safe(job / relative, job)).get('status') != 'PASS':
            raise ValueError('Require complete PASS reconstruction stages; never evict an active job')
    return job


def versions():
    return dict(numpy=np.__version__, opencv=cv2.__version__, pillow=PIL.__version__,
                opencvBuildSha256=sha(cv2.getBuildInformation().encode()),
                pngZlib=features.version('zlib'), jpeg=features.version('jpg'), machine=platform.machine())


def module(path):
    spec = importlib.util.spec_from_file_location('retained_png_projection', path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def atomic(path, raw, mode=0o644):
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if temporary.exists():temporary.unlink()


def save(path, value):
    atomic(path, (json.dumps(value, indent=2, allow_nan=False) + '\n').encode())


def inventory(job, acquisition, repo=ROOT):
    """Only declared pipeline paths; unexpected generated PNGs fail closed."""
    job = completed(job, repo, new_only=False)
    acquisition = safe(acquisition, repo)
    source_report = read(acquisition / 'acquisition.json')
    if source_report.get('status') != 'PASS':raise ValueError('Original acquisition is incomplete')
    sources = {}
    for frame in source_report['frames']:
        original = safe(acquisition / frame['file'], acquisition)
        if file_sha(original) != frame['sha256']:raise ValueError('Original ERP checksum changed')
        sources[Path(frame['file']).name] = dict(path=str(original), sha256=frame['sha256'], dimensions=frame['dimensions'], rank=frame['rank'])
    prep = module(Path(__file__).with_name('prepare-panoramas.py'))
    spec = importlib.util.spec_from_file_location('png_tangent_recipe', Path(__file__).with_name('tangent_geometry.py'))
    tangent = importlib.util.module_from_spec(spec);spec.loader.exec_module(tangent)
    directions = [tangent.view_angles(normal) for normal in tangent.icosahedron_normals()]
    report = read(job / 'tangent-inputs/report.json')
    if (report['size'], report['fovDegrees'], report['viewsPerPhysical']) != (768, 80, 20):
        raise ValueError('Only the declared 20-direction 768px route recipe is supported')
    recipes, aliases = {}, {}
    def add(recipe_id, recipe, path, checksum=None):
        relative = path.relative_to(job).as_posix()
        if not ALLOWED.fullmatch(relative):raise ValueError('File is outside the generated PNG allowlist')
        safe(path, job)
        raw_sha = file_sha(path)
        if checksum and raw_sha != checksum:raise ValueError('Existing PNG differs from its original stage SHA')
        st = path.stat()
        aliases[relative] = dict(recipe=recipe_id, sha256=raw_sha, bytes=st.st_size, mode=stat.S_IMODE(st.st_mode), mtimeNs=st.st_mtime_ns)
        recipes.setdefault(recipe_id, recipe)
    tangent_by_file = {}
    for frame in read(job / 'tangent-inputs/frames.json'):
        source_row = report['sources'][frame['physical']]
        source = sources[source_row['file']]
        if source['sha256'] != source_row['sha256'] or source['rank'] != frame['rank']:
            raise ValueError('Tangent source lineage differs from retained ERP')
        yaw, pitch = directions[frame['view']]
        if not np.allclose(prep.crop_rotation(yaw, pitch), frame['rotation'], atol=1e-14, rtol=0):
            raise ValueError('Recorded tangent orientation differs from declared recipe')
        name = Path(frame['file_path']).name
        for kind in ['rgb', 'mask']:
            key = f'tangent-{kind}-{frame["physical"]}-{frame["view"]}'
            recipe = dict(kind='tangent-' + kind, source=source_row['file'], size=768, fov=80, yaw=yaw, pitch=pitch, maskBoundary=.78)
            folder = 'images' if kind == 'rgb' else 'masks'
            add(key, recipe, job / 'tangent-inputs' / folder / name)
            add(key, recipe, job / 'dataset' / folder / name)
            if kind == 'rgb':tangent_by_file[name] = (key, recipe)
    crops = read(job / 'sfm-inputs/crops.json')
    intrinsic = crops['intrinsics']
    if (intrinsic['width'], intrinsic['height'], intrinsic['horizontalFovDegrees']) != (512, 512, 100):
        raise ValueError('Only the declared six-direction 512px SfM recipe is supported')
    by_crop = {}
    for crop in crops['crops']:
        key = 'sfm-' + crop['file']
        recipe = dict(kind='sfm-bgr', source=crop['sourceId'], size=512, fov=100, yaw=crop['yawDegrees'], pitch=crop['pitchDegrees'])
        if recipe['source'] not in sources:raise ValueError('Missing original SfM ERP')
        add(key, recipe, job / 'sfm-inputs' / crop['file'], crop['sha256'])
        add(key, recipe, job / 'sfm/dataset' / crop['file'], crop['sha256'])
        by_crop[crop['file']] = (key, recipe)
    for name, crop in read(job / 'sfm/rig-image-mapping.json').items():
        key, recipe = by_crop[crop['file']]
        add(key, recipe, job / 'sfm/rig-images' / name, crop['sha256'])
    for folder in [job / 'depth', *([job / 'depth/computed'] if (job / 'depth/computed').exists() else [])]:
        rows = read(folder / 'report.json')
        if rows['status'] != 'PASS':raise ValueError('Incomplete computed depth outputs')
        for index, row in enumerate(rows['images']):
            source = Path(row['source'])
            if source.resolve() != (job / 'tangent-inputs/images' / source.name).resolve():
                raise ValueError('Depth preview source is not this job tangent crop')
            if file_sha(source) != row['sourceSha256']:raise ValueError('Depth source crop changed')
            key, recipe = tangent_by_file[source.name]
            add(key, recipe, folder / f'view-{index:02d}-source.png', row.get('sourcePreviewSha256'))
    actual = {p.relative_to(job).as_posix() for p in job.rglob('*.png') if ALLOWED.fullmatch(p.relative_to(job).as_posix())}
    if actual != set(aliases):raise ValueError('Unaccounted generated PNG paths; refusing incomplete recipe')
    return dict(job=str(job), acquisition=str(acquisition), sources=sources, recipes=recipes, files=aliases)


def rendered(manifest, prep):
    """At most one decoded ERP and one crop at a time; no GPU/model inference."""
    groups = {}
    for key, recipe in manifest['recipes'].items():
        engine = 'opencv' if recipe['kind'] == 'sfm-bgr' else 'pillow'
        groups.setdefault((recipe['source'], engine), []).append((key, recipe))
    for (source_key, engine), rows in groups.items():
        source = manifest['sources'][source_key]
        original = Path(source['path']).read_bytes()
        if sha(original) != source['sha256']:raise ValueError('Retained ERP SHA differs')
        if engine == 'opencv':pixels = cv2.imdecode(np.frombuffer(original, np.uint8), cv2.IMREAD_UNCHANGED)
        else:
            with Image.open(io.BytesIO(original)) as image:pixels = np.array(image.convert('RGB'))
        if pixels is None or list(pixels.shape[1::-1]) != source['dimensions']:raise ValueError('Retained ERP dimensions differ')
        for key, recipe in rows:
            if recipe['kind'] == 'tangent-mask':
                _, y = prep.sampling_map(pixels.shape[1], pixels.shape[0], recipe['size'], recipe['fov'], recipe['yaw'], recipe['pitch'])
                value = (((y + .5) / pixels.shape[0] < recipe['maskBoundary']).astype(np.uint8) * 255)
            else:value = prep.crop_panorama(pixels, recipe['size'], recipe['fov'], recipe['yaw'], recipe['pitch'])
            if engine == 'opencv':
                ok, encoded = cv2.imencode('.png', value, [cv2.IMWRITE_PNG_COMPRESSION, 3])
                if not ok:raise ValueError('OpenCV PNG encoding failed')
                raw = encoded.tobytes()
            else:
                buffer = io.BytesIO();Image.fromarray(value).save(buffer, format='PNG');raw = buffer.getvalue()
            yield key, raw
        del pixels


def prove_png_cache(job, acquisition, output, *, repo=ROOT):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():raise ValueError('Preserve previous proof; output already exists')
    manifest = inventory(job, acquisition, repo)
    if output.is_relative_to(Path(job)):
        completed(job, repo, new_only=True)
    output.mkdir(parents=True)
    projection = Path(__file__).with_name('prepare-panoramas.py').read_bytes()
    atomic(output / 'prepare-panoramas.py', projection)
    atomic(output / 'restore-script.py', Path(__file__).read_bytes())
    manifest.update(schemaVersion=1, kind='seine-generated-png-cache-v1', status='RUNNING', state='PRESENT', versions=versions(), projectionSha256=sha(projection), rendererSha256=sha(Path(__file__).read_bytes()))
    path = output / 'manifest.json';save(path, manifest);started = time.monotonic()
    by_recipe = {}
    for relative, row in manifest['files'].items():by_recipe.setdefault(row['recipe'], []).append((relative, row))
    try:
        count = 0
        for key, raw in rendered(manifest, module(output / 'prepare-panoramas.py')):
            for relative, row in by_recipe[key]:
                if sha(raw) != row['sha256'] or len(raw) != row['bytes']:
                    raise ValueError(f'Exact PNG regeneration failed: {relative}')
                count += 1
        manifest.update(status='PASS', verifiedAliases=count, verifiedRecipes=len(by_recipe), seconds=time.monotonic() - started, peakProcessRssBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except BaseException as error:
        manifest.update(status='FAIL', error=f'{type(error).__name__}: {error}')
        raise
    finally:save(path, manifest)
    return manifest


def checked_manifest(path, repo=ROOT):
    path = safe(path, repo);manifest = read(path)
    if (manifest.get('schemaVersion') != 1 or manifest.get('kind') != 'seine-generated-png-cache-v1'
            or manifest.get('status') != 'PASS' or manifest.get('versions') != versions()
            or manifest.get('verifiedAliases') != len(manifest.get('files', {}))
            or manifest.get('verifiedRecipes') != len(manifest.get('recipes', {}))):
        raise ValueError('Require complete exact proof with matching library versions')
    for name, field in [('prepare-panoramas.py', 'projectionSha256'), ('restore-script.py', 'rendererSha256')]:
        if file_sha(safe(path.parent / name, path.parent)) != manifest[field]:raise ValueError('Retained recipe code changed')
    job = completed(Path(manifest['job']), repo, new_only=True)
    for relative, row in manifest['files'].items():
        if not ALLOWED.fullmatch(relative) or row['recipe'] not in manifest['recipes']:raise ValueError('Unexpected PNG candidate')
        safe(job / relative, job, absent=True)
    for source in manifest['sources'].values():
        if file_sha(safe(source['path'], repo)) != source['sha256']:raise ValueError('Retained ERP changed')
    return manifest, job


def evict_verified_pngs(path, *, keep_jobs, repo=ROOT, apply=False):
    manifest, job = checked_manifest(path, repo)
    if not keep_jobs:raise ValueError('Explicit retained reference frontier is required')
    keep = [completed(Path(p), repo, new_only=False) for p in keep_jobs]
    if job in keep:raise ValueError('The retained reference frontier must keep its PNGs')
    existing = {p.relative_to(job).as_posix() for p in job.rglob('*.png') if ALLOWED.fullmatch(p.relative_to(job).as_posix())}
    if existing - set(manifest['files']):raise ValueError('New unproved PNGs appeared')
    if manifest['state'] == 'PRESENT' and existing != set(manifest['files']):raise ValueError('PNG disappeared before eviction began')
    stamps, inodes = {}, {}
    for relative in existing:
        target = job / relative;row = manifest['files'][relative];st = target.stat()
        if st.st_size != row['bytes'] or file_sha(target) != row['sha256']:raise ValueError('PNG changed since regeneration proof')
        stamps[relative] = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
        inodes.setdefault((st.st_dev, st.st_ino), dict(bytes=st.st_size, links=st.st_nlink, aliases=0))['aliases'] += 1
    report = dict(status='PASS', mode='apply' if apply else 'audit', removedAliases=0,
        candidateAliases=len(existing), rawUniqueBytes=sum(v['bytes'] for v in inodes.values()),
        uniqueBytesWithNoExternalLinks=sum(v['bytes'] for v in inodes.values() if v['links'] == v['aliases']))
    if apply:
        manifest['state'] = 'EVICTING';save(Path(path), manifest)
        for relative, stamp in stamps.items():
            target = job / relative;st = target.stat()
            if (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns) != stamp:raise ValueError('PNG changed during eviction')
            target.unlink();report['removedAliases'] += 1
        manifest['state'] = 'EVICTED';save(Path(path), manifest)
    return report


def restore_png_cache(path, *, repo=ROOT):
    manifest, job = checked_manifest(path, repo)
    by_recipe = {}
    for relative, row in manifest['files'].items():by_recipe.setdefault(row['recipe'], []).append((relative, row))
    written = 0
    for key, raw in rendered(manifest, module(Path(path).parent / 'prepare-panoramas.py')):
        canonical = None
        for relative, row in by_recipe[key]:
            if sha(raw) != row['sha256'] or len(raw) != row['bytes']:raise ValueError('Restored PNG differs from proof')
            target = job / relative
            if target.exists():
                if file_sha(target) != row['sha256']:raise ValueError('Refuse to overwrite changed PNG')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                if canonical is None:atomic(target, raw, row['mode'])
                else:os.link(canonical, target)
                written += 1
            canonical = target
    manifest['state'] = 'PRESENT';save(Path(path), manifest)
    return dict(status='PASS', restoredAliases=written)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    sub = parser.add_subparsers(dest='action', required=True)
    proof = sub.add_parser('prove');proof.add_argument('job', type=Path);proof.add_argument('acquisition', type=Path);proof.add_argument('output', type=Path)
    restore = sub.add_parser('restore');restore.add_argument('manifest', type=Path)
    evict = sub.add_parser('evict');evict.add_argument('manifest', type=Path);evict.add_argument('--keep-job', type=Path, action='append', required=True);evict.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.action == 'prove':
        result = prove_png_cache(args.job, args.acquisition, args.output, repo=args.repo)
        print(json.dumps({k:result[k] for k in ['status', 'verifiedAliases', 'verifiedRecipes', 'seconds', 'peakProcessRssBytes']}))
    else:
        result = restore_png_cache(args.manifest, repo=args.repo) if args.action == 'restore' else evict_verified_pngs(args.manifest, keep_jobs=args.keep_job, repo=args.repo, apply=args.apply)
        print(json.dumps(result))


if __name__ == '__main__':main()
