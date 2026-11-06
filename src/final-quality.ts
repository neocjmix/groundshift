import './experiment.css';
import './street-experiment.css';
import './final-quality.css';

type Stage={title:string;status:string;detail:string};
type Picture={title:string;highres:string;baseline?:string;caption:string};
type Run={status:string;splats?:number;bytes?:number;seconds?:number;sha256?:string;world?:string;preview?:string;quality:string};
type Comparison={title:string;image:string;caption:string};
type Summary={phase:string;updatedAt:string;title:string;summary:string;stages:Stage[];notes:string[];samples:Picture[];run?:Run;
  comparisons?:Comparison[];video?:string;metrics?:{label:string;baseline:number;candidate:number;unit?:string}[];
  sources:{title:string;url:string;licenseUrl:string}[]};

document.querySelector('#app')!.innerHTML=`
<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header>
<main><span class="eyebrow">Final quality attempt · same real street data · local M2</span>
<h1>같은 거리에서,<br>마지막 품질 실험.</h1>
<p>새 사진이나 새 깊이 모델을 추가하지 않습니다. 기존 DAV2 초기 점군과 카메라를 유지하고, 실제 사진 크롭을 512→1024px, Gaussian 상한을 40만→80만으로 올린 조합 하나를 실행합니다.</p>
<span id="status" class="status" role="status">실행 기록을 불러오는 중…</span>
<section class="section verdict"><span id="phase" class="eyebrow"></span><h2 id="title"></h2><p id="summary"></p>
<div class="actions"><a id="new-world" class="action" href="/" hidden>새 결과 3D 열기 ↗</a><a href="/?world=/worlds/street-dense/world.json">기존 DAV2 기준 3D ↗</a><a href="/experiments/model-selection/">앞선 모델 비교 ↗</a></div>
<p id="quality" class="note"></p><div id="run"></div></section>
<section class="section"><h2>작은 결과부터 먼저 공개합니다</h2><p>입력 사진, 학습 산출물, 실제 렌더와 측정을 준비되는 순서대로 배포합니다. 배포 성공과 장면 품질은 별개입니다. PASS는 표시된 단계만 통과했다는 뜻이고, 아직 실행하지 않은 검사는 NOT RUN입니다.</p><div id="stages"></div></section>
<section class="section"><h2>실제 원본에서 다시 뽑은 1024px 입력</h2><p>이전 512px 사진을 확대하지 않고, 보존된 실제 360° 사진에서 같은 카메라 방향으로 다시 잘랐습니다. 실제 촬영 위치는 8개, 학습 크롭은 96장입니다. 가운데 5번 사진 RGB는 학습에서 제외하고, 전체 9장으로 추정한 카메라 위치는 그대로 사용합니다.</p><div id="samples" class="street-comparisons"></div></section>
<section id="evidence-section" class="section" hidden><h2>실제로 렌더한 결과와 비교</h2><p>비교 이미지는 같은 위치·방향의 실제 GS 렌더입니다. 색 오차는 입체 형상 정확도와 다릅니다. 기존 결과와 같은 512px 검사 외에 1024px 검사도 별도로 표시합니다.</p><div id="comparisons" class="street-comparisons"></div><video id="motion" controls playsinline preload="metadata" hidden aria-label="기존 기준과 마지막 품질 실험의 실제 이동 렌더"></video><div class="street-table-wrap"><table id="metrics"><thead><tr><th>측정</th><th>기존 512/40만</th><th>새 1024/80만</th></tr></thead><tbody></tbody></table></div></section>
<section class="section"><h2>해석 범위와 다음 경계</h2><div id="notes" class="note"></div><ul id="sources"></ul><p>미터 단위의 실측 깊이, 독립 카메라 정답, 충돌 표면 또는 자유 보행 가능성을 확보한 실험이 아닙니다. 이 데이터에 대한 해상도·학습량·모델 조합 탐색은 이번 시도로 마칩니다.</p></section>
<footer><a href="./summary.json">공개 실행 기록 JSON</a> · <a href="./ATTRIBUTION.txt">출처와 변형 내역</a> · <a href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/FINAL_QUALITY.md">실행 방법 · 한계 · 종료 기준 ↗</a><p id="updated"></p></footer></main>`;

const put=(selector:string,value:string)=>{document.querySelector(selector)!.textContent=value;};
function picture(src:string,title:string){const f=document.createElement('figure'),img=document.createElement('img'),a=document.createElement('a'),c=document.createElement('figcaption');img.src=src;img.alt=title;img.loading='lazy';a.href=src;a.target='_blank';a.rel='noreferrer';a.title='원본 해상도로 열기';a.append(img);c.textContent=title+' · 원본 크기로 열기 ↗';img.addEventListener('error',()=>{c.textContent=title+' · 불러오기 FAIL';});f.append(a,c);return f;}
async function start(){
  const response=await fetch('./summary.json');if(!response.ok)throw new Error(`summary.json HTTP ${response.status}`);
  const s:Summary=await response.json();put('#status','공개 단계 · '+s.phase);put('#phase',s.phase);put('#title',s.title);put('#summary',s.summary);put('#updated','이 기록의 갱신 시각: '+s.updatedAt);
  for(const stage of s.stages){const row=document.createElement('div');row.className='street-stage';const tag=document.createElement('span');tag.className='status '+(stage.status==='PASS'?'':'pending');tag.textContent=stage.status;const title=document.createElement('strong');title.textContent=stage.title;const p=document.createElement('p');p.textContent=stage.detail;row.append(tag,title,p);document.querySelector('#stages')!.append(row);}
  for(const sample of s.samples){const f=picture(sample.highres,sample.title+' · 실제 1024px 입력'),p=document.createElement('p');p.textContent=sample.caption;f.append(p);document.querySelector('#samples')!.append(f);if(sample.baseline)document.querySelector('#samples')!.append(picture(sample.baseline,sample.title+' · 이전 512px 입력'));}
  if(s.run){put('#quality',s.run.quality);if(s.run.world){const a=document.querySelector<HTMLAnchorElement>('#new-world')!;a.href='/?world='+s.run.world;a.hidden=false;}if(s.run.preview)document.querySelector('#run')!.append(picture(s.run.preview,'새 GS 결과 · 실제 렌더 미리보기'));const p=document.createElement('p');p.textContent=`학습 ${s.run.status} · ${s.run.splats?.toLocaleString()??'NOT RUN'} Gaussians · ${s.run.seconds?.toFixed(3)??'NOT RUN'}초 · ${s.run.bytes===undefined?'NOT RUN':(s.run.bytes/1048576).toFixed(2)+'MiB'}`;document.querySelector('#run')!.append(p);}
  if(s.comparisons?.length||s.video||s.metrics?.length){document.querySelector<HTMLElement>('#evidence-section')!.hidden=false;for(const c of s.comparisons??[]){const f=picture(c.image,c.title),p=document.createElement('p');p.textContent=c.caption;f.append(p);document.querySelector('#comparisons')!.append(f);}if(s.video){const video=document.querySelector<HTMLVideoElement>('#motion')!;video.src=s.video;video.hidden=false;}for(const m of s.metrics??[]){const row=document.createElement('tr');for(const value of [m.label,m.baseline.toFixed(3)+(m.unit??''),m.candidate.toFixed(3)+(m.unit??'')]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}document.querySelector('#metrics tbody')!.append(row);}}
  for(const note of s.notes){const p=document.createElement('p');p.textContent=note;document.querySelector('#notes')!.append(p);}
  for(const source of s.sources){const li=document.createElement('li'),a=document.createElement('a'),license=document.createElement('a');a.href=source.url;a.textContent=source.title;license.href=source.licenseUrl;license.textContent=' · CC BY-SA4.0';li.append(a,license);document.querySelector('#sources')!.append(li);}
}
void start().catch((error:unknown)=>put('#status','불러오기 FAIL · '+String(error)));
