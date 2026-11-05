#!/usr/bin/env python3
"""Prepare explicitly selected object trial assets and a chronological lab index.

Run after the native export; --finish adds actual browser previews. No raw logs,
original panoramas, weights or absolute source paths are published.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'


def read(path): return json.loads(path.read_text())


def write(path,data): path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def ply(path):
    with path.open('rb') as f:
        header=[];props=[];count=0
        while True:
            line=f.readline().decode('ascii').strip();header.append(line)
            if line.startswith('element vertex '):count=int(line.split()[-1])
            if line.startswith('property '):
                _,kind,name=line.split();props.append((name,{'float':'<f4','uchar':'u1'}[kind]))
            if line=='end_header':break
        data=np.fromfile(f,dtype=np.dtype(props),count=count)
    return header,data


def time_of(folder):
    for name in ['job.json','report.json','pipeline.json','prepare.json']:
        p=folder/name
        if p.is_file():
            d=read(p)
            stamp=d.get('finishedAt') or d.get('startedAt') or d.get('createdAt')
            if stamp:return stamp
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('job',type=Path);parser.add_argument('--finish',action='store_true');parser.add_argument('--real-only',action='store_true');args=parser.parse_args()
    job=args.job.resolve(); export=job/'training/world'; fusion=read(job/'fusion/report.json'); training=read(job/'training/job.json'); gen=read(job/'diffuse.json') if not args.real_only else None
    prefix='scooter-real-' if args.real_only else 'scooter-'
    report_slug='object-real' if args.real_only else 'object-focus'
    total=9 if args.real_only else 65; generated=0 if args.real_only else 56
    out=PUBLIC/'experiments'/report_slug;(out/'images').mkdir(parents=True,exist_ok=True);(out/'depth').mkdir(exist_ok=True)
    if not args.finish:
        raw=read(export/'world.json');cameras=read(export/'cameras.json')
        spec=importlib.util.spec_from_file_location('reconstruct',ROOT/'scripts/reconstruct.py');recon=importlib.util.module_from_spec(spec);spec.loader.exec_module(recon)
        q=raw['coordinates']['assetToWorld']['quaternion']; focus=recon.rotate(fusion['focus'],q)
        home=next((f for f in cameras['frames'] if Path(f['image']).name=='frame_0032.png'),cameras['frames'][len(cameras['frames'])//2])
        middle=home['cameraToWorld'];raw['navigation']['camera'].update(position=[middle[i][3] for i in range(3)],target=focus,up=[middle[i][1] for i in range(3)],fov=40)
        raw['provenance']['notes']='Object experiment: 9 observed perspective crops of one white scooter from nine 7680x3840 Mapillary panoramas, plus 56 whole-frame diffusion images. Relative depth was fitted to adjacent feature reprojection, fused and used as Brush initialization. All camera poses were estimated from these images; no synthetic pose was assigned from frame time. Source crop intrinsics are analytical pinhole projections. Arbitrary scale; gravity and metric depth unmeasured. Asset coordinates retain Brush output; the explicit asset transform aligns mean camera up to +Y. Viewer focus is a display choice from the fused object points. Independent quality measurement NOT RUN.'
        if args.real_only:
            raw['provenance']['notes']='Real-only object ablation: the same nine observed 512x512 perspective crops, original-image camera solution and relative-depth model as the reference experiment. No RIFE interpolation, diffusion or other intermediate images. Depth calibration, filtering, visual-hull selection and 5000-step Brush settings are unchanged. Only real-image depth contributes to initialization. Camera poses are image-estimated, not surveyed; scale is arbitrary. Comparative quality measurement NOT RUN.'
        cameras['sequenceNotes']='Ordered observed and generated image sequence in a single estimated SfM component. Poses are fitted to the images, not measured synthetic camera motion. Playback interpolates these estimated positions and orientations.'
        raw['provenance']['license']='CC-BY-SA-4.0 source images; CreativeML OpenRAIL-M generative model'
        raw['provenance']['attribution']='Original photographs: Cicero101 / Mapillary via Wikimedia Commons. Perspective crops and reconstruction: Groundshift. Synthetic intermediate frames: Practical-RIFE 4.25 + Segmind Tiny-SD.'
        if args.real_only:
            raw['provenance']['license']='CC-BY-SA-4.0 source images'
            raw['provenance']['attribution']='Original photographs: Cicero101 / Mapillary via Wikimedia Commons. Perspective crops and real-only reconstruction: Groundshift. No intermediate image generation.'
            cameras['sequenceNotes']='Nine observed images in capture order, using the original-image SfM camera estimates. No intermediate image generation; viewer path playback interpolates cameras only.'
        header,data=ply(export/'scene.ply');xyz=np.column_stack([data[x] for x in ['x','y','z']]);keep=np.isfinite(xyz).all(1)
        for clip in fusion['clipping']:
            T=np.array(clip['worldToCamera']);K=np.array(clip['intrinsics']);b=clip['bounds'];p=(xyz@T[:,:3].T+T[:,3])@K.T;uv=p[:,:2]/np.maximum(p[:,2:],1e-8)
            keep&=(p[:,2]>0)&(uv[:,0]>=b[0])&(uv[:,0]<=b[2])&(uv[:,1]>=b[1])&(uv[:,1]<=b[3])
        selected=data[keep]
        if len(selected)<100:raise RuntimeError('Object selection produced fewer than 100 splats')
        cropped=job/'object/world';cropped.mkdir(parents=True,exist_ok=False)
        object_header=[f'element vertex {len(selected)}' if h.startswith('element vertex ') else h for h in header]
        with (cropped/'scene.ply').open('wb') as f:f.write(('\n'.join(object_header)+'\n').encode());selected.tofile(f)
        for slug,title,source,notes in [(prefix+'context','스쿠터 · 실제 9장 · 전체' if args.real_only else '스쿠터 · 전체 학습 장면',export,'Uncropped training export, including the black neighboring scooter and background.'),(prefix+'object','스쿠터 · 실제 9장만' if args.real_only else '스쿠터 · 한 물체 집중',cropped,'Selected Gaussian centers inside manually observed white-scooter bounds in three actual images. This is a display crop, not independent semantic segmentation.')]:
            manifest=json.loads(json.dumps(raw));manifest['id']=slug;manifest['title']=title;manifest['provenance']['notes']+=' '+notes
            write(source/'world.json',manifest);write(source/'cameras.json',cameras)
            (source/'SOURCE_LICENSE').write_text('Original photos: Cicero101 / Mapillary via Wikimedia Commons. CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/\nDerived perspective images and reconstruction. Segmind Tiny-SD model: CreativeML OpenRAIL-M, https://huggingface.co/segmind/tiny-sd/blob/cad0bd7495fa6c4bcca01b19a723dc91627fe84f/README.md\n')
            if args.real_only:
                (source/'SOURCE_LICENSE').write_text('Original photos: Cicero101 / Mapillary via Wikimedia Commons. CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/\nDerived perspective images and reconstruction. No generated intermediate images or diffusion.\n')
            dest=PUBLIC/'worlds'/slug;dest.mkdir(exist_ok=True)
            for name in ['world.json','cameras.json','scene.ply','SOURCE_LICENSE']:shutil.copyfile(source/name,dest/name)
        write(job/'object/report.json',dict(status='PASS',finishedAt=datetime.now(timezone.utc).isoformat(),operation='visual-hull-center-selection',inputSplats=len(data),outputSplats=len(selected)))
    frames=[]
    registered=read(job/'poses/report.json')
    registered_names=set(registered['registeredImages'])
    fused_names={item['file'] for item in fusion['calibration'] if item.get('usedForDepthFusion')}
    depth=read(job/'depth/report.json')
    for i,record in enumerate(depth['images']):
        name=Path(record['source']).name
        shutil.copyfile(job/'augmented/images'/name,out/'images'/name)
        depth_name=f'{Path(name).stem}.png';shutil.copyfile(job/'depth'/f'view-{i:02d}-visual.png',out/'depth'/depth_name)
        frames.append(dict(file='images/'+name,depth='depth/'+depth_name,kind='observed' if int(Path(name).stem.split('_')[-1])%8==0 else 'synthetic',registered=name in registered_names,depthFused=name in fused_names))
    shutil.copyfile(job/'originals-contact.jpg',out/'originals-contact.jpg');shutil.copyfile(job/'fusion/cloud.json',out/'cloud.json')
    if args.real_only:
        shutil.copyfile(ROOT/'data/jobs/object-focus-20261105/fusion/cloud.json',out/'real-cloud.json')
    elif (job/'fusion-real-focused/cloud.json').is_file():
        shutil.copyfile(job/'fusion-real-focused/cloud.json',out/'real-cloud.json')
    else:
        raise RuntimeError('Prepare the original-only depth cloud before publishing the comparison selector')
    cropped=read(job/'object/report.json')
    summary=dict(completedAt=training['finishedAt'],realImages=9,generatedImages=generated,registeredImages=len(registered['registeredImages']),points=fusion['points'],splats=cropped['outputSplats'],frames=frames,
        generation=f"RIFE 초기 이미지 → Tiny-SD 전체 프레임 img2img. 강도 0.2, 30단계 중 6단계 디노이징, 시드 41. 원본 9장은 그대로 보존. 생성 작업 {(gen or {'elapsedSeconds':0})['elapsedSeconds']:.1f}초. 영상 디퓨전이나 실측 중간 카메라가 아닙니다.",
        training=f"입력 후보 65장 중 카메라가 정합된 {len(registered_names)}장으로 Apple M2 Metal에서 {training['options']['steps']:,}단계 학습. 깊이 {len(fused_names)}장이 {fusion['points']:,}개 초기 점을 제공했습니다. 학습 {training['elapsedSeconds']:.1f}초. 전체 {training['artifact']['splats']:,}개 Gaussian 중 흰 스쿠터 영역 {cropped['outputSplats']:,}개를 표시합니다.",
        notes=[f"65장 중 {65-len(registered_names)}장은 카메라 정합 실패로 GS에서 제외했습니다. 정합된 이미지 중 {fusion['rejectedDepthImages']}장의 깊이는 보정 실패로 점군에서 제외했습니다. 이 제외는 독립적인 품질 검증이 아니라 실행 중 발생한 한계입니다.",'실행한 결과를 우선 공개했습니다. 독립적인 깊이·포즈 정확도와 기존 장면 대비 품질 개선 측정은 NOT RUN입니다.','장수는 작은 물체의 50–100장 촬영 가이드를 참고해 65장으로 정했지만, 생성 56장은 실제 56개 관측을 대신했다는 뜻이 아닙니다.','실제 경로는 물체 한쪽을 지나갑니다. 보이지 않은 반대편 전체까지 복원했다는 주장은 하지 않습니다.'])
    if args.real_only:
        summary['generation']='중간 이미지 보간·생성 모두 생략. 기존 실험과 같은 실제 파노라마 크롭 9장만 사용했습니다. RIFE와 디퓨전은 실행하지 않았습니다.'
        summary['training']=f"실제 사진 {len(registered_names)}장으로 Apple M2 Metal에서 {training['options']['steps']:,}단계 학습. 깊이 {len(fused_names)}장이 {fusion['points']:,}개 초기 점을 제공했습니다. 학습 {training['elapsedSeconds']:.1f}초. 전체 {training['artifact']['splats']:,}개 Gaussian 중 물체 영역 {cropped['outputSplats']:,}개를 표시합니다."
        summary['notes']=[f"원본 9장 중 {len(registered_names)}장 정합, {len(fused_names)}장 깊이 사용. 이전 실험의 동일한 원본 사진·원본 전용 카메라·깊이 예측을 재사용하고, 점군 융합과 GS 학습은 새로 실행했습니다.", '보간/디퓨전 중간 이미지 56장을 모두 제거했습니다. 해상도 512, 시야각 45도, 깊이 보정 방식, 물체 선택 영역, 학습 5000단계, 최대 150000 splat, 시드 42는 유지했습니다.', '이전 결과와 새 결과를 직접 볼 수 있습니다. 정량적인 품질 비교는 NOT RUN입니다. 물체 반대편 전체를 찍은 입력은 여전히 없습니다.']
    summary['variant']='real-only' if args.real_only else 'diffusion'
    if args.real_only:
        summary['notes'].append('처음에 RIFE 보간을 유지하려던 실행은 요청을 바로잡아 카메라 정합 중 취소했습니다. 그 실행은 GS 학습까지 진행하지 않았고 이번 결과에 포함되지 않습니다.')
    write(out/'summary.json',summary)
    if args.finish:
        shutil.copyfile(PUBLIC/'worlds'/f'{prefix}object/preview.jpg',out/'gs-preview.jpg');shutil.copyfile(PUBLIC/'worlds'/f'{prefix}context/preview.jpg',out/'context-preview.jpg')
    catalog=read(PUBLIC/'worlds/catalog.json');catalog['scenes']=[s for s in catalog['scenes'] if s['id'] not in [prefix+'object',prefix+'context']]
    for slug,title,description,source in [(prefix+'object','스쿠터 · 실제 9장만' if args.real_only else '스쿠터 · 한 물체 집중','이동 파노라마에서 같은 물체를 모아 65장으로 보충. 보정된 깊이 점군에서 시작한 GS.',job/'object'),(prefix+'context','스쿠터 · 실제 9장 · 전체' if args.real_only else '스쿠터 · 전체 학습 장면','동일한 학습 결과의 주변부를 포함한 원본 export. 생성 이미지가 포함된 실험.',job/'training')]:
        catalog['scenes'].append(dict(id=slug,title=title,description=('보간·디퓨전 없이 원본 9장만으로 깊이 보정 → 점군 → GS. 이전 실험과 나머지 설정 동일.' if args.real_only else description),category='experiment',manifestPath=f'/worlds/{slug}/world.json',thumbnailPath=f'/worlds/{slug}/preview.jpg',detail=f"{total} candidates → {len(registered_names)} posed RGB views · {len(fused_names)} depth maps → Metal GS · quality measurement pending",createdAt=time_of(source)))
    spec=read(ROOT/'scripts/observation-worlds.json');spec['worlds']=[w for w in spec['worlds'] if w['id'] not in [prefix+'object',prefix+'context']]
    for slug,folder in [(prefix+'object',job/'object/world'),(prefix+'context',job/'training/world')]:
        spec['worlds'].append(dict(id=slug,source=str(folder.relative_to(ROOT)),asset='scene.ply',format='ply',credits=['SOURCE_LICENSE']))
    sources={w['id']:ROOT/w['source'] for w in spec['worlds']}
    sources.update(reconstructed=ROOT/'data/jobs/dozer-1500/world',independent=ROOT/'data/jobs/dozer-independent-120/world',desk=ROOT/'data/jobs/desk-video-full-sdr/training/world')
    for scene in catalog['scenes']:
        folder=sources.get(scene['id']);stamp=time_of(folder.parent) if folder else None
        if stamp:scene['createdAt']=stamp
    write(PUBLIC/'worlds/catalog.json',catalog)
    entries=[dict(id=s['id'],title=s['title'],description=s['description'],image=s['thumbnailPath'],href='/?world='+s['manifestPath'],kind='scene',detail=s['detail'],**({'createdAt':s['createdAt']} if s.get('createdAt') else {})) for s in catalog['scenes']]
    for slug,title,description,image,stamp in [
        ('object-focus','한 물체 집중 · 스쿠터','9장 실제 사진 → 65장 입력 → 깊이 정합 → 점군 → GS. 원본·생성·깊이·점군을 한 화면에서 봅니다.','/experiments/object-focus/originals-contact.jpg',time_of((ROOT/'data/jobs/object-focus-20261105' if args.real_only else job)/'object')),
        ('depth-warp','깊이 투영과 빈틈 채우기','상대 깊이 투영 뒤 마스크 디퓨전을 적용한 이전 실험. 품질 개선 FAIL.','/experiments/depth-warp/images/diffusion.png',time_of(ROOT/'data/jobs/mapillary-depth-gs-10000-20261105')),
        ('depth-v2','사진 세 장의 단안 깊이','Depth Anything V2 Small의 상대 깊이 예측.','/experiments/depth-v2/view-01-visual.png',time_of(ROOT/'data/jobs/mapillary-depth-v2-3views-20261105')),
        ('video-4to6','구면 사진 두 장 → 65프레임','RIFE 광학 흐름 보간 영상과 생성 중간 시점을 추가한 GS.','/experiments/video-4to6/images/midpoint.jpg',time_of(ROOT/'data/jobs/mapillary-video-4to6-20261105/gs-rife6-10000')),
        ('mapillary','첫 Mapillary 연속 구면 실험','원본, 기하 투영, 생성 이미지와 실행 이력.','/experiments/mapillary/images/stereo-completed.png',time_of(ROOT/'data/jobs/mapillary-beijing-generated-gs-smoke'))]:
        entries.append(dict(id='report-'+slug,title=title,description=description,image=image,href=f'/experiments/{slug}/',kind='report',detail='실험 묶음 · 결과와 과정',**({'createdAt':stamp} if stamp else {})))
    lab=PUBLIC/'experiments/lab'
    prior=read(lab/'timeline.json')['entries'] if (lab/'timeline.json').is_file() else []
    if args.real_only:
        entries.append(dict(id='report-object-real',title='원본 9장만 · 보간과 디퓨전 제거',description='같은 스쿠터와 설정으로 중간 이미지 56장을 전부 뺀 비교 실험.',image='/experiments/object-real/originals-contact.jpg',href='/experiments/object-real/',kind='report',detail='이전 생성 이미지 포함 결과와 비교',createdAt=time_of(job/'object')))
    ids={e['id'] for e in entries}
    entries.extend(e for e in prior if e['kind']=='report' and e['id'] not in ids)
    lab.mkdir(exist_ok=True);write(lab/'timeline.json',dict(version=1,entries=entries))
    selected=[f'experiments/{report_slug}/index.html','experiments/lab/index.html','experiments/lab/timeline.json']
    selected += [str(p.relative_to(PUBLIC)) for p in out.rglob('*') if p.is_file()]
    for file in selected:
        if file not in spec['files']:spec['files'].append(file)
    # Preview paths must be planned even when actual rendering follows this preparation.
    for file in [f'experiments/{report_slug}/gs-preview.jpg',f'experiments/{report_slug}/context-preview.jpg']:
        if file not in spec['files']:spec['files'].append(file)
    write(ROOT/'scripts/observation-worlds.json',spec)
    print(json.dumps(dict(worlds=2,frames=len(frames),points=fusion['points'],objectSplats=cropped['outputSplats'],timeline=len(entries))))


if __name__=='__main__':main()
