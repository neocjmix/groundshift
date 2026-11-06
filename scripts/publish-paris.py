#!/usr/bin/env python3
"""Publish only selected Paris GS derivatives and sanitized observation metadata."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil


ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')


def main(a):
    job=a.job.resolve();source=a.world.resolve();world=read(source/'world.json');ident=world['id']
    if ident not in ['paris-58m-spz','paris-58m-lod','paris-58m-lod-compact'] or world.get('background'):raise ValueError('Require an explicitly selected actual Paris GS-only derivative')
    native=read(job/'training/job.json');fusion=read(job/'fusion/report.json');depth=read(job/'depth/report.json');sfm=read(job/'sfm/report.json')
    if any(r['status']!='PASS' for r in [native,fusion,depth,sfm]):raise ValueError('Require completed native evidence')
    if not a.preview.is_file():raise ValueError('Require selected actual GS render preview')
    dest=ROOT/'public/worlds'/ident;dest.mkdir(exist_ok=True)
    for name in ['world.json','scene.spz','cameras.json','SOURCE_LICENSE']:shutil.copyfile(source/name,dest/name)
    shutil.copyfile(a.preview,dest/'preview.jpg')
    if world.get('streaming'):
        index_path=source/world['streaming']['path'];index=read(index_path);out=dest/'chunks';out.mkdir(exist_ok=True);shutil.copyfile(index_path,out/'index.json')
        for c in index['chunks']:
            data=(index_path.parent/c['path']).read_bytes()
            if len(data)!=c['bytes'] or hashlib.sha256(data).hexdigest()!=c['sha256']:raise ValueError('Chunk checksum mismatch')
            (out/c['path']).write_bytes(data)
    if world.get('paging'):
        index_path=source/world['paging']['path'];index=read(index_path);out=dest/'rad';out.mkdir(exist_ok=True);shutil.copyfile(index_path,out/'index.json')
        for c in index['files']:
            data=(index_path.parent/c['path']).read_bytes()
            if len(data)!=c['bytes'] or hashlib.sha256(data).hexdigest()!=c['sha256']:raise ValueError('RAD checksum mismatch')
            (out/c['path']).write_bytes(data)
    report=ROOT/'public/experiments/tourist-streaming';summary=read(report/'summary.json');now=datetime.now(timezone.utc).isoformat()
    summary.update(updatedAt=now,phase='native-rad-paging' if world.get('paging') else ('native-export-spatial' if world.get('streaming') else 'native-export'),
        result=dict(worldPath=f'/worlds/{ident}/world.json',poster=f'/worlds/{ident}/preview.jpg',detail='실제 로컬 M2 GS의 Chrome 렌더. 파리 원본24장·GPS약58m. 전체2.19km 재구성 아님. '+a.finding,label='LoD 스트리밍으로 탐색' if world.get('paging') else '구간 로딩으로 탐색'))
    for stage in summary['stages']:
        if stage['title']=='새 관광지 GS 재구성':stage.update(status='PASS',detail=f"실제 M2 Metal8k768px GS 완료:{native['artifact']['splats']:,}점,{native['elapsedSeconds']:.3f}초. 로컬 원본 PLY 보존,공개 SPZ 파생 장면. {a.finding}")
        if stage['title']=='SPZ 구간 스트리밍·레이지로딩' and not world.get('paging'):stage.update(status='NOT RUN',detail='6개 공간SPZ파일·최대3개 상주·단일fetch/decode구현.실제브라우저 전환/오류복구 검증은 아직 완료 전.' if world.get('streaming') else '실제GS 전체SPZ 우선 게시.공간 분할·선로딩·해제는 다음 갱신에서 표시.')
    if world.get('paging'):
        summary['stages']=[s for s in summary['stages'] if s['title']!='Native RAD·LoD 스트리밍']
        summary['stages'].append(dict(title='Native RAD·LoD 스트리밍',status='PASS local execution',detail=a.finding+' 공개검증 및 다른방향 비교는 진행 중.'))
    summary['stages']=[s for s in summary['stages'] if s['title'] not in ['공개 원본 보고서 실제 브라우저','새 GS 공개 브라우저 검증']]
    summary['stages'].append(dict(title='새 GS 공개 브라우저 검증',status='NOT RUN',detail='앞선 원본 답사 사진 페이지의 브라우저PASS는 새GS/구간로딩PASS가 아님.배포 후 실제검증을 별도 갱신.'))
    # Keep the first source/acquisition stages and old comparisons intact.
    serialized=json.dumps({'world':world,'summary':summary})
    if '/Users/' in serialized or 'data/jobs/' in serialized or 'file://' in serialized:raise ValueError('Local source in public metadata')
    write(report/'summary.json',summary)
    catalog=read(ROOT/'public/worlds/catalog.json');entry=dict(id=ident,title='Paris · '+('LoD 스트리밍 · compact' if ident.endswith('compact') else 'LoD 스트리밍' if world.get('paging') else '첫58m와 구간 로딩'),description='실제24파노라마 · 같은 M2 GS · '+('먼영역은거친GS,가까운영역은정밀GS' if world.get('paging') else '최근접3영역표시 · 전체로딩비교가능'),category='experiment',manifestPath=f'/worlds/{ident}/world.json',thumbnailPath=f'/worlds/{ident}/preview.jpg',createdAt=now,detail=a.finding)
    catalog['scenes']=[s for s in catalog['scenes'] if s['id']!=ident]+[entry];write(ROOT/'public/worlds/catalog.json',catalog)
    timeline=read(ROOT/'public/experiments/lab/timeline.json');timeline['entries']=[e for e in timeline['entries'] if e['id']!=ident];timeline['entries'].append(dict(id=ident,kind='scene',title=entry['title'],description=entry['description'],image=entry['thumbnailPath'],href='/?world='+entry['manifestPath'],createdAt=native['finishedAt'],detail=a.finding))
    for e in timeline['entries']:
        if e['href']=='/experiments/tourist-streaming/':e.update(title='Paris · 첫 GS와 공간 스트리밍',description='실제24장/58m 재구성 결과 · 전체2.19km 원본 답사와 구분',createdAt=now,detail=a.finding)
    write(ROOT/'public/experiments/lab/timeline.json',timeline)
    canonical=job/('publication-'+ident)/'world'
    canonical.parent.mkdir(exist_ok=True)
    # Publication lineage is a frozen ordinary artifact ending in /world.
    # Copy only the already selected public files; keep native/raw diagnostics out.
    shutil.copytree(dest,canonical)
    allow=read(ROOT/'scripts/observation-worlds.json');allow['worlds']=[w for w in allow['worlds'] if w['id']!=ident]+[dict(id=ident,source=str(canonical.relative_to(ROOT)),asset='scene.spz',format='spz',credits=['SOURCE_LICENSE'])];write(ROOT/'scripts/observation-worlds.json',allow)
    print('PASS public selected derivative',ident,'streaming',bool(world.get('streaming')))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('world',type=Path);p.add_argument('--preview',type=Path,required=True);p.add_argument('--finding',default='최초 실제 렌더 확인.상세 화질/구간 로딩 검증은 진행 중.');main(p.parse_args())
