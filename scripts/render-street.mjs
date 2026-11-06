#!/usr/bin/env node
// Batch real headed Chrome/Spark renders of explicit observed/derived cameras.
// Coordinates stay in raw Brush/SfM space, without a second display transform.
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createServer } from 'vite';
import { chromium } from '@playwright/test';
import { PNG } from 'pngjs';

const [configPath, outputPath] = process.argv.slice(2);
if (!configPath || !outputPath) throw new Error('Usage: render-street.mjs CONFIG.json NEW_OUTPUT');
const config = JSON.parse(await readFile(configPath,'utf8'));
const resolution=config.resolution??512;
if(!Number.isInteger(resolution)||resolution<64||resolution>2048||config.cameras.some(c=>c.w!==resolution||c.h!==resolution))throw new Error('Require matching square camera/output resolution64..2048');
const output = path.resolve(outputPath);await mkdir(output,{ recursive:false });
const started=performance.now();const report={status:'RUNNING',startedAt:new Date().toISOString(),models:[],poseMeaning:config.poseMeaning??'Observed poses from preserved all-nine SfM, or explicitly interpolated/extrapolated display poses. No independent geometry truth.'};
let server,browser;
try {
  const assets=new Map(config.models.map(m=>[m.id,path.resolve(m.ply)]));
  const source=`
import * as THREE from 'three';
import {SparkRenderer,SplatMesh,SplatFileType} from '@sparkjsdev/spark';
let renderer,scene,camera,spark,mesh;
const pause=()=>new Promise(requestAnimationFrame);
window.loadStreet=async(id)=>{
 if(mesh){scene.remove(mesh);mesh.dispose();spark.dispose();renderer.dispose();document.body.replaceChildren();}
 renderer=new THREE.WebGLRenderer({alpha:true,premultipliedAlpha:true,antialias:false,preserveDrawingBuffer:true});
 renderer.setPixelRatio(1);renderer.setSize(${resolution},${resolution});renderer.setClearColor(0x000000,0);document.body.append(renderer.domElement);
 scene=new THREE.Scene();camera=new THREE.PerspectiveCamera();spark=new SparkRenderer({renderer});scene.add(spark);
 const downloadStart=performance.now();
 const response=await fetch('/street-asset/'+id,{cache:'no-store'});if(!response.ok)throw new Error('Asset HTTP '+response.status);
 const fileBytes=new Uint8Array(await response.arrayBuffer()),downloadMilliseconds=performance.now()-downloadStart;
 const format=${JSON.stringify(Object.fromEntries(config.models.map(m=>[m.id,path.extname(m.ply).slice(1)])))}[id];
 const decodeStart=performance.now();
 mesh=new SplatMesh({fileBytes,fileType:format==='spz'?SplatFileType.SPZ:SplatFileType.PLY});scene.add(mesh);await mesh.initialized;
 const decodeMilliseconds=performance.now()-decodeStart;
 const gl=renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');
 return {splats:mesh.numSplats,downloadMilliseconds,decodeMilliseconds,assetBytes:fileBytes.length,gpu:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER)};
};
window.renderStreet=async(c,waitFrames)=>{
 const near=.01,far=10000;camera.near=near;camera.far=far;
 camera.projectionMatrix.makePerspective(-c.cx*near/c.fl_x,(c.w-c.cx)*near/c.fl_x,c.cy*near/c.fl_y,-(c.h-c.cy)*near/c.fl_y,near,far);
 camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
 camera.matrix.fromArray(c.transform_matrix[0].map((_,i)=>c.transform_matrix.map(row=>row[i])).flat());
 camera.matrix.decompose(camera.position,camera.quaternion,camera.scale);camera.updateMatrixWorld(true);
 const timings=[];
 for(let i=0;i<waitFrames;i++){const before=performance.now();renderer.render(scene,camera);await pause();timings.push(performance.now()-before);}
 return {png:renderer.domElement.toDataURL('image/png'),timings};
};`;
  server=await createServer({configFile:false,root:process.cwd(),
    plugins:[{name:'street-render',configureServer(s){s.middlewares.use(async(req,res,next)=>{
      if(req.url==='/street-render/'){res.setHeader('Content-Type','text/html');res.end('<body style="margin:0;background:#000"><script type="module" src="/street-render/main.js"></script>');}
      else if(req.url?.startsWith('/street-asset/')){
        const filename=assets.get(req.url.slice('/street-asset/'.length));
        if(!filename){res.statusCode=404;res.end();return;}
        try{const info=await stat(filename);res.setHeader('Content-Type','application/octet-stream');res.setHeader('Content-Length',info.size);createReadStream(filename).pipe(res);}catch{res.statusCode=404;res.end();}
      }else next();});},resolveId(id){if(id==='/street-render/main.js')return '\0street-render';},load(id){if(id==='\0street-render')return source;}}],
    optimizeDeps:{include:['three','@sparkjsdev/spark']},server:{host:'127.0.0.1',port:4326,strictPort:true,hmr:false,watch:{ignored:['**/data/**','**/dist/**','**/test-results/**']}}});
  await server.listen();browser=await chromium.launch({channel:'chrome',headless:false});
  const page=await browser.newPage({viewport:{width:resolution,height:resolution},deviceScaleFactor:1});const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('http://127.0.0.1:4326/street-render/');await page.waitForFunction(()=>typeof window.renderStreet==='function');
  for(const model of config.models){
    const folder=path.join(output,model.id);await mkdir(folder);const item={id:model.id,status:'RUNNING',renders:[]};report.models.push(item);const before=performance.now();
    try{
      item.assetSha256=createHash('sha256').update(await readFile(model.ply)).digest('hex');
      Object.assign(item,await page.evaluate(id=>Promise.race([window.loadStreet(id),new Promise((_,reject)=>setTimeout(()=>reject(new Error('Model load timeout')),90000))]),model.id));
      if(!item.splats)throw new Error('No actual Gaussian splats loaded');
      for(let i=0;i<config.cameras.length;i++){
        const camera=config.cameras[i];const result=await page.evaluate(async({camera,wait})=>window.renderStreet(camera,wait),{camera,wait:i===0?90:(camera.kind==='path'?4:12)});
        const rgbaBytes=Buffer.from(result.png.split(',')[1],'base64');const rgba=PNG.sync.read(rgbaBytes),rgb=new PNG({width:rgba.width,height:rgba.height});let alpha=0,colored=0;
        for(let j=0;j<rgba.data.length;j+=4){const a=rgba.data[j+3]/255;alpha+=a;if(a>.1&&Math.max(...rgba.data.subarray(j,j+3))>30)colored++;
          for(let k=0;k<3;k++)rgb.data[j+k]=Math.round(rgba.data[j+k]*a+127*(1-a));rgb.data[j+3]=255;}
        const name=camera.id+'.png';await writeFile(path.join(folder,name),PNG.sync.write(rgb));await writeFile(path.join(folder,camera.id+'-rgba.png'),rgbaBytes);
        item.renders.push({id:camera.id,kind:camera.kind,reference:camera.reference??null,meanAlpha:alpha/(rgba.width*rgba.height),coloredPixels:colored,
          rgbaSha256:createHash('sha256').update(rgbaBytes).digest('hex'),displayFrameMilliseconds:result.timings,convention:'RGB is straight-alpha PNG composited over127 grey; opacity is diagnostic, not geometry confidence.'});
      }
      if(!item.renders.some(r=>(r.kind==='held'||r.kind==='train')&&r.coloredPixels>1000))throw new Error('No actual visible scene pixels in any matched observed camera');
      item.status='PASS';
    }catch(error){item.status='FAIL';item.error=String(error.stack??error);}
    item.elapsedSeconds=(performance.now()-before)/1000;await writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');
  }
  report.errors=errors;report.browser=browser.version();report.headed=true;report.resolution=resolution;report.status=report.models.every(m=>m.status==='PASS')&&errors.length===0?'PASS':'FAIL';
}catch(error){report.status='FAIL';report.error=String(error.stack??error);}
finally{await browser?.close();await server?.close();report.finishedAt=new Date().toISOString();report.elapsedSeconds=(performance.now()-started)/1000;await writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(report.status,report.models.map(m=>({id:m.id,status:m.status,splats:m.splats,renders:m.renders.length,error:m.error})));}
if(report.status!=='PASS')process.exitCode=1;
