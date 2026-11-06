import './experiment.css';
import './street-experiment.css';
import './final-quality.css';
import './tangent-background.css';

type Summary={updatedAt:string;summary:string;measurement:{source:{bytes:number;count:number;shDegree:number};output:{bytes:number;fractionalBits:number};conversionSeconds:number;maxRssBytes:number;gzipControl:{bytes:number};positions:{maxAbsoluteError:number}};
  conclusion?:string;checks?:{title:string;status:string;detail:string}[];comparisons?:{title:string;image:string;caption:string}[];video?:string;metrics?:{label:string;value:string}[]};
document.querySelector('#app')!.innerHTML=`<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header>
<main><span class="eyebrow">Storage experiment · same scene · no training</span><h1>보이는 세계는 유지하고,<br>파일은 작게.</h1>
<p>전방위 tangent20 장면을 그대로 사용합니다. 점을 지우거나 다시 학습하지 않고 PLY를 SPZ로 변환합니다. 수치 양자화에 의한 손실은 있으며, 용량 절감과 실제 화면의 차이를 구분해 관찰합니다.</p>
<section class="section verdict"><h2>동일 장면의 두 저장 형식</h2><p id="summary" role="status">결과를 불러오는 중…</p><div class="actions"><a class="action" href="/?world=/worlds/street-tangent20-spz/world.json">작은 SPZ 장면 열기 ↗</a><a href="/?world=/worlds/street-tangent20/world.json">보존한 원본 PLY 열기 ↗</a></div><p id="conclusion"></p><div class="street-table-wrap"><table><thead><tr><th>측정</th><th>실제 결과</th></tr></thead><tbody id="metrics"></tbody></table></div></section>
<section class="section"><h2>실행과 검증 상태</h2><div id="checks"></div></section>
<section class="section"><h2>같은 카메라의 실제 렌더</h2><p>화면 비교는 원본 PLY와 SPZ 사이의 차이입니다. 실제 거리의 형상 정확도를 검증하거나 개선한 실험은 아닙니다.</p><div id="comparisons" class="street-comparisons"></div><video id="motion" controls playsinline preload="metadata" hidden aria-label="PLY와 SPZ의 동일 경로 실제 이동 비교"></video></section>
<section class="section"><h2>어디까지 줄였나</h2><p>점 개수와 SH 차수, 카메라 및 좌표계 메타데이터는 유지합니다. 위치·크기·회전·색상·불투명도·방향별 색상 계수의 정밀도는 SPZ 형식에 따라 양자화됩니다. 바이트 단위 무손실은 아닙니다. 보존된 모든 점의 위치를 직접 비교하고 화면의 미세한 구조와 이동 중 변화를 별도로 확인합니다.</p><p>파일 절감이 같은 비율의 GPU 메모리 절감이나 FPS 향상을 뜻하지 않습니다. 공개 다운로드 측정과 로컬 렌더/디코딩 측정은 서로 다른 조건이며, 적은 횟수의 측정은 통계적인 성능 보장이 아닙니다. 새로운 데이터·깊이 예측·학습·배경 보완은 없습니다.</p></section>
<footer><a href="./summary.json">공개 측정 JSON</a> · <a href="./ATTRIBUTION.txt">출처와 변형</a> · <a href="https://github.com/nianticlabs/spz">SPZ 공식 문서</a> · <a href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/COMPRESSION.md">재현 방법</a><p id="updated"></p></footer></main>`;
const put=(id:string,text:string)=>{document.querySelector(id)!.textContent=text;};
async function start(){
  const response=await fetch('./summary.json');if(!response.ok)throw new Error(`HTTP ${response.status}`);
  const s:Summary=await response.json(),m=s.measurement;
  put('#summary',s.summary);put('#conclusion',s.conclusion??'파일 변환 PASS. 실제 브라우저 렌더와 비교 측정은 NOT RUN입니다.');put('#updated',s.updatedAt);
  const metrics=[{label:'원본 PLY',value:(m.source.bytes/1e6).toFixed(2)+' MB'}, {label:'PLY gzip 대조군',value:(m.gzipControl.bytes/1e6).toFixed(2)+' MB'},
    {label:'SPZ v3',value:(m.output.bytes/1e6).toFixed(2)+' MB'}, {label:'Gaussian / SH',value:m.source.count.toLocaleString()+' / SH'+m.source.shDegree},
    {label:'CPU/WASM 변환 시간',value:m.conversionSeconds.toFixed(3)+'초'}, {label:'최대 좌표 차이',value:m.positions.maxAbsoluteError.toExponential(3)+' (임의 SfM 단위)'},...(s.metrics??[])];
  for(const m of metrics){const row=document.createElement('tr');for(const text of [m.label,m.value]){const cell=document.createElement('td');cell.textContent=text;row.append(cell);}document.querySelector('#metrics')!.append(row);}
  const checks=s.checks??[{title:'SPZ 변환·구조·전체 위치 검사',status:'PASS',detail:'80만 점·SH1 유지. 좌표계와 카메라 메타데이터 유지.'},{title:'실제 렌더와 화질 비교',status:'NOT RUN',detail:'변환본을 먼저 공개하고 확인 중입니다.'}];
  for(const check of checks){const row=document.createElement('div');row.className='street-stage';const tag=document.createElement('span');tag.className='status';tag.textContent=check.status;const title=document.createElement('strong');title.textContent=check.title;const detail=document.createElement('p');detail.textContent=check.detail;row.append(tag,title,detail);document.querySelector('#checks')!.append(row);}
  for(const c of s.comparisons??[]){const f=document.createElement('figure'),a=document.createElement('a'),img=document.createElement('img'),caption=document.createElement('figcaption');a.href=c.image;a.target='_blank';a.rel='noreferrer';img.src=c.image;img.alt=c.title;img.loading='lazy';caption.textContent=c.title+' · '+c.caption;a.append(img);f.append(a,caption);document.querySelector('#comparisons')!.append(f);}
  if(s.video){const v=document.querySelector<HTMLVideoElement>('#motion')!;v.src=s.video;v.hidden=false;}
}
void start().catch(e=>put('#summary','불러오기 FAIL · '+String(e)));
