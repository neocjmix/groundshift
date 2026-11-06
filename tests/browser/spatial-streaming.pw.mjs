import {test,expect} from '@playwright/test';
import {writeFile} from 'node:fs/promises';
import {PNG} from 'pngjs';

const world='/worlds/paris-58m-spz/world.json';
const state=async page=>{const value=await page.locator('canvas').getAttribute('data-stream');return value?JSON.parse(value):{pending:1,resident:0};};
const settled=async page=>expect.poll(async()=>{const s=await state(page);return s.pending===0&&s.resident===3;},{timeout:120000}).toBe(true);
async function capture(page,info,name){
 const style=await page.addStyleTag({content:'.scene-shell > :not(.canvas-mount){visibility:hidden!important}'});
 const bytes=await page.locator('canvas').screenshot({path:info.outputPath(name+'.png')});await style.evaluate(e=>e.remove());
 const png=PNG.sync.read(bytes);let colored=0;
 for(let i=0;i<png.data.length;i+=4){const [r,g,b]=png.data.subarray(i,i+3);if(Math.max(r,g,b)-Math.min(r,g,b)>12&&Math.max(r,g,b)>45)colored++;}
 expect(colored).toBeGreaterThan(10000);return {coloredPixels:colored,width:png.width,height:png.height};
}
test('actual Paris SPZ lazy rendering, forward/reverse/jumps, eviction and whole-scene control',async({page,browser},info)=>{
 const cdp=await page.context().newCDPSession(page);await cdp.send('Network.enable');await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});
 const requests=[],errors=[];page.on('request',r=>{if(r.url().endsWith('.spz'))requests.push(new URL(r.url()).pathname);});page.on('pageerror',e=>errors.push(e.message));
 const started=performance.now();await page.goto('/?world='+world);
 await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});
 const readySignalMs=performance.now()-started;await settled(page);const first=await state(page);
 expect(first.resident).toBe(3);expect(first.requested).toBe(3);expect(first.errors).toEqual([]);expect(requests.every(r=>r.includes('/chunks/'))).toBe(true);
 const firstPixels=await capture(page,info,'start-lazy'),firstVerifiedVisibleMs=performance.now()-started;
 const slider=page.getByRole('slider',{name:'Recorded camera view'}),before=await page.locator('canvas').getAttribute('data-camera-position');
 await slider.focus();await slider.press('End');await expect.poll(()=>page.locator('canvas').getAttribute('data-path-progress').then(Number)).toBe(23);await settled(page);
 const end=await state(page);expect(end.resident).toBeLessThanOrEqual(3);expect(end.evicted).toBeGreaterThanOrEqual(3);expect(await page.locator('canvas').getAttribute('data-camera-position')).not.toBe(before);await capture(page,info,'end-lazy');
 await slider.press('Home');await expect.poll(()=>page.locator('canvas').getAttribute('data-path-progress').then(Number)).toBe(0);await settled(page);const reverse=await state(page);expect(reverse.evicted).toBeGreaterThanOrEqual(6);expect(reverse.requested).toBeGreaterThanOrEqual(9);
 await page.getByRole('button',{name:'Play path',exact:true}).click();await expect.poll(()=>page.locator('canvas').getAttribute('data-path-progress').then(Number)).toBeGreaterThan(.15);await page.getByRole('button',{name:'Pause path',exact:true}).click();
 await page.getByRole('button',{name:'전체 로딩으로 비교',exact:true}).click();await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});expect(requests.filter(r=>r.endsWith('/scene.spz'))).toHaveLength(1);await capture(page,info,'whole-control');
 await page.getByRole('button',{name:'구간 로딩으로 전환',exact:true}).click();await settled(page);
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath('mobile-ui.png')});
 expect(errors).toEqual([]);
 await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',scope:'Actual short Paris GS spatial lazy loading, not 2.19km reconstruction or geometry truth',browser:browser.version(),headed:process.env.HEADLESS!=='1',cacheDisabled:true,readySignalMs,firstVerifiedVisibleMs,visibleTimingMeaning:'Upper bound measured after 3 chunks settle and a screenshot proves visible pixels; includes test/screenshot overhead, not first visible GPU timestamp',first,end,reverse,firstPixels,requests,errors},null,2));
});

test('a failed real chunk shows an error, keeps other content and retries without a whole download',async({page},info)=>{
 let fail=true;const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/chunks/chunk-00.spz',async route=>{if(fail)await route.fulfill({status:503,body:'deliberate synthetic transport failure for real scene'});else await route.continue();});
 await page.goto('/?world='+world);await expect(page.getByRole('alert').filter({hasText:'구간 오류'})).toContainText('503',{timeout:120000});
 await expect.poll(async()=>(await state(page)).resident).toBeGreaterThan(0);fail=false;await page.getByRole('button',{name:'구간 다시 시도',exact:true}).click();await settled(page);expect((await state(page)).errors).toEqual([]);
 await page.screenshot({path:info.outputPath('retry-recovered.png')});expect(errors).toEqual([]);
});
