import { describe,it,expect } from 'vitest';
import { gzipSync } from 'node:zlib';
import { inspectPly,inspectSpz,fractionalBitsFor,positionError } from '../compress-world.mjs';

function plyFixture(){
  const names=['x','y','z','f_dc_0','f_dc_1','f_dc_2',...Array.from({length:9},(_,i)=>'f_rest_'+i),'opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3'];
  const header=Buffer.from('ply\nformat binary_little_endian 1.0\nelement vertex 2\n'+names.map(n=>'property float '+n+'\n').join('')+'end_header\n');
  const body=Buffer.alloc(names.length*8);[-1.25,2.5,-3.75,.125,-.25,.5].forEach((v,i)=>body.writeFloatLE(v,Math.floor(i/3)*names.length*4+(i%3)*4));
  return Buffer.concat([header,body]);
}
function spzFixture(){const raw=Buffer.alloc(16+2*29);raw.writeUInt32LE(0x5053474e);raw.writeUInt32LE(3,4);raw.writeUInt32LE(2,8);raw[12]=1;raw[13]=15;raw[14]=1;
  [-1.25,2.5,-3.75,.125,-.25,.5].forEach((v,i)=>raw.writeIntLE(Math.round(v*32768),16+i*3,3));return raw;}

describe('bounded storage conversion integrity (synthetic fixtures, not visual acceptance)',()=>{
  it('reads actual property order and SH count',()=>{const p=inspectPly(plyFixture());expect(p.count).toBe(2);expect(p.shDegree).toBe(1);expect(p.min).toEqual([-1.25,-.25,-3.75]);});
  it('rejects a truncated body and nonfinite Gaussian data',()=>{const p=plyFixture();expect(()=>inspectPly(p.subarray(0,-1))).toThrow();p.writeFloatLE(NaN,inspectPly(p).offset+12);expect(()=>inspectPly(p)).toThrow('Nonfinite');});
  it('rejects missing Gaussian attributes and nonfloat layouts',()=>{const p=plyFixture();expect(()=>inspectPly(Buffer.from(p.toString('latin1').replace('float x','float q'),'latin1'))).toThrow();expect(()=>inspectPly(Buffer.from(p.toString('latin1').replace('float x','uchar x'),'latin1'))).toThrow('float32');});
  it('selects maximum safe precision without implicit recentering/scaling',()=>{expect(fractionalBitsFor({min:[-117,-1,-1],max:[129.1,1,1]})).toBe(15);expect(()=>fractionalBitsFor({min:[-1e9],max:[1e9]})).toThrow('range');});
  it('verifies signed negative positions and all point ordering',()=>{const p=plyFixture(),s=inspectSpz(gzipSync(spzFixture()));expect(positionError(p,inspectPly(p),s).maxAbsoluteError).toBe(0);});
  it('detects a flipped axis rather than accepting a plausible cloud',()=>{const raw=spzFixture();raw.writeIntLE(40960,16,3);const p=plyFixture();expect(()=>positionError(p,inspectPly(p),inspectSpz(gzipSync(raw)))).toThrow('preservation');});
  it('rejects corrupt gzip, count mismatch and lost SH',()=>{expect(()=>inspectSpz(Buffer.from('garbage'))).toThrow();const raw=spzFixture();raw.writeUInt32LE(1,8);expect(()=>inspectSpz(gzipSync(raw))).toThrow('payload');const p=plyFixture(),s=inspectSpz(gzipSync(spzFixture()));expect(()=>positionError(p,inspectPly(p),{...s,shDegree:0})).toThrow('SH');});
  it('allows known antialias metadata but rejects unknown flags/version',()=>{const raw=spzFixture();expect(inspectSpz(gzipSync(raw)).flags).toBe(1);raw[14]=2;expect(()=>inspectSpz(gzipSync(raw))).toThrow();raw[14]=0;raw.writeUInt32LE(4,4);expect(()=>inspectSpz(gzipSync(raw))).toThrow('v3');});
});
