import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './experiment.css';

type Cloud = { positions: number[]; colors: number[]; center: number[]; radius: number; camera: { position: number[]; up: number[]; fov: number } };
type Summary = { initialPoints: number; sfmPoints: number; objectSplats: number; exportSplats: number; steps: number; trainingSeconds: number; completedAt: string; images: {file: string;kind: string}[]; notes: string[]; sameTrainingImageBytes: boolean; sameCameraBytes: boolean };
const root = document.querySelector<HTMLDivElement>('#app')!;
root.innerHTML = `<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header><main><span class="eyebrow">No learned depth / experiment 07</span><h1>단안 깊이도 없이.<br>같은 실제 사진 9장.</h1><p>보간과 디퓨전이 없는 직전 실험에서, 이번에는 단안 깊이 모델과 깊이 점군 융합까지 뺐습니다. 사진들 사이에서 같은 특징을 찾아 삼각측량한 희소 점으로 GS 학습을 시작합니다.</p><div class="actions"><a class="action" href="/?world=/worlds/scooter-nodepth-object/world.json">깊이 없는 스쿠터 3D ↗</a><a class="action" href="/?world=/worlds/scooter-nodepth-context/world.json">전체 학습 장면 ↗</a><span class="status pending">먼저 공개 · 정량 품질 비교 대기</span></div><div id="metrics" class="metrics"></div><div class="steps"><span>같은 실제 사진 9장</span><span>→ 같은 카메라</span><span>→ SfM 희소 점</span><span>→ 같은 5,000단계 GS</span></div><section class="section"><h2>단안 깊이 사용 / 미사용</h2><p>직전 결과와 이번 결과를 같은 표시용 카메라에서 봅니다. 사진을 누르면 각 3D 장면을 회전할 수 있습니다.</p><div class="image-pair"><figure><a href="/?world=/worlds/scooter-real-object/world.json"><img src="/experiments/object-real/gs-preview.jpg" alt="직전 실제 9장과 단안 깊이를 사용한 GS"></a><figcaption>직전 · 단안 깊이 보정 → 초기 점 41,533개 → GS</figcaption></figure><figure><a href="/?world=/worlds/scooter-nodepth-object/world.json"><img src="gs-preview.jpg" alt="같은 실제 9장으로 단안 깊이 없이 학습한 GS"></a><figcaption>이번 · 사진 대응점의 삼각측량 → 희소 점 → GS</figcaption></figure></div><a href="/experiments/object-real/">직전 실험 과정 ↗</a></section><section class="section"><h2>그대로 사용한 실제 사진 9장</h2><p>학습 이미지 파일과 카메라 행렬은 직전 실행과 같습니다. 단안 깊이 지도는 이번 입력에 없습니다.</p><img class="contact" src="originals-contact.jpg" alt="스쿠터를 지나가며 촬영한 실제 사진 9장"><div class="toolbar"><input id="frame" class="scrub" type="range" min="0" max="8" value="4" aria-label="실제 사진 위치"><span id="frame-label" class="status"></span></div><figure><img id="rgb" class="contact" alt="이번 GS에 실제 들어간 원본 사진"><figcaption>학습에 사용한 실제 사진 · 생성 이미지 없음</figcaption></figure></section><section class="section"><h2>GS의 시작점</h2><p id="initialization"></p><div class="cloud" id="cloud"><span id="cloud-status" class="cloud-status">희소 점군을 불러오는 중…</span></div><div class="actions"><label>초기 점군 <select id="cloud-set"><option value="cloud.json">이번 · 사진 정합의 희소 점</option><option value="previous-cloud.json">직전 · 단안 깊이의 조밀한 점</option></select></label><button id="reset">시점 초기화</button><button id="rotate" aria-pressed="false">자동 회전</button><label>점 크기 <input id="point-size" type="range" min="1" max="8" value="3"></label></div></section><section class="section"><h2>학습한 장면 전체</h2><a href="/?world=/worlds/scooter-nodepth-context/world.json"><img class="contact" src="context-preview.jpg" alt="단안 깊이를 쓰지 않은 전체 GS 결과"></a><p id="training"></p><div id="notes" class="note"></div></section><footer>원본: Cicero101 / Mapillary via Wikimedia Commons · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>.<br>중간 이미지 생성·보간·단안 깊이 추론 없음. 사진 대응점 삼각측량과 Brush M2 Metal 학습.<br><a href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/OBJECT_NO_DEPTH.md">실행 기록과 제한 사항 ↗</a> · <span id="completed"></span></footer></main>`;
const frame = document.querySelector<HTMLInputElement>('#frame')!;
let summary: Summary;
function showFrame() {
  if (!summary) return;
  const index = Number(frame.value);
  document.querySelector<HTMLImageElement>('#rgb')!.src = summary.images[index].file;
  document.querySelector('#frame-label')!.textContent = `${index+1} / 9 · 실제 사진`;
}
frame.addEventListener('input', showFrame);
async function pointCloud() {
  const response = await fetch('./cloud.json'); if (!response.ok) throw new Error(`HTTP ${response.status}`);
  let cloud: Cloud = await response.json();
  const host = document.querySelector<HTMLDivElement>('#cloud')!;
  const renderer = new THREE.WebGLRenderer({antialias: true}); renderer.setPixelRatio(Math.min(devicePixelRatio,2)); renderer.setClearColor(0x080e15); host.append(renderer.domElement);
  const scene = new THREE.Scene(); const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position',new THREE.Float32BufferAttribute(cloud.positions,3));
  const rgb = new Float32Array(cloud.colors.length);
  const c = new THREE.Color(); for (let i=0;i<rgb.length;i+=3) { c.setRGB(cloud.colors[i]/255,cloud.colors[i+1]/255,cloud.colors[i+2]/255,THREE.SRGBColorSpace); rgb.set([c.r,c.g,c.b],i); }
  geometry.setAttribute('color',new THREE.BufferAttribute(rgb,3));
  const material = new THREE.PointsMaterial({size:cloud.radius/130,vertexColors:true}); scene.add(new THREE.Points(geometry,material));
  const camera = new THREE.PerspectiveCamera(cloud.camera.fov,1,cloud.radius/1000,cloud.radius*100); camera.up.fromArray(cloud.camera.up); camera.position.fromArray(cloud.camera.position);
  const controls = new OrbitControls(camera,renderer.domElement); controls.target.fromArray(cloud.center); controls.enableDamping=true; controls.autoRotateSpeed=.8; controls.update(); controls.saveState();
  const resize = new ResizeObserver(() => { renderer.setSize(host.clientWidth,host.clientHeight);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix(); }); resize.observe(host);
  document.querySelector('#cloud-status')!.textContent = `${(cloud.positions.length/3).toLocaleString()}개 점 · 드래그하여 회전`;
  document.querySelector('#reset')!.addEventListener('click',()=>controls.reset());
  document.querySelector('#rotate')!.addEventListener('click',event=>{controls.autoRotate=!controls.autoRotate;(event.target as HTMLElement).setAttribute('aria-pressed',String(controls.autoRotate));});
  document.querySelector('#point-size')!.addEventListener('input',event=>{material.size=cloud.radius/390*Number((event.target as HTMLInputElement).value);});
  document.querySelector('#cloud-set')!.addEventListener('change', async event => {
    const status = document.querySelector('#cloud-status')!; status.textContent = '점군을 바꾸는 중…';
    try {
      const result = await fetch('./'+(event.target as HTMLSelectElement).value);
      if (!result.ok) throw new Error(`HTTP ${result.status}`);
      cloud = await result.json();
      geometry.setAttribute('position',new THREE.Float32BufferAttribute(cloud.positions,3));
      const colors = new Float32Array(cloud.colors.length);
      for(let i=0;i<colors.length;i+=3){c.setRGB(cloud.colors[i]/255,cloud.colors[i+1]/255,cloud.colors[i+2]/255,THREE.SRGBColorSpace);colors.set([c.r,c.g,c.b],i);}
      geometry.setAttribute('color',new THREE.BufferAttribute(colors,3));geometry.computeBoundingSphere();
      camera.up.fromArray(cloud.camera.up);camera.position.fromArray(cloud.camera.position);controls.target.fromArray(cloud.center);controls.update();controls.saveState();material.size=cloud.radius/130;
      status.textContent=`${(cloud.positions.length/3).toLocaleString()}개 점 · 드래그하여 회전`;
    } catch(error) { status.textContent=String(error); }
  });
  renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
  window.addEventListener('pagehide',()=>{renderer.setAnimationLoop(null);resize.disconnect();controls.dispose();geometry.dispose();material.dispose();renderer.dispose();},{once:true});
}

fetch('./summary.json').then(async response => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  summary = await response.json();
  document.querySelector('#metrics')!.innerHTML = [['실제 사진',9],['단안 깊이 지도',0],['초기 SfM 점',summary.initialPoints],['물체 Gaussian',summary.objectSplats]].map(([label,value])=>`<div class="metric"><strong>${Number(value).toLocaleString()}</strong><span>${label}</span></div>`).join('');
  document.querySelector('#initialization')!.textContent = `사진 정합에서 얻은 ${summary.sfmPoints.toLocaleString()}개 점 중, 이전과 같은 물체 선택 영역에 들어가는 ${summary.initialPoints.toLocaleString()}개를 사용했습니다. 드래그로 회전하고 휠로 확대할 수 있습니다. 직전 점군은 표시용으로 일부 점만 보여줍니다.`;
  document.querySelector('#training')!.textContent = `Apple M2 Metal · ${summary.steps.toLocaleString()}단계 · ${summary.trainingSeconds.toFixed(1)}초. 전체 ${summary.exportSplats.toLocaleString()}개 Gaussian 중 물체 영역 ${summary.objectSplats.toLocaleString()}개를 표시합니다.`;
  document.querySelector('#notes')!.textContent = summary.notes.join(' ');
  document.querySelector('#completed')!.textContent = new Date(summary.completedAt).toLocaleString('ko-KR');
  showFrame(); return pointCloud();
}).catch(error=>{document.querySelector('#cloud-status')!.textContent=`불러오기 실패: ${error.message}`;});
