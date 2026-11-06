import './experiment.css';
import './street-experiment.css';

type Metric = {pixelCount:number;mae?:number;psnrDb?:number;opacityCoverage95?:number};
type Model = {id:string;title:string;meaning:string;status:string;quality:string;world:string;preview:string;video:string;init:string;
  points:number;splats:number;bytes:number;steps:number;trainingSeconds:number;maxResidentSetBytes:number;peakMemoryFootprintBytes?:number;heldLevelMaeMean:number;heldLevelCoverage95Mean:number};
type View = {id:string;title:string;kind:string;source?:string};
type Summary = {status:string;completedAt:string;best:string;verdict:{state:string;title:string;summary:string;works:string[];limits:string[];recommendation:string};
  models:Model[];views:View[];metrics:{model:string;view:string;regions:Record<string,Metric>}[];
  stages:{title:string;status:string;detail:string}[];depthEvidence:{title:string;image:string;caption:string}[];notes:string[];
  sources:{title:string;url:string;licenseUrl:string}[];comparisonVideo:string;repair?:string};

document.querySelector('#app')!.innerHTML=`
<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header>
<main><span class="eyebrow">Panoramic street reconstruction · end-to-end conclusion</span>
<h1>스쿠터 한 대에서,<br>짧은 거리 전체로.</h1>
<p>실제 360° 사진 9장의 카메라를 유지하고, 8개 촬영 위치에서 뽑은 96장으로 거리 GS를 학습했습니다. 가운데 5번 사진은 학습과 조밀 점군 색 입력에서 제외해 비교에 사용했습니다. 중간 이미지 생성과 디퓨전은 없습니다.</p>
<span id="status" class="status" role="status">실행 기록을 불러오는 중…</span>
<section class="section verdict"><span id="verdict-state" class="eyebrow"></span><h2 id="verdict-title"></h2><p id="verdict-summary"></p>
<div class="actions"><a id="best-world" class="action" href="/">추천 장면 3D 열기 ↗</a><a id="best-video" href="/">추천 장면 이동 영상 ↗</a></div>
<div class="street-columns"><div><h3>이번에 확인한 것</h3><ul id="works"></ul></div><div><h3>아직 안 된 것</h3><ul id="limits"></ul></div></div><p id="recommendation" class="note"></p>
</section>
<section class="section"><h2>같은 길을 이동하며 비교</h2>
<p>모든 칸은 동일한 카메라 위치와 방향입니다. 기존 촬영 위치 사이를 보간해 실제 GS를 렌더했습니다. 원본 영상이나 생성형 영상이 아닙니다. 아래 재생 속도는 렌더링 성능 수치가 아닙니다.</p>
<video id="comparison-video" controls playsinline preload="metadata" aria-label="동일 카메라 경로의 모든 거리 GS 비교"></video>
<p id="video-label" class="muted"></p></section>
<section class="section"><h2>3D를 직접 보기</h2><div id="scene-cards" class="street-cards"></div>
<div class="toolbar"><label>장면 선택 <select id="scene-select" disabled></select></label><button id="open-scene" disabled>선택한 3D 여기서 열기</button><a id="scene-link" href="/">큰 화면으로 열기 ↗</a></div>
<p>3D 화면의 Camera path로 촬영 경로를 이동하고, 자유롭게 둘러볼 수 있습니다. 경로는 추정 카메라 사이의 이동이며, 걸어도 되는 바닥이나 충돌을 복원한 것이 아닙니다.</p>
<div id="viewer-host"></div></section>
<section class="section"><h2>학습에서 뺀 실제 사진과 비교</h2><p>같은 위치·같은 방향에서 원본과 GS를 나란히 봅니다. 회색 부분은 렌더된 불투명도가 부족한 곳을 포함합니다. 색 오차는 비교 가능한 모든 선택 픽셀에 계산해 구멍도 분모에 남겼습니다.</p>
<div class="toolbar"><label>비교 시점 <select id="view-select" disabled></select></label><label>측정 영역 <select id="region-select"><option value="band">전체 검사 대역</option><option value="road-band">아래쪽 도로 대역</option><option value="mid-height-band">중간 높이 · 벽·나무 포함</option></select></label></div>
<p id="view-kind" class="note"></p><div id="compare-images" class="street-comparisons"></div>
<p class="muted">색 차이는 0–255 단위이며 작을수록 원본에 가깝습니다. 표시된 채움 비율은 alpha≥.95의 픽셀 비율이며, 실제 형상 정확도나 가려짐 정답이 아닙니다.</p>
<div class="street-table-wrap"><table id="view-metrics"><thead><tr><th>장면</th><th>검사 픽셀</th><th>색 차이</th><th>PSNR</th><th>불투명도 기준 채움</th></tr></thead><tbody></tbody></table></div></section>
<section class="section"><h2>실제로 실행한 비교군</h2><p>사진·카메라·마스크·시드·학습 설정을 맞추고 초기 점군을 바꿨습니다. 초기 점 개수도 달라지는 비교이므로, 깊이 모델의 정확도만을 분리해 증명하는 실험은 아닙니다.</p>
<div class="street-table-wrap"><table id="run-metrics"><thead><tr><th>장면</th><th>초기 점</th><th>최종 Gaussian</th><th>학습 단계</th><th>실제 학습 시간</th><th>장면 파일</th><th>최대 프로세스 footprint</th><th>학습에서 뺀 사진 5 색 차이</th></tr></thead><tbody></tbody></table></div>
<p class="muted">footprint는 macOS가 해당 프로세스에 기록한 값입니다. 시스템 전체나 GPU 전체 메모리의 최대 사용량을 뜻하지 않습니다.</p>
<p id="repair-note" class="note" hidden></p></section>
<section class="section"><h2>사진 → 깊이 → 초기 점군 → GS</h2><p>각 사진의 상대 깊이를 특징점·스테레오 근거에 맞춰 보정한 뒤 같은 좌표에 놓았습니다. 미터 단위의 실측 깊이가 아닙니다. 필터는 다른 촬영 위치의 깊이·색과 비슷한 점을 남기는 휴리스틱입니다.</p><div id="depth-evidence" class="image-pair"></div>
<p>각 장면 카드의 초기 점군 PLY는 실제 학습에 쓴 파일입니다. 원본 전체 해상도 사진·원시 깊이 배열·가중치·원시 로그는 Mac에 보존합니다.</p></section>
<section class="section"><h2>성공·실패·실행하지 않은 단계</h2><div id="stages"></div></section>
<section class="section"><h2>해석 범위와 출처</h2><div id="notes" class="note"></div><ul id="sources"></ul>
<p>사진5는 GS 학습에서 제외했지만, 카메라와 희소 형상은9장 전체로 추정했습니다. 독립적으로 측정한 실제 깊이·카메라 정답은 없습니다.</p></section>
<footer><a href="./summary.json">공개 측정 기록 JSON</a> · <a href="./ATTRIBUTION.txt">출처와 변형 내역</a> · <a href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/STREET_CONCLUSION.md">재현 명령·실행 기록·결론 ↗</a> · <a href="/experiments/road-third-view/">직전 국소 검사</a><p id="completed"></p></footer></main>`;

const text=(selector:string,value:string)=>{document.querySelector(selector)!.textContent=value;};
const value=(n:number|undefined,unit='')=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString('ko-KR',{maximumFractionDigits:2})+unit:'NOT RUN';
function cells(body:Element,values:string[]){const row=document.createElement('tr');for(const v of values){const cell=document.createElement('td');cell.textContent=v;row.append(cell);}body.append(row);}
function figure(src:string,title:string,lazy=false){const f=document.createElement('figure'),img=document.createElement('img'),caption=document.createElement('figcaption');img.src=src;img.alt=title;if(lazy)img.loading='lazy';caption.textContent=title;f.append(img,caption);img.addEventListener('error',()=>{caption.textContent=title+' · 이미지 불러오기 FAIL';});return f;}

async function start(){
  const response=await fetch('./summary.json');if(!response.ok)throw new Error(`summary.json HTTP ${response.status}`);
  const s:Summary=await response.json();text('#status',`실제 학습·렌더 ${s.status} · 실측 형상 검증 NOT RUN`);
  text('#verdict-state',s.verdict.state);text('#verdict-title',s.verdict.title);text('#verdict-summary',s.verdict.summary);text('#recommendation',s.verdict.recommendation);
  for(const [id,items]of [['#works',s.verdict.works],['#limits',s.verdict.limits]] as const)for(const item of items){const li=document.createElement('li');li.textContent=item;document.querySelector(id)!.append(li);}
  const video=document.querySelector<HTMLVideoElement>('#comparison-video')!;video.src=s.comparisonVideo;
  text('#video-label','칸 순서: '+s.models.map(m=>`${m.id.toUpperCase()} = ${m.title}`).join(' / '));
  const select=document.querySelector<HTMLSelectElement>('#scene-select')!;select.disabled=false;
  for(const m of s.models){
    const option=document.createElement('option');option.value=m.id;option.textContent=m.title;select.append(option);
    const card=document.createElement('article');card.className='street-card';card.dataset.model=m.id;
    const link=document.createElement('a');link.href='/?world='+m.world;link.append(figure(m.preview,m.title,true));
    const meaning=document.createElement('p');meaning.textContent=m.meaning;
    const status=document.createElement('span');status.className='status';status.textContent=`${m.id===s.best?'추천 · ':''}학습 ${m.status} · ${m.quality}`;
    const actions=document.createElement('div');actions.className='actions';
    for(const [href,label]of [['/?world='+m.world,'3D 열기 ↗'],[m.video,'이 장면 이동 영상 ↗'],[m.init,'초기 점군 PLY ↓']]){const a=document.createElement('a');a.href=href;a.textContent=label;actions.append(a);}
    card.append(link,meaning,status,actions);document.querySelector('#scene-cards')!.append(card);
    cells(document.querySelector('#run-metrics tbody')!,[m.title,value(m.points),value(m.splats),value(m.steps),value(m.trainingSeconds,'초'),value(m.bytes/1048576,'MiB'),value(m.peakMemoryFootprintBytes===undefined?undefined:m.peakMemoryFootprintBytes/1073741824,'GiB'),value(m.heldLevelMaeMean)]);
  }
  select.value=s.best;const sceneLink=document.querySelector<HTMLAnchorElement>('#scene-link')!,open=document.querySelector<HTMLButtonElement>('#open-scene')!;open.disabled=false;
  const best=s.models.find(m=>m.id===s.best)!;document.querySelector<HTMLAnchorElement>('#best-world')!.href='/?world='+best.world;document.querySelector<HTMLAnchorElement>('#best-video')!.href=best.video;
  function setLink(){sceneLink.href='/?world='+s.models.find(m=>m.id===select.value)!.world;}
  select.addEventListener('change',setLink);setLink();
  open.addEventListener('click',()=>{const host=document.querySelector('#viewer-host')!,iframe=document.createElement('iframe');iframe.title=select.selectedOptions[0].textContent??'거리 GS';iframe.src=sceneLink.href;iframe.allow='fullscreen';host.replaceChildren(iframe);});
  const views=document.querySelector<HTMLSelectElement>('#view-select')!,region=document.querySelector<HTMLSelectElement>('#region-select')!;views.disabled=false;
  for(const v of s.views){const option=document.createElement('option');option.value=v.id;option.textContent=v.title;views.append(option);}
  views.value=s.views.find(v=>v.kind==='held'&&v.id.endsWith('level-300'))?.id??s.views[0].id;
  function comparison(){
    const v=s.views.find(v=>v.id===views.value)!,images=document.querySelector('#compare-images')!,body=document.querySelector('#view-metrics tbody')!;images.replaceChildren();body.replaceChildren();
    text('#view-kind',v.kind==='held'?'사진5 · GS 최적화와 조밀 초기 색에서 제외한 실제 사진과 비교합니다. 카메라·희소 형상 추정에는 참여했습니다.':v.kind==='offpath'?'경로 옆으로 일부러 옮긴 표시용 카메라입니다. 이 위치의 원본 사진이 없어 색 오차 검사는 NOT RUN입니다.':'GS 학습에 사용한 위치입니다. 학습 사진에 맞는 정도이며 새 시점 품질을 보장하지 않습니다.');
    if(v.source)images.append(figure(v.source,'실제 원본 크롭 · '+v.title));
    for(const m of s.models){images.append(figure(`./renders/${m.id}/${v.id}.png`,m.title+' · 실제 GS 렌더'));
      const r=s.metrics.find(r=>r.model===m.id&&r.view===v.id)?.regions[region.value];
      cells(body,[m.title,value(r?.pixelCount),value(r?.mae),value(r?.psnrDb,'dB'),typeof r?.opacityCoverage95==='number'?value(r.opacityCoverage95*100,'%'):'NOT RUN']);}
  }
  views.addEventListener('change',comparison);region.addEventListener('change',comparison);comparison();
  if(s.repair){const p=document.querySelector<HTMLElement>('#repair-note')!;p.hidden=false;p.textContent=s.repair;}
  for(const d of s.depthEvidence){const f=figure(d.image,d.title,true);const p=document.createElement('p');p.textContent=d.caption;f.append(p);document.querySelector('#depth-evidence')!.append(f);}
  for(const stage of s.stages){const div=document.createElement('div');div.className='street-stage';const status=document.createElement('span');status.className='status '+(stage.status==='PASS'?'':'pending');status.textContent=stage.status;const title=document.createElement('strong');title.textContent=stage.title;const p=document.createElement('p');p.textContent=stage.detail;div.append(status,title,p);document.querySelector('#stages')!.append(div);}
  for(const note of s.notes){const p=document.createElement('p');p.textContent=note;document.querySelector('#notes')!.append(p);}
  for(const source of s.sources){const li=document.createElement('li'),a=document.createElement('a'),license=document.createElement('a');a.href=source.url;a.textContent=source.title;license.href=source.licenseUrl;license.textContent=' · CC BY-SA4.0';li.append(a,license);document.querySelector('#sources')!.append(li);}
  text('#completed',s.completedAt);
}
void start().catch((error:unknown)=>text('#status',`불러오기 FAIL · ${String(error)}`));
