import { describe,it,expect,vi } from 'vitest';
import { ChunkStream,nearbyChunks,parseStreamIndex,type StreamIndex } from './streaming';
const index:StreamIndex={schemaVersion:1,coordinateSpace:'viewer-world',totalSplats:60,maxResidentChunks:3,chunks:Array.from({length:6},(_,i)=>({id:''+i,path:i+'.spz',splats:10,bytes:100,sha256:'a'.repeat(64),anchors:[[i*10,0,0]]}))};
const tick=()=>new Promise(r=>setTimeout(r,0));
describe('real streaming contracts with synthetic resources',()=>{
 it('rejects duplicate ownership and count mismatch/unsafe paths',()=>{expect(()=>parseStreamIndex({...index,totalSplats:59})).toThrow();expect(()=>parseStreamIndex({...index,chunks:[index.chunks[0],index.chunks[0]]})).toThrow();expect(()=>parseStreamIndex({...index,chunks:[{...index.chunks[0],path:'../secret'}]})).toThrow();});
 it('selects a bounded neighborhood in either direction and at ends',()=>{expect(nearbyChunks(index,[0,0,0])).toEqual(['0','1','2']);expect(nearbyChunks(index,[50,0,0])).toEqual(['5','4','3']);expect(new Set(nearbyChunks(index,[20,0,0]))).toEqual(new Set(['1','2','3']));expect(()=>nearbyChunks(index,[NaN,0,0])).toThrow();});
 it('evicts on a jump and disposes late uncancellable decode before next load',async()=>{
  let finish!:(v:{dispose:()=>void})=>void;const late={dispose:vi.fn()},shown=vi.fn(),hidden=vi.fn();
  const load=vi.fn((c:unknown,u:string,signal:AbortSignal)=>{void c;void u;void signal;return new Promise<{dispose:()=>void}>(r=>finish=r);});const s=new ChunkStream({index,urls:new Map(index.chunks.map(c=>[c.id,c.path]))},{load,show:shown,hide:hidden});
  s.select(['0']);s.select(['5']);expect(load).toHaveBeenCalledTimes(1);expect(load.mock.calls[0][2].aborted).toBe(true);finish(late);await tick();expect(late.dispose).toHaveBeenCalledOnce();expect(shown).not.toHaveBeenCalled();expect(load).toHaveBeenCalledTimes(2);s.dispose();finish(late);await tick();expect(late.dispose).toHaveBeenCalledTimes(2);
 });
 it('releases old meshes, counts real transfers and retries failures explicitly',async()=>{
  let fail=true;const owned:{dispose:ReturnType<typeof vi.fn>}[]=[];
  const s=new ChunkStream({index,urls:new Map(index.chunks.map(c=>[c.id,c.path]))},{load:async(c,_u,_s,bytes)=>{bytes(c.bytes);if(c.id==='5'&&fail)throw new Error('HTTP503');const r={dispose:vi.fn()};owned.push(r);return r;},show:vi.fn(),hide:vi.fn()});
  s.select(['0']);await tick();expect(s.stats().splats).toBe(10);s.select(['5']);await tick();expect(owned[0].dispose).toHaveBeenCalledOnce();expect(s.stats().resident).toBe(0);expect(s.stats().errors[0]).toContain('503');s.select(['5']);await tick();expect(s.stats().requested).toBe(2);fail=false;s.retry();await tick();expect(s.stats().resident).toBe(1);expect(s.stats().transferredBytes).toBe(300);s.dispose();expect(owned[1].dispose).toHaveBeenCalledOnce();
 });
});
