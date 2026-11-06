#!/usr/bin/env python3
"""Publish the executed fixed-pair calibration diagnostic through the observation allowlist."""
import argparse
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public'
def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('--perspective',type=Path);args=p.parse_args()
    report=read(args.job/'report.json')
    if report['status']!='PASS' or len(report['models'])!=2:raise ValueError('Require the completed two-model experiment')
    out=PUBLIC/'experiments/panoramic-calibration';out.mkdir(parents=True,exist_ok=False)
    source=read(ROOT/'scripts/samples/mapillary-beijing.json');photos=[x for x in source['images'] if x['image_id'] in ['1677293342921360','679966948337536']]
    for model in report['models']:
        if model['trainingTracks']!=784 or model['withheldTracks']!=217:raise ValueError('Narrative is specific to the declared fixed-pair study')
        dest=out/model['model'];dest.mkdir()
        for name in ['4-to-5-features.png','5-to-4-features.png','cloud.json','cloud.ply']:shutil.copyfile(args.job/model['model']/name,dest/name)
    summary=dict(completedAt=report['finishedAt'],status=report['status'],elapsedSeconds=report['elapsedSeconds'],maxResidentSetBytes=report['maxResidentSetBytes'],models=report['models'],
        conclusion='같은 점으로 보정을 맞춰도 뚜렷한 개선은 없었습니다. 가까워 시차가 큰 점에서 깊이 예측의 오차가 크게 남습니다. 전체 평균이 작아도 정확한 거리라고 해석할 수 없습니다.',
        notes=['첫 번째 공통점 보정 실험에서는 보정 대상만 1,195개에서 동일한 공통 784개로 바꿨습니다. 카메라·모델 출력·좌표·보정 공식은 그대로입니다. 새 GPU 추론은 실행하지 않았습니다.',
               '특징점의 실제 사진 좌표에서 깊이를 읽어 상대 사진에 투영했습니다. 두 사진마다 가장 중앙에 가까운 실제 관측 크롭 한 개를 골라 중복 관측을 늘려 세지 않았습니다.',
               '두 방향 각각 같은 217개 점을 검사했습니다. 보정에서 제외했어도 기존 SfM은 이 사진들을 사용하므로 독립적인 실제 깊이 정답은 아닙니다.',
               '시차가 10도 이상인 26개 점에서는 DA² 공통점 보정의 오차 중앙값이 약 28–38픽셀, DAV2는 약 7픽셀입니다. 같은 광선의 SfM 거리 대조군은 약 0.8–0.9픽셀입니다. 기존 보정도 비슷해서, 보정 점 집합 차이만이 원인이라는 가설은 지지되지 않았습니다.',
               '작은 전체 픽셀 오차에는 시차 1도 미만인 94개 점이 크게 기여합니다. 낮은 시차에서는 깊이 차이를 판단하기 어렵습니다. SfM 대조군 역시 카메라·특징점·스티칭 오류의 영향을 받습니다.',
               '깊이의 방향별·공간별 왜곡을 다음에 대조할 근거는 생겼지만 카메라가 정확하다고 증명한 것은 아닙니다. 후속 후보는 같은 관측 크롭의 원근 깊이와 ERP 깊이를 비교하는 대조 실험입니다.',
               '도로 영역에는 검사할 공통 제외점이 없고, 건물·난간 영역에는 각 방향 1개뿐입니다. 이 영역만의 개선이나 정확도를 주장하지 않습니다.'],
        sourceLinks=[dict(title=f'Cicero101 / Mapillary · {x["image_id"]}',href=x['commons_page']) for x in photos])
    if args.perspective:
        control=read(args.perspective/'report.json')
        if control['status']!='PASS':raise ValueError('Perspective control must actually execute')
        dest=out/'perspective';dest.mkdir()
        for name in ['4-to-5-features.png','5-to-4-features.png']:shutil.copyfile(args.perspective/name,dest/name)
        summary['perspective']=control;summary['completedAt']=max(summary['completedAt'],control['finishedAt'])
        summary['conclusion']='공통점 보정의 효과는 작았습니다. 추가한 원근 깊이 대조군은 시차가 큰 점의 오차 중앙값이 약 7픽셀에서 2.2–2.6픽셀로 줄었습니다. 다음은 이 개선이 점군의 연속성으로 이어지는지 확인할 단계입니다.'
        summary['notes'].append('추가 DAV2 원근 대조군은 실제 MPS 추론을 실행했습니다. 원근 입력과 카메라-Z 보정을 함께 사용하므로, 입력 투영만 바꾼 순수 단일변수 실험이라고 주장하지 않습니다. 같은 보정점·같은 파라미터 수의 ERP 영역별 보정 대조군도 함께 표시합니다.')
    write(out/'summary.json',summary)
    (out/'ATTRIBUTION.txt').write_text('Source: Cicero101 / Mapillary via Wikimedia Commons. CC BY-SA 4.0.\n'+source['licenseUrl']+'\n'+'\n'.join(x['commons_page'] for x in photos)+'\nChanges: perspective reprojection, depth estimation, sparse calibration and diagnostic feature arrows; point-cloud colors derived from these images.\n')
    timeline=read(PUBLIC/'experiments/lab/timeline.json')
    if any(e['id']=='report-panoramic-calibration' for e in timeline['entries']):raise ValueError('Preserve prior report; choose a new experiment ID')
    timeline['entries'].append(dict(id='report-panoramic-calibration',title='공통 특징점 보정 · 무엇이 어긋났을까?',description='같은 784점으로 보정하고 217점으로 검사. 원근 사진 깊이 대조군에서 가까운 점의 재투영 오차 감소.',createdAt=summary['completedAt'],image='/experiments/panoramic-calibration/dav2/4-to-5-features.png',href='/experiments/panoramic-calibration/',kind='report',detail='로컬 CPU 진단 · 기존 MPS 예측 재사용 · 새 GS 없음'))
    write(PUBLIC/'experiments/lab/timeline.json',timeline)
    spec=read(ROOT/'scripts/observation-worlds.json');files=[str(f.relative_to(PUBLIC)) for f in out.rglob('*') if f.is_file()]+['experiments/panoramic-calibration/index.html'];spec['files']=list(dict.fromkeys(spec['files']+files));write(ROOT/'scripts/observation-worlds.json',spec)
    print(json.dumps(dict(files=len(files),timelineEntries=len(timeline['entries']))))

if __name__=='__main__':main()
