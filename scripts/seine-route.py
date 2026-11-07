#!/usr/bin/env python3
"""Resume bounded, overlapping local Seine reconstruction jobs and export a route.

No GPS-derived camera poses. Every new window must register completely and
pass image-derived shared-pose alignment before training. Native outputs and
failed stages are retained; new export snapshots never overwrite old ones.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
from seine_alignment import compose_alignment, transform_pose

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT/'data/jobs/paris-streaming-20261107'
ORIGINALS = ROOT/'data/jobs/tourist-streaming-20261107/hd-initial'
SOURCE_ROUTE = ROOT/'data/jobs/tourist-streaming-20261107/route.json'
PY = ROOT/'data/tools/venv/bin/python'
COLMAP = ROOT/'data/tools/colmap-venv/bin/python'
DEPTH = ROOT/'data/tools/diffusion-venv/bin/python'
LOD = ROOT/'data/tools/spark-2.4.0/rust/target/release/build-lod'
IDENTITY = dict(scale=1.0, rotation=np.eye(3).tolist(), translation=[0, 0, 0])


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''):h.update(block)
    return h.hexdigest()


def windows(total=876, baseline=180, size=24, stride=16):
    if not 6 <= size-stride < size or not 0 <= baseline <= total-size:
        raise ValueError('Require >=6 shared physical cameras and an existing baseline window')
    right = list(range(baseline+stride, total-size+1, stride))
    if not right or right[-1] != total-size:right.append(total-size)
    left = list(range(baseline-stride, -1, -stride))
    if not left or left[-1] != 0:left.append(0)
    result = []
    for index in [baseline, *right, *left]:
        if index not in result:result.append(index)
    return result


def link_or_copy(source, target):
    try:os.link(source, target)
    except OSError:shutil.copy2(source, target)
    return target


def quaternion_matrix(value):
    q=np.asarray(value,dtype=float)
    if q.shape!=(4,) or not np.isfinite(q).all() or not np.isclose(np.linalg.norm(q),1,atol=1e-7):raise ValueError('Require a unit XYZW quaternion')
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def matrix_quaternion(matrix):
    m=np.asarray(matrix,dtype=float)
    if m.shape!=(3,3) or not np.allclose(m.T@m,np.eye(3),atol=1e-7) or not np.isclose(np.linalg.det(m),1,atol=1e-7):raise ValueError('Require a proper rotation')
    a,b,c=m[0];d,e,f=m[1];g,h,i=m[2]
    k=np.array([[a-e-i,b+d,c+g,h-f],[b+d,e-a-i,f+h,c-g],[c+g,f+h,i-a-e,d-b],[h-f,c-g,d-b,a+e+i]])/3
    _,vectors=np.linalg.eigh(k);q=vectors[:,-1]
    return (-q if q[3]<0 else q).tolist()


def similarity(asset):
    return dict(scale=asset['scale'], rotation=quaternion_matrix(asset['quaternion']).tolist(), translation=asset['position'])


def inverse(transform):
    scale=transform['scale']; rotation=np.array(transform['rotation']); translation=np.array(transform['translation'])
    return dict(scale=1/scale, rotation=rotation.T.tolist(), translation=(-rotation.T@translation/scale).tolist())


def segment_to_route(local_asset, baseline_asset, raw_to_baseline):
    """Segment VIEWER -> route VIEWER, not a second asset transform."""
    return compose_alignment(similarity(baseline_asset), compose_alignment(raw_to_baseline, inverse(similarity(local_asset))))


def paged_world(job, output):
    source=job/'spz-world'; native=read(job/'training/job.json'); world=read(source/'world.json')
    if native['status']!='PASS' or read(source/'compression.json')['status']!='PASS':
        raise ValueError('Require actual native export and verified SPZ conversion')
    output.mkdir(exist_ok=False)
    rad=output/'rad';rad.mkdir();files=[]
    for path in sorted((job/'rad-build').glob('*.rad*')):
        if path.suffix not in ('.rad','.radc'):continue
        link_or_copy(path,rad/path.name)
        files.append(dict(path=path.name,bytes=path.stat().st_size,sha256=sha(path)))
    roots=[x['path'] for x in files if x['path'].endswith('.rad')]
    if len(roots)!=1 or not any(x['path'].endswith('.radc') for x in files):raise ValueError('Incomplete native RAD hierarchy')
    write(rad/'index.json',dict(schemaVersion=1,kind='spark-rad',sourceSplats=native['artifact']['splats'],root=roots[0],files=files))
    world.update(id=world['id'].replace('-spz','-lod'),paging=dict(path='rad/index.json',maxPagedSplats=917504,lodSplatCount=800000))
    world['provenance']['notes']+=' Same native reconstruction; pinned Spark2.4.0 quality SH1 csplat chunked RAD. No background. Global route alignment is separate metadata.'
    write(output/'world.json',world)
    for name in ('scene.spz','cameras.json','SOURCE_LICENSE'):link_or_copy(source/name,output/name)


def export_route(root, records, output):
    """Export only completed, aligned real segments; never fill unbuilt gaps."""
    route=read(SOURCE_ROUTE);items=route['images']; baseline=read(BASELINE/'lod-compact-world/world.json')
    baseline_asset=baseline['coordinates']['assetToWorld']; output.mkdir(parents=True,exist_ok=False)
    directory=output/'route/segments';directory.mkdir(parents=True)
    candidates={}; segments=[]; transformations={}
    ordered=sorted(records,key=lambda r:r['first'])
    for record in ordered:
        job=Path(record['job']); native=Path(record['world']); world=read(native/'world.json'); identifier=f"segment-{record['firstRank']}-{record['lastRank']}"
        if record['status']!='PASS':raise ValueError('Unexecuted segment cannot be exported')
        transform=segment_to_route(world['coordinates']['assetToWorld'],baseline_asset,record['rawToBaseline'])
        transformations[identifier]=transform
        # Every snapshot keeps immutable bytes. A future publisher must replace
        # changed paths atomically rather than writing through these hardlinks.
        shutil.copytree(native,directory/identifier,copy_function=link_or_copy)
        frames=read(native/'cameras.json')['frames']
        for frame in frames:
            rank=int(frame['image'].removeprefix('panorama-rank-'))
            pose=transform_pose(frame['cameraToWorld'],transform)
            middle=(record['firstRank']+record['lastRank'])/2
            candidates.setdefault(rank,[]).append((abs(rank-middle),identifier,pose))
        segments.append(dict(id=identifier,world=f'segments/{identifier}/world.json',transform=dict(position=transform['translation'],quaternion=matrix_quaternion(transform['rotation']),scale=transform['scale']),anchors=[]))
    by_id={s['id']:s for s in segments};global_frames=[];ranks=sorted(candidates)
    if ranks != list(range(ranks[0],ranks[-1]+1)):raise ValueError('Cannot claim continuity over unbuilt source ranks')
    for rank in ranks:
        _,owner,pose=min(candidates[rank],key=lambda item:(item[0],item[1]))
        by_id[owner]['anchors'].append(pose[:3,3].tolist())
        global_frames.append(dict(image=f'panorama-rank-{rank}',cameraToWorld=pose.tolist(),componentId='seine-shared-overlap',continuousFromPrevious=bool(global_frames)))
    if any(not s['anchors'] for s in segments):raise ValueError('Every segment needs an owned recorded center')
    write(output/'route/index.json',dict(schemaVersion=1,coordinateSpace='viewer-world',segments=segments))
    write(output/'cameras.json',dict(schemaVersion=1,cameraConvention='OpenGL: +X right, +Y up, -Z forward',worldConvention='right-handed Y-up, arbitrary units',frames=global_frames,sequenceNotes='Consecutive original source ranks. Independently estimated local poses aligned through shared camera orientations and centers. Chain drift remains unmeasured; interpolation is not a surveyed road or collision surface.'))
    source_by_rank={x['rank']:x for x in items};covered=source_by_rank[ranks[-1]]['distanceMeters']-source_by_rank[ranks[0]]['distanceMeters']
    world=baseline.copy();world=json.loads(json.dumps(world));world.pop('paging',None);world.pop('streaming',None)
    world.update(id='seine-full-route',title=f'Seine · {covered:.0f}m of 2.185km',route=dict(path='route/index.json',maxPagedSplats=917504,lodSplatCount=800000))
    first=np.array(global_frames[0]['cameraToWorld']);world['navigation']['camera'].update(position=first[:3,3].tolist(),target=(first[:3,3]-first[:3,2]*5).tolist(),up=first[:3,1].tolist())
    world['navigation']['camerasPath']='cameras.json';world['navigation']['mode']='camera-path'
    world['provenance']['notes']=f'{len(ranks)} actual registered physical source panoramas, ranks {ranks[0]}-{ranks[-1]}, {len(segments)} trained local segments. Source GPS polyline coverage about {covered:.2f}m; not metric reconstruction truth. Shared real-image camera poses establish relative Sim3 alignment, not GPS. One active local GS plus a bounded transition neighbor; whole-route distant skyline and independent geometry are not established. No diffusion or photo background. Native artifacts and alignment residuals retained locally.'
    write(output/'world.json',world)
    for name in ('scene.spz','SOURCE_LICENSE'):link_or_copy(BASELINE/'lod-compact-world'/name,output/name)
    report=dict(status='PASS',worldId=world['id'],segments=len(segments),sourceCount=len(ranks),firstRank=ranks[0],lastRank=ranks[-1],sourceGpsCoverageMeters=covered,targetSourceCount=876,targetGpsMeters=route['statistics']['lengthMeters'],remainingSourceCount=876-len(ranks),browserRendering='NOT RUN',globalGeometry='NOT ACCEPTED',exportedAt=datetime.now(timezone.utc).isoformat())
    write(output/'coverage.json',report)
    return report


def run_stage(job, name, command, cwd=ROOT, env=None):
    status=job/'runner.json';record=read(status) if status.exists() else dict(status='RUNNING',stages=[])
    earlier=next((s for s in record['stages'] if s['name']==name),None)
    if earlier:
        if earlier['status']=='PASS':return
        raise RuntimeError(f'{name} has incomplete/failed evidence; preserve it and create a new attempt explicitly')
    stage=dict(name=name,status='RUNNING',command=list(map(str,command)),startedAt=datetime.now(timezone.utc).isoformat());record['stages'].append(stage);write(status,record)
    start=time.monotonic()
    try:
        with (job/(name+'.log')).open('x') as log:
            result=subprocess.run(list(map(str,command)),cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
        stage.update(exitCode=result.returncode,status='PASS' if result.returncode==0 else 'FAIL')
        if result.returncode:raise RuntimeError(f'{name} exited {result.returncode}; see retained log')
    except BaseException as error:
        stage.update(status='FAIL',error=str(error))
        raise
    finally:
        stage['seconds']=time.monotonic()-start;record['status']='FAIL' if stage['status']=='FAIL' else 'RUNNING';write(status,record)


def snapshot(root, state):
    """Recover an export interruption without rerunning a native reconstruction.

    Incomplete directories remain diagnostic evidence. Only an atomic rename
    exposes a complete export; publication can watch route-run.json safely.
    """
    count=len(state['records']);output=root/f'route-world-{count:03d}'
    if output.exists():
        report=read(output/'coverage.json')
        expected=set()
        for record in state['records']:expected.update(range(record['firstRank'],record['lastRank']+1))
        if (report['segments']!=count or report['sourceCount']!=len(expected)
                or report['firstRank']!=min(expected) or report['lastRank']!=max(expected)):
            raise ValueError('Existing snapshot does not match completed source coverage')
    else:
        temporary=root/(output.name+'.partial-'+str(time.time_ns()))
        report=export_route(root,state['records'],temporary)
        temporary.rename(output)
    if not any(item['path']==str(output) for item in state['exports']):
        state['exports'].append(dict(path=str(output),**report))
    write(root/'route-run.json',state)
    print('EXPORTED',output,report['sourceCount'],report['sourceGpsCoverageMeters'],flush=True)
    return report


def baseline_record():
    return dict(first=180,firstRank=988,lastRank=1011,job=str(BASELINE),world=str(BASELINE/'lod-compact-world'),rawToBaseline=IDENTITY,status='PASS',reusedExistingBaseline=True)


def execute(root, limit=None):
    root.mkdir(parents=True,exist_ok=True);source=read(SOURCE_ROUTE);frames=source['images'];path=root/'route-run.json'
    state=read(path) if path.exists() else dict(schemaVersion=1,status='RUNNING',configuration=dict(window=24,stride=16,cropSize=768,directions=20,steps=8000,maxSplats=800000,model='Depth Anything V2 Small',training='Brush0.3.0 Metal'),sourceManifestSha256=sha(SOURCE_ROUTE),records=[baseline_record()],exports=[])
    if state['sourceManifestSha256']!=sha(SOURCE_ROUTE):raise ValueError('Source manifest changed')
    state['status']='RUNNING';write(path,state);completed=0
    if len(state['records'])>1 and not any(item['segments']==len(state['records']) for item in state['exports']):snapshot(root,state)
    for first in windows():
        if any(r['first']==first and r['status']=='PASS' for r in state['records']):continue
        if limit is not None and completed>=limit:break
        if shutil.disk_usage(root).free < 6*1024**3:
            state.update(status='BLOCKED',blocker='Less than6GiB free; preserve all native evidence and acquire no new images');write(path,state);return state
        ranks=[frames[first]['rank'],frames[first+23]['rank']];job=root/f'segment-{ranks[0]}-{ranks[1]}';acquired=root/f'acquisition-{ranks[0]}-{ranks[1]}'
        job.mkdir(exist_ok=True)
        provenance=read(ROOT/'scripts/samples/paris-seine-provenance.json');provenance['notes']=f'24 real unchanged 12288x6144 public ERP photos, source ranks{ranks[0]}-{ranks[1]}; no generated RGB. GPS/azimuth are source estimates, never full poses or metric geometry.';write(job/'provenance.json',provenance)
        reference=max(state['records'],key=lambda r:len(set(range(first,first+24))&set(range(r['first'],r['first']+24))))
        overlap=len(set(range(first,first+24))&set(range(reference['first'],reference['first']+24)))
        if overlap<6:raise ValueError('No already reconstructed shared-pose neighbor')
        try:
            if not acquired.exists():
                reuse=[ORIGINALS,*sorted(root.glob('acquisition-*'))]
                run_stage(job,'acquisition',[PY,'scripts/acquire-tourist-route.py',SOURCE_ROUTE,acquired,'--first',first,'--count',24,*[arg for p in reuse for arg in ('--reuse-acquisition',p)]])
            if read(acquired/'acquisition.json')['status']!='PASS':raise ValueError('Incomplete source acquisition')
            # Import the already-running first real pilot without rerunning it.
            imported=job/'pipeline.json'
            pilot_pass=imported.exists() and read(imported)['status']=='PASS'
            if not pilot_pass:
                if imported.exists():raise RuntimeError('First pilot is still running or failed; do not overwrite it')
                run_stage(job,'sfm-inputs',[PY,'scripts/prepare-panoramas.py',acquired/'images',job/'sfm-inputs','--provenance',job/'provenance.json','--size',512,'--hfov',100])
                run_stage(job,'sfm',[COLMAP,'scripts/estimate-panorama-poses.py',job/'sfm-inputs',job/'sfm','--threads',4,'--max-features',4096])
                run_stage(job,'anchors',[COLMAP,'scripts/paris-pipeline.py','anchors',job])
            if not (job/'alignment.json').exists():run_stage(job,'alignment',[PY,'scripts/seine_alignment.py',job,reference['job'],job/'alignment.json'])
            alignment=read(job/'alignment.json')
            if alignment['status']!='PASS':raise ValueError('Independent overlap check failed; refusing an invented connection')
            raw_transform=compose_alignment(reference['rawToBaseline'],alignment['transform'])
            if not pilot_pass:
                run_stage(job,'tangent-inputs',[PY,'scripts/paris-pipeline.py','prepare',job,'--source',acquired])
                reused=[BASELINE/'depth',*[Path(r['job'])/'depth' for r in state['records'] if r['first']!=180]]
                run_stage(job,'depth',[DEPTH,'scripts/infer-seine-depth.py',job/'depth',job/'tangent-inputs/inference-inputs.json',*[arg for p in reused for arg in ('--reuse',p)]],env={**os.environ,'HF_HOME':str(ROOT/'data/tools/depth-hf-cache')})
                run_stage(job,'fusion',[PY,'scripts/paris-pipeline.py','fusion',job])
                run_stage(job,'training',[PY,'scripts/reconstruct.py',job/'dataset',job/'training','--steps',8000,'--resolution',768,'--max-splats',800000,'--title',f'Seine · {ranks[0]}–{ranks[1]}','--id',f'seine-{ranks[0]}-{ranks[1]}'])
                run_stage(job,'finalize',[PY,'scripts/paris-pipeline.py','finalize',job,'--source',acquired])
                run_stage(job,'compress',['node','scripts/compress-world.mjs',job/'view-world',job/'spz-world'])
            rad=job/'rad-build';rad.mkdir(exist_ok=True)
            if not (rad/'scene.ply').exists():link_or_copy(job/'view-world/scene.ply',rad/'scene.ply')
            run_stage(job,'rad',[LOD,'--quality','--csplat','--max-sh=1','--rad-chunked','scene.ply'],cwd=rad)
            world=job/'lod-world'
            if not world.exists():paged_world(job,world)
            state['records'].append(dict(first=first,firstRank=ranks[0],lastRank=ranks[1],job=str(job),world=str(world),rawToBaseline=raw_transform,referenceFirst=reference['first'],alignmentSha256=sha(job/'alignment.json'),status='PASS'))
            runner=read(job/'runner.json');runner['status']='PASS';write(job/'runner.json',runner)
            write(path,state)
            snapshot(root,state);completed+=1
        except BaseException as error:
            state.update(status='FAIL',failedWindow=dict(first=first,ranks=ranks),error=str(error));write(path,state);raise
    state['status']='PASS' if len(state['records'])==len(windows()) else 'PARTIAL';write(path,state);return state


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path);parser.add_argument('--limit',type=int)
    args=parser.parse_args();args.root=args.root.resolve();args.root.mkdir(parents=True,exist_ok=True)
    with (args.root/'coordinator.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Another coordinator owns this run; no duplicate work started')
        result=execute(args.root,args.limit)
    print(json.dumps({k:result[k] for k in ('status','configuration')},indent=2))
    raise SystemExit(0 if result['status'] in ('PASS','PARTIAL') else 1)
