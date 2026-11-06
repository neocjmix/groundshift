import {test,expect} from '@playwright/test';
import {writeFile} from 'node:fs/promises';
import {PNG} from 'pngjs';
const world=process.env.GS_PAGING_WORLD??'/worlds/paris-58m-lod/world.json';
const stats=async page=>{const s=await page.locator('canvas').getAttribute('data-paging');return s?JSON.parse(s):{selected:0,requested:0};};
async function quiet(page){let previous=-1,since=Date.now();await expect.poll(async()=>{const s=await stats(page);if(s.requested!==previous){previous=s.requested;since=Date.now();}return s.selected>1000&&(s.pending??0)===0&&Date.now()-since>700;},{timeout:30000}).toBe(true);}
async function screenshot(page,info,name){const style=await page.addStyleTag({content:'.scene-shell > :not(.canvas-mount){visibility:hidden!important}'});const bytes=await page.locator('canvas').screenshot({path:info.outputPath(name+'.png')});await style.evaluate(e=>e.remove());return PNG.sync.read(bytes);}
test('actual native LoD paging keeps a bounded pool, covers the world and switches to the identical SPZ control',async({page,browser},info)=>{
 const cdp=await page.context().newCDPSession(page);await cdp.send('Network.enable');await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});const requests=[],errors=[];page.on('request',r=>{if(/\.(rad|radc|spz)$/.test(new URL(r.url()).pathname))requests.push(new URL(r.url()).pathname);});page.on('pageerror',e=>errors.push(e.message));
 const started=performance.now();await page.goto('/?world='+world);await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});const readySignalMs=performance.now()-started;await quiet(page);const first=await stats(page),lod=await screenshot(page,info,'lod-start');
 expect(first.pages).toBeLessThanOrEqual(8);expect(first.selected).toBeGreaterThan(1000);expect(first.errors).toEqual([]);expect(requests.some(p=>p.endsWith('.spz'))).toBe(false);
 const slider=page.getByRole('slider',{name:'Recorded camera view'});await slider.focus();await slider.press('End');await expect.poll(()=>page.locator('canvas').getAttribute('data-path-progress').then(Number)).toBe(23);await quiet(page);const end=await stats(page);expect(end.pages).toBeLessThanOrEqual(8);await screenshot(page,info,'lod-end');
 await slider.press('Home');await expect.poll(()=>page.locator('canvas').getAttribute('data-path-progress').then(Number)).toBe(0);await quiet(page);const reverse=await stats(page);expect(reverse.pages).toBeLessThanOrEqual(8);
 await page.getByRole('button',{name:'전체 SPZ로 비교',exact:true}).click();await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});await expect.poll(()=>page.locator('canvas').getAttribute('data-frame-count').then(Number)).toBeGreaterThan(30);const full=await screenshot(page,info,'whole-start');expect(full.width).toBe(lod.width);expect(full.height).toBe(lod.height);
 let sum=0,changed=0,colored=0;for(let i=0;i<lod.data.length;i+=4){let max=0;for(let c=0;c<3;c++){const d=Math.abs(lod.data[i+c]-full.data[i+c]);sum+=d;max=Math.max(max,d);}if(max>20)changed++;if(Math.max(...lod.data.subarray(i,i+3))-Math.min(...lod.data.subarray(i,i+3))>12)colored++;}
 const mae=sum/(lod.width*lod.height*3),changedFraction=changed/(lod.width*lod.height);expect(colored).toBeGreaterThan(10000);
 // Appearance is measured and reported; do not relabel an unexpected result as PASS.
 const quality=mae<=5&&changedFraction<=.10?'PASS':'FAIL';expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS execution',quality,qualityThreshold:{mae:5,changedFraction:.10},mae,changedFraction,first,end,reverse,readySignalMs,firstSettledBytes:first.bytes,scope:'One-off actual short-Paris LoD paging, not kilometer-scale or independent geometry acceptance',browser:browser.version(),headed:process.env.HEADLESS!=='1',cacheDisabled:true,requests,errors},null,2));
});
