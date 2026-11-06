#!/usr/bin/env node
// One bounded codec comparison, using frozen raw SfM cameras and explicitly derived display views.
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { Matrix4 } from 'three';
import { PNG } from 'pngjs';

const [configPath,ply,spz,out] = process.argv.slice(2);
if (!out) throw new Error('Usage: compare-compression.mjs EXISTING_RENDER_CONFIG PLY SPZ NEW_OUTPUT');
await mkdir(out,{recursive:false});
const source=JSON.parse(await readFile(configPath,'utf8'));
const cameras=source.cameras.filter(c=>c.kind==='held');
const origin=cameras.find(c=>c.pitch===0);
if (!origin || source.resolution!==1024) throw new Error('Require frozen 1024px matched cameras');
// Existing real pinhole matrices keep their original coordinates. Up/down are display rotations only.
for (const pitch of [-80,80]) for(const base of source.cameras.filter(c=>c.kind==='held'&&c.pitch===0).filter((_,i)=>i%2===0)) {
  const m=new Matrix4().set(...base.transform_matrix.flat()).multiply(new Matrix4().makeRotationX(pitch*Math.PI/180));
  const a=m.toArray();cameras.push({...base,id:`display-${base.yaw}-pitch${pitch}`,kind:'display',pitch,
    reference:null,transform_matrix:[0,1,2,3].map(r=>[0,1,2,3].map(c=>a[c*4+r]))});
}
// Keep the existing49-frame movement sequence; camera labels do not imply measured surfaces.
cameras.push(...source.cameras.filter(c=>c.kind==='path'));
const config={resolution:1024,cameras,models:[{id:'ply',ply:path.resolve(ply)},{id:'spz',ply:path.resolve(spz)},{id:'ply-repeat',ply:path.resolve(ply)}]};
await writeFile(path.join(out,'config.json'),JSON.stringify(config,null,2)+'\n');
const protocol={createdAt:new Date().toISOString(),purpose:'Storage representation only; unchanged reconstruction',
  comparison:'same cameras, resolution, renderer and settled-frame policy; all directional and movement cases retained',
  appearanceScreen:{activeRgbMeanAbsoluteErrorAtMost:2,activeRgbPsnrAtLeast:35,scope:'heuristic codec screen, not geometric accuracy or universal perceptual equivalence'},
  repeatControl:'Original PLY reloaded and rendered a second time to expose renderer variability',
  publicDownloadPerformance:'Measured separately; local uncompressed HTTP timings are not Railway transfer speed'};
await writeFile(path.join(out,'protocol.json'),JSON.stringify(protocol,null,2)+'\n');
const exit=await new Promise((resolve,reject)=>{const child=spawn(process.execPath,['scripts/render-street.mjs',path.join(out,'config.json'),path.join(out,'renders')],{stdio:'inherit'});child.on('error',reject);child.on('exit',resolve);});
if(exit!==0)throw new Error('Actual renderer failed; retain output report');
const rows=[],repeat=[];
for(const c of cameras){
  const a=PNG.sync.read(await readFile(path.join(out,'renders/ply',c.id+'.png'))),alpha=PNG.sync.read(await readFile(path.join(out,'renders/ply',c.id+'-rgba.png')));
  for(const [candidate,list] of [['spz',rows],['ply-repeat',repeat]]){
    const b=PNG.sync.read(await readFile(path.join(out,'renders',candidate,c.id+'.png'))),bAlpha=PNG.sync.read(await readFile(path.join(out,'renders',candidate,c.id+'-rgba.png')));
    let count=0,sum=0,squares=0,max=0;const histogram=new Uint32Array(256);
    for(let i=0;i<a.data.length;i+=4){if(alpha.data[i+3]<=25&&bAlpha.data[i+3]<=25)continue;count++;
      for(let k=0;k<3;k++){const d=Math.abs(a.data[i+k]-b.data[i+k]);sum+=d;squares+=d*d;max=Math.max(max,d);histogram[d]++;}}
    if(!count)throw new Error('No active comparison pixels: '+c.id);
    let cumulative=0,p99=255;for(let j=0;j<256;j++){cumulative+=histogram[j];if(cumulative>=count*3*.99){p99=j;break;}}
    const mae=sum/(count*3),mse=squares/(count*3),psnr=mse===0?null:10*Math.log10(255**2/mse);
    list.push({id:c.id,kind:c.kind,activePixels:count,mae,psnr,infinitePsnr:mse===0,p99ChannelDifference:p99,maxChannelDifference:max,
      screenPass:mae<=protocol.appearanceScreen.activeRgbMeanAbsoluteErrorAtMost&&(psnr===null||psnr>=protocol.appearanceScreen.activeRgbPsnrAtLeast)});
  }
}
const average=(list,k)=>list.reduce((s,r)=>s+r[k],0)/list.length;
const summary={status:'PASS',renderedFrames:cameras.length*3,comparedViews:cameras.length,sourceConfigSha256:(await import('./compress-world.mjs')).sha256(await readFile(configPath)),
  appearanceScreen:rows.every(r=>r.screenPass)?'PASS':'FAIL',activeRgbMae:average(rows,'mae'),worstViewMae:Math.max(...rows.map(r=>r.mae)),
  minViewPsnr:Math.min(...rows.filter(r=>r.psnr!==null).map(r=>r.psnr)),repeatMeanMae:average(repeat,'mae'),repeatWorstMae:Math.max(...repeat.map(r=>r.mae)),
  rows,repeat,visualInspection:'NOT RUN',independentGeometry:'NOT RUN'};
await writeFile(path.join(out,'comparison.json'),JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify({...summary,rows:undefined,repeat:undefined},null,2));
