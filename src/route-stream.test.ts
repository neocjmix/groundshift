import {describe,it,expect,vi} from 'vitest';
import {Vector3} from 'three';
import {parseRouteIndex,type RouteIndex} from './world';
import {RouteStream,routeOwner,routeAssetTransform} from './route-stream';

const identity={position:[0,0,0] as [number,number,number],quaternion:[0,0,0,1] as [number,number,number,number],scale:1};
const index:RouteIndex={schemaVersion:1,coordinateSpace:'viewer-world',segments:[0,1,2].map(i=>({id:String(i),world:`s${i}/world.json`,transform:identity,anchors:[[i*10,0,0]]}))};
const tick=()=>new Promise(r=>setTimeout(r,0));
const resource=()=>({dispose:vi.fn(),alpha:1,ready:true});
const operations=()=>({load:vi.fn(async()=>resource()),show:vi.fn(),hide:vi.fn(),opacity:(r:ReturnType<typeof resource>,value:number)=>{r.alpha=value;},ready:(r:ReturnType<typeof resource>)=>r.ready});

describe('route ownership and independent-frame delivery, synthetic resources',()=>{
  it('rejects duplicate identities, unsafe references and invalid similarities',()=>{
    expect(()=>parseRouteIndex({...index,segments:[index.segments[0],index.segments[0]]})).toThrow();
    for(const patch of [{world:'../world.json'},{transform:{...identity,scale:0}},{transform:{...identity,quaternion:[1,1,1,1]}}])expect(()=>parseRouteIndex({...index,segments:[{...index.segments[0],...patch}]})).toThrow();
  });
  it('composes asset rotation/scale before segment translation without moving a world camera twice',()=>{
    const segment={...index.segments[0],transform:{...identity,position:[10,0,0] as [number,number,number],scale:3}};
    const asset={position:[1,0,0] as [number,number,number],quaternion:[0,0,Math.SQRT1_2,Math.SQRT1_2] as [number,number,number,number],scale:2};
    new Vector3(1,0,0).applyMatrix4(routeAssetTransform(segment,asset)).toArray().forEach((v,i)=>expect(v).toBeCloseTo([13,6,0][i],12));
  });
  it('has a stable dead band at a seam and supports reverse and distant jumps',()=>{
    expect(routeOwner(index,[5.2,0,0],'0').id).toBe('0');expect(routeOwner(index,[6,0,0],'0').id).toBe('1');
    expect(routeOwner(index,[4,0,0],'1').id).toBe('0');expect(routeOwner(index,[20,0,0],'0').id).toBe('2');
    expect(()=>routeOwner(index,[NaN,0,0])).toThrow();
  });
  it('retains the previous owner at a comparison-return seam without resetting the camera',async()=>{
    const op=operations(),s=new RouteStream(index,op,'0');s.update([5.2,0,0],0);await tick();expect(s.primary()?.segment.id).toBe('0');s.dispose();
  });
  it('retains primary until real readiness, never shows both at full opacity, then disposes old',async()=>{
    const op=operations(),s=new RouteStream(index,op);s.update([0,0,0],0);await tick();const first=s.primary()!.resource;
    s.update([10,0,0],10);await tick();const second=s.entries()[1].resource;second.ready=false;
    s.update([10,0,0],100);expect(first.alpha).toBe(1);expect(second.alpha).toBe(0);expect(s.stats().resident).toBe(2);
    second.ready=true;s.update([10,0,0],200);s.update([10,0,0],350);expect(first.alpha+second.alpha).toBe(1);expect(first.dispose).not.toHaveBeenCalled();
    s.update([10,0,0],500);expect(first.dispose).toHaveBeenCalledOnce();expect(s.stats()).toMatchObject({active:'1',resident:1,transitions:1});s.dispose();expect(second.dispose).toHaveBeenCalledOnce();
  });
  it('serializes cancellation, disposes a late decode and does not flash the obsolete segment',async()=>{
    const op=operations(),s=new RouteStream(index,op);s.update([0,0,0],0);await tick();
    let finish!:(r:ReturnType<typeof resource>)=>void;
    op.load.mockImplementationOnce(()=>new Promise(r=>finish=r));s.update([10,0,0],1);s.update([20,0,0],2);
    expect(op.load).toHaveBeenCalledTimes(2);const obsolete=resource();finish(obsolete);await tick();await tick();
    expect(obsolete.dispose).toHaveBeenCalledOnce();expect(op.show).not.toHaveBeenCalledWith(obsolete);expect(op.load).toHaveBeenCalledTimes(3);expect(s.stats().resident).toBe(2);s.dispose();
  });
  it('failed or timed-out incoming keeps primary and supports explicit retry',async()=>{
    const op=operations(),s=new RouteStream(index,op);s.update([0,0,0],0);await tick();const first=s.primary()!.resource;
    op.load.mockRejectedValueOnce(new Error('HTTP503'));s.update([10,0,0],10);await tick();expect(s.stats().errors[0]).toContain('503');expect(first.dispose).not.toHaveBeenCalled();
    s.retry();await tick();const incoming=s.entries()[1].resource;incoming.ready=false;s.update([10,0,0],100);s.update([10,0,0],60200);
    expect(incoming.dispose).toHaveBeenCalledOnce();expect(s.stats()).toMatchObject({active:'0',resident:1,phase:'error'});expect(first.alpha).toBe(1);s.dispose();
  });
  it('reversing during a fade restores primary and releases incoming',async()=>{
    const op=operations(),s=new RouteStream(index,op);s.update([0,0,0],0);await tick();s.update([10,0,0],1);await tick();
    const next=s.entries()[1].resource;s.update([10,0,0],2);s.update([10,0,0],102);s.update([0,0,0],103);
    expect(next.dispose).toHaveBeenCalledOnce();expect(s.primary()!.resource.alpha).toBe(1);expect(s.stats().resident).toBe(1);s.dispose();
  });
  it('retains primary if incoming RAD fails after metadata succeeded, including mid-fade',async()=>{
    const failure={message:undefined as string|undefined};const op={...operations(),error:()=>failure.message},s=new RouteStream(index,op);
    s.update([0,0,0],0);await tick();const first=s.primary()!.resource;
    s.update([10,0,0],1);await tick();const incoming=s.entries()[1].resource;
    s.update([10,0,0],2);s.update([10,0,0],102);expect(first.alpha).toBeLessThan(1);
    failure.message='RAD checksum mismatch';s.update([10,0,0],103);
    expect(incoming.dispose).toHaveBeenCalledOnce();expect(first.dispose).not.toHaveBeenCalled();expect(first.alpha).toBe(1);
    expect(s.stats()).toMatchObject({active:'0',incoming:null,resident:1,transitions:0,phase:'error'});
    expect(s.stats().errors[0]).toContain('checksum');s.dispose();
  });
});
