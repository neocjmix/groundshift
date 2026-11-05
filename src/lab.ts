import './experiment.css';

type Entry = { id: string; title: string; description: string; createdAt?: string; image: string; href: string; kind: string; detail: string };
const root = document.querySelector<HTMLDivElement>('#app')!;
root.innerHTML = `<header><a href="/">GROUND SHIFT</a><a href="/">모든 3D 장면 ↗</a></header><main><span class="eyebrow">Experiment log / local M2</span><h1>실험실.</h1><p>가장 최근에 만든 결과부터 봅니다. 원본, 생성 이미지, 점군과 3D 장면을 연결하고, 품질이 낮은 결과도 기록합니다.</p><div class="toolbar"><label>시간순 <select id="order"><option value="newest">최신 결과부터</option><option value="oldest">처음부터</option></select></label><label>보기 <select id="kind"><option value="all">전체 결과</option><option value="report">실험 묶음</option><option value="scene">3D 장면</option></select></label><span id="count" class="muted"></span></div><div id="timeline" class="timeline" aria-live="polite"></div><footer>카드의 시각은 기록된 작업 완료 시각입니다. 기록이 없는 항목은 뒤에 표시합니다.<br>재구성과 생성은 Mac에서 실행합니다. Railway는 결과를 보는 관측면입니다.</footer></main>`;
const order = document.querySelector<HTMLSelectElement>('#order')!;
const kind = document.querySelector<HTMLSelectElement>('#kind')!;
const timeline = document.querySelector<HTMLDivElement>('#timeline')!;
let entries: Entry[] = [];
function render() {
  const rows = entries.filter(item => kind.value === 'all' || item.kind === kind.value).sort((a, b) => {
    if (!a.createdAt) return b.createdAt ? 1 : 0;
    if (!b.createdAt) return -1;
    const difference = (Date.parse(a.createdAt) - Date.parse(b.createdAt)) * (order.value === 'newest' ? -1 : 1);
    return difference || (a.kind === b.kind ? 0 : a.kind === 'report' ? -1 : 1);
  });
  timeline.replaceChildren(...rows.map(item => {
    const card = document.createElement('article'); card.className = 'entry'; card.dataset.id = item.id;
    if (item.createdAt) card.dataset.createdAt = item.createdAt;
    const imageLink = document.createElement('a'); imageLink.href = item.href;
    const image = document.createElement('img'); image.src = item.image; image.alt = item.title; image.loading = 'lazy'; imageLink.append(image);
    const copy = document.createElement('div'); copy.className = 'copy';
    const time = document.createElement('time'); time.textContent = item.createdAt ? new Date(item.createdAt).toLocaleString('ko-KR') : '시각 기록 없음'; if (item.createdAt) time.dateTime = item.createdAt;
    const heading = document.createElement('h2'); const link = document.createElement('a'); link.href = item.href; link.textContent = item.title + ' ↗'; heading.append(link);
    const p = document.createElement('p'); p.textContent = item.description;
    const detail = document.createElement('small'); detail.textContent = item.detail;
    copy.append(time, heading, p, detail); card.append(imageLink, copy); return card;
  }));
  document.querySelector('#count')!.textContent = `${rows.length}개 결과`;
}
order.addEventListener('change', render); kind.addEventListener('change', render);
fetch('./timeline.json').then(async response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); entries = (await response.json()).entries; render(); })
  .catch(error => { timeline.textContent = `실험 기록을 불러오지 못했습니다: ${error.message}`; timeline.classList.add('error'); });
