#!/usr/bin/env python3
"""Fetch a bounded set of pinned public HD source images, preserving download evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request


def acquire(manifest, output, first, count):
    route = json.loads(manifest.read_text())
    selected = route['images'][first:first+count]
    if first < 0 or count < 1 or count > 64 or len(selected) != count:
        raise ValueError('Require an existing contiguous window of1..64images')
    output.mkdir(parents=True, exist_ok=False)
    (output/'images').mkdir()
    report = dict(status='RUNNING', sourceManifestSha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                  sourceCollection=route['collection'], firstIndex=first, requested=count, frames=[],
                  note='Highest publicly available blurred HD JPEG, unchanged upstream bytes; GPS/azimuth are not full poses.')
    start = time.monotonic()
    try:
        from PIL import Image
        for item in selected:
            if item['license'] != 'etalab-2.0' or not item['hdUrl'].startswith('https://'):
                raise ValueError('Require explicitly licensed public HTTPS source')
            before = time.monotonic()
            request = urllib.request.Request(item['hdUrl'], headers={'User-Agent': 'GroundshiftPrototype/0.1 (github.com/neocjmix/groundshift; local research)'})
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read(32*1024*1024+1)
            if len(raw) > 32*1024*1024:
                raise ValueError('Bounded32MiB source limit exceeded')
            digest = hashlib.sha256(raw).hexdigest()
            if item.get('hdSha256') and item['hdSha256'] != digest:
                raise ValueError('Pinned image bytes changed')
            filename = f"{item['rank']:05d}_{item['id']}.jpg"
            target = output/'images'/filename
            target.with_suffix('.part').write_bytes(raw)
            with Image.open(target.with_suffix('.part')) as image:
                if image.format != 'JPEG' or list(image.size) != item['dimensions']:
                    raise ValueError('JPEG format/resolution differs from metadata')
                image.verify()
            target.with_suffix('.part').rename(target)
            report['frames'].append(dict(id=item['id'], rank=item['rank'], file='images/'+filename,
                                         bytes=len(raw), sha256=digest, dimensions=item['dimensions'],
                                         seconds=time.monotonic()-before, jpegHeaderVerified=True))
            (output/'acquisition.json').write_text(json.dumps(report, indent=2)+'\n')
            print(f"Verified {len(report['frames'])}/{count}: rank{item['rank']} {len(raw)}bytes", flush=True)
            time.sleep(.5)
        report['status'] = 'PASS'
    except Exception as error:
        report['status'] = 'FAIL'
        report['error'] = str(error)
    finally:
        report['elapsedSeconds'] = time.monotonic()-start
        report['totalBytes'] = sum(f['bytes'] for f in report['frames'])
        (output/'acquisition.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--first', type=int, default=180); p.add_argument('--count', type=int, default=24)
    a = p.parse_args(); r = acquire(a.manifest, a.output, a.first, a.count)
    print(json.dumps({k: r[k] for k in ['status', 'requested', 'totalBytes', 'elapsedSeconds']}))
    raise SystemExit(0 if r['status'] == 'PASS' else 1)
