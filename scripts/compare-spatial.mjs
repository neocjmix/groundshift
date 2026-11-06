#!/usr/bin/env node
// Actual pinned Spark renders: whole SPZ vs the union of independently decoded chunks.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createServer as createHttpServer} from 'node:http';
import {createReadStream} from 'node:fs';
import path from 'node:path';
import {createServer} from 'vite';
import {chromium} from '@playwright/test';
import {PNG} from 'pngjs';

const [folder,output,nativePly]=process.argv.slice(2);if(!nativePly)throw new Error('Usage: compare-spatial.mjs STREAM_WORLD NEW_OUTPUT NATIVE_PLY');
await mkdir(output,{recursive:false});const report={status:'RUNNING',views:[],meaning:'Same-camera actual GS rendering. All-chunk union compared with whole SPZ; not lazy subset equality or independent geometric accuracy.'};
const start=performance.now(),manifest=JSON.parse(await readFile(path.join(folder,'world.json'),'utf8')),index=JSON.parse(await readFile(path.join(folder,'chunks/index.json'),'utf8')),cameras=JSON.parse(await readFile(path.join(folder,'cameras.json'),'utf8'));
const files=['scene.spz',...index.chunks.map(c=>'chunks/'+c.path)],nativeId=files.length,mapped=new Map([...files.map((name,i)=>['/asset/'+i,path.join(folder,name)]),['/asset/'+nativeId,nativePly]]);
let vite,browser,http;
try{
 http=createHttpServer((req,res)=>{const file=mapped.get(req.url);if(!file){res.writeHead(404);res.end();return;}res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('Content-Type','application/octet-stream');createReadStream(file).pipe(res);});await new Promise(r=>http.listen(4329,'127.0.0.1',r));
 const source=`import * as T from 'three';import {SparkRenderer,SplatMesh,SplatFileType} from '@sparkjsdev/spark';
 const renderer=new T.WebGLRenderer({alpha:false,antialias:false,preserveDrawingBuffer:true});renderer.setSize(768,768);renderer.setClearColor(0x111614,1);document.body.append(renderer.domElement);const scene=new T.Scene(),spark=new SparkRenderer({renderer});scene.add(spark);const camera=new T.PerspectiveCamera(80,1,.01,10000);let meshes=[];
 window.load=async(ids)=>{for(const m of meshes){scene.remove(m);m.dispose();}meshes=[];for(const id of ids){const response=await fetch('http://127.0.0.1:4329/asset/'+id);if(!response.ok)throw new Error('assetHTTP'+response.status);const m=new SplatMesh({fileBytes:new Uint8Array(await response.arrayBuffer()),fileType:id===${nativeId}?SplatFileType.PLY:SplatFileType.SPZ});await m.initialized;const t=${JSON.stringify(manifest.coordinates.assetToWorld)};m.position.fromArray(t.position);m.quaternion.fromArray(t.quaternion);m.scale.setScalar(t.scale);scene.add(m);meshes.push(m);}return meshes.reduce((n,m)=>n+m.numSplats,0);};
 window.draw=async(matrix,yaw,pitch)=>{const m=new T.Matrix4().set(...matrix.flat());m.decompose(camera.position,camera.quaternion,camera.scale);camera.quaternion.multiply(new T.Quaternion().setFromEuler(new T.Euler(pitch,yaw,0,'YXZ')));const times=[];for(let i=0;i<30;i++){const t=performance.now();renderer.render(scene,camera);await new Promise(requestAnimationFrame);times.push(performance.now()-t);}return{png:renderer.domElement.toDataURL('image/png'),times};};`;
 vite=await createServer({configFile:false,root:process.cwd(),plugins:[{name:'spatial-control',configureServer(s){s.middlewares.use((req,res,next)=>{if(req.url==='/control/'){res.setHeader('Content-Type','text/html');res.end('<body style="margin:0"><script type="module" src="/control/main.js"></script>');}else next();});},resolveId(id){if(id==='/control/main.js')return'\0spatial-control';},load(id){if(id==='\0spatial-control')return source;}}],server:{host:'127.0.0.1',port:4328,strictPort:true,hmr:false,watch:{ignored:['**/data/**','**/dist/**']}}});await vite.listen();
 browser=await chromium.launch({channel:'chrome',headless:false});const page=await browser.newPage({viewport:{width:768,height:768},deviceScaleFactor:1}),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('http://127.0.0.1:4328/control/');await page.waitForFunction(()=>typeof window.draw==='function');
 const views=[0,4,8,12,16,20,23].flatMap(p=>[0,Math.PI].map((yaw,i)=>({id:`p${p}-${i}`,matrix:cameras.frames[p].cameraToWorld,yaw,pitch:0}))),images=new Map(),nativeImages=new Map();
 for(const pitch of [-Math.PI/3,Math.PI/3])views.push({id:'vertical-'+pitch.toFixed(2),matrix:cameras.frames[12].cameraToWorld,yaw:0,pitch});
 for(const [mode,ids] of [['native',[nativeId]],['whole',[0]],['native-reload',[nativeId]],['union',files.slice(1).map((_,i)=>i+1)]]){
  const before=performance.now(),splats=await page.evaluate(ids=>window.load(ids),ids);if(splats!==index.totalSplats)throw new Error('Actual decoded count mismatch');report[mode]={splats,loadMs:performance.now()-before};
  for(const v of views){const result=await page.evaluate(v=>window.draw(v.matrix,v.yaw,v.pitch),v),bytes=Buffer.from(result.png.split(',')[1],'base64');await writeFile(path.join(output,mode+'-'+v.id+'.png'),bytes);const png=PNG.sync.read(bytes);
   if(mode==='native')nativeImages.set(v.id,png.data);else{if(mode==='whole')images.set(v.id,png.data);const original=(mode==='union'?images:nativeImages).get(v.id),hist=new Uint32Array(256);let total=0;for(let i=0;i<png.data.length;i+=4)for(let c=0;c<3;c++){const d=Math.abs(png.data[i+c]-original[i+c]);total+=d;hist[d]++;}let n=0,p99=255;for(let k=0;k<256;k++){n+=hist[k];if(n>=768*768*3*.99){p99=k;break;}}report.views.push({id:v.id,mode,mae:total/(768*768*3),p99,displayFrameMs:result.times});}
  }
 }
 report.errors=errors;report.browser=browser.version();report.headed=true;report.meanMae=report.views.reduce((n,v)=>n+v.mae,0)/report.views.length;report.thresholds={whole:{mae:3,p99:24},union:{mae:2,p99:12},'native-reload':{mae:.2,p99:1}};report.status=errors.length===0&&report.views.every(v=>v.mae<=report.thresholds[v.mode].mae&&v.p99<=report.thresholds[v.mode].p99)?'PASS':'FAIL';
}catch(error){report.status='FAIL';report.error=String(error.stack??error);}
finally{await browser?.close();await vite?.close();await new Promise(r=>http?http.close(r):r());report.seconds=(performance.now()-start)/1000;await writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');console.log(report.status,report.meanMae,report.error??'');}
if(report.status!=='PASS')process.exitCode=1;
