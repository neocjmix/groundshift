import {test,expect,devices} from '@playwright/test';
import {writeFile,readFile} from 'node:fs/promises';
import {PNG} from 'pngjs';

if(process.env.GS_ROUTE_WEBKIT==='1'){
 const {defaultBrowserType,...iphone}=devices['iPhone 16 Pro'];
 test.use({...iphone,browserName:defaultBrowserType,channel:'',headless:true});
}
const world=process.env.GS_ROUTE_WORLD??'/worlds/seine-full-route/world.json';
const state=page=>page.locator('canvas').evaluate(c=>({route:c.dataset.route?JSON.parse(c.dataset.route):null,paging:c.dataset.paging?JSON.parse(c.dataset.paging):null,
 diagnostics:c.dataset.pagingDiagnostics?JSON.parse(c.dataset.pagingDiagnostics):null,position:c.dataset.cameraPosition?.split(',').map(Number),quaternion:c.dataset.cameraQuaternion?.split(',').map(Number),fov:Number(c.dataset.cameraFov),mode:c.dataset.navigationMode,frames:Number(c.dataset.frameCount)}));
const distance=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i]));
async function settled(page,id){
 await expect.poll(async()=>{const s=await state(page);return s.route?.active===id&&s.route.resident===1&&!s.route.incoming&&!s.route.pending&&s.paging.selected>100000&&s.paging.pending===0&&s.diagnostics?.phase==='settled'&&Object.values(s.diagnostics.queues).every(v=>v===0);},{timeout:90000}).toBe(true);
 const frame=(await state(page)).frames;await expect.poll(async()=>(await state(page)).frames).toBeGreaterThan(frame+30);return state(page);
}
async function inspect(page,info,name){
 const bytes=await page.locator('canvas').screenshot({path:info.outputPath(name+'.png')}),png=PNG.sync.read(bytes);let colored=0;
 for(let i=0;i<png.data.length;i+=4)if(Math.max(...png.data.subarray(i,i+3))-Math.min(...png.data.subarray(i,i+3))>12)colored++;
 expect(colored).toBeGreaterThan(10000);return {width:png.width,height:png.height,coloredPixels:colored};
}
async function routeInfo(page){
 const response=await page.request.get(world),manifest=await response.json();
 const indexUrl=new URL(manifest.route.path,response.url());return (await page.request.get(indexUrl.href)).json();
}
async function initial(page){await page.addInitScript(()=>{Element.prototype.requestFullscreen=undefined;Element.prototype.requestPointerLock=undefined;});await page.goto('/?world='+encodeURIComponent(world));await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:90000});}
test('real independently reconstructed route crosses and reverses with bounded pages and same-pose current-segment SPZ',async({page,browser},info)=>{
 test.setTimeout(180000);const errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/\.(rad|radc|spz)$/.test(new URL(r.url()).pathname))requests.push(new URL(r.url()).pathname);});
 const index=await routeInfo(page);expect(index.segments.length).toBeGreaterThanOrEqual(2);
 await initial(page);const firstId=(await state(page)).route.active;const first=await settled(page,firstId);await inspect(page,info,'route-start');
 expect(requests.some(p=>p.endsWith('.spz'))).toBe(false);expect(first.paging.capacity).toBe(917504);expect(first.paging.selectionTarget).toBe(800000);
 const canvas=page.locator('canvas');await page.evaluate(()=>{window.__routeTrace=[];window.__routeTimer=setInterval(()=>{const c=document.querySelector('canvas');if(c?.dataset.route&&c?.dataset.paging)window.__routeTrace.push({route:JSON.parse(c.dataset.route),paging:JSON.parse(c.dataset.paging)});},50);});
 const slider=page.getByRole('slider',{name:'Recorded camera view'});await slider.focus();await slider.press('End');
 const lastId=index.segments.at(-1).id;const end=await settled(page,lastId);await inspect(page,info,'route-end');
 await slider.focus();await slider.press('Home');const reverse=await settled(page,firstId);await inspect(page,info,'route-reverse');
 const trace=await page.evaluate(()=>{clearInterval(window.__routeTimer);return window.__routeTrace;});
 expect(trace.every(s=>s.route.resident<=2&&s.paging.pages<=14)).toBe(true);
 expect(trace.some(s=>s.route.resident===2)).toBe(true);expect(reverse.route.transitions).toBeGreaterThanOrEqual(2);
 expect(trace.every(s=>s.route.segments.reduce((n,r)=>n+r.opacity,0)<=1.000001)).toBe(true);
 await page.getByRole('button',{name:'Zoom in',exact:true}).click();await page.getByRole('button',{name:'Fly',exact:true}).click();
 await page.keyboard.down('KeyW');await page.waitForTimeout(150);await page.keyboard.up('KeyW');
 const moved=await settled(page,firstId),panel=page.locator('details[aria-label="Loading diagnostics"]');await panel.locator('summary').click();
 const waitDownload=page.waitForEvent('download');await panel.getByRole('button',{name:'진단 JSON 저장',exact:true}).click();const download=await waitDownload;await download.saveAs(info.outputPath('route-diagnostics.json'));
 const diagnostic=JSON.parse(await readFile(await download.path(),'utf8'));expect(diagnostic.route.active).toBe(firstId);expect(diagnostic.mode).toBe('route-lod');
 await panel.getByRole('button',{name:'같은 위치 · 현재 구간 SPZ 비교',exact:true}).click();await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:90000});
 const whole=await state(page);expect(distance(whole.position,moved.position)).toBeLessThan(1e-8);expect(distance(whole.quaternion,moved.quaternion)).toBeLessThan(1e-8);expect(whole.fov).toBe(moved.fov);expect(whole.mode).toBe('fly');
 expect(requests.filter(p=>p.endsWith('.spz'))).toHaveLength(1);await inspect(page,info,'current-segment-whole');
 await panel.getByRole('button',{name:'같은 위치 · LoD로 복귀',exact:true}).click();const returned=await settled(page,firstId);
 expect(distance(returned.position,moved.position)).toBeLessThan(1e-8);expect(distance(returned.quaternion,moved.quaternion)).toBeLessThan(1e-8);expect(returned.fov).toBe(moved.fov);
 await panel.locator('summary').click();await page.screenshot({path:info.outputPath('route-fly-return.png')});expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',browser:browser.version(),world,first,end,reverse,moved,whole,returned,trace,requests,errors,scope:'Actual declared reconstructed segments only; source route metadata is not GS coverage. Physical iPhone NOT RUN. Zero-opacity incoming and300ms fade use shared800k/14page budget; not a geometry or performance benchmark.'},null,2));
 expect(await canvas.getAttribute('data-navigation-mode')).toBe('fly');
});

test('failed incoming route metadata retains the current rendered world and retries',async({page},info)=>{
 test.setTimeout(120000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const index=await routeInfo(page),last=index.segments.at(-1);expect(index.segments.length).toBeGreaterThanOrEqual(2);
 let broken=true;await page.route('**/'+last.world,async route=>{if(broken)await route.fulfill({status:503,body:'Explicit route transport-failure fixture'});else await route.continue();});
 await initial(page);const firstId=(await state(page)).route.active;await settled(page,firstId);
 const slider=page.getByRole('slider',{name:'Recorded camera view'});await slider.focus();await slider.press('End');
 await expect.poll(async()=>(await state(page)).route.errors.join(' ')).toContain('503');
 const failed=await state(page);expect(failed.route.active).toBe(firstId);expect(failed.route.resident).toBe(1);expect(failed.paging.selected).toBeGreaterThan(0);await page.screenshot({path:info.outputPath('incoming-failed-current-retained.png')});
 broken=false;await page.getByLabel('Route streaming status').getByRole('button',{name:'구간 다시 시도',exact:true}).click();const recovered=await settled(page,last.id);expect(recovered.route.errors).toEqual([]);expect(errors).toEqual([]);
 await inspect(page,info,'incoming-retry');await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',fixture:'503 on real incoming world metadata, then actual release/retry',failed,recovered,errors},null,2));
});
