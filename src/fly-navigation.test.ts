import {describe,it,expect} from 'vitest';
import {PerspectiveCamera,Vector3} from 'three';
import {FlyNavigation,flySpeed} from './fly-navigation';
import type {CameraPath} from './camera-path';
function setup(){const camera=new PerspectiveCamera();camera.position.set(0,2,0);camera.lookAt(0,2,-1);const fly=new FlyNavigation(camera,2);fly.enter();return{camera,fly};}
describe('free camera navigation',()=>{
  it('moves with heading on the horizontal plane while looking up, with separate lift',()=>{
    const {camera,fly}=setup();fly.rotate(0,-.6);fly.keys.add('KeyW');fly.update(.1);expect(camera.position.z).toBeCloseTo(-.2);expect(camera.position.y).toBeCloseTo(2);
    fly.keys.clear();fly.lift.add(1);fly.update(.1);expect(camera.position.y).toBeCloseTo(2.2);expect(camera.position.z).toBeCloseTo(-.2);
  });
  it('normalizes diagonals and produces equal movement at different frame rates',()=>{
    const a=setup(),b=setup();a.fly.move.set(1,-1);b.fly.keys.add('KeyW');
    for(let i=0;i<60;i++)a.fly.update(1/60);for(let i=0;i<30;i++)b.fly.update(1/30);
    expect(a.camera.position.distanceTo(new Vector3(0,2,0))).toBeCloseTo(2);expect(b.camera.position.z).toBeCloseTo(-2);
  });
  it('clears held input, limits suspended-frame jumps and restores the entry position',()=>{
    const {camera,fly}=setup();fly.keys.add('KeyW');fly.update(30);expect(camera.position.z).toBeCloseTo(-.2);fly.clear();const position=camera.position.clone();fly.update(.1);expect(camera.position.equals(position)).toBe(true);
    fly.reset();expect(camera.position.toArray()).toEqual([0,2,0]);fly.enabled=false;fly.keys.add('KeyW');fly.update(.1);expect(camera.position.z).toBe(0);
  });
  it('uses the declared camera up and heading rather than applying the asset transform',()=>{
    const camera=new PerspectiveCamera();camera.up.set(0,0,1);camera.lookAt(0,1,0);const fly=new FlyNavigation(camera,1);fly.enter();fly.keys.add('KeyW');fly.update(.1);expect(camera.position.y).toBeCloseTo(.1);expect(camera.position.z).toBeCloseTo(0);fly.keys.clear();fly.lift.add(1);fly.update(.1);expect(camera.position.z).toBeCloseTo(.1);
  });
  it('derives a viewer-unit speed from marked camera edges, ignoring disconnected jumps',()=>{
    const poses=[0,2,1000,1004].map((x,i)=>({image:String(i),position:new Vector3(x,0,0),quaternion:new PerspectiveCamera().quaternion,continuousFromPrevious:i===1||i===3}));
    expect(flySpeed({poses} as CameraPath,100)).toBe(4);expect(flySpeed(undefined,8)).toBe(2);
  });
});
