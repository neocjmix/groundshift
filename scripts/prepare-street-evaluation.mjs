#!/usr/bin/env node
// Explicit matched camera set and portable route from real fixed-rig poses.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {Matrix4,Vector3,Quaternion} from 'three';
import {parseArgs} from 'node:util';

const {values,positionals}=parseArgs({options:{name:{type:'string',default:'render-config.json'}},allowPositionals:true});
const [jobArg,...variantsArg]=positionals;if(!jobArg)throw new Error('Require job directory');
if(path.basename(values.name)!==values.name||!values.name.endsWith('.json'))throw new Error('Config name must be a local JSON filename');
const job=path.resolve(jobArg),variants=variantsArg.length?variantsArg:['sparse','dense','filtered','stereo'];
const read=async p=>JSON.parse(await readFile(p,'utf8'));const write=(p,v)=>writeFile(p,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
const writeOrVerify=async(p,v)=>{try{await write(p,v);}catch(error){if(error.code!=='EEXIST')throw error;const old=await read(p);if(JSON.stringify(old)!==JSON.stringify(v))throw new Error('Existing presentation or route changed: '+p);}};
const all=(await read(path.join(job,'inputs/evaluation/transforms.json'))).frames;
const matrix=f=>new Matrix4().set(...f.transform_matrix.flat());
const rowMatrix=m=>{const e=m.elements;return Array.from({length:4},(_,r)=>Array.from({length:4},(_,c)=>e[c*4+r]));};
const position=f=>new Vector3().setFromMatrixPosition(matrix(f));
const f1=all.find(f=>f.physicalPanorama===1&&f.ring==='level'),f9=all.find(f=>f.physicalPanorama===9&&f.ring==='level');
const direction=position(f9).sub(position(f1)).normalize();
const route=Array.from({length:9},(_,i)=>all.filter(f=>f.physicalPanorama===i+1&&f.ring==='level').sort((a,b)=>{
 const forward=f=>new Vector3(0,0,-1).transformDirection(matrix(f)).dot(direction);return forward(b)-forward(a);
})[0]);
const distances=route.slice(1).map((f,i)=>position(f).distanceTo(position(route[i]))).sort((a,b)=>a-b);
const baseline=(distances[3]+distances[4])/2;
const cameras=[];
for(const frame of all.filter(f=>f.physicalPanorama===5||([4,6].includes(f.physicalPanorama)&&f.ring==='level'))){
 cameras.push({...frame,id:`${frame.physicalPanorama===5?'held':'train'}-${frame.physicalPanorama}-${frame.ring}-${frame.yaw.toString().padStart(3,'0')}`,kind:frame.physicalPanorama===5?'held':'train',reference:path.resolve(job,'inputs/evaluation',frame.file_path)});
}
for(let segment=0;segment<8;segment++)for(let step=0;step<6;step++){
 const a=route[segment],b=route[segment+1],t=step/6;
 const pa=new Vector3(),pb=new Vector3(),qa=new Quaternion(),qb=new Quaternion(),scale=new Vector3();
 matrix(a).decompose(pa,qa,scale);matrix(b).decompose(pb,qb,scale);
 const m=new Matrix4().compose(pa.lerp(pb,t),qa.slerp(qb,t),new Vector3(1,1,1));
 cameras.push({...a,id:`path-${String(cameras.filter(c=>c.kind==='path').length).padStart(3,'0')}`,kind:'path',reference:null,transform_matrix:rowMatrix(m),interpolation:{fromPhysical:segment+1,toPhysical:segment+2,t},meaning:'Display interpolation between recovered centers/orientations, not another photograph or measured floor.'});
}
cameras.push({...route[8],id:'path-048',kind:'path',reference:null,meaning:'Last recovered route camera.'});
for(const sign of [-1,1]){
 const frame=route[4],m=matrix(frame),right=new Vector3().setFromMatrixColumn(m,0),p=position(frame).addScaledVector(right,sign*baseline*.25);m.setPosition(p);
 cameras.push({...frame,id:'offpath-'+(sign<0?'left':'right'),kind:'offpath',reference:null,transform_matrix:rowMatrix(m),meaning:'Deliberate display extrapolation by one quarter of median estimated adjacent baseline; not an observed camera or safe walking surface.'});
}
const config={createdAt:new Date().toISOString(),cameraConvention:'Raw SfM world; OpenGL camera+X right,+Y up,-Z forward',heldPhysicalPanorama:5,
 models:variants.map(id=>({id,ply:path.join(job,'training-'+id,'world/scene.ply')})),cameras};
await write(path.join(job,values.name),config);
await writeOrVerify(path.join(job,'route.json'),{cameraConvention:config.cameraConvention,medianBaselineSfm:baseline,frames:route});
for(const id of variants){
 const folder=path.join(job,'training-'+id,'world');
 try{
  const world=await read(path.join(folder,'world.json'));const q=new Quaternion(...world.coordinates.assetToWorld.quaternion);const rotate=new Matrix4().makeRotationFromQuaternion(q);
  const frames=route.map((f,i)=>({image:path.basename(f.file_path),componentId:'street-fixed-rig',continuousFromPrevious:i>0,cameraToWorld:rowMatrix(rotate.clone().multiply(matrix(f)))}));
  const middle=frames[4].cameraToWorld,position=middle.slice(0,3).map(r=>r[3]),forward=middle.slice(0,3).map(r=>-r[2]),up=middle.slice(0,3).map(r=>r[1]);
  world.navigation={mode:'camera-path',camera:{position,target:position.map((p,i)=>p+forward[i]*baseline*4),up,fov:90,near:.01,far:10000},camerasPath:'cameras.json'};
  world.provenance.notes+=' Display route:9 actual fixed-rig camera centers, level view closest to global route direction. Panorama5 was withheld from optimization but participates in all-image pose estimation. Route interpolation is a viewing control, not a recovered walking floor.';
  // Native exported files are retained. Write presentation documents separately.
  await mkdir(path.join(job,'presentation',id),{recursive:true});
  await writeOrVerify(path.join(job,'presentation',id,'world.json'),world);
  await writeOrVerify(path.join(job,'presentation',id,'cameras.json'),{schemaVersion:1,cameraConvention:'OpenGL: +X right, +Y up, -Z forward',worldConvention:'right-handed Y-up, arbitrary units',sequenceNotes:'Actual consecutive panorama center poses;9 observed camera centers, one level orientation each. Original5 RGB withheld from GS optimization. Continuous edge means allowed pose interpolation, not independently verified geometry or collision.',frames});
 }catch(error){if(error.code!=='ENOENT')throw error;}
}
console.log('Prepared',cameras.length,'matched renders per model; route yaws',route.map(f=>f.yaw));
