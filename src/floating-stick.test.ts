import {describe,it,expect} from 'vitest';
import {stickVector} from './floating-stick';
describe('floating touch stick',()=>{
  it('starts neutral at the touch origin and ignores small hand jitter',()=>{
    expect(stickVector(0,0,40)).toEqual({x:0,y:0,knobX:0,knobY:0});
    const small=stickVector(2,-1,40);expect(small.x).toBe(0);expect(Math.abs(small.y)).toBe(0);
  });
  it('offers symmetric forward and backward motion independent of screen placement',()=>{
    expect(stickVector(0,-40,40).y).toBe(-1);expect(stickVector(0,40,40).y).toBe(1);
    expect(stickVector(0,-20,40).y).toBe(-stickVector(0,20,40).y);
  });
  it('keeps captured drags bounded outside the activation area and preserves direction',()=>{
    const {x,y,knobX,knobY}=stickVector(300,400,40);
    expect(Math.hypot(x,y)).toBeCloseTo(1);expect(Math.hypot(knobX,knobY)).toBeCloseTo(40);
    expect(x/y).toBeCloseTo(3/4);
  });
});
