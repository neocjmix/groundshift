import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './experiment.css';

type Status = 'PASS' | 'FAIL' | 'NOT RUN';
type QualityStatus = Status | 'NOT ACCEPTED';
type Vector = [number, number, number];
type View = { position: Vector; up: Vector; target: Vector; fov?: number };
type Cloud = {
  positions: number[]; colors: number[]; sourceIds: number[]; center: Vector; radius: number;
  camera: View; captures: (View & { id: string; title: string })[];
};
type Metric = { label: string; value: number | null; unit?: string; precision?: number };
type Direction = {
  id: string; title: string; source?: string; target?: string; depth?: string;
  warp?: string; residual?: string; mask?: string; overlap?: string; metrics: Metric[]; notes: string[];
};
type Model = {
  id: string; title: string; status: Status; qualityStatus: QualityStatus; meaning: string;
  cloud?: string; ply?: string; metrics: Metric[]; directions: Direction[]; notes: string[];
};
type Summary = {
  heading?: string; intro?: string; docHref?: string; maskCaption?: string;
  evidence?: { title: string; image: string; caption: string }[];
  completedAt: string; status: Status; qualityStatus: QualityStatus; conclusion: string;
  sources: { id: string; title: string; image: string; sourceUrl: string; licenseUrl: string }[];
  models: Model[]; notes: string[]; nextStep: string;
};

document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header>
<main>
  <span class="eyebrow">Panoramic street reconstruction · adjacent pair</span>
  <h1 id="heading">두 사진이 말하는 거리,<br>같은 공간일까?</h1>
  <p id="intro">연속해서 촬영한 360도 사진 4·5번에서 각각 깊이를 추정했습니다. 기존 SfM 카메라 좌표에 놓은 두 점군이 같은 도로와 벽면을 가리키는지 비교합니다. 색을 합쳐 그럴듯하게 보이는 것과, 두 추정이 실제로 일치하는 것은 다릅니다.</p>
  <div class="actions"><span id="execution-status" class="status" role="status">실행 기록을 불러오는 중…</span><span id="quality-status" class="status pending"></span><a href="/experiments/panoramic-depth/">앞선 한 파노라마 실험 ↗</a></div>
  <div class="note" id="conclusion"></div>
  <div class="steps" style="margin-top:24px"><span>실제 ERP 사진 2장</span><span>→ 각각 깊이 추정·보정</span><span>→ 기존 공통 좌표</span><span>→ 양방향 겹침 검사</span></div>
  <section class="section">
    <h2>같은 거리, 두 실제 촬영 위치</h2>
    <div class="image-pair" id="sources"></div>
    <p>원본 RGB는 실제 사진입니다. 깊이와 카메라는 추정값이며, 여기에서 표시하는 거리는 SfM 임의 단위입니다. GPS나 미터 단위 거리로 해석할 수 없습니다.</p>
  </section>
  <section class="section">
    <h2>두 점군을 같은 좌표에 겹쳐 보기</h2>
    <div class="toolbar"><label>표시 결과 <select id="model-select" disabled aria-label="표시 결과 선택"></select></label><span id="model-status" class="status" role="status"></span></div>
    <p id="model-meaning"></p><div id="metrics" class="metrics"></div>
    <div class="actions">
      <label>표시 색 <select id="color-mode" disabled><option value="rgb">원본 사진 RGB</option><option value="source">출처별 색 · 4번 청록 / 5번 주황</option></select></label>
      <label>표시 출처 <select id="source-select" disabled><option value="both">4·5번 함께</option><option value="0">4번만</option><option value="1">5번만</option></select></label>
      <button id="capture-4" disabled>4번 촬영 위치</button><button id="capture-5" disabled>5번 촬영 위치</button>
      <button id="overview-view" disabled>바깥에서 전체 보기</button><button id="reset" disabled>현재 시점 초기화</button>
      <label>점 크기 <input id="point-size" type="range" min="1" max="8" value="3" disabled></label>
    </div>
    <div class="cloud" id="cloud"><span id="cloud-status" class="cloud-status" role="status">점군을 불러오는 중…</span></div>
    <p class="muted">드래그로 회전 · 휠로 확대 · 우클릭 드래그로 이동. 두 점군을 정합 보정이나 융합 없이 함께 표시합니다. 촬영 위치는 기존 SfM 추정값이며, 표시 카메라를 움직여도 점군 좌표는 바뀌지 않습니다.</p>
    <div class="actions"><a id="download" class="action" hidden download>합쳐 표시한 점군 PLY ↓</a><span class="status pending">점군 융합 · GS 학습 NOT RUN</span></div>
    <div id="model-notes" class="note"></div>
  </section>
  <section class="section">
    <h2>다른 사진으로 옮겨 보면 어디가 어긋날까?</h2>
    <p>출발 사진의 픽셀을 추정 깊이로 3D에 놓고, 그 점이 도착 사진의 어디에 보이는지 찾습니다. 그 위치의 도착 사진 색을 출발 사진의 픽셀 자리에 가져와 비교합니다. 재투영·거리 차이·마스크는 모두 출발 ERP 격자에 표시하며, 도착 시점에서 새로 렌더링한 사진이 아닙니다. 검은 영역은 제외했거나 비교할 수 없는 곳입니다.</p>
    <div class="toolbar"><label>비교 방향 <select id="direction-select" disabled aria-label="재투영 방향 선택"></select></label></div>
    <div id="direction-metrics" class="metrics"></div><div id="direction-notes" class="note"></div>
    <div class="image-pair" style="margin-top:24px">
      <figure hidden><img id="direction-source" alt="재투영의 출발점인 관측 ERP 사진"><figcaption>출발 사진 · 실제 관측 RGB</figcaption></figure>
      <figure hidden><img id="direction-target" alt="재투영과 비교하는 다른 촬영 위치의 관측 ERP 사진"><figcaption>도착 사진 · 실제 관측 RGB</figcaption></figure>
      <figure hidden><img id="direction-depth" alt="출발 사진의 보정된 방사 깊이"><figcaption>보정된 방사 거리 · SfM 임의 단위</figcaption></figure>
      <figure hidden><img id="direction-warp" alt="도착 사진의 관측 색을 가져와 출발 ERP 격자에 표시한 역방향 워프"><figcaption>도착 사진 RGB를 출발 ERP 격자에 가져온 역방향 워프 · 검정은 제외·미지원 영역 · 생성 이미지 아님</figcaption></figure>
      <figure hidden><img id="direction-residual" alt="출발 ERP 격자에 표시한 두 시점의 방사 거리 불일치"><figcaption>출발 ERP 격자의 거리 불일치 · 정의와 색 범위는 방향별 기록 참조</figcaption></figure>
      <figure hidden><img id="direction-mask" alt="출발 ERP 격자에 표시한 재투영 비교 유효 영역과 제외 영역"><figcaption id="mask-caption">출발 ERP 격자의 겹침·가려짐 마스크 · 원본 전체에 대한 정확도 점수가 아님</figcaption></figure>
      <figure hidden><img id="direction-overlap" alt="같은 촬영 위치의 크롭들이 예측한 방사 거리의 로그 범위"><figcaption>같은 촬영 위치 · 크롭 간 log 거리 범위 · 초록은 낮은 불일치, 빨강은 기준 이상 · 검정은 비교 미지원 · 정확도나 가려짐 판정 아님</figcaption></figure>
    </div>
  </section>
  <section class="section" id="matching-evidence" hidden>
    <h2>실제 사진에서 찾은 대응점</h2>
    <details><summary>촬영 방향별 대응점 증거 펼쳐보기</summary><div class="image-pair" id="evidence-images"></div></details>
  </section>
  <section class="section">
    <h2>이 결과로 말할 수 있는 범위</h2>
    <div id="notes" class="note"></div><p id="next-step"></p>
    <p>두 깊이가 비슷하더라도 둘 다 같은 방식으로 틀렸을 수 있습니다. 보정에 쓰지 않은 SfM 점 역시 같은 사진들에서 추정한 내부 비교 자료입니다. 독립적인 실제 깊이 측정, 9장 융합, 새 Gaussian 학습은 이 보고서의 성공으로 간주하지 않습니다.</p>
  </section>
  <footer>Cicero101 / Mapillary via Wikimedia Commons · 출처와 CC BY-SA 4.0 링크는 각 원본 사진 아래 표시합니다.<br>
    기존 원본 사진, 카메라, 한 파노라마 결과와 스쿠터 GS는 보존했습니다.<br>
    <a id="doc-link" href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/PANORAMIC_PAIR_P1.md">실행 기록과 제한 사항 ↗</a> · <span id="completed"></span>
  </footer>
</main>`;

const select = document.querySelector<HTMLSelectElement>('#model-select')!;
const directionSelect = document.querySelector<HTMLSelectElement>('#direction-select')!;
const colorSelect = document.querySelector<HTMLSelectElement>('#color-mode')!;
const sourceSelect = document.querySelector<HTMLSelectElement>('#source-select')!;
const pointSize = document.querySelector<HTMLInputElement>('#point-size')!;
const cloudStatus = document.querySelector<HTMLElement>('#cloud-status')!;
let summary: Summary;
let cloud: Cloud | undefined;
let requestVersion = 0;
let activeView = 'overview';
let renderer: THREE.WebGLRenderer | undefined;
let geometry: THREE.BufferGeometry | undefined;
let material: THREE.PointsMaterial | undefined;
let camera: THREE.PerspectiveCamera | undefined;
let controls: OrbitControls | undefined;
let resize: ResizeObserver | undefined;
let points: THREE.Points | undefined;

function showMetrics(id: string, items: Metric[]) {
  document.querySelector(`#${id}`)!.replaceChildren(...items.map(item => {
    const element = document.createElement('div'); element.className = 'metric';
    const value = document.createElement('strong'); const label = document.createElement('span');
    value.textContent = typeof item.value === 'number' && Number.isFinite(item.value)
      ? `${item.value.toLocaleString('ko-KR', { maximumFractionDigits: item.precision ?? 3 })}${item.unit ?? ''}` : 'NOT RUN';
    label.textContent = item.label; element.append(value, label); return element;
  }));
}
function view(id = activeView) {
  if (!cloud || !camera || !controls) return;
  const target = id === 'overview' ? cloud.camera : cloud.captures.find(item => item.id === id);
  if (!target) return;
  activeView = id;
  camera.fov = target.fov ?? 65;
  camera.near = Math.max(cloud.radius / 10000, 1e-7); camera.far = cloud.radius * 100;
  camera.up.fromArray(target.up); camera.position.fromArray(target.position);
  controls.target.fromArray(target.target);
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
function colorCloud() {
  if (!cloud || !geometry) return;
  const colors = new Float32Array(cloud.colors.length); const color = new THREE.Color();
  for (let i = 0; i < colors.length; i += 3) {
    if (colorSelect.value === 'source') color.setHex(cloud.sourceIds[i / 3] === 0 ? 0x4fdfcf : 0xffa764);
    else color.setRGB(cloud.colors[i] / 255, cloud.colors[i + 1] / 255, cloud.colors[i + 2] / 255, THREE.SRGBColorSpace);
    colors.set([color.r, color.g, color.b], i);
  }
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
}
function showSources() {
  if (!cloud || !geometry) return;
  const ids = sourceSelect.value === 'both' ? null : cloud.sourceIds.flatMap((id, index) => id === Number(sourceSelect.value) ? [index] : []);
  geometry.setIndex(ids);
  const model = summary.models.find(item => item.id === select.value)!;
  const label = sourceSelect.value === 'both' ? '4·5번 두 출처, 융합 없음' : `${Number(sourceSelect.value) + 4}번 출처만`;
  cloudStatus.textContent = `${model.title} · ${(ids?.length ?? cloud.sourceIds.length).toLocaleString()}개 표시 점 · ${label} · SfM 임의 단위`;
}
function cloudButtons(enabled: boolean) {
  for (const id of ['capture-4', 'capture-5', 'overview-view', 'reset']) document.querySelector<HTMLButtonElement>(`#${id}`)!.disabled = !enabled;
  pointSize.disabled = !enabled; colorSelect.disabled = !enabled; sourceSelect.disabled = !enabled;
}
async function showCloud(model: Model, version: number) {
  cloudButtons(false); cloud = undefined;
  if (points) points.visible = false;
  if (!model.cloud) { cloudStatus.textContent = '점군 없음 · 실행 상태와 오류 기록을 확인하세요.'; return; }
  cloudStatus.textContent = '선택한 두 점군을 불러오는 중…';
  try {
    const response = await fetch(model.cloud); if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data: Cloud = await response.json();
    if (version !== requestVersion) return;
    if (!data.positions?.length || data.positions.length % 3 || data.colors?.length !== data.positions.length
      || !data.positions.every(Number.isFinite) || data.sourceIds?.length !== data.positions.length / 3
      || !data.sourceIds.every(value => value === 0 || value === 1)
      || !Number.isFinite(data.radius) || data.radius <= 0 || !data.camera
      || !data.captures?.some(item => item.id === '4') || !data.captures.some(item => item.id === '5')) {
      throw new Error('두 점군 또는 촬영 위치의 형식이 올바르지 않습니다.');
    }
    setupRenderer(); cloud = data;
    geometry!.setAttribute('position', new THREE.Float32BufferAttribute(data.positions, 3));
    colorCloud(); geometry!.computeBoundingSphere();
    material!.size = data.radius / 390 * Number(pointSize.value); points!.visible = true;
    view(); cloudButtons(true); showSources();
  } catch (error) {
    if (version === requestVersion) cloudStatus.textContent = `점군 불러오기 실패: ${String(error)}`;
  }
}
function showDirection() {
  const model = summary.models.find(item => item.id === select.value)!;
  const direction = model.directions.find(item => item.id === directionSelect.value);
  showMetrics('direction-metrics', direction?.metrics ?? []);
  document.querySelector('#direction-notes')!.textContent = direction?.notes.join(' ') ?? '방향별 진단 NOT RUN';
  for (const key of ['source', 'target', 'depth', 'warp', 'residual', 'mask', 'overlap'] as const) {
    const image = document.querySelector<HTMLImageElement>(`#direction-${key}`)!;
    const path = direction?.[key]; image.closest('figure')!.hidden = !path;
    if (path) image.src = path; else image.removeAttribute('src');
  }
}
async function showModel() {
  const model = summary.models.find(item => item.id === select.value)!;
  const version = ++requestVersion;
  const status = document.querySelector('#model-status')!;
  status.textContent = `실행 ${model.status} · 공간 일치 ${model.qualityStatus}`;
  status.classList.toggle('pending', model.qualityStatus !== 'PASS');
  document.querySelector('#model-meaning')!.textContent = model.meaning;
  document.querySelector('#model-notes')!.textContent = model.notes.join(' ');
  showMetrics('metrics', model.metrics);
  const previousDirection = directionSelect.value;
  directionSelect.replaceChildren(...model.directions.map(direction => new Option(direction.title, direction.id)));
  if (model.directions.some(direction => direction.id === previousDirection)) directionSelect.value = previousDirection;
  directionSelect.disabled = !model.directions.length; showDirection();
  const download = document.querySelector<HTMLAnchorElement>('#download')!;
  download.hidden = !model.ply; if (model.ply) download.href = model.ply; else download.removeAttribute('href');
  await showCloud(model, version);
}

select.addEventListener('change', () => void showModel());
directionSelect.addEventListener('change', showDirection);
colorSelect.addEventListener('change', colorCloud);
sourceSelect.addEventListener('change', showSources);
document.querySelector('#capture-4')!.addEventListener('click', () => view('4'));
document.querySelector('#capture-5')!.addEventListener('click', () => view('5'));
document.querySelector('#overview-view')!.addEventListener('click', () => view('overview'));
document.querySelector('#reset')!.addEventListener('click', () => view());
pointSize.addEventListener('input', () => { if (cloud && material) material.size = cloud.radius / 390 * Number(pointSize.value); });
window.addEventListener('pagehide', () => {
  requestVersion++; renderer?.setAnimationLoop(null); resize?.disconnect(); controls?.dispose();
  geometry?.dispose(); material?.dispose(); renderer?.dispose();
}, { once: true });

fetch('./summary.json').then(async response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  summary = await response.json();
  if (!summary.models?.length || summary.sources?.length !== 2) throw new Error('두 파노라마 실행 기록이 없습니다.');
  if (summary.heading) document.querySelector('#heading')!.textContent = summary.heading;
  if (summary.intro) document.querySelector('#intro')!.textContent = summary.intro;
  if (summary.maskCaption) document.querySelector('#mask-caption')!.textContent = summary.maskCaption;
  if (summary.docHref) document.querySelector<HTMLAnchorElement>('#doc-link')!.href = summary.docHref;
  if (summary.evidence?.length) {
    document.querySelector<HTMLElement>('#matching-evidence')!.hidden = false;
    document.querySelector('#evidence-images')!.replaceChildren(...summary.evidence.map(item => {
      const figure = document.createElement('figure'); const image = document.createElement('img');
      image.src = item.image; image.alt = item.title; image.loading = 'lazy';
      const caption = document.createElement('figcaption'); caption.textContent = `${item.title} · ${item.caption}`;
      figure.append(image, caption); return figure;
    }));
  }
  for (const model of summary.models) select.add(new Option(`${model.title} · ${model.status}`, model.id));
  select.value = summary.models.find(model => model.cloud)?.id ?? summary.models[0].id; select.disabled = false;
  document.querySelector('#execution-status')!.textContent = `로컬 실행 ${summary.status}`;
  document.querySelector('#quality-status')!.textContent = `공간 일치 ${summary.qualityStatus}`;
  document.querySelector('#conclusion')!.textContent = summary.conclusion;
  document.querySelector('#sources')!.replaceChildren(...summary.sources.map(source => {
    const figure = document.createElement('figure'); const image = document.createElement('img');
    image.src = source.image; image.alt = `${source.title} · 실제 촬영 ERP`;
    const caption = document.createElement('figcaption'); const link = document.createElement('a'); const license = document.createElement('a');
    link.href = source.sourceUrl; link.textContent = source.title; license.href = source.licenseUrl; license.textContent = 'CC BY-SA 4.0';
    caption.append(link, ' · ', license); figure.append(image, caption); return figure;
  }));
  document.querySelector('#notes')!.textContent = summary.notes.join(' ');
  document.querySelector('#next-step')!.textContent = summary.nextStep;
  document.querySelector('#completed')!.textContent = new Date(summary.completedAt).toLocaleString('ko-KR');
  await showModel();
}).catch(error => {
  document.querySelector('#execution-status')!.textContent = '기록 불러오기 실패';
  cloudStatus.textContent = `불러오기 실패: ${String(error)}`;
});
