import './experiment.css';
import './street-experiment.css';
import './tourist-streaming.css';

type Stage={title:string;status:string;detail:string};
type Preview={rank:number;image:string;title:string;caption:string;metadataUrl:string};
type Candidate={name:string;decision:string;count:number;lengthMeters?:number;medianSpacingMeters?:number;dimensions?:string;detail:string;source:string};
type Summary={updatedAt:string;title:string;summary:string;route:string;previews:Preview[];candidates:Candidate[];stages:Stage[];nextSteps:string[];limits:string[];acquisition?:{status:string;count:number;bytes:number;seconds:number};result?:{worldPath:string;poster:string;detail:string}};
type Route={images:{id:string;rank:number;gps:number[];distanceMeters:number}[];statistics:{count:number;lengthMeters:number;medianSpacingMeters:number;maximumSpacingMeters:number}};
document.querySelector('#app')!.innerHTML=`<header><a href="/">GROUND SHIFT</a><a href="/experiments/lab/">← 시간순 실험실</a></header><main>
<span class="eyebrow">New source scouting · Paris · NOT a Gaussian render</span><h1>다음 거리로,<br>파리의 센강변.</h1><p id="summary" role="status">원본 데이터 답사 결과를 불러오는 중…</p>
<div id="scope-note" class="note">이 페이지는 새 촬영 데이터와 구간 서빙 계획입니다. 원본 답사 사진은 실제 공개 파노라마이며 생성 이미지나 GS 렌더가 아닙니다. 새 관광지의 GS 재구성과 스트리밍 검증은 실행 상태에 따로 표시합니다. 폐기한 GS 배경 보완을 다시 켜는 기능은 없습니다.</div>
<section id="result" class="section" hidden><h2>파리 첫 구간 · 실제 GS 결과</h2><div id="result-links" class="actions"></div><figure><img id="result-poster" alt="실제 파리 Gaussian Splatting 렌더"><figcaption id="result-detail"></figcaption></figure></section>
<section class="section"><h2>한 촬영열, 끊기지 않는 순서</h2><div id="metrics" class="metrics"></div><p>지도 타일 없이 원본 GPS 경로를 그렸습니다. 길이는 되돌아감과 골목 진입을 포함한 근사 폴리라인 길이입니다. 위치 정확도 표시는 2m이며 실제 카메라 포즈·깊이 정답이 아닙니다.</p><svg id="route" viewBox="0 0 1000 480" role="img" aria-label="선정한876개 실제 GPS 위치의 연결 경로"></svg><p id="selected" class="note"></p>
<label for="preview-index">원본 답사 지점</label><input id="preview-index" type="range" min="0" max="4" value="1" aria-label="원본 답사 지점"><figure><a id="photo-link" target="_blank" rel="noreferrer"><img id="photo" alt="선택한 위치의 실제 공개 파노라마"></a><figcaption id="caption"></figcaption></figure><p><a id="metadata" target="_blank" rel="noreferrer">이 사진의 원본 메타데이터 ↗</a></p></section>
<section class="section"><h2>후보를 실제 데이터로 비교</h2><div id="candidates" class="timeline"></div></section>
<section class="section"><h2>지금 실행한 것과 남은 것</h2><div id="stages"></div></section>
<section class="section"><h2>다음은 구간 단위의 GS</h2><ol id="steps"></ol><div id="limits" class="note"></div></section>
<footer><a href="./route.json">선정한876장 메타데이터</a> · <a href="./acquisition.json">HD24장 취득·해시 증빙</a> · <a href="./summary.json">실행 상태 JSON</a> · <a href="./ATTRIBUTION.txt">원본 출처·라이선스</a> · <a href="https://github.com/neocjmix/groundshift/blob/feat/local-viewer-reconstruction/docs/TOURIST_STREAMING.md">취득 명령과 다음 실험 경계</a><p id="updated"></p></footer></main>`;
const put=(selector:string,text:string)=>{document.querySelector(selector)!.textContent=text;};
async function start(){
  const response=await fetch('./summary.json');if(!response.ok)throw new Error('Summary HTTP '+response.status);const s:Summary=await response.json();
  const r=await fetch(s.route);if(!r.ok)throw new Error('Route HTTP '+r.status);const route:Route=await r.json(),m=route.statistics;
  put('#summary',s.summary);put('#updated','기록 갱신 '+s.updatedAt);
  if(s.result){
    put('.eyebrow','Paris · actual local Gaussian reconstruction · spatial SPZ delivery');
    put('#scope-note','첫58m의 실제 GS 결과와 전체2.19km의 원본 답사를 구분합니다. GS는 이 Mac에서 사진으로 재구성했으며 원본 파노라마를 배경으로 띄우지 않습니다. 아래 답사 사진은 원본이며 GS 렌더가 아닙니다. 전체2.19km 재구성·스트리밍은 아직 실행하지 않았습니다.');
    document.querySelector<HTMLElement>('#result')!.hidden=false;
    document.querySelector<HTMLImageElement>('#result-poster')!.src=s.result.poster;put('#result-detail',s.result.detail);
    for(const [label,extra] of [['구간 로딩으로 탐색',''],['전체 로딩 비교','&stream=off']]){const a=document.createElement('a');a.textContent=label;a.href='/?world='+s.result.worldPath+extra;document.querySelector('#result-links')!.append(a);}
  }
  const metrics=[['동일 촬영열',m.count.toLocaleString()+'장'],['GPS 경로', (m.lengthMeters/1000).toFixed(2)+'km'],['중앙 촬영 간격',m.medianSpacingMeters.toFixed(2)+'m'],['최대 간격',m.maximumSpacingMeters.toFixed(2)+'m']];
  if(s.acquisition)metrics.push(['HD 실제 취득',s.acquisition.count+'장 · '+(s.acquisition.bytes/1e6).toFixed(1)+'MB']);
  for(const [name,value] of metrics){const d=document.createElement('div');d.className='metric';const a=document.createElement('strong'),b=document.createElement('span');a.textContent=value;b.textContent=name;d.append(a,b);document.querySelector('#metrics')!.append(d);}
  const ns='http://www.w3.org/2000/svg',svg=document.querySelector('#route')!,lat=route.images.reduce((v,i)=>v+i.gps[1],0)/m.count;
  const xs=route.images.map(i=>i.gps[0]*Math.cos(lat*Math.PI/180)),ys=route.images.map(i=>-i.gps[1]),xMin=Math.min(...xs),yMin=Math.min(...ys);
  const scale=Math.min(920/(Math.max(...xs)-xMin),400/(Math.max(...ys)-yMin));
  const points=xs.map((x,i)=>[40+(x-xMin)*scale,40+(ys[i]-yMin)*scale]);
  const line=document.createElementNS(ns,'polyline');line.setAttribute('points',points.map(p=>p.join(',')).join(' '));line.setAttribute('fill','none');line.setAttribute('stroke','#91d7c7');line.setAttribute('stroke-width','3');svg.append(line);
  const dot=document.createElementNS(ns,'circle');dot.setAttribute('r','8');dot.setAttribute('fill','#f2be76');svg.append(dot);
  const north=document.createElementNS(ns,'text');north.setAttribute('x','915');north.setAttribute('y','30');north.setAttribute('fill','#bac9d3');north.textContent='N ↑';svg.append(north);
  function choose(index:number){const p=s.previews[index],i=route.images.findIndex(i=>i.rank===p.rank),xy=points[i];dot.setAttribute('cx',String(xy[0]));dot.setAttribute('cy',String(xy[1]));
    const img=document.querySelector<HTMLImageElement>('#photo')!;img.src=p.image;img.alt=p.title;img.dataset.rank=String(p.rank);
    document.querySelector<HTMLAnchorElement>('#photo-link')!.href=p.image;document.querySelector<HTMLAnchorElement>('#metadata')!.href=p.metadataUrl;put('#caption',p.caption);put('#selected',`순번 ${p.rank} · 시작에서 GPS 경로 ${(route.images[i].distanceMeters/1000).toFixed(2)}km · 실제 원본사진`);}
  const slider=document.querySelector<HTMLInputElement>('#preview-index')!;slider.max=String(s.previews.length-1);slider.addEventListener('input',()=>choose(Number(slider.value)));choose(1);
  for(const c of s.candidates){const d=document.createElement('article');d.className='entry';const body=document.createElement('div');body.className='copy';const title=document.createElement('h3'),p=document.createElement('p'),tag=document.createElement('span'),a=document.createElement('a');title.textContent=c.name;tag.className='status';tag.textContent=c.decision;p.textContent=(c.lengthMeters?`${c.count.toLocaleString()}장 · ${(c.lengthMeters/1000).toFixed(2)}km · 중앙 ${c.medianSpacingMeters?.toFixed(2)}m · ${c.dimensions}. `:'')+c.detail;a.href=c.source;a.textContent='공개 데이터 확인 ↗';body.append(tag,title,p,a);d.append(body);document.querySelector('#candidates')!.append(d);}
  for(const stage of s.stages){const d=document.createElement('div');d.className='street-stage';const tag=document.createElement('span'),title=document.createElement('strong'),p=document.createElement('p');tag.className='status';tag.textContent=stage.status;title.textContent=stage.title;p.textContent=stage.detail;d.append(tag,title,p);document.querySelector('#stages')!.append(d);}
  for(const step of s.nextSteps){const li=document.createElement('li');li.textContent=step;document.querySelector('#steps')!.append(li);}for(const limit of s.limits){const p=document.createElement('p');p.textContent=limit;document.querySelector('#limits')!.append(p);}
}
void start().catch(e=>put('#summary','불러오기 FAIL · '+String(e)));
