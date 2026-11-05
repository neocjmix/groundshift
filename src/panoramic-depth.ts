import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './experiment.css';

type Vector = [number, number, number];
type View = { position: Vector; up: Vector; target: Vector; fov?: number };
type Cloud = { positions: number[]; colors: number[]; center: Vector; radius: number; camera: View; capture: View };
type Model = {
  id: string; title: string; status: 'PASS' | 'FAIL' | 'NOT RUN'; meaning: string;
  inferenceSeconds?: number; rawDepth?: string; rangeDepth?: string; mask?: string;
  cloud?: string; fullCloud?: string; ply?: string; notes: string[];
  diagnostics?: {
    calibration?: { trainingSamples?: number; heldOutSamples?: number; scale?: number; offset?: number };
    heldOut?: { medianAbsRel?: number; p90AbsRel?: number }; coverageFraction?: number;
  };
};
type Size = string | number[] | { width: number; height: number };
type Summary = {
  completedAt: string; source: { title: string; sourceUrl: string; licenseUrl: string; originalSize: Size; workingSize: Size };
  baseline: { href: string }; models: Model[]; notes: string[]; p1ReadyForPair: string;
};

const root = document.querySelector<HTMLDivElement>('#app')!;
root.innerHTML = `
<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header>
<main>
  <span class="eyebrow">Panoramic street reconstruction · P0 / bounded P1</span>
  <h1>물체 하나에서<br>사진 한 구 전체로.</h1>
  <p>실제 360도 사진 한 장에서 깊이를 추정하고, 같은 사진의 색을 입힌 구면 점군을 만듭니다. 거리 전체를 복원하기 전, 앞·뒤·위·아래를 함께 다룰 수 있는지 보는 첫 실험입니다.</p>
  <div class="actions"><span class="status">관측된 원본 RGB · 생성 이미지 없음</span><span class="status pending">기하 정확도 미검증 · GS 학습 안 함</span><a id="baseline" href="/experiments/object-real/">보존된 스쿠터 기준 실험 ↗</a></div>
  <div class="steps"><span>실제 ERP 사진 1장</span><span>→ 깊이 모델</span><span>→ SfM 기준 보정</span><span>→ 구면 방향 × 거리</span><span>→ 색상 점군</span></div>
  <section class="section">
    <h2>같은 구면 사진, 다른 깊이 추정</h2>
    <div class="toolbar"><label>실행 모델 <select id="model-select" disabled aria-label="깊이 모델 선택"></select></label><span id="model-status" class="status" role="status">실행 기록을 불러오는 중…</span></div>
    <p id="model-meaning"></p><div id="metrics" class="metrics"></div>
    <div id="model-notes" class="note"></div>
    <div class="image-pair" style="margin-top:24px">
      <figure><img id="source" src="source.jpg" alt="실제로 촬영한 360도 ERP 파노라마"><figcaption id="source-label">관측 RGB · 원본 구면을 평면으로 펼친 사진</figcaption></figure>
      <figure id="depth-figure"><img id="depth" alt="선택한 모델의 상대 깊이 시각화"><figcaption>모델 원출력 시각화 · 색의 밝기는 미터 단위 거리가 아닙니다.</figcaption></figure>
      <figure id="range-figure"><img id="range" alt="SfM 기준으로 보정한 구면 방사 거리"><figcaption>보정된 방사 거리 · SfM 임의 단위, 절대 거리 아님</figcaption></figure>
      <figure id="mask-figure"><img id="mask" alt="점군 생성에 사용한 보수적 유효 영역 마스크"><figcaption>보수적 선택 마스크 · 제외 영역이 정확한 하늘·물체 분할이라는 뜻은 아닙니다.</figcaption></figure>
    </div>
  </section>
  <section class="section">
    <h2>구면에서 3D로 펼쳐 보기</h2>
    <p>각 픽셀을 원래 바라보던 방향으로 보내고 보정된 거리만큼 놓았습니다. 점들은 추정한 동일한 SfM 좌표계에 있습니다. 촬영 위치에서 보면 원본 색이 그럴듯하게 겹칠 수 있지만, 이것만으로 공간 구조가 맞는 것은 아닙니다.</p>
    <div class="actions">
      <label>점군 범위 <select id="cloud-set" disabled><option value="filtered">보수적 마스크 적용</option><option value="full">유효 거리 전체 · 진단용</option></select></label>
      <button id="capture-view" disabled>촬영 위치에서 보기</button><button id="overview-view" disabled>바깥에서 전체 보기</button><button id="reset" disabled>현재 시점 초기화</button>
      <label>점 크기 <input id="point-size" type="range" min="1" max="8" value="3" disabled></label>
    </div>
    <div class="cloud" id="cloud"><span id="cloud-status" class="cloud-status" role="status">점군을 불러오는 중…</span></div>
    <p class="muted">드래그로 회전 · 휠로 확대 · 우클릭 드래그로 이동. 점군은 표시용으로 줄인 샘플일 수 있습니다. 촬영 위치 버튼은 제공된 카메라 위치와 방향으로 돌아갑니다.</p>
    <div class="actions"><a id="download" class="action" hidden download>색상 점군 PLY 다운로드 ↓</a><span class="status pending">독립적인 실제 깊이 측정 없음</span></div>
  </section>
  <section class="section">
    <h2>무엇을 확인했고, 무엇이 남았나</h2>
    <p id="calibration"></p><div id="notes" class="note"></div>
    <p>ERP의 왼쪽과 오른쪽은 실제로 이어진 한 방향입니다. 이 경계와 위·아래 극점에서 깊이가 끊기거나 늘어나는지 살펴야 합니다. 보정에 쓰지 않은 SfM 점도 같은 사진들로 추정한 내부 비교 자료이며, 독립적인 기하 정답은 아닙니다.</p>
    <p id="next-step"></p>
  </section>
  <footer><a id="source-link">원본 출처</a> · Cicero101 / Mapillary via Wikimedia Commons · <a id="license-link">CC BY-SA 4.0</a><br>
    관측 RGB, 추정 깊이와 추정 카메라를 사용한 진단용 점군입니다. 원본 사진·기존 카메라·기존 GS 결과는 보존했습니다.<br>
    <a href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/PANORAMIC_DEPTH_P1.md">실행 기록과 제한 사항 ↗</a> · <span id="completed"></span>
  </footer>
</main>`;

const select = document.querySelector<HTMLSelectElement>('#model-select')!;
const cloudSelect = document.querySelector<HTMLSelectElement>('#cloud-set')!;
const pointSize = document.querySelector<HTMLInputElement>('#point-size')!;
const cloudStatus = document.querySelector<HTMLElement>('#cloud-status')!;
let summary: Summary;
let cloud: Cloud | undefined;
let requestVersion = 0;
let activeView: 'capture' | 'camera' = 'camera';
let renderer: THREE.WebGLRenderer | undefined;
let geometry: THREE.BufferGeometry | undefined;
let material: THREE.PointsMaterial | undefined;
let camera: THREE.PerspectiveCamera | undefined;
let controls: OrbitControls | undefined;
let resize: ResizeObserver | undefined;
let points: THREE.Points | undefined;

function sizeLabel(size: Size) {
  return typeof size === 'string' ? size : Array.isArray(size) ? size.join(' × ') : `${size.width} × ${size.height}`;
}
function measured(value: number | undefined, suffix = '', precision = 0) {
  return typeof value === 'number' && Number.isFinite(value) ? `${value.toLocaleString('ko-KR', { maximumFractionDigits: precision })}${suffix}` : 'NOT RUN';
}
function metric(label: string, value: string) {
  const item = document.createElement('div'); item.className = 'metric';
  const number = document.createElement('strong'); number.textContent = value;
  const caption = document.createElement('span'); caption.textContent = label;
  item.append(number, caption); return item;
}
function view(kind = activeView) {
  if (!cloud || !camera || !controls) return;
  activeView = kind;
  const target = cloud[kind];
  camera.fov = target.fov ?? cloud.camera.fov ?? 65;
  camera.near = Math.max(cloud.radius / 10000, 1e-7); camera.far = cloud.radius * 100;
  camera.up.fromArray(target.up); camera.position.fromArray(target.position);
  controls.target.fromArray(target.target ?? cloud.center);
  camera.updateProjectionMatrix(); controls.update(); controls.saveState();
}
function setupRenderer() {
  if (renderer) return;
  const host = document.querySelector<HTMLDivElement>('#cloud')!;
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setClearColor(0x080e15);
  host.append(renderer.domElement);
  const scene = new THREE.Scene();
  geometry = new THREE.BufferGeometry(); material = new THREE.PointsMaterial({ vertexColors: true });
  points = new THREE.Points(geometry, material); scene.add(points);
  camera = new THREE.PerspectiveCamera(65, 1, .001, 1000);
  controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true;
  resize = new ResizeObserver(() => {
    if (!renderer || !camera) return;
    renderer.setSize(host.clientWidth, host.clientHeight);
    camera.aspect = host.clientWidth / Math.max(host.clientHeight, 1); camera.updateProjectionMatrix();
  }); resize.observe(host);
  renderer.setAnimationLoop(() => { if (camera) { controls?.update(); renderer?.render(scene, camera); } });
}
function cloudButtons(enabled: boolean) {
  for (const id of ['capture-view', 'overview-view', 'reset']) document.querySelector<HTMLButtonElement>(`#${id}`)!.disabled = !enabled;
  pointSize.disabled = !enabled;
}
async function showCloud(model: Model, version: number) {
  cloudButtons(false); cloud = undefined;
  if (points) points.visible = false;
  const path = cloudSelect.value === 'full' ? model.fullCloud : model.cloud;
  if (!path || model.status !== 'PASS') { cloudStatus.textContent = '점군 없음 · 실행 상태와 오류 기록을 확인하세요.'; return; }
  cloudStatus.textContent = '선택한 점군을 불러오는 중…';
  try {
    const response = await fetch(path); if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data: Cloud = await response.json();
    if (version !== requestVersion) return;
    if (!data.positions?.length || data.positions.length % 3 || data.colors?.length !== data.positions.length
      || !Number.isFinite(data.radius) || data.radius <= 0 || !data.camera || !data.capture) throw new Error('점군 형식이 올바르지 않습니다.');
    setupRenderer(); cloud = data;
    geometry!.setAttribute('position', new THREE.Float32BufferAttribute(data.positions, 3));
    const colors = new Float32Array(data.colors.length); const color = new THREE.Color();
    for (let i = 0; i < colors.length; i += 3) {
      color.setRGB(data.colors[i] / 255, data.colors[i + 1] / 255, data.colors[i + 2] / 255, THREE.SRGBColorSpace);
      colors.set([color.r, color.g, color.b], i);
    }
    geometry!.setAttribute('color', new THREE.BufferAttribute(colors, 3)); geometry!.computeBoundingSphere();
    material!.size = data.radius / 390 * Number(pointSize.value); points!.visible = true;
    view(); cloudButtons(true);
    cloudStatus.textContent = `${model.title} · ${(data.positions.length / 3).toLocaleString()}개 표시 점 · ${cloudSelect.value === 'full' ? '유효 거리 전체' : '보수적 마스크'} · SfM 임의 단위`;
  } catch (error) {
    if (version === requestVersion) cloudStatus.textContent = `점군 불러오기 실패: ${String(error)}`;
  }
}
function image(id: string, path: string | undefined) {
  const element = document.querySelector<HTMLImageElement>(`#${id}`)!;
  element.closest('figure')!.hidden = !path;
  if (path) element.src = path; else element.removeAttribute('src');
}
async function showModel() {
  const model = summary.models.find(item => item.id === select.value)!;
  const version = ++requestVersion;
  document.querySelector('#model-status')!.textContent = `${model.status} · ${model.title} 실행`;
  document.querySelector('#model-status')!.classList.toggle('pending', model.status !== 'PASS');
  document.querySelector('#model-meaning')!.textContent = model.meaning;
  document.querySelector('#model-notes')!.textContent = model.notes.join(' ');
  const diagnostic = model.diagnostics;
  document.querySelector('#metrics')!.replaceChildren(
    metric('실측 추론 시간', measured(model.inferenceSeconds, '초', 2)),
    metric('보정용 SfM 표본', measured(diagnostic?.calibration?.trainingSamples)),
    metric('보정에서 제외한 SfM 표본', measured(diagnostic?.calibration?.heldOutSamples)),
    metric('보수적 선택 영역', measured(diagnostic?.coverageFraction === undefined ? undefined : diagnostic.coverageFraction * 100, '%', 1)),
  );
  image('depth', model.rawDepth); image('range', model.rangeDepth); image('mask', model.mask);
  cloudSelect.disabled = model.status !== 'PASS' || !model.cloud;
  cloudSelect.options[1].disabled = !model.fullCloud;
  if (cloudSelect.value === 'full' && !model.fullCloud) cloudSelect.value = 'filtered';
  const download = document.querySelector<HTMLAnchorElement>('#download')!;
  download.hidden = !model.ply; if (model.ply) download.href = model.ply; else download.removeAttribute('href');
  document.querySelector('#calibration')!.textContent = `같은 SfM 추정에 대한 내부 보정 검사: 제외 표본의 상대 오차 중앙값 ${measured(diagnostic?.heldOut?.medianAbsRel, '', 4)}, 90백분위 ${measured(diagnostic?.heldOut?.p90AbsRel, '', 4)}. 보정 계수 scale ${measured(diagnostic?.calibration?.scale, '', 6)}, offset ${measured(diagnostic?.calibration?.offset, '', 6)}. 이 수치는 외부 측정에 대한 정확도 점수가 아닙니다.`;
  await showCloud(model, version);
}

select.addEventListener('change', () => void showModel());
cloudSelect.addEventListener('change', () => void showCloud(summary.models.find(item => item.id === select.value)!, ++requestVersion));
document.querySelector('#capture-view')!.addEventListener('click', () => view('capture'));
document.querySelector('#overview-view')!.addEventListener('click', () => view('camera'));
document.querySelector('#reset')!.addEventListener('click', () => view());
pointSize.addEventListener('input', () => { if (cloud && material) material.size = cloud.radius / 390 * Number(pointSize.value); });
window.addEventListener('pagehide', () => {
  requestVersion++; renderer?.setAnimationLoop(null); resize?.disconnect(); controls?.dispose();
  geometry?.dispose(); material?.dispose(); renderer?.dispose();
}, { once: true });

fetch('./summary.json').then(async response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  summary = await response.json();
  if (!summary.models?.length) throw new Error('실행 모델 기록이 없습니다.');
  for (const model of summary.models) { const option = new Option(`${model.title} · ${model.status}`, model.id); select.add(option); }
  select.value = summary.models.find(model => model.status === 'PASS')?.id ?? summary.models[0].id; select.disabled = false;
  document.querySelector('#source-label')!.textContent = `${summary.source.title} · 원본 ${sizeLabel(summary.source.originalSize)} → 실험 ${sizeLabel(summary.source.workingSize)}`;
  document.querySelector<HTMLAnchorElement>('#source-link')!.href = summary.source.sourceUrl;
  document.querySelector<HTMLAnchorElement>('#license-link')!.href = summary.source.licenseUrl;
  document.querySelector<HTMLAnchorElement>('#baseline')!.href = summary.baseline.href;
  document.querySelector('#notes')!.textContent = summary.notes.join(' ');
  document.querySelector('#next-step')!.textContent = summary.p1ReadyForPair === 'diagnostic-only'
    ? '다음 두 파노라마 실험은 불일치 원인을 찾는 진단 단계입니다. 같은 거리 표면이 두 시점에서 맞는지 확인하기 전에는 전체 거리 GS 학습으로 확장하지 않습니다.'
    : `다음 단계 판단: ${summary.p1ReadyForPair}`;
  document.querySelector('#completed')!.textContent = new Date(summary.completedAt).toLocaleString('ko-KR');
  await showModel();
}).catch(error => {
  document.querySelector('#model-status')!.textContent = '기록 불러오기 실패';
  cloudStatus.textContent = `불러오기 실패: ${String(error)}`;
});
