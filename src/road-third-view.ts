import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './experiment.css';
import './road-third-view.css';

type Stats = { median: number | null; p90: number | null };
type Result = { total: number; valid: number; invalid: number; angularResidualDegrees: Stats; absoluteRelativeRangeDifference: Stats };
type Summary = {
  heading: string; conclusion: string; status: string; qualityStatus: string; completedAt: string;
  sources: { id: string; image: string; title: string; sourceUrl: string; licenseUrl: string }[];
  stereo: { totalTracks: number; supportedTracks: number; unsupportedTracks: number; supportFraction: number;
    stableTracks: number; angularResidualDegrees: Stats; absoluteRelativeRangeDifference: Stats;
    elapsedSeconds: number; maxResidentSetBytes: number; diagnosticGate: string };
  evaluation: { results: Record<string, Record<string, Result>> }; notes: string[]; nextStep: string;
};
type Cloud = { positions: number[]; colors: number[]; kinds: number[]; common: boolean[]; up: [number, number, number] };

document.querySelector('#app')!.innerHTML = `
<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header>
<main><span class="eyebrow">Panoramic street reconstruction · third observed view</span>
<h1 id="heading">세 번째 실제 사진 확인</h1>
<p>4·5번에서 찾은 도로 점을 그대로 보존하고, 실제5·6번 사진에서 별도로 찾은 점과 비교했습니다. 새로운 사진 생성이나 깊이 추론은 없습니다.</p>
<div class="actions"><span id="execution-status" class="status" role="status">실행 기록을 불러오는 중…</span><span id="quality-status" class="status pending"></span></div>
<p id="conclusion" class="note"></p><div id="metrics" class="metrics"></div>
<section class="section"><h2>원본에서 가져온 실제 사진3장</h2><div class="image-pair" id="sources"></div>
<p>사진6은 이전 도로 보정에 쓰지 않았습니다. 카메라 자세는9장 전체로 추정했으므로 독립적인 깊이 정답은 아닙니다.</p></section>
<section class="section"><h2>두 번의 삼각측량을 같은 좌표에서 보기</h2>
<p>청록=기존4·5번의291개 점, 주황=새5·6번에서 다시 찾은44개 점. 처음에는 공통44개씩을 확대해 봅니다. 전체 범위를 선택하면 멀리 떨어진 기존 후보도 포함합니다. 얇은 도로 일부의 희소점이며, 새 GS나 조밀 거리 장면이 아닙니다. 위치 수정이나 융합은 없습니다.</p>
<div class="toolbar"><label>표시 범위 <select id="cloud-selection" disabled><option value="common">양쪽에서 확인된44개씩</option><option value="all">기존 전체 + 다시 찾은 점</option><option value="previous">기존4·5번만</option><option value="third">새5·6번만</option></select></label>
<label>표시 색 <select id="cloud-color" disabled><option value="pair">사진 쌍별 색</option><option value="rgb">5번 실제 사진 색</option></select></label><button id="cloud-reset" disabled>전체 보기 초기화</button></div>
<div id="cloud" class="cloud"><span id="cloud-status" class="cloud-status" role="status">점군을 불러오는 중…</span></div>
<p>드래그 회전 · 휠 확대 · 우클릭 이동. 초기 시점은 점들을 보기 위한 표시용 카메라입니다. SfM 임의 단위이며 미터가 아닙니다.</p>
<div class="actions"><a href="./previous45.ply" download>기존291점 PLY ↓</a><a href="./observed56.ply" download>새44점 PLY ↓</a><a href="/experiments/stereo-anchors/">이전 조밀 점군·보정 대조군5개 ↗</a></div></section>
<section class="section"><h2>깊이 보정은 세 번째 사진에도 도움이 됐을까?</h2>
<p>동일한5번 광선의 기존 깊이와 새 보정을,5·6번 스테레오 거리와 비교합니다. 비교 대상44개 중 무효5개는 숨기지 않습니다. 무효를 뺀 수치는39개에서만 계산합니다.</p>
<label>검사 집합 <select id="subset"><option value="all">다시 확인한 전체44개</option><option value="previous-held">이전 보정에서 제외했던6개</option><option value="previous-training">이전 보정에 사용한38개</option></select></label>
<div style="overflow-x:auto"><table id="comparison"><thead><tr><th>보정 방식</th><th>전체</th><th>유효</th><th>무효</th><th>6번 위치 차이 중앙값</th><th>거리 차이 중앙값</th><th>거리 차이 P90</th></tr></thead><tbody></tbody></table></div>
<p>위치 차이는6번 카메라에서 본 두 추정의 광선 각도입니다. 거리 차이는5번 중심에서의 |기존 또는 보정 거리 −5·6번 거리| /5·6번 거리입니다. 작은 지역의 일치도이며 실제 정확도나 거리 전체 개선을 뜻하지 않습니다.</p></section>
<section class="section"><h2>세 번째 실제 사진 위의 확인 범위</h2>
<figure><img id="third-overlay" src="./third-overlay.jpg" alt="6번 실제 사진에 이전 도로 점을 투영하고 새 매칭과 비교한 증거"><figcaption>초록=매칭되고 위치1°·거리5% 이내, 빨강=매칭되지만 참고값 초과, 노랑=매칭 미지원. 선은 이전 점의 투영과 새 매칭을 잇습니다. 이 색은 실측 정확도나 가려짐 판정이 아닙니다.</figcaption></figure>
<details id="examples"><summary>성공 여부로 고르지 않은24개 실제 사진 패치</summary><figure><img loading="lazy" src="./track-examples.jpg" alt="291개에서 균등 간격으로 고른24개 점의4·5·6번 실제 사진 패치"><figcaption>왼쪽4번 · 가운데5번 · 오른쪽6번의 기존 점 예상 위치. 흰 십자는 그 위치이며, 미지원 사례도 포함합니다. 각 패치는 원본의352×224픽셀 범위를176×112로 줄인 실제 RGB입니다.</figcaption></figure></details></section>
<section class="section"><h2>해석의 한계와 다음 단계</h2><div id="notes" class="note"></div><p id="next-step"></p>
<p>국소 재확인 참고값 통과는 P2 거리 정합 승인과 다릅니다. 도로 전체·벽면·먼 물체 검사는 남아 있으며, 점군 융합과 Gaussian 학습은 NOT RUN입니다.</p></section>
<footer>Cicero101 / Mapillary via Wikimedia Commons · CC BY-SA4.0 · 모든 이전 결과 보존<br>
<a href="./summary.json">측정 기록 JSON</a> · <a href="./track-diagnostics.json">전체291개 지원·실패 기록</a> · <a href="./ATTRIBUTION.txt">출처</a> · <a href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/ROAD_THIRD_VIEW.md">실행 방법과 한계 ↗</a><p id="completed"></p></footer></main>`;

const number = (value: number | null, factor = 1, suffix = '') => value === null ? 'NOT RUN' : `${(value*factor).toLocaleString('ko-KR', { maximumFractionDigits: 3 })}${suffix}`;
async function json<T>(url: string): Promise<T> {
  const response = await fetch(url); if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.json() as Promise<T>;
}
function metric(label: string, value: string) {
  const div = document.createElement('div'); div.className = 'metric';
  const strong = document.createElement('strong'); strong.textContent = value;
  const span = document.createElement('span'); span.textContent = label; div.append(strong, span); return div;
}

async function start() {
  const summary = await json<Summary>('./summary.json');
  document.querySelector('#heading')!.textContent = summary.heading;
  document.querySelector('#execution-status')!.textContent = `로컬 CPU 실행 ${summary.status}`;
  document.querySelector('#quality-status')!.textContent = `거리 전체 품질 ${summary.qualityStatus}`;
  document.querySelector('#conclusion')!.textContent = summary.conclusion;
  const s = summary.stereo;
  document.querySelector('#metrics')!.replaceChildren(
    metric('이전 도로 후보 전체', number(s.totalTracks)), metric('새 사진에서 지원', `${s.supportedTracks} / ${s.totalTracks}`),
    metric('판단하지 못한 점', number(s.unsupportedTracks)), metric('지원 비율', number(s.supportFraction,100,'%')),
    metric('지원점의6번 위치 차이 중앙값', number(s.angularResidualDegrees.median,1,'°')),
    metric('지원점의 거리 차이 중앙값',number(s.absoluteRelativeRangeDifference.median,100,'%')),
    metric('실제 스테레오·출력 시간',number(s.elapsedSeconds,1,'초')),metric('프로세스 최대 RSS',number(s.maxResidentSetBytes/1024**2,1,'MiB')));
  for (const item of summary.sources) {
    const figure = document.createElement('figure'); const img = document.createElement('img');
    img.src = item.image; img.alt = item.title;
    const caption = document.createElement('figcaption'); caption.textContent = `${item.title} · Cicero101 / Mapillary `;
    const a = document.createElement('a'); a.href = item.sourceUrl; a.textContent = '원본 출처';
    const license = document.createElement('a'); license.href = item.licenseUrl; license.textContent = ' · CC BY-SA4.0';
    caption.append(a,license); figure.append(img,caption); document.querySelector('#sources')!.append(figure);
  }
  const subset = document.querySelector<HTMLSelectElement>('#subset')!;
  function table() {
    const body = document.querySelector('#comparison tbody')!; body.replaceChildren();
    for (const [id,title] of [['baseline','기존 보정 유지'],['augmented','기존 + 새 도로 근거'],['new-only','새 근거만 · 먼 영역 악화 이력']]) {
      const r = summary.evaluation.results[id][subset.value]; const tr = document.createElement('tr'); tr.dataset.variant = id;
      for (const value of [title,String(r.total),String(r.valid),String(r.invalid),number(r.angularResidualDegrees.median,1,'°'),number(r.absoluteRelativeRangeDifference.median,100,'%'),number(r.absoluteRelativeRangeDifference.p90,100,'%')]) {
        const td = document.createElement('td'); td.textContent = value; tr.append(td);
      }
      body.append(tr);
    }
  }
  subset.addEventListener('change',table); table();
  for (const note of summary.notes) { const p = document.createElement('p'); p.textContent = note; document.querySelector('#notes')!.append(p); }
  document.querySelector('#next-step')!.textContent = summary.nextStep;
  document.querySelector('#completed')!.textContent = summary.completedAt;
  await showCloud(await json<Cloud>('./cloud.json'));
}

async function showCloud(data: Cloud) {
  const element = document.querySelector<HTMLElement>('#cloud')!;
  const status = document.querySelector<HTMLElement>('#cloud-status')!;
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#090e16');
  const camera = new THREE.PerspectiveCamera(55,1,.001,1000); camera.up.fromArray(data.up);
  const renderer = new THREE.WebGLRenderer({ antialias:true, preserveDrawingBuffer:true }); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); element.append(renderer.domElement);
  const geometry = new THREE.BufferGeometry(); const material = new THREE.PointsMaterial({ size:6, sizeAttenuation:false, vertexColors:true });
  const points = new THREE.Points(geometry,material); scene.add(points);
  const sphere = new THREE.Sphere();
  const controls = new OrbitControls(camera,renderer.domElement); controls.target.copy(sphere.center);
  const reset = () => {camera.position.copy(sphere.center).add(new THREE.Vector3(-1,-1,1).normalize().multiplyScalar(Math.max(sphere.radius,.1)*2.8)); controls.target.copy(sphere.center); controls.update();};
  const selection = document.querySelector<HTMLSelectElement>('#cloud-selection')!;
  const color = document.querySelector<HTMLSelectElement>('#cloud-color')!;
  function update() {
    const xyz:number[] = []; const rgb:number[] = []; let old = 0; let next = 0;
    for (let i=0;i<data.kinds.length;i++) {
      const kind = data.kinds[i];
      if ((selection.value==='common' && !data.common[i]) || (selection.value==='previous' && kind!==0) || (selection.value==='third' && kind!==1)) continue;
      xyz.push(...data.positions.slice(i*3,i*3+3));
      const c = color.value==='rgb' ? new THREE.Color().setRGB(...data.colors.slice(i*3,i*3+3).map(v=>v/255) as [number,number,number],THREE.SRGBColorSpace) : new THREE.Color(kind===0 ? '#28efb0' : '#ff943e');
      rgb.push(c.r,c.g,c.b); if (kind===0) old++; else next++;
    }
    geometry.setAttribute('position',new THREE.Float32BufferAttribute(xyz,3));geometry.setAttribute('color',new THREE.Float32BufferAttribute(rgb,3));geometry.computeBoundingSphere();
    sphere.copy(geometry.boundingSphere!);
    status.textContent = `표시 PASS · 기존 ${old}점 + 새 ${next}점 · 정합·융합 없음`;
  }
  selection.disabled = false; color.disabled = false;
  const resetButton = document.querySelector<HTMLButtonElement>('#cloud-reset')!; resetButton.disabled = false;
  selection.addEventListener('change',()=>{update();reset();});color.addEventListener('change',update);resetButton.addEventListener('click',reset);
  const resize = new ResizeObserver(() => { const width=element.clientWidth,height=element.clientHeight;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix(); }); resize.observe(element);
  update();reset();renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
  window.addEventListener('pagehide',()=>{renderer.setAnimationLoop(null);resize.disconnect();controls.dispose();geometry.dispose();material.dispose();renderer.dispose();},{once:true});
}

void start().catch((error:unknown) => {
  document.querySelector('#execution-status')!.textContent = `불러오기 FAIL · ${String(error)}`;
  document.querySelector('#cloud-status')!.textContent = '표시 FAIL · 실행 기록 또는 점군을 불러오지 못했습니다.';
});
