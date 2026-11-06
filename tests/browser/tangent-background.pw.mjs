import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {PNG} from 'pngjs';
import path from 'node:path';
const summary=JSON.parse(await readFile(path.join(process.env.GS_EXPECTATION_ROOT||'public','experiments/tangent-background/summary.json'),'utf8'));

test('tangent observation shows actual phase, selected inputs, pending stages and retained history',async({page},info)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/experiments/tangent-background/');
  await expect(page.locator('#status')).toHaveText('공개 단계 · '+summary.phase);
  await expect(page.locator('#title')).toHaveText(summary.title);
  await expect(page.locator('#stages .street-stage')).toHaveCount(summary.stages.length);
  const images=page.locator('#samples img');await expect(images).toHaveCount(summary.samples.reduce((n,s)=>n+1+Number(Boolean(s.baseline)),0));
  for(const img of await images.all())await img.scrollIntoViewIfNeeded();
  await expect.poll(()=>images.evaluateAll(imgs=>imgs.every(i=>i.complete&&i.naturalWidth>0)),{timeout:30000}).toBe(true);
  for(const img of await page.locator('#comparisons img').all()){await img.scrollIntoViewIfNeeded();await expect.poll(()=>img.evaluate(i=>i.complete&&i.naturalWidth>0)).toBe(true);}
  if(summary.run?.world)await expect(page.locator('#new-world')).toHaveAttribute('href','/?world='+summary.run.world);else await expect(page.locator('#new-world')).toBeHidden();
  const rows=page.locator('#metrics tbody tr');await expect(rows).toHaveCount(summary.metrics?.length??0);
  for(let i=0;i<(summary.metrics?.length??0);i++){const m=summary.metrics[i];await expect(rows.nth(i).locator('td').nth(0)).toHaveText(m.label);await expect(rows.nth(i).locator('td').nth(1)).toHaveText(m.baseline.toFixed(3)+(m.unit??''));await expect(rows.nth(i).locator('td').nth(2)).toHaveText(m.candidate.toFixed(3)+(m.unit??''));}
  if(summary.video){const video=page.locator('#motion');await video.scrollIntoViewIfNeeded();await video.evaluate(v=>v.load());await expect.poll(()=>video.evaluate(v=>v.readyState),{timeout:30000}).toBeGreaterThanOrEqual(2);expect(await video.evaluate(v=>v.duration)).toBeGreaterThan(1);
    await video.evaluate(v=>new Promise(resolve=>{v.addEventListener('seeked',resolve,{once:true});v.currentTime=Math.min(3,v.duration/2);}));const frame=await video.evaluate(v=>{const c=document.createElement('canvas');c.width=128;c.height=128;c.getContext('2d').drawImage(v,0,0,128,128);return c.toDataURL();});expect(Buffer.from(frame.split(',')[1],'base64').length).toBeGreaterThan(1000);}
  await expect(page.locator('canvas,iframe')).toHaveCount(0);
  await page.screenshot({path:info.outputPath('report.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test('tangent report errors remain explicit and previous observations remain discoverable',async({page})=>{
  await page.route('**/experiments/tangent-background/summary.json',r=>r.fulfill({status:503,body:'SYNTHETIC ERROR'}));
  await page.goto('/experiments/tangent-background/');await expect(page.locator('#status')).toContainText('불러오기 FAIL');
  await page.goto('/experiments/lab/');for(const id of ['report-tangent-background','report-final-quality','report-model-selection'])await expect(page.locator(`.entry[data-id="${id}"]`)).toHaveCount(1);
  await page.goto('/');await expect(page.getByRole('link',{name:'최신 · 이십면체 방향과 배경 보완',exact:true})).toHaveAttribute('href','/experiments/tangent-background/');
});

function colored(png){let n=0;for(let i=0;i<png.data.length;i+=4)if(Math.max(...png.data.subarray(i,i+3))>65)n++;return n;}
async function captureCanvas(page,canvas,path){const style=await page.addStyleTag({content:'.scene-shell > :not(.canvas-mount){visibility:hidden!important}'});try{return PNG.sync.read(await canvas.screenshot({path}));}finally{await style.evaluate(e=>e.remove());}}

for(const legacy of [false,true])test(`actual tangent GS explores without background controls or requests${legacy?' even from an archived background reference':''}`,async({page,browser},info)=>{
  test.skip(!summary.run?.world,'New native scene has not exported; actual GS rendering NOT RUN.');
  const errors=[],backgroundRequests=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/\/background\//.test(r.url()))backgroundRequests.push(r.url());});
  if(legacy){
    // Only the retired metadata reference is a fixture. GS bytes and poses are real.
    await page.route('**/worlds/street-tangent20/world.json',async route=>{
      const response=await route.fetch();const world=await response.json();world.background={path:'background/background.json'};
      await route.fulfill({response,json:world});
    });
  }
  await page.goto('/?world='+encodeURIComponent(summary.run.world));
  await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});
  await expect(page.getByRole('link',{name:'Comparison & stage history ↗'})).toHaveAttribute('href','/experiments/tangent-background/');
  const canvas=page.locator('canvas');
  await expect(page.getByRole('combobox',{name:'Background completion'})).toHaveCount(0);
  await expect(page.locator('.background-panel,.background-warning')).toHaveCount(0);
  await expect.poll(()=>canvas.getAttribute('data-frame-count').then(Number)).toBeGreaterThan(12);
  const gsOnly=await captureCanvas(page,canvas,info.outputPath('gs-only.png'));const gsColored=colored(gsOnly);expect(gsColored).toBeGreaterThan(10000);
  const positionBefore=await canvas.getAttribute('data-camera-position');
  await page.getByRole('button',{name:'Play path',exact:true}).click();
  await expect.poll(()=>canvas.getAttribute('data-path-progress').then(Number)).toBeGreaterThan(.1);
  await page.getByRole('button',{name:'Pause path',exact:true}).click();
  expect(await canvas.getAttribute('data-camera-position')).not.toBe(positionBefore);
  await canvas.focus();for(let i=0;i<20;i++)await canvas.press('ArrowUp');
  await captureCanvas(page,canvas,info.outputPath('look-up.png'));
  for(let i=0;i<40;i++)await canvas.press('ArrowDown');
  await captureCanvas(page,canvas,info.outputPath('look-down.png'));
  expect(backgroundRequests).toEqual([]);expect(errors).toEqual([]);
  await writeFile(info.outputPath('evidence.json'),JSON.stringify({browser:browser.version(),world:summary.run.world,gsOnlyColoredPixels:gsColored,backgroundRequests,legacyReferenceFixture:legacy,actualNativeScene:true,translation:true,freeLook:true,errors,geometryAccuracy:'NOT RUN'},null,2));
});
