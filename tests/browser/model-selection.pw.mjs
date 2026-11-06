import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';
import { PNG } from 'pngjs';

const summary=JSON.parse(await readFile('public/experiments/model-selection/summary.json','utf8'));

test('model comparison exposes actual candidates, metrics, references and decoded motion',async({page},info)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/experiments/model-selection/');
  await expect(page.locator('h1')).toHaveText('같은 거리,다른 깊이 모델.');
  await expect(page.locator('#status')).toContainText('실제 학습·렌더 PASS');
  await expect(page.locator('#best-world')).toBeInViewport();
  await expect(page.locator('#verdict-summary')).toHaveText(summary.verdict.summary);
  await expect(page.locator('#candidates .street-stage')).toHaveCount(summary.candidates.length);
  await expect(page.locator('.street-card')).toHaveCount(summary.models.length);
  await expect(page.locator('#stages .street-stage')).toHaveCount(summary.stages.length);
  for(const id of ['held-5-level-300','held-5-down-000','train-4-level-000','offpath-left']){
    await page.selectOption('#view-select',id);
    const view=summary.views.find(v=>v.id===id),imgs=page.locator('#compare-images img');
    await expect(imgs).toHaveCount(summary.models.length+(view.source?1:0));
    await expect.poll(()=>imgs.evaluateAll(images=>images.every(i=>i.complete&&i.naturalWidth===512))).toBe(true);
    for(const region of ['band','road-band','mid-height-band']){
      await page.selectOption('#region-select',region);
      const rows=page.locator('#view-metrics tbody tr');
      for(let i=0;i<summary.models.length;i++){
        const m=summary.metrics.find(m=>m.model===summary.models[i].id&&m.view===id)?.regions[region];
        await expect(rows.nth(i).locator('td').nth(1)).toHaveText(m?m.pixelCount.toLocaleString('ko-KR'):'NOT RUN');
      }
    }
  }
  const video=page.locator('#comparison-video');await video.scrollIntoViewIfNeeded();await video.evaluate(v=>v.load());
  await expect.poll(()=>video.evaluate(v=>v.readyState)).toBeGreaterThanOrEqual(2);
  expect(await video.evaluate(v=>v.duration)).toBeGreaterThan(8);
  await video.evaluate(v=>new Promise(resolve=>{v.addEventListener('seeked',resolve,{once:true});v.currentTime=3;}));
  const decoded=await video.evaluate(v=>{const c=document.createElement('canvas');c.width=128;c.height=128;c.getContext('2d').drawImage(v,0,0,128,128);return c.toDataURL();});
  expect(Buffer.from(decoded.split(',')[1],'base64').length).toBeGreaterThan(1000);
  await video.evaluate(v=>v.play());
  await expect.poll(()=>video.evaluate(v=>v.currentTime)).toBeGreaterThan(3.5);await video.evaluate(v=>v.pause());
  const depth=page.locator('#depth-evidence img');await expect(depth).toHaveCount(summary.depthEvidence.length);
  for(const img of await depth.all())await img.scrollIntoViewIfNeeded();
  await expect.poll(()=>depth.evaluateAll(images=>images.every(i=>i.complete&&i.naturalWidth>0))).toBe(true);
  await page.locator('#verdict-title').scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('model-comparison.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await expect(page.locator('iframe,canvas')).toHaveCount(0);expect(errors).toEqual([]);
});

for(const model of summary.models.filter(m=>m.id!=='dav2'))test(`actual selected model ${model.id} renders and moves on recovered route`,async({page,browser},info)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/?world='+encodeURIComponent(model.world));
  await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:90000});
  await expect(page.getByRole('link',{name:'Comparison & stage history ↗'})).toHaveAttribute('href','/experiments/model-selection/');
  const canvas=page.locator('canvas');await expect.poll(()=>canvas.getAttribute('data-frame-count').then(Number)).toBeGreaterThan(10);
  const pixels=PNG.sync.read(await canvas.screenshot());let colored=0;
  for(let y=Math.floor(pixels.height*.2);y<pixels.height*.75;y++)for(let x=Math.floor(pixels.width*.2);x<pixels.width*.8;x++){
    const i=(y*pixels.width+x)*4;if(Math.max(...pixels.data.subarray(i,i+3))>65)colored++;
  }
  expect(colored).toBeGreaterThan(10000);
  const before=await canvas.getAttribute('data-camera-position');await page.getByRole('button',{name:'Play path',exact:true}).click();
  await expect.poll(()=>canvas.getAttribute('data-path-progress').then(Number)).toBeGreaterThan(.05);await page.getByRole('button',{name:'Pause path',exact:true}).click();
  expect(await canvas.getAttribute('data-camera-position')).not.toBe(before);expect(errors).toEqual([]);
  await page.screenshot({path:info.outputPath('actual-'+model.id+'.png')});
  await writeFile(info.outputPath('evidence.json'),JSON.stringify({browser:browser.version(),id:model.id,coloredPixels:colored,errors},null,2));
});

test('model report error state is explicit and old/new lab entries remain reachable',async({page})=>{
  await page.route('**/experiments/model-selection/summary.json',r=>r.fulfill({status:503,body:'TEST ONLY'}));
  await page.goto('/experiments/model-selection/');await expect(page.locator('#status')).toContainText('FAIL');await expect(page.locator('#open-scene')).toBeDisabled();
  await page.goto('/experiments/lab/');await expect(page.locator('.entry').first()).toHaveAttribute('data-id','report-model-selection');
  for(const id of ['report-street-conclusion',...summary.models.filter(m=>m.id!=='dav2').map(m=>'street-model-'+m.id)])await expect(page.locator(`.entry[data-id="${id}"]`)).toHaveCount(1);
});
