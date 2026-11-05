import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './experiment.css';

type Summary = { completedAt: string; realImages: number; generatedImages: number; registeredImages: number; points: number; splats: number; frames: {file: string;kind: string;depth: string;registered: boolean;depthFused: boolean}[]; generation: string; training: string; notes: string[] };
type Cloud = { positions: number[]; colors: number[]; center: number[]; radius: number; camera: { position: number[]; up: number[]; fov: number } };
const root = document.querySelector<HTMLDivElement>('#app')!;
root.innerHTML = `<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header><main><span class="eyebrow">Object focus / experiment 05</span><h1>한 대의 스쿠터를<br>앞에서 뒤까지.</h1><p>이동하며 찍은 9장 파노라마에서 같은 흰 스쿠터를 바라보는 이미지를 추출했습니다. 중간 이미지를 생성한 뒤, 각 이미지의 깊이를 이웃 시점과 맞춰 점군으로 합치고 Gaussian Splatting을 학습했습니다.</p><div class="actions"><a class="action" href="/?world=/worlds/scooter-object/world.json">스쿠터 3D 열기 ↗</a><a class="action" href="/?world=/worlds/scooter-context/world.json">학습 장면 전체 ↗</a><span class="status pending">먼저 공개 · 상세 품질 측정 대기</span></div><div class="metrics" id="metrics"></div><div class="steps"><span>9장 실제 크롭</span><span>→ 중간 이미지 보충</span><span>→ 이미지별 상대 깊이</span><span>→ 이웃 시점으로 보정</span><span>→ 점군 통합</span><span>→ GS 학습</span></div><section class="section"><h2>실제 사진에서 보이는 면</h2><p>첫 사진부터 마지막 사진까지 같은 대상입니다. 경로가 물체 한쪽을 지나가므로, 완전한 360° 촬영은 아닙니다.</p><img class="contact" src="originals-contact.jpg" alt="실제 파노라마 9장에서 추출한 흰 스쿠터의 앞, 옆, 뒤 모습"></section><section class="section"><h2>65장 입력과 각각의 깊이</h2><div class="toolbar"><button id="play">순서대로 보기</button><input class="scrub" id="frame" aria-label="입력 이미지 위치" type="range" min="0" max="64" value="32"><span class="status" id="frame-label"></span></div><div class="image-pair"><figure><img id="rgb" alt="선택한 학습 입력"><figcaption id="rgb-caption"></figcaption></figure><figure><img id="depth" alt="선택한 이미지의 단안 상대 깊이"><figcaption>단안 상대 깊이 · 밝을수록 가까운 예측 · 미터 단위 아님</figcaption></figure></div><p id="generation" class="muted"></p></section><section class="section"><h2>깊이를 합쳐 만든 포인트클라우드</h2><p>드래그로 회전하고 휠로 확대할 수 있습니다. 이 점들이 GS의 초기 위치가 됐습니다.</p><div class="cloud" id="cloud"><span class="cloud-status" id="cloud-status">점군을 불러오는 중…</span></div><div class="actions"><label>점군 입력 <select id="cloud-set"><option value="cloud.json">정합된 시점 · 원본 + 생성</option><option value="real-cloud.json">9장 · 원본만</option></select></label><button id="reset">시점 초기화</button><button id="rotate" aria-pressed="false">자동 회전</button><label>점 크기 <input id="point-size" type="range" min="1" max="8" value="3"></label></div></section><section class="section"><h2>실제 GS 렌더</h2><div class="image-pair"><figure><img src="gs-preview.jpg" alt="Mac에서 학습한 스쿠터 GS의 실제 브라우저 렌더"><figcaption>물체 영역을 남긴 GS · 클릭해서 자유롭게 회전해 보세요</figcaption></figure><figure><img src="context-preview.jpg" alt="동일 학습의 주변부를 포함한 GS 렌더"><figcaption>영역을 자르기 전 학습 결과</figcaption></figure></div><div class="actions"><a class="action" href="/?world=/worlds/scooter-object/world.json">스쿠터 3D 열기 ↗</a></div><p id="training"></p><div id="notes" class="note"></div></section><footer>원본: Cicero101 / Mapillary, Wikimedia Commons · <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>. 생성: RIFE 4.25 + Segmind Tiny-SD, CreativeML OpenRAIL-M. 깊이: Depth Anything V2 Small, Apache 2.0.<br><a href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/OBJECT_FOCUS_EXPERIMENT.md">실행 기록과 제한 사항 ↗</a> · <span id="completed"></span></footer></main>`;
const frame = document.querySelector<HTMLInputElement>('#frame')!;
let summary: Summary;
let timer: ReturnType<typeof setInterval> | undefined;
function showFrame() {
  if (!summary) return;
  const i = Number(frame.value); const record = summary.frames[i];
  document.querySelector<HTMLImageElement>('#rgb')!.src = record.file;
  document.querySelector<HTMLImageElement>('#depth')!.src = record.depth;
  document.querySelector('#frame-label')!.textContent = `${i+1} / ${summary.frames.length} · ${record.kind === 'observed' ? '실제 사진' : '생성 이미지'} · ${record.registered ? 'GS 입력' : '미정합·학습 제외'}${record.depthFused ? ' · 점군 사용' : ' · 점군 제외'}`;
  document.querySelector('#rgb-caption')!.textContent = record.kind === 'observed' ? '원본 파노라마에서 투영한 실제 크롭' : '이웃 원본 사이의 RIFE 초기 이미지에 전체 프레임 img2img 디퓨전 적용';
}
frame.addEventListener('input', showFrame);
document.querySelector('#play')!.addEventListener('click', event => {
  if (timer) { clearInterval(timer); timer = undefined; (event.target as HTMLButtonElement).textContent = '순서대로 보기'; }
  else { timer = setInterval(() => { frame.value = String((Number(frame.value)+1)%summary.frames.length); showFrame(); }, 350); (event.target as HTMLButtonElement).textContent = '멈추기'; }
});
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
  window.addEventListener('pagehide',()=>{renderer.setAnimationLoop(null);resize.disconnect();controls.dispose();geometry.dispose();material.dispose();renderer.dispose();if(timer)clearInterval(timer);},{once:true});
}
fetch('./summary.json').then(async response=>{if(!response.ok)throw new Error(`HTTP ${response.status}`);summary=await response.json();frame.max=String(summary.frames.length-1);document.querySelector('#metrics')!.innerHTML=[['실제 사진',summary.realImages],['생성 이미지',summary.generatedImages],['정합된 시점',summary.registeredImages],['초기 점군',summary.points.toLocaleString()],['물체 Gaussian',summary.splats.toLocaleString()]].map(([label,value])=>`<div class="metric"><strong>${value}</strong><span>${label}</span></div>`).join('');document.querySelector('#generation')!.textContent=summary.generation;document.querySelector('#training')!.textContent=summary.training;document.querySelector('#notes')!.textContent=summary.notes.join(' ');document.querySelector('#completed')!.textContent=new Date(summary.completedAt).toLocaleString('ko-KR');showFrame();return pointCloud();}).catch(error=>{document.querySelector('#cloud-status')!.textContent=`불러오기 실패: ${error.message}`;});
