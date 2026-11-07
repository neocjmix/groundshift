import {test,expect} from '@playwright/test';
import {writeFile} from 'node:fs/promises';
import {PNG} from 'pngjs';

test.use({actionTimeout:15000});
const world='/worlds/paris-58m-lod/world.json';
const paging=async page=>JSON.parse((await page.locator('canvas').getAttribute('data-paging'))||'{}');
const pose=async page=>page.locator('canvas').evaluate(c=>({position:c.dataset.cameraPosition,quaternion:c.dataset.cameraQuaternion,progress:c.dataset.pathProgress,fov:c.dataset.cameraFov}));
async function settled(page){
 let signature='',since=Date.now();
 await expect.poll(async()=>{
  const s=await paging(page),next=JSON.stringify([s.requested,s.selected,s.residentChunks]);
  if(next!==signature){signature=next;since=Date.now();}
  return s.selected>1000&&s.pending===0&&Date.now()-since>900;
 },{timeout:60000}).toBe(true);
 // Network/selection quiescence can precede the async GPU sort/display handoff.
 const frame=Number(await page.locator('canvas').getAttribute('data-frame-count'));
 await expect.poll(()=>page.locator('canvas').getAttribute('data-frame-count').then(Number),{timeout:15000}).toBeGreaterThan(frame+30);
 return paging(page);
}
async function capture(page,info,name){
 const style=await page.addStyleTag({content:'.scene-shell > :not(.canvas-mount){visibility:hidden!important}'});
 try{return PNG.sync.read(await page.locator('canvas').screenshot({path:info.outputPath(name+'.png')}));}
 finally{await style.evaluate(e=>e.remove());}
}
function compare(actual,control){
 expect([actual.width,actual.height]).toEqual([control.width,control.height]);
 let sum=0,center=0,count=0,edge=0,refEdge=0;
 for(let y=0;y<actual.height;y++)for(let x=0;x<actual.width;x++){
  const i=4*(y*actual.width+x),central=x>=actual.width*.25&&x<actual.width*.75&&y>=actual.height*.25&&y<actual.height*.75;
  for(let c=0;c<3;c++){
   const d=Math.abs(actual.data[i+c]-control.data[i+c]);sum+=d;
   if(central){center+=d;count++;edge+=Math.abs(actual.data[i+c]-actual.data[i+4+c]);refEdge+=Math.abs(control.data[i+c]-control.data[i+4+c]);}
  }
 }
 return {mae:sum/(actual.width*actual.height*3),centerMae:center/count,centralEdgeRatio:edge/refEdge};
}

test('native LoD progressively restores nearby detail, reselects pages and matches the whole-scene view',async({page,browser},info)=>{
 const errors=[],requests=[];let manifest;
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{const p=new URL(r.url()).pathname;if(/\.(rad|radc|spz)$/.test(p))requests.push(p);});
 const cdp=await page.context().newCDPSession(page);await cdp.send('Network.enable');await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});
 // Explicit latency fixture makes intermediate refinement inspectable; timings are not production benchmarks.
 await page.route('**/*.radc',async route=>{await new Promise(r=>setTimeout(r,250));await route.continue();});
 await page.addInitScript(()=>{
  window.__lodRefinement=[];
  window.__lodRefinementTimer=setInterval(()=>{
   const c=document.querySelector('canvas');if(!c?.dataset.paging)return;
   const s=JSON.parse(c.dataset.paging);window.__lodRefinement.push({ms:performance.now(),selected:s.selected,pages:s.pages,pending:s.pending});
   if(window.__lodRefinement.length>2400)window.__lodRefinement.shift();
  },50);
 });
 const response=page.waitForResponse(r=>new URL(r.url()).pathname===world);
 await page.goto('/?world='+world);manifest=await(await response).json();
 await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});
 const first=await settled(page),initialRequests=[...requests];
 await page.evaluate(()=>clearInterval(window.__lodRefinementTimer));const progression=await page.evaluate(()=>window.__lodRefinement);
 expect(first.selected).toBeGreaterThan(500000); // Fails the original permanently coarse350k cap.
 const maxPages=manifest.paging.maxPagedSplats/65536;
 const index=await(await page.request.get('/worlds/paris-58m-lod/'+manifest.paging.path)).json();
 const totalChunks=index.files.filter(f=>f.path.endsWith('.radc')).length;
 expect(new Set(initialRequests.filter(p=>p.endsWith('.radc'))).size).toBeLessThan(totalChunks);
 expect(first.pages).toBeLessThanOrEqual(maxPages);expect(first.capacity).toBe(manifest.paging.maxPagedSplats);
 expect(progression.some(s=>s.selected>0&&s.selected<200000)).toBe(true);
 expect(progression.some(s=>s.selected>500000)).toBe(true);
 expect(progression.filter(s=>s.pages>0).every(s=>s.pages<=maxPages)).toBe(true);
 expect(first.errors).toEqual([]);expect(requests.some(p=>p.endsWith('.spz'))).toBe(false);
 const initial=await capture(page,info,'refined-start');
 const slider=page.getByRole('slider',{name:'Recorded camera view'});
 await slider.focus();await slider.press('End');await expect.poll(()=>page.locator('canvas').getAttribute('data-path-progress').then(Number)).toBe(23);
 const end=await settled(page);expect(end.requested).toBeGreaterThan(first.requested);expect(end.pages).toBeLessThanOrEqual(maxPages);
 expect([...end.residentChunks].sort()).not.toEqual([...first.residentChunks].sort());
 await slider.press('Home');await expect.poll(()=>page.locator('canvas').getAttribute('data-path-progress').then(Number)).toBe(0);
 const reverse=await settled(page);expect(reverse.requested).toBeGreaterThan(end.requested);expect(reverse.pages).toBeLessThanOrEqual(maxPages);
 expect([...reverse.residentChunks].sort()).not.toEqual([...end.residentChunks].sort());
 const returned=await capture(page,info,'refined-return'),returnDifference=compare(returned,initial);expect.soft(returnDifference.mae).toBeLessThan(.2);
 await writeFile(info.outputPath('interim-evidence.json'),JSON.stringify({first,end,reverse,returnDifference,progression,requests,errors},null,2));
 // Actual UI zoom; switching must preserve this exact viewpoint and zoom.
 await page.getByRole('button',{name:'Zoom in',exact:true}).click();await page.getByRole('button',{name:'Zoom in',exact:true}).click();
 const zoomed=await settled(page),lodPose=await pose(page),lod=await capture(page,info,'refined-zoom');
 expect(requests.some(p=>p.endsWith('.spz'))).toBe(false);
 await page.getByRole('button',{name:'전체 SPZ로 비교',exact:true}).click();await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});
 const frame=Number(await page.locator('canvas').getAttribute('data-frame-count'));await expect.poll(()=>page.locator('canvas').getAttribute('data-frame-count').then(Number)).toBeGreaterThan(frame+30);
 const wholePose=await pose(page);expect(wholePose).toEqual(lodPose);
 const whole=await capture(page,info,'whole-zoom'),difference=compare(lod,whole);
 const quality=difference.mae<=4&&difference.centerMae<=3&&difference.centralEdgeRatio>=.9?'PASS':'FAIL';
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'Completed actual rendering and interaction',quality,thresholds:{mae:4,centerMae:3,centralEdgeRatio:.9},difference,returnDifference,first,end,reverse,zoomed,totalChunks,initialRequests,requests,progression,lodPose,wholePose,errors,browser:browser.version(),headed:process.env.HEADLESS!=='1',cacheDisabled:true,latencyFixtureMs:250,scope:'Actual bounded58m paging and same-camera whole-SPZ detail check. No independent geometry, physicalmobiledevice or kilometer-scale acceptance.'},null,2));
 expect(quality).toBe('PASS');expect(errors).toEqual([]);
});
