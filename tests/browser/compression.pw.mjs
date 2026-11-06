import { test,expect } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
import { PNG } from 'pngjs';

test('compression report exposes both real formats, evidence and mobile layout',async({page},info)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/experiments/compression/');
  await expect(page.locator('#summary')).toContainText('78.3%');
  await expect(page.getByRole('link',{name:'작은 SPZ 장면 열기 ↗'})).toHaveAttribute('href','/?world=/worlds/street-tangent20-spz/world.json');
  await expect(page.getByRole('link',{name:'보존한 원본 PLY 열기 ↗'})).toHaveAttribute('href','/?world=/worlds/street-tangent20/world.json');
  for(const img of await page.locator('#comparisons img').all()){await img.scrollIntoViewIfNeeded();await expect.poll(()=>img.evaluate(i=>i.complete&&i.naturalWidth>0),{timeout:30000}).toBe(true);}
  const video=page.locator('#motion');
  if(await video.isVisible()){
    await video.scrollIntoViewIfNeeded();
    const frames=await video.evaluate(async v=>{
      v.muted=true;
      const sample=target=>new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>reject(new Error('Decoded video frame timeout')),30000);
        const next=(_now,metadata)=>{if(metadata.mediaTime<target){v.requestVideoFrameCallback(next);return;}
          v.pause();clearTimeout(timer);const canvas=document.createElement('canvas');canvas.width=320;canvas.height=169;
          canvas.getContext('2d').drawImage(v,0,0,320,169);resolve({time:metadata.mediaTime,png:canvas.toDataURL('image/png')});};
        v.requestVideoFrameCallback(next);v.play().catch(reject);
      });
      return [await sample(.2),await sample(2.3)];
    });
    expect(frames[1].time-frames[0].time).toBeGreaterThan(1);expect(frames[1].png).not.toBe(frames[0].png);
    await writeFile(info.outputPath('decoded-frame-first.png'),Buffer.from(frames[0].png.split(',')[1],'base64'));
    await writeFile(info.outputPath('decoded-frame-later.png'),Buffer.from(frames[1].png.split(',')[1],'base64'));
    await writeFile(info.outputPath('video-evidence.json'),JSON.stringify({status:'PASS',decodedMediaTimes:frames.map(f=>f.time),actualDecodedFrameChange:true},null,2));
  }
  await page.screenshot({path:info.outputPath('report.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(errors).toEqual([]);
  await page.goto('/experiments/lab/');await expect(page.locator('a[href="/experiments/compression/"]').first()).toBeVisible();
});

for(const [id,extension,bytes] of [['street-tangent20-spz','spz',15936671],['street-tangent20','ply',73600652]]){
  test(`actual ${extension} browser render, transfer evidence and movement`,async({page,browser},info)=>{
    const errors=[],background=[];let response;
    page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('/background/'))background.push(r.url());});
    page.on('response',r=>{if(new URL(r.url()).pathname===`/worlds/${id}/scene.${extension}`)response=r;});
    const cdp=await page.context().newCDPSession(page);await cdp.send('Network.enable');await cdp.send('Network.setCacheDisabled',{cacheDisabled:true});
    const started=performance.now();await page.goto('/?world='+encodeURIComponent(`/worlds/${id}/world.json`));
    await expect(page.locator('.scene-shell')).toHaveAttribute('data-phase','ready',{timeout:120000});
    const readyMilliseconds=performance.now()-started,canvas=page.locator('canvas');
    await expect.poll(()=>canvas.getAttribute('data-frame-count').then(Number)).toBeGreaterThan(12);
    const style=await page.addStyleTag({content:'.scene-shell > :not(.canvas-mount){visibility:hidden!important}'});
    const image=PNG.sync.read(await canvas.screenshot({path:info.outputPath('actual-render.png')}));await style.evaluate(e=>e.remove());
    let colored=0;for(let i=0;i<image.data.length;i+=4)if(Math.max(...image.data.subarray(i,i+3))>65)colored++;
    expect(colored).toBeGreaterThan(10000);
    const asset=await page.evaluate(ext=>{const r=performance.getEntriesByType('resource').find(r=>r.name.endsWith('/scene.'+ext));return r?{encodedBodySize:r.encodedBodySize,decodedBodySize:r.decodedBodySize,transferSize:r.transferSize,downloadMilliseconds:r.responseEnd-r.startTime,responseMilliseconds:r.responseEnd-r.responseStart}:null;},extension);
    expect(asset.decodedBodySize).toBe(bytes);
    const before=await canvas.getAttribute('data-camera-position');await page.getByRole('button',{name:'Play path',exact:true}).click();
    await expect.poll(()=>canvas.getAttribute('data-path-progress').then(Number)).toBeGreaterThan(.1);await page.getByRole('button',{name:'Pause path',exact:true}).click();
    expect(await canvas.getAttribute('data-camera-position')).not.toBe(before);
    const rotation=await canvas.getAttribute('data-camera-quaternion');await canvas.focus();for(let i=0;i<20;i++)await canvas.press('ArrowUp');
    expect(await canvas.getAttribute('data-camera-quaternion')).not.toBe(rotation);
    for(let i=0;i<40;i++)await canvas.press('ArrowDown');
    await canvas.screenshot({path:info.outputPath('look-down.png')});
    if(extension==='spz')await expect(page.getByRole('link',{name:'Comparison & stage history ↗'})).toHaveAttribute('href','/experiments/compression/');
    expect(errors).toEqual([]);expect(background).toEqual([]);expect(response.status()).toBe(200);
    await writeFile(info.outputPath('evidence.json'),JSON.stringify({status:'PASS',world:id,browser:browser.version(),headed:process.env.HEADLESS!=='1',origin:process.env.GS_BASE_URL??'http://127.0.0.1:4318',
      cacheDisabled:true,readyMilliseconds,asset,contentEncoding:response.headers()['content-encoding']??null,coloredPixels:colored,translation:true,freeLook:true,backgroundRequests:background,errors,
      measurementLimits:'One cold browser context per format; order SPZ then PLY, uncontrolled network/server cache, not a statistical speed claim. Ready means 3 submitted frames; screenshot separately confirms visible pixels. Not a GPU-memory benchmark.'},null,2));
  });
}
