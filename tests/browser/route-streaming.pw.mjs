import {test,expect,devices} from '@playwright/test';
import {writeFile,readFile} from 'node:fs/promises';
import {PNG} from 'pngjs';
import {Vector3,Quaternion} from 'three';

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
 // A locator screenshot includes DOM overlays above the canvas. Remove only
 // their visibility so green status controls cannot satisfy the pixel check.
 const overlay=await page.addStyleTag({content:'.scene-shell>*:not(.canvas-mount){visibility:hidden!important}.scene-shell::after{visibility:hidden!important}'});
 let bytes;try{bytes=await page.locator('canvas').screenshot({path:info.outputPath(name+'.png')});}finally{await overlay.evaluate(node=>node.remove());}
 const png=PNG.sync.read(bytes);let colored=0;
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
 for(const segment of index.segments.filter(s=>s.id!==firstId))expect(requests.some(p=>p.includes('/'+segment.world.replace(/world\.json$/,'')))).toBe(false);
 const canvas=page.locator('canvas');await page.evaluate(()=>{window.__routeTrace=[];window.__routeTimer=setInterval(()=>{const c=document.querySelector('canvas');if(c?.dataset.route&&c?.dataset.paging)window.__routeTrace.push({route:JSON.parse(c.dataset.route),paging:JSON.parse(c.dataset.paging)});},50);});
 const slider=page.getByRole('slider',{name:'Recorded camera view'});await slider.focus();await slider.press('End');
 const lastId=index.segments.at(-1).id;const end=await settled(page,lastId);await inspect(page,info,'route-end');
 await slider.focus();await slider.press('Home');const reverse=await settled(page,firstId);await inspect(page,info,'route-reverse');
 const trace=await page.evaluate(()=>{clearInterval(window.__routeTimer);return window.__routeTrace;});
 expect(trace.every(s=>s.route.resident<=2&&s.paging.pages<=14)).toBe(true);
 expect(trace.some(s=>s.route.resident===2)).toBe(true);expect(reverse.route.transitions).toBeGreaterThanOrEqual(2);
 expect(trace.every(s=>s.route.segments.reduce((n,r)=>n+r.opacity,0)<=1.000001)).toBe(true);
 // Seek the last owned real center before the seam, then cross using real Fly
 // input. The actual heading decides forward/strafe; no camera test setter.
 const response=await page.request.get(world),manifest=await response.json();
 const cameras=await (await page.request.get(new URL(manifest.navigation.camerasPath,response.url()).href)).json();
 const current=index.segments.find(s=>s.id===firstId),next=index.segments[index.segments.indexOf(current)+1];
 const seam=current.anchors.at(-1),seamView=cameras.frames.findIndex(f=>distance(f.cameraToWorld.slice(0,3).map(r=>r[3]),seam)<1e-8);expect(seamView).toBeGreaterThanOrEqual(0);
 await slider.focus();await slider.press('Home');for(let i=0;i<seamView;i++)await slider.press('ArrowRight');await settled(page,firstId);
 await page.getByRole('button',{name:'Zoom in',exact:true}).click();await page.getByRole('button',{name:'Fly',exact:true}).click();
 const beforeFly=await state(page),up=new Vector3(...manifest.navigation.camera.up).normalize(),forward=new Vector3(0,0,-1).applyQuaternion(new Quaternion(...beforeFly.quaternion)).projectOnPlane(up).normalize(),right=forward.clone().cross(up).normalize(),toward=new Vector3(...next.anchors[0]).sub(new Vector3(...beforeFly.position));
 const along=toward.dot(forward),across=toward.dot(right),key=Math.abs(along)>=Math.abs(across)?(along>=0?'KeyW':'KeyS'):(across>=0?'KeyD':'KeyA');
 try{await page.keyboard.down('Shift');await page.keyboard.down(key);await expect.poll(async()=>(await state(page)).route.wanted,{timeout:15000}).toBe(next.id);}
 finally{await page.keyboard.up(key);await page.keyboard.up('Shift');}
 const stopped=await state(page),moved=await settled(page,next.id);expect(moved.mode).toBe('fly');expect(distance(moved.position,stopped.position)).toBeLessThan(1e-8);expect(distance(moved.quaternion,stopped.quaternion)).toBeLessThan(1e-8);expect(moved.fov).toBe(stopped.fov);expect(distance(moved.position,beforeFly.position)).toBeGreaterThan(.01);
 const panel=page.locator('details[aria-label="Loading diagnostics"]');await panel.locator('summary').click();
 const waitDownload=page.waitForEvent('download');await panel.getByRole('button',{name:'진단 JSON 저장',exact:true}).click();const download=await waitDownload;await download.saveAs(info.outputPath('route-diagnostics.json'));
 const diagnostic=JSON.parse(await readFile(await download.path(),'utf8'));expect(diagnostic.route.active).toBe(next.id);expect(diagnostic.mode).toBe('route-lod');
 await panel.getByRole('button',{name:'같은 위치 · 현재 구간 SPZ 비교',exact:true}).click();await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:90000});
 const whole=await state(page);expect(distance(whole.position,moved.position)).toBeLessThan(1e-8);expect(distance(whole.quaternion,moved.quaternion)).toBeLessThan(1e-8);expect(whole.fov).toBe(moved.fov);expect(whole.mode).toBe('fly');
 expect(requests.filter(p=>p.endsWith('.spz'))).toHaveLength(1);expect(requests.find(p=>p.endsWith('.spz'))).toContain('/'+next.world.replace(/world\.json$/,''));await inspect(page,info,'current-segment-whole');
 await panel.getByRole('button',{name:'같은 위치 · LoD로 복귀',exact:true}).click();const returned=await settled(page,next.id);
 expect(distance(returned.position,moved.position)).toBeLessThan(1e-8);expect(distance(returned.quaternion,moved.quaternion)).toBeLessThan(1e-8);expect(returned.fov).toBe(moved.fov);
 await panel.locator('summary').click();await page.screenshot({path:info.outputPath('route-fly-return.png')});expect(errors).toEqual([]);
 // Catalog preview of the actual GS frame at this recorded-route neighborhood.
 // Hide only overlaid controls; pose, dimensions and reconstructed pixels stay.
 const previewStyle=await page.addStyleTag({content:'.is-fly>.fly-ui,.is-fly>.paging-inspector{visibility:hidden!important}'});
 await canvas.screenshot({path:info.outputPath('route-observation-preview.png')});await previewStyle.evaluate(node=>node.remove());
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',browser:browser.version(),world,first,end,reverse,beforeFly,stopped,moved,whole,returned,flyInput:{seamView,key,target:next.id},trace,requests,errors,scope:'Actual declared reconstructed segments only; source route metadata is not GS coverage. Physical iPhone NOT RUN. Zero-opacity incoming and300ms fade use shared800k/14page budget; not a geometry or performance benchmark.'},null,2));
 expect(await canvas.getAttribute('data-navigation-mode')).toBe('fly');
});

test('latest real route extension crosses its new Fly boundary and returns within the shared budget',async({page,browser},info)=>{
 test.setTimeout(150000);
 const errors=[],requests=[],observations={};
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{const path=new URL(r.url()).pathname;if(/\.(rad|radc|spz)$/.test(path))requests.push(path);});
 const index=await routeInfo(page);test.skip(index.segments.length<3,'An additional native route segment has not been exported.');
 const from=index.segments.at(-2),to=index.segments.at(-1);
 const response=await page.request.get(world),manifest=await response.json();
 const cameras=await (await page.request.get(new URL(manifest.navigation.camerasPath,response.url()).href)).json();
 const seam=from.anchors.at(-1),seamView=cameras.frames.findIndex(f=>distance(f.cameraToWorld.slice(0,3).map(r=>r[3]),seam)<1e-8);
 expect(seamView).toBeGreaterThanOrEqual(0);
 let status='FAIL';
 try{
  await initial(page);await settled(page,(await state(page)).route.active);
  const slider=page.getByRole('slider',{name:'Recorded camera view'});await slider.focus();await slider.press('Home');
  for(let i=0;i<seamView;i++)await slider.press('ArrowRight');
  observations.seam=await settled(page,from.id);await inspect(page,info,'extension-before');
  expect(requests.some(p=>p.includes('/'+to.world.replace(/world\.json$/,'')))).toBe(false);
  await page.evaluate(()=>{window.__routeTrace=[];window.__routeTimer=setInterval(()=>{const c=document.querySelector('canvas');if(c?.dataset.route&&c?.dataset.paging)window.__routeTrace.push({route:JSON.parse(c.dataset.route),paging:JSON.parse(c.dataset.paging)});},50);});
  await page.getByRole('button',{name:'Fly',exact:true}).click();observations.beforeFly=await state(page);
  const up=new Vector3(...manifest.navigation.camera.up).normalize(),forward=new Vector3(0,0,-1).applyQuaternion(new Quaternion(...observations.beforeFly.quaternion)).projectOnPlane(up).normalize(),right=forward.clone().cross(up).normalize(),toward=new Vector3(...to.anchors[0]).sub(new Vector3(...observations.beforeFly.position));
  const along=toward.dot(forward),across=toward.dot(right),key=Math.abs(along)>=Math.abs(across)?(along>=0?'KeyW':'KeyS'):(across>=0?'KeyD':'KeyA');
  const reverseKey={KeyW:'KeyS',KeyS:'KeyW',KeyD:'KeyA',KeyA:'KeyD'}[key];
  observations.input={seamView,key,reverseKey,from:from.id,to:to.id};
  for(const [direction,target,input] of [['forward',to.id,key],['reverse',from.id,reverseKey]]){
   try{await page.keyboard.down('Shift');await page.keyboard.down(input);await expect.poll(async()=>(await state(page)).route.wanted,{timeout:15000}).toBe(target);}
   finally{await page.keyboard.up(input);await page.keyboard.up('Shift');}
   const stopped=await state(page),loaded=await settled(page,target);observations[direction]={stopped,loaded};
   expect(loaded.mode).toBe('fly');expect(distance(loaded.position,stopped.position)).toBeLessThan(1e-8);expect(distance(loaded.quaternion,stopped.quaternion)).toBeLessThan(1e-8);expect(loaded.fov).toBe(stopped.fov);
   expect(loaded.route.errors).toEqual([]);expect(loaded.paging.capacity).toBe(917504);expect(loaded.paging.selectionTarget).toBe(800000);
   await inspect(page,info,'extension-'+direction);await page.screenshot({path:info.outputPath('extension-'+direction+'-ui.png')});
  }
  const trace=await page.evaluate(()=>window.__routeTrace);
  expect(trace.every(s=>s.route.resident<=2&&s.paging.pages<=14)).toBe(true);expect(trace.some(s=>s.route.resident===2)).toBe(true);
  expect(trace.every(s=>s.route.segments.reduce((n,r)=>n+r.opacity,0)<=1.000001)).toBe(true);
  expect(observations.reverse.loaded.route.transitions-observations.seam.route.transitions).toBeGreaterThanOrEqual(2);
  expect(distance(observations.forward.loaded.position,observations.beforeFly.position)).toBeGreaterThan(.01);
  expect(requests.some(p=>p.endsWith('.spz'))).toBe(false);expect(errors).toEqual([]);status='PASS';
 }finally{
  const trace=await page.evaluate(()=>{clearInterval(window.__routeTimer);return window.__routeTrace??[];}).catch(()=>[]);
  await writeFile(info.outputPath('evidence.json'),JSON.stringify({status,browser:browser.version(),world,segmentCount:index.segments.length,from:from.id,to:to.id,...observations,trace,requests,errors,scope:'Actual added native segment and Fly boundary in both directions. Desktop WebKit iPhone profile when GS_ROUTE_WEBKIT=1; physical iPhone NOT RUN. Shared 800k selection target and14-page pool. Not a global geometry, seamlessness or performance acceptance.'},null,2));
 }
});

for(const stage of ['metadata','RAD chunk'])test(`failed incoming route ${stage} retains the current rendered world and retries`,async({page},info)=>{
 test.setTimeout(120000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const index=await routeInfo(page),last=index.segments.at(-1);expect(index.segments.length).toBeGreaterThanOrEqual(2);
 let broken=true,rejected=0;const pattern='**/'+(stage==='metadata'?last.world:last.world.replace(/world\.json$/,'rad/*.radc'));
 await page.route(pattern,async route=>{if(broken){rejected++;await route.fulfill({status:503,body:'Explicit route transport-failure fixture'});}else await route.continue();});
 await initial(page);const firstId=(await state(page)).route.active;await settled(page,firstId);
 const slider=page.getByRole('slider',{name:'Recorded camera view'});await slider.focus();await slider.press('End');
 await expect.poll(async()=>(await state(page)).route.errors.join(' '),{timeout:30000}).toContain('503');
 const failed=await state(page);expect(rejected).toBeGreaterThan(0);expect(failed.route.active).toBe(firstId);expect(failed.route.resident).toBe(1);expect(failed.paging.selected).toBeGreaterThan(0);await page.screenshot({path:info.outputPath('incoming-failed-current-retained.png')});
 broken=false;await page.getByLabel('Route streaming status').getByRole('button',{name:'구간 다시 시도',exact:true}).click();const recovered=await settled(page,last.id);expect(recovered.route.errors).toEqual([]);expect(errors).toEqual([]);
 await inspect(page,info,'incoming-retry');await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',fixture:`503 on real incoming ${stage}, then actual release/retry`,rejected,failed,recovered,errors},null,2));
});
