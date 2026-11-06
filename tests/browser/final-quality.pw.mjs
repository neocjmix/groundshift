import {test,expect} from '@playwright/test';
import {readFile,writeFile} from 'node:fs/promises';
import {PNG} from 'pngjs';

const summary=JSON.parse(await readFile('public/experiments/final-quality/summary.json','utf8'));

test('final quality report displays the actual publication phase and real source resolutions',async({page},info)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/experiments/final-quality/');
  await expect(page.locator('#status')).toHaveText('공개 단계 · '+summary.phase);
  await expect(page.locator('#title')).toHaveText(summary.title);
  await expect(page.locator('#stages .street-stage')).toHaveCount(summary.stages.length);
  const images=page.locator('#samples img');await expect(images).toHaveCount(summary.samples.reduce((n,s)=>n+1+Number(Boolean(s.baseline)),0));
  for(const image of await images.all())await image.scrollIntoViewIfNeeded();
  await expect.poll(()=>images.evaluateAll(imgs=>imgs.map(i=>i.complete?i.naturalWidth:0)),{timeout:30000}).toEqual(summary.samples.flatMap(s=>s.baseline?[1024,512]:[1024]));
  const link=page.locator('#new-world');if(summary.run?.world){await expect(link).toBeVisible();await expect(link).toHaveAttribute('href','/?world='+summary.run.world);}else await expect(link).toBeHidden();
  await expect(page.locator('iframe,canvas')).toHaveCount(0);
  await page.locator('h1').scrollIntoViewIfNeeded();await page.screenshot({path:info.outputPath('final-quality-report.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test('final quality report failure is explicit and current plus earlier observations are discoverable',async({page})=>{
  await page.route('**/experiments/final-quality/summary.json',r=>r.fulfill({status:503,body:'SIMULATED TEST FAILURE'}));
  await page.goto('/experiments/final-quality/');await expect(page.locator('#status')).toContainText('불러오기 FAIL');await expect(page.locator('#new-world')).toBeHidden();
  await page.goto('/experiments/lab/');
  for(const id of ['report-final-quality','report-model-selection','report-street-conclusion'])await expect(page.locator(`.entry[data-id="${id}"]`)).toHaveCount(1);
  await page.goto('/');await expect(page.getByRole('link',{name:'최신 · 같은 데이터의 마지막 품질 실험',exact:true})).toHaveAttribute('href','/experiments/final-quality/');
});

test('actual final quality scene renders and moves along the recovered camera route',async({page,browser},info)=>{
  test.skip(!summary.run?.world,'No completed scene exported yet; GPU rendering NOT RUN.');
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/?world='+encodeURIComponent(summary.run.world));
  await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:90000});
  await expect(page.getByRole('link',{name:'Comparison & stage history ↗'})).toHaveAttribute('href','/experiments/final-quality/');
  const canvas=page.locator('canvas');await expect.poll(()=>canvas.getAttribute('data-frame-count').then(Number)).toBeGreaterThan(10);
  const pixels=PNG.sync.read(await canvas.screenshot());let colored=0;
  for(let y=Math.floor(pixels.height*.2);y<pixels.height*.75;y++)for(let x=Math.floor(pixels.width*.2);x<pixels.width*.8;x++){
    const i=(y*pixels.width+x)*4;if(Math.max(...pixels.data.subarray(i,i+3))>65)colored++;
  }
  expect(colored).toBeGreaterThan(10000);
  const before=await canvas.getAttribute('data-camera-position');await page.getByRole('button',{name:'Play path',exact:true}).click();
  await expect.poll(()=>canvas.getAttribute('data-path-progress').then(Number)).toBeGreaterThan(.05);await page.getByRole('button',{name:'Pause path',exact:true}).click();
  expect(await canvas.getAttribute('data-camera-position')).not.toBe(before);expect(errors).toEqual([]);
  await page.screenshot({path:info.outputPath('actual-final-quality.png')});
  await writeFile(info.outputPath('evidence.json'),JSON.stringify({browser:browser.version(),world:summary.run.world,coloredPixels:colored,errors},null,2));
});
