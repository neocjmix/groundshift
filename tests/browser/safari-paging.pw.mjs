import {test,expect,devices} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';

const {defaultBrowserType,...iphone}=devices['iPhone 16 Pro'];
// Empty channel clears the repository's Chrome default; undefined inherits it.
test.use({...iphone,browserName:defaultBrowserType,channel:'',headless:true,actionTimeout:15000});
const world=process.env.GS_SAFARI_WORLD??'/worlds/paris-58m-lod/world.json';
const worldId=world.split('/').at(-2);
const distance=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i]));
const state=page=>page.locator('canvas').evaluate(c=>({
 position:c.dataset.cameraPosition?.split(',').map(Number),quaternion:c.dataset.cameraQuaternion?.split(',').map(Number),
 fov:Number(c.dataset.cameraFov),mode:c.dataset.navigationMode,frames:Number(c.dataset.frameCount),
 paging:c.dataset.paging?JSON.parse(c.dataset.paging):null,
 diagnostics:c.dataset.pagingDiagnostics?JSON.parse(c.dataset.pagingDiagnostics):null,
 buffer:[c.width,c.height],viewport:[innerWidth,innerHeight],dpr:devicePixelRatio,
}));
async function samePose(page,expected){
 await expect.poll(async()=>distance((await state(page)).position,expected.position)).toBeLessThan(1e-8);
 const actual=await state(page);
 expect(distance(actual.quaternion,expected.quaternion)).toBeLessThan(1e-8);
 expect(actual.fov).toBeCloseTo(expected.fov,8);expect(actual.mode).toBe(expected.mode);
 return actual;
}
async function ready(page){await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:90000});}
async function refined(page){
 await expect.poll(async()=>{
  const s=await state(page),d=s.diagnostics;
  return s.paging?.selected>500000&&s.paging.pending===0&&d?.phase==='settled'
   &&Object.values(d.queues).every(count=>count===0)
   &&Object.values(d.stages).every(stage=>stage.state==='idle');
 },{timeout:60000}).toBe(true);
 const frame=(await state(page)).frames;
 await expect.poll(async()=>(await state(page)).frames,{timeout:15000}).toBeGreaterThan(frame+30);
 return state(page);
}
async function download(page,info,name){
 const waiting=page.waitForEvent('download');await page.getByRole('button',{name:'진단 JSON 저장',exact:true}).tap();
 const file=await waiting;await file.saveAs(info.outputPath(name));return JSON.parse(await readFile(await file.path(),'utf8'));
}
async function openInspector(page){
 const panel=page.locator('details[aria-label="Loading diagnostics"]');
 if(!await panel.evaluate(e=>e.open))await panel.locator('summary').tap();return panel;
}

test('desktop WebKit mobile profile preserves a moved Fly view across same-position SPZ comparison and exports real diagnostics',async({page,browser},info)=>{
 test.setTimeout(120000);
 const errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{const p=new URL(r.url()).pathname;if(/\.(rad|radc|spz)$/.test(p))requests.push(p);});
 // Explicit platform-capability fixture. This tests the viewport fallback,
 // not a physical iPhone or the installed iOS Safari fullscreen implementation.
 await page.addInitScript(()=>{
  Element.prototype.requestFullscreen=undefined;Element.prototype.requestPointerLock=undefined;
  window.__safariProgress=[];window.__safariProgressTimer=setInterval(()=>{
   const c=document.querySelector('canvas');if(c?.dataset.paging)window.__safariProgress.push(JSON.parse(c.dataset.paging));
  },50);
 });
 // A small declared network fixture makes refinement observable, not a load-time benchmark.
 await page.route('**/*.radc',async route=>{await new Promise(r=>setTimeout(r,200));await route.continue();});
 await page.goto('/?world='+world);await ready(page);const first=await refined(page);
 expect(first.paging.capacity).toBe(917504);expect(first.paging.selectionTarget).toBe(800000);
 expect(first.paging.pages).toBeLessThanOrEqual(14);expect(first.paging.errors).toEqual([]);
 const progression=await page.evaluate(()=>{clearInterval(window.__safariProgressTimer);return window.__safariProgress;});
 expect(progression.some(s=>s.selected>0&&s.selected<200000)).toBe(true);
 expect(progression.some(s=>s.selected>500000)).toBe(true);
 expect(progression.every(s=>s.pages<=14)).toBe(true);
 // Non-default FOV plus translated/rotated camera catches reset-to-initial bugs.
 await page.getByRole('button',{name:'Camera path',exact:true}).tap();
 const originalFov=(await state(page)).fov;
 await page.getByRole('button',{name:'Zoom in',exact:true}).tap();
 await expect.poll(async()=>(await state(page)).fov).toBeLessThan(originalFov);
 await page.getByRole('button',{name:'Fly',exact:true}).tap();
 await expect(page.locator('canvas')).toHaveAttribute('data-navigation-mode','fly');
 expect(await page.evaluate(()=>Boolean(document.fullscreenElement))).toBe(false);
 const box=await page.locator('.scene-shell').boundingBox();expect([box.x,box.y,box.width,box.height]).toEqual([0,0,402,681]);
 const start=await state(page);
 await page.keyboard.down('KeyW');await page.waitForTimeout(250);await page.keyboard.up('KeyW');
 await expect.poll(async()=>distance((await state(page)).position,start.position)).toBeGreaterThan(.01);
 // WebKit's public Playwright touch API supports taps only. Real mouse drag
 // exercises the shared pointer-look path; do not call this physical touch/swipe proof.
 await page.mouse.move(270,300);await page.mouse.down();await page.mouse.move(315,318,{steps:8});await page.mouse.up();
 await expect.poll(async()=>distance((await state(page)).quaternion,start.quaternion)).toBeGreaterThan(.02);
 await refined(page);const moved=await state(page);
 const panel=await openInspector(page);await page.screenshot({path:info.outputPath('webkit-fly-diagnostics.png')});
 const diagnostic=await download(page,info,'diagnostic-lod.json');
 expect(diagnostic.version).toBe('safari-paging-20261107-v2');expect(diagnostic.worldId).toBe(worldId);
 expect(diagnostic.devicePixelRatio).toBe(3);expect(diagnostic.samples.length).toBeGreaterThan(1);
 expect(diagnostic.mode).toBe('lod');expect(diagnostic.view.mode).toBe('fly');
 expect(distance(diagnostic.view.position,moved.position)).toBeLessThan(1e-8);
 expect(distance(diagnostic.view.quaternion,moved.quaternion)).toBeLessThan(1e-8);
 expect(diagnostic.view.fov).toBeCloseTo(moved.fov,8);
 const sample=diagnostic.samples.at(-1);
 expect(sample.runtime.lodSplatCount).toBe(800000);expect(sample.runtime.maxPagedSplats).toBe(917504);
 expect(sample.selection.active).toBeGreaterThan(0);expect(sample.selection.residentPages).toBeLessThanOrEqual(14);
 expect(sample.network.errorCount).toBe(0);expect(sample.heartbeat.frames).toBeGreaterThan(30);
 expect(Object.keys(sample.stages)).toEqual(['network','decode','lod','upload','display']);
 await panel.getByRole('button',{name:'같은 위치 · 전체 SPZ 비교',exact:true}).tap();await ready(page);
 await expect(page.locator('canvas')).toHaveAttribute('data-navigation-mode','fly');
 const whole=await samePose(page,moved);expect(requests.some(p=>p.endsWith('.spz'))).toBe(true);
 await page.screenshot({path:info.outputPath('webkit-whole-same-pose.png')});
 await panel.getByRole('button',{name:'같은 위치 · LoD로 복귀',exact:true}).tap();await ready(page);await refined(page);
 const returned=await samePose(page,moved);await page.screenshot({path:info.outputPath('webkit-return-same-pose.png')});
 await panel.locator('summary').tap();await page.screenshot({path:info.outputPath('webkit-return-collapsed.png')});
 expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',browser:browser.version(),platform:'Actual desktop WebKit with iPhone16Pro emulation; physical iPhone NOT RUN',fullscreen:'Explicit API-unavailable fixture',input:'Native tap, keyboard movement and mouse drag look; physical touch swipe NOT RUN',latencyFixtureMs:200,first,moved,whole,returned,progression,requests,errors,diagnosticFile:'diagnostic-lod.json'},null,2));
});

test('desktop WebKit diagnostic distinguishes held network requests from a completed download',async({page,browser},info)=>{
 test.setTimeout(60000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{Element.prototype.requestFullscreen=undefined;});
 let release,chunks=0;const held=new Promise(resolve=>{release=resolve;});
 // Allow the initial coarse page to render, then hold real detail requests.
 // Holding every page prevents ready by design. This is not an iOS decoder hang.
 await page.route('**/*.radc',async route=>{if(chunks++>0)await held;await route.continue();});
 try{
  await page.goto('/?world='+world);await ready(page);
  await page.getByRole('button',{name:'Fly',exact:true}).tap();
  await expect(page.locator('canvas')).toHaveAttribute('data-navigation-mode','fly');
  await expect.poll(async()=>(await state(page)).diagnostics?.stages.network.state,{timeout:22000}).toBe('waiting');
  const stalled=await state(page);expect(stalled.diagnostics.phase).toBe('network');expect(stalled.diagnostics.network.pending).toBeGreaterThan(0);
  await openInspector(page);await expect(page.getByRole('status').filter({hasText:'10초 이상 진행 변화'})).toBeVisible();
  const diagnostic=await download(page,info,'diagnostic-held-network.json');
  expect(diagnostic.samples.some(s=>s.stages.network.state==='waiting')).toBe(true);
  await page.screenshot({path:info.outputPath('webkit-held-network.png')});
  release();const recovered=await refined(page);expect(recovered.paging.errors).toEqual([]);expect(errors).toEqual([]);
  await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',browser:browser.version(),fixture:'Actual RAD chunk requests held then released; not an iOS decoder reproduction',stalled,recovered,errors,physicalIos:'NOT RUN'},null,2));
 }finally{release();}
});
