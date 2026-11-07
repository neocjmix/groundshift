import {expect,it} from 'vitest';
import {PagedSplats,SplatFileType,SparkRenderer} from '@sparkjsdev/spark';
import {guardRoutePagedUpdates} from './route-stream';

// Actual pinned Spark continuation, with a renderer upload counter instead of
// WebGL. This verifies resource ownership, not GPU rendering or a device race.
it('prevents late Spark traversal from recreating a retired route index texture',()=>{
  const run=(guarded:boolean)=>{
    let uploads=0,released=false;
    const unused=async()=>{throw new Error('No fetch is expected in this lifecycle fixture');};
    const paged=new PagedSplats({fileType:SplatFileType.SPZ,fetchSource:{fetchRange:unused,fetchChunkFile:unused,fetchChunkById:unused}});
    paged.pager={renderer:{initTexture(){uploads++;}}} as unknown as typeof paged.pager;
    if(guarded)guardRoutePagedUpdates(paged,()=>released);
    const continuation=(SparkRenderer.prototype as unknown as {updateLodIndices:(meshes:Map<string,unknown>,updates:Record<string,unknown>)=>void}).updateLodIndices;
    const lateUpdate=(count:number)=>continuation.call({},new Map([['retired',{paged,updateMappingVersion(){}}]]),{retired:{lodId:1,numSplats:count,indices:new Uint32Array(16384)}});
    // An owned source still receives normal updates.
    lateUpdate(2);expect(uploads).toBe(1);
    released=true;paged.dispose();const empty=paged.dynoIndices.value;uploads=0;
    lateUpdate(1);const result={aborted:paged.abortController.signal.aborted,recreated:paged.dynoIndices.value!==empty,splats:paged.numSplats,uploads};
    paged.dispose();return result;
  };
  expect(run(false)).toEqual({aborted:true,recreated:true,splats:1,uploads:1});
  expect(run(true)).toEqual({aborted:true,recreated:false,splats:2,uploads:0});
});
