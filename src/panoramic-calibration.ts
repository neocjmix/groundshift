import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './experiment.css';

type Stats = { samples: number; validSamples: number; invalidSamples: number; outOfImageSamples: number; medianPixels: number | null; p90Pixels: number | null; medianAngularDegrees: number | null };
type Group = { methods: Record<string, Stats>; paired: { pairedValidSamples: number; excludedPairs: number; improved: number; medianDeltaPixels: number | null } };
type Direction = Group & { id: string; strata: (Group & { group: string; label: string })[] };
type Model = { model: string; directions: Direction[]; cloudPoints: number[] };
type Summary = { completedAt: string; status: string; conclusion: string; notes: string[]; models: Model[]; elapsedSeconds: number; maxResidentSetBytes: number; sourceLinks: { title: string; href: string }[]; perspective?: { directions: (Omit<Direction,'paired'> & { pairedVersusGlobal: Group['paired'] })[]; inference: { elapsedSeconds: number; inferenceSeconds: number[] } } };
type View = { position: number[]; up: number[]; target: number[]; fov?: number };
type Cloud = { positions: number[]; colors: number[]; sourceIds: number[]; radius: number; camera: View; captures: (View & { id: string })[] };
const labels: Record<string,string> = { sfmPoint: 'SfM 3D 점 대조군', sfmRay: '관측 광선 + SfM 거리', original: '기존 보정 · 사진별 1,195점', common: '공통점 보정 · 같은 784점' };
const number = (x: number | null, digits = 3) => x === null ? '자료 없음' : x.toLocaleString('ko-KR', { maximumFractionDigits: digits });

document.querySelector('#app')!.innerHTML = `<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header><main>
<span class="eyebrow">Panoramic street · calibration ablation</span><h1>같은 점으로 맞추면<br>두 사진이 더 잘 겹칠까?</h1>
<p>두 사진에서 공통으로 보이는 점 1,001개를 찾았습니다. 그중 같은 784개로 깊이를 보정하고, 보정에 쓰지 않은 217개가 다른 사진의 실제 특징점 위치에 맞는지 검사했습니다.</p>
<div class="actions"><span id="status" role="status" class="status">실행 기록을 불러오는 중…</span><a href="/experiments/panoramic-pair/">앞선 두 파노라마 실험 ↗</a></div><div id="conclusion" class="note"></div>
<section class="section"><h2>같은 특징점에서 비교한 결과</h2><p>512×512 원근 사진의 픽셀 단위입니다. 값이 작을수록 실제로 관측한 점에 가깝습니다. SfM 대조군도 같은 사진으로 만든 내부 기준입니다.</p>
<div class="toolbar"><label>깊이 모델 <select id="model-select" disabled><option value="da2">DA²</option><option value="dav2">Depth Anything V2 Small</option></select></label><label>비교 방향 <select id="direction-select" disabled><option value="4-to-5">4번 → 5번</option><option value="5-to-4">5번 → 4번</option></select></label></div>
<div style="overflow-x:auto"><table id="comparison" style="width:100%;text-align:left;border-spacing:12px"><thead><tr><th>거리 계산 방법</th><th>검사 점 수</th><th>유효 / 무효</th><th>화면 밖</th><th>오차 중앙값 px</th><th>상위 10% 경계 px</th></tr></thead><tbody></tbody></table></div><p id="paired" class="muted"></p>
<label>어떤 점에서 차이가 커지나? <select id="strata-select" disabled><option value="parallax">두 카메라 사이 시차</option><option value="longitude">파노라마를 바라보는 방향</option><option value="region">앞서 정한 도로·건물 영역</option></select></label>
<div style="overflow-x:auto"><table id="strata" style="width:100%;text-align:left;border-spacing:12px"><thead><tr><th>영역</th><th>점 수</th><th>SfM 광선 px</th><th>기존 보정 px</th><th>공통점 보정 px</th></tr></thead><tbody></tbody></table></div>
<p>시차는 두 촬영 위치에서 같은 점을 향하는 방향 사이의 각도입니다. 각도가 작으면 거리가 많이 틀려도 사진에서는 조금만 어긋날 수 있습니다. 같은 점을 찍은 가상 크롭 여러 개를 별도 관측으로 늘려 세지 않았습니다.</p></section>
<section class="section"><h2>실제 사진 위에서 어긋난 위치 보기</h2><p>노란 원이 실제 관측 위치입니다. 빨강은 기존 보정, 청록은 공통점 보정, 분홍은 관측 광선과 SfM 거리 대조군입니다. 화살표는 가독성을 위해 2배 확대하고 최대 48픽셀로 제한했습니다. 위 표의 수치는 제한 전 실제 오차입니다.</p><figure><img id="features" alt="실제 원근 사진 위의 보정 전후 특징점 재투영 오차"><figcaption>선택한 도착 사진의 실제 관측 217점 · 디퓨전이나 새 특징점 생성 없음</figcaption></figure></section>
<section id="perspective-control" class="section" hidden><h2>추가 대조 · DAV2를 원근 사진에 넣으면?</h2><p>같은 모델을 기존 512×512 원근 사진 12장에 실행했습니다. 각 크롭에서 같은 공통 보정점을 쓰는 파노라마 깊이 대조군도 추가했습니다. 원근 예측은 카메라 앞쪽 Z 거리로 보정한 뒤 실제 광선의 Z 성분으로 나누어 방사 거리로 바꿨습니다.</p><div style="overflow-x:auto"><table id="control-comparison" style="width:100%;text-align:left;border-spacing:12px"><thead><tr><th>거리 계산 방법</th><th>검사 점</th><th>무효 / 화면 밖</th><th>중앙값 px</th><th>상위 10% 경계 px</th></tr></thead><tbody></tbody></table></div><label>영역 <select id="control-strata-select" disabled><option value="parallax">시차별</option><option value="longitude">방향별</option></select></label><div style="overflow-x:auto"><table id="control-strata" style="width:100%;text-align:left;border-spacing:12px"><thead><tr><th>영역</th><th>점 수</th><th>ERP 전체 보정 px</th><th>ERP 크롭별 보정 px</th><th>원근 크롭별 보정 px</th></tr></thead><tbody></tbody></table></div><p id="control-runtime"></p><figure><img id="control-features" alt="DAV2 ERP 영역별 깊이와 원근 깊이의 실제 특징점 재투영 대조"><figcaption>빨강: ERP 크롭별 보정 · 청록: 원근 크롭별 보정 · 분홍: SfM 거리 대조군. 같은 217점, 선 길이 2배·최대 48px 표시.</figcaption></figure><p>ERP 전체 보정과 크롭별 보정은 파라미터 수가 다릅니다. ERP 크롭별 보정과 원근 크롭별 보정은 같은 점 집합·같은 파라미터 수를 사용하지만 입력 투영과 올바른 깊이 해석이 함께 달라집니다. 독립적인 실제 거리 정확도나 새 GS 품질을 증명하는 결과는 아닙니다.</p></section>
<section class="section"><h2>공통점 보정 전후 점군을 같은 시점에서 보기</h2><p>이 점군은 위 첫 번째 공통점 보정 실험의 결과입니다. 추가 원근 깊이 대조군의 여러 크롭은 아직 점군으로 융합하지 않았습니다.</p><div class="actions"><label>깊이 보정 <select id="fit-select" disabled><option value="original">기존 보정</option><option value="common">공통점 보정</option></select></label><label>색 <select id="color-select" disabled><option value="rgb">실제 사진 색</option><option value="source">4번 청록 / 5번 주황</option></select></label><label>시점 <select id="view-select" disabled><option value="overview">전체 보기</option><option value="4">4번 촬영 위치</option><option value="5">5번 촬영 위치</option></select></label><button id="reset" disabled>시점 초기화</button></div><div id="cloud" class="cloud"><span id="cloud-status" role="status" class="cloud-status">점군을 불러오는 중…</span></div><p>기존 마스크·샘플 간격·표시 카메라를 유지하고 거리만 바꿨습니다. 사진별 점군을 한 좌표계에서 함께 표시합니다. 좌표는 미터가 아닌 SfM 임의 단위이며, 점군 융합과 GS 학습은 하지 않았습니다.</p><a id="download" download>공통점 보정 점군 PLY ↓</a></section>
<section class="section"><h2>이번 결과가 말해주는 범위</h2><div id="notes" class="note"></div><p id="runtime"></p><p>첫 번째 공통점 보정 실험은 앞선 M2/MPS 예측을 재사용해 로컬 CPU에서 계산했습니다. 추가 원근 깊이 대조군은 같은 DAV2 모델로 새 MPS 추론을 실행했습니다. 독립적인 실제 거리 정답, 카메라 재추정, 9장 융합, GS 학습은 NOT RUN입니다.</p></section>
<footer><div id="sources"></div><p>원본·변환 이미지와 점군 색상: Cicero101 / Mapillary via Wikimedia Commons · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>. 깊이 추정·재투영 표시를 추가했습니다.</p><a href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/PANORAMIC_CALIBRATION.md">실행 기록과 재현 방법 ↗</a> · <span id="completed"></span></footer></main>`;
const select = (id: string) => document.querySelector<HTMLSelectElement>(`#${id}`)!;
const modelSelect = select('model-select'), directionSelect = select('direction-select'), fitSelect = select('fit-select');
let summary: Summary; let cloud: Cloud | undefined; let revision = 0; let fetchController: AbortController | undefined;
let renderer: THREE.WebGLRenderer | undefined; let geometry: THREE.BufferGeometry; let material: THREE.PointsMaterial; let camera: THREE.PerspectiveCamera; let controls: OrbitControls; let points: THREE.Points; let resize: ResizeObserver;
function table(id: string, rows: (string | number)[][]) {
  document.querySelector(`#${id} tbody`)!.replaceChildren(...rows.map(values => { const row = document.createElement('tr'); values.forEach(value => { const cell = document.createElement('td'); cell.textContent = String(value); row.append(cell); }); return row; }));
}
function diagnostics() {
  const model = summary.models.find(m => m.model === modelSelect.value)!; const direction = model.directions.find(d => d.id === directionSelect.value)!;
  table('comparison', Object.entries(labels).map(([key,label]) => { const s = direction.methods[key]; return [label,s.samples,`${s.validSamples} / ${s.invalidSamples}`,s.outOfImageSamples,number(s.medianPixels),number(s.p90Pixels)]; }));
  const p = direction.paired; document.querySelector('#paired')!.textContent = `같은 유효 점 ${p.pairedValidSamples}개 중 ${p.improved}개에서 오차가 줄었습니다. 공통점 보정 − 기존 보정의 점별 차이 중앙값: ${number(p.medianDeltaPixels)} px. 무효로 제외한 쌍: ${p.excludedPairs}개.`;
  table('strata', direction.strata.filter(s => s.group === select('strata-select').value).map(s => [s.label,s.methods.common.samples,number(s.methods.sfmRay.medianPixels),number(s.methods.original.medianPixels),number(s.methods.common.medianPixels)]));
  document.querySelector<HTMLImageElement>('#features')!.src = `${model.model}/${direction.id}-features.png`;
  document.querySelector<HTMLAnchorElement>('#download')!.href = `${model.model}/cloud.ply`;
  if (summary.perspective) {
    document.querySelector<HTMLElement>('#perspective-control')!.hidden = false;
    const control = summary.perspective.directions.find(d => d.id === directionSelect.value)!;
    const names: Record<string,string> = { sfmRay:'SfM 거리 대조군', erpGlobal:'ERP 전체 보정 · 784점', erpLocal:'ERP 크롭별 보정', perspective:'원근 크롭별 보정' };
    table('control-comparison',Object.entries(names).map(([key,label]) => { const s = control.methods[key]; return [label,s.samples,`${s.invalidSamples} / ${s.outOfImageSamples}`,number(s.medianPixels),number(s.p90Pixels)]; }));
    table('control-strata',control.strata.filter(s => s.group === select('control-strata-select').value).map(s => [s.label,s.methods.perspective.samples,number(s.methods.erpGlobal.medianPixels),number(s.methods.erpLocal.medianPixels),number(s.methods.perspective.medianPixels)]));
    document.querySelector<HTMLImageElement>('#control-features')!.src = `perspective/${control.id}-features.png`;
    document.querySelector('#control-runtime')!.textContent = `실제 MPS 실행 · 12장 작업 ${number(summary.perspective.inference.elapsedSeconds)}초 (모델 로딩·저장 포함). 같은 217점, 카메라 고정. 픽셀 오차 감소가 실제 거리 정확도나 점군 융합 성공을 뜻하지는 않습니다.`;
  }
}
function showView() {
  if (!cloud || !renderer) return;
  const view = select('view-select').value === 'overview' ? cloud.camera : cloud.captures.find(v => v.id === select('view-select').value)!;
  camera.up.fromArray(view.up); camera.position.fromArray(view.position); controls.target.fromArray(view.target);
  camera.fov = view.fov ?? 65; camera.near = Math.max(1e-7,cloud.radius / 10000); camera.far = cloud.radius * 100; camera.updateProjectionMatrix(); controls.update();
}
function showColors() {
  if (!cloud || !renderer) return;
  const data = new Float32Array(cloud.colors.length), color = new THREE.Color();
  for (let i = 0; i < data.length; i += 3) {
    if (select('color-select').value === 'source') color.setHex(cloud.sourceIds[i / 3] === 0 ? 0x4fdfcf : 0xffa764);
    else color.setRGB(cloud.colors[i] / 255,cloud.colors[i + 1] / 255,cloud.colors[i + 2] / 255,THREE.SRGBColorSpace);
    data.set([color.r,color.g,color.b],i);
  } geometry.setAttribute('color',new THREE.BufferAttribute(data,3));
}
function setup() {
  if (renderer) return;
  const host = document.querySelector<HTMLDivElement>('#cloud')!; renderer = new THREE.WebGLRenderer({ antialias:true }); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.setClearColor(0x080e15); host.append(renderer.domElement);
  const scene = new THREE.Scene(); geometry = new THREE.BufferGeometry(); material = new THREE.PointsMaterial({ vertexColors:true }); points = new THREE.Points(geometry,material); scene.add(points);
  camera = new THREE.PerspectiveCamera(); controls = new OrbitControls(camera,renderer.domElement); controls.enableDamping = true;
  resize = new ResizeObserver(() => { renderer!.setSize(host.clientWidth,host.clientHeight); camera.aspect = host.clientWidth / Math.max(host.clientHeight,1); camera.updateProjectionMatrix(); }); resize.observe(host);
  renderer.setAnimationLoop(() => { controls.update(); renderer!.render(scene,camera); });
}
async function showCloud() {
  const version = ++revision; fetchController?.abort(); fetchController = new AbortController(); cloud = undefined;
  document.querySelector<HTMLButtonElement>('#reset')!.disabled = true; if (points) points.visible = false;
  const status = document.querySelector('#cloud-status')!; status.textContent = '선택한 점군을 불러오는 중…';
  const url = fitSelect.value === 'original' ? `/experiments/panoramic-pair/${modelSelect.value}/cloud.json` : `${modelSelect.value}/cloud.json`;
  try {
    const response = await fetch(url,{ signal:fetchController.signal }); if (!response.ok) throw Error(`HTTP ${response.status}`); const data: Cloud = await response.json(); if (version !== revision) return;
    if (!data.positions?.length || data.positions.length % 3 || data.colors.length !== data.positions.length || data.sourceIds.length !== data.positions.length / 3 || !data.positions.every(Number.isFinite) || !(data.radius > 0)) throw Error('점군 형식이 올바르지 않습니다.');
    setup(); cloud = data; geometry.setAttribute('position',new THREE.Float32BufferAttribute(data.positions,3)); geometry.computeBoundingSphere(); material.size = data.radius / 130; showColors(); showView(); points.visible = true;
    status.textContent = `${modelSelect.value.toUpperCase()} · ${fitSelect.selectedOptions[0].text} · ${data.positions.length / 3}개 점 · 융합 없음`; document.querySelector<HTMLButtonElement>('#reset')!.disabled = false;
  } catch (error) { if (version === revision) status.textContent = `점군 불러오기 실패: ${String(error)}`; }
}
modelSelect.addEventListener('change',() => { diagnostics(); void showCloud(); }); fitSelect.addEventListener('change',() => void showCloud()); directionSelect.addEventListener('change',diagnostics); select('control-strata-select').addEventListener('change',diagnostics); select('strata-select').addEventListener('change',diagnostics); select('color-select').addEventListener('change',showColors); select('view-select').addEventListener('change',showView); document.querySelector('#reset')!.addEventListener('click',showView);
window.addEventListener('pagehide',() => { revision++; fetchController?.abort(); renderer?.setAnimationLoop(null); resize?.disconnect(); controls?.dispose(); geometry?.dispose(); material?.dispose(); renderer?.dispose(); },{ once:true });
fetch('./summary.json').then(async response => {
  if (!response.ok) throw Error(`HTTP ${response.status}`); summary = await response.json(); document.querySelector('#status')!.textContent = `로컬 실행 ${summary.status}`; document.querySelector('#conclusion')!.textContent = summary.conclusion; document.querySelector('#notes')!.textContent = summary.notes.join(' ');
  document.querySelector('#runtime')!.textContent = `계산 시간 ${number(summary.elapsedSeconds)}초 · 최대 프로세스 RSS ${number(summary.maxResidentSetBytes / 1e6,1)} MB (한 번 실행한 관측값)`;
  document.querySelector('#sources')!.replaceChildren(...summary.sourceLinks.map(s => { const a = document.createElement('a'); a.href = s.href; a.textContent = `${s.title} ↗ `; return a; })); document.querySelector('#completed')!.textContent = new Date(summary.completedAt).toLocaleString('ko-KR');
  document.querySelectorAll<HTMLSelectElement>('select').forEach(item => { item.disabled = false; }); diagnostics(); await showCloud();
}).catch(error => { document.querySelector('#status')!.textContent = `기록 불러오기 실패: ${String(error)}`; });
