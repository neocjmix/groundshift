#!/usr/bin/env python3
"""Package a real native Spark LoD conversion beside its unchanged SPZ control."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main(a):
    if not 65536 <= a.max_paged_splats <= 2097152 or a.max_paged_splats % 65536:
        raise ValueError('Page pool must be a multiple of65536 within65536..2097152')
    if not 0 < a.lod_splat_count <= a.max_paged_splats:
        raise ValueError('Selection budget must be positive and fit the page pool')
    source=a.job/'spz-world';native=json.loads((a.job/'training/job.json').read_text());world=json.loads((source/'world.json').read_text())
    if native['status']!='PASS' or world['id']!='paris-58m-spz':raise ValueError('Require actual completed Paris source')
    if a.id not in ['paris-58m-lod','paris-58m-lod-compact']:raise ValueError('Require explicitly selected delivery variant')
    a.output.mkdir(exist_ok=False)
    world.update(id=a.id,title='Paris · native LoD streaming',paging=dict(path='rad/index.json',maxPagedSplats=a.max_paged_splats,lodSplatCount=a.lod_splat_count))
    world['provenance']['notes']+=' Storage-only native Spark2.4.0 ffe210dc0a45d0515a06c9235878108112827d61 quality/Bhatt LoD,SH1,chunkedRAD. Encoding '+a.encoding+f'. Same original800k Brush Gaussians plus derived hierarchy parents; no retraining. Page pool{a.max_paged_splats}slots,selection budget{a.lod_splat_count}. Measured visual differences and transfer counts require separate actual browser tests.'
    (a.output/'world.json').write_text(json.dumps(world,indent=2)+'\n')
    for name in ['scene.spz','cameras.json','SOURCE_LICENSE']:shutil.copyfile(source/name,a.output/name)
    rad=a.output/'rad';rad.mkdir();files=[]
    for p in sorted(a.rad.glob('*.rad*')):
        if p.suffix not in ['.rad','.radc']:continue
        data=p.read_bytes();shutil.copyfile(p,rad/p.name);files.append(dict(path=p.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    if len([f for f in files if f['path'].endswith('.rad')])!=1 or not any(f['path'].endswith('.radc') for f in files):raise ValueError('Require one native root and actual chunks')
    (rad/'index.json').write_text(json.dumps(dict(schemaVersion=1,kind='spark-rad',sourceSplats=native['artifact']['splats'],root=next(f['path'] for f in files if f['path'].endswith('.rad')),files=files),indent=2)+'\n')
    print('PASS',a.encoding,len(files),'files',sum(f['bytes'] for f in files),'bytes')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('rad',type=Path);p.add_argument('output',type=Path);p.add_argument('--id',required=True);p.add_argument('--encoding',choices=['gsplat','csplat'],required=True)
    p.add_argument('--max-paged-splats',type=int,default=917504,help='Bounded resident pool;14pages preserves nearby Paris detail')
    p.add_argument('--lod-splat-count',type=int,default=800000,help='Selection ceiling; actual selected count depends on view/residency')
    main(p.parse_args())
