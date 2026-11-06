import {describe,it,expect} from 'vitest';
import {partitionOwners} from '../partition-world.mjs';
describe('shared-frame Gaussian ownership',()=>{
 it('keeps every point exactly once including ties/outside route and bends',()=>{
  const points=[[0,0,0],[1,0,0],[1,1,0],[20,2,4],[-8,5,9]],centers=[[0,0,0],[2,0,0],[2,2,0],[0,2,0]];
  const owners=partitionOwners(points,centers,2);expect(owners).toEqual([0,0,0,1,1]);expect(owners).toHaveLength(points.length);
  const translated=partitionOwners(points.map(p=>p.map(x=>x+100)),centers.map(p=>p.map(x=>x+100)),2);expect(translated).toEqual(owners);
 });
 it('rejects unknown/invalid coordinate frames',()=>{expect(()=>partitionOwners([[NaN,0,0]],[[0,0,0]])).toThrow();expect(()=>partitionOwners([[0,0,0]],[])).toThrow();expect(()=>partitionOwners([[0,0,0]],[[0,0,0]],0)).toThrow();});
});
