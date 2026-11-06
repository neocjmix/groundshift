#!/usr/bin/env node
// Storage-only spatial partition of one actual Brush scene; no separate training.
import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {inspectPly,inspectSpz,fractionalBitsFor,positionError,sha256} from './compress-world.mjs';

export function partitionOwners(points,centers,groupSize=4){
  if(!Number.isInteger(groupSize)||groupSize<1||!centers.length||[...points,...centers].some(p=>p.length!==3||!p.every(Number.isFinite)))throw new Error('Finite shared-frame points and route centers required');
  return points.map(p=>{let best=Infinity,owner=0;centers.forEach((c,i)=>{const d=c.reduce((s,v,k)=>s+(v-p[k])**2,0);if(d<best){best=d;owner=Math.floor(i/groupSize);}});return owner;});
}

export async function partitionWorld(plyDir,spzDir,output){
  await mkdir(output,{recursive:false});const started=performance.now();const report={status:'RUNNING',chunks:[],meaning:'Each native Gaussian assigned once to the nearest recorded camera region. No new geometry, retraining, duplicate opacity or coordinate recentering.'};
  try{
    const manifest=JSON.parse(await readFile(path.join(spzDir,'world.json'),'utf8')),cameras=JSON.parse(await readFile(path.join(spzDir,'cameras.json'),'utf8'));
    const bytes=await readFile(path.join(plyDir,'scene.ply')),info=inspectPly(bytes),bits=fractionalBitsFor(info);
    const t=manifest.coordinates.assetToWorld;
    if(t.scale!==1||t.position.some(v=>v!==0))throw new Error('This bounded partition requires a rotation-only asset transform');
    const [qx,qy,qz,qw]=t.quaternion;
    const rotate=p=>{const [x,y,z]=p,tx=2*(qy*z-qz*y),ty=2*(qz*x-qx*z),tz=2*(qx*y-qy*x);return[x+qw*tx+qy*tz-qz*ty,y+qw*ty+qz*tx-qx*tz,z+qw*tz+qx*ty-qy*tx];};
    const centers=cameras.frames.map(f=>f.cameraToWorld.slice(0,3).map(r=>r[3]));
    const points=Array.from({length:info.count},(_,i)=>rotate(info.axes.map(k=>bytes.readFloatLE(info.offset+i*info.stride+k))));
    const owners=partitionOwners(points,centers),count=Math.ceil(centers.length/4),groups=Array.from({length:count},()=>[]);
    owners.forEach((owner,i)=>groups[owner].push(i));
    const ownership=Buffer.alloc(owners.length*2);owners.forEach((o,i)=>ownership.writeUInt16LE(o,i*2));
    // Stored locally alongside reproducible evidence; not required by the viewer.
    await writeFile(path.join(output,'ownership.bin'),ownership,{flag:'wx'});
    await mkdir(path.join(output,'chunks'));const {transcodeSpz}=await import('@sparkjsdev/spark');
    for(let k=0;k<count;k++){
      const ids=groups[k];if(!ids.length)throw new Error('Empty route ownership region');
      const header=Buffer.from(bytes.subarray(0,info.offset).toString('ascii').replace(/^element vertex \d+$/m,'element vertex '+ids.length));
      const ply=Buffer.alloc(header.length+ids.length*info.stride);header.copy(ply);ids.forEach((id,i)=>bytes.copy(ply,header.length+i*info.stride,info.offset+id*info.stride,info.offset+(id+1)*info.stride));
      const result=await transcodeSpz({inputs:[{fileBytes:new Uint8Array(ply),fileType:'ply',pathOrUrl:'chunk.ply'}],maxSh:info.shDegree,fractionalBits:bits,opacityThreshold:0,version:3});
      const spz=Buffer.from(result.fileBytes),decoded=inspectSpz(spz),positions=positionError(ply,inspectPly(ply),decoded);
      const name=`chunk-${String(k).padStart(2,'0')}.spz`;await writeFile(path.join(output,'chunks',name),spz,{flag:'wx'});
      report.chunks.push({id:String(k),path:name,bytes:spz.length,splats:ids.length,sha256:sha256(spz),anchors:centers.slice(k*4,k*4+4),positions});
    }
    await copyFile(path.join(spzDir,'scene.spz'),path.join(output,'scene.spz'));
    await copyFile(path.join(spzDir,'cameras.json'),path.join(output,'cameras.json'));
    await copyFile(path.join(spzDir,'SOURCE_LICENSE'),path.join(output,'SOURCE_LICENSE'));
    manifest.streaming={path:'chunks/index.json'};manifest.provenance.notes+=' Spatial SPZ delivery: unique Gaussian ownership by nearest recorded center,4centers per region,3regions resident,one fetch/decode in flight. Distant visible content may disappear when its owner is unloaded; no guarantee of full-scene visual equivalence with a subset. Whole-scene control retained in scene.spz.';
    await writeFile(path.join(output,'world.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
    const index={schemaVersion:1,coordinateSpace:'viewer-world',totalSplats:info.count,maxResidentChunks:3,chunks:report.chunks.map(({positions,...c})=>c)};
    await writeFile(path.join(output,'chunks/index.json'),JSON.stringify(index,null,2)+'\n',{flag:'wx'});
    Object.assign(report,{status:'PASS',totalSplats:info.count,assignedExactlyOnce:owners.length===info.count&&groups.reduce((n,g)=>n+g.length,0)===info.count,ownershipSha256:sha256(ownership),nativePlySha256:sha256(bytes),fractionalBits:bits,chunkBytes:report.chunks.reduce((n,c)=>n+c.bytes,0),fullSpzBytes:(await readFile(path.join(spzDir,'scene.spz'))).length,allChunksRendering:'NOT RUN',lazyRendering:'NOT RUN'});
  }catch(e){report.status='FAIL';report.error=String(e.stack??e);}
  report.seconds=(performance.now()-started)/1000;await writeFile(path.join(output,'partition.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});return report;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const [ply,spz,out]=process.argv.slice(2);if(!out)throw new Error('Usage: partition-world.mjs NATIVE_VIEW_WORLD SPZ_WORLD NEW_OUTPUT');
  const result=await partitionWorld(ply,spz,out);console.log(result.status,result.chunks.map(c=>[c.id,c.splats,c.bytes]));if(result.status!=='PASS')process.exitCode=1;
}
