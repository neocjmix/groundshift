import {Euler, MathUtils, Quaternion, Vector2, Vector3, type PerspectiveCamera} from 'three';
import {cameraPathGap,type CameraPath} from './camera-path';

/** Viewer-world units per second, never an inferred metric walking speed. */
export function flySpeed(path:CameraPath|undefined,orbitDistance:number):number{
  const distances:number[]=[];
  if(path)for(let i=1;i<path.poses.length;i++){
    const d=path.poses[i].position.distanceTo(path.poses[i-1].position);
    if(!cameraPathGap(path,i)&&d>1e-6)distances.push(d);
  }
  distances.sort((a,b)=>a-b);
  return Math.max(1e-5,distances.length?distances[Math.floor(distances.length/2)]:orbitDistance*.25);
}

/** One camera, no floor, gravity, collision geometry or renderer ownership. */
export class FlyNavigation{
  enabled=false;
  readonly move=new Vector2();
  readonly look=new Vector2();
  readonly keys=new Set<string>();
  readonly lift=new Set<number>();
  speed=1;
  private yaw=0;
  private pitch=0;
  private readonly upRotation:Quaternion;
  private readonly euler=new Euler(0,0,0,'YXZ');
  private readonly direction=new Vector3();
  private readonly movement=new Vector3();
  private readonly yawRotation=new Quaternion();
  private readonly startPosition=new Vector3();
  private readonly startQuaternion=new Quaternion();
  constructor(private readonly camera:PerspectiveCamera,readonly baseSpeed:number){
    this.upRotation=new Quaternion().setFromUnitVectors(new Vector3(0,1,0),camera.up.clone().normalize());
  }
  enter(){
    this.clear();this.enabled=true;
    this.startPosition.copy(this.camera.position);this.startQuaternion.copy(this.camera.quaternion);
    this.syncLook();
  }
  private syncLook(){
    this.camera.getWorldDirection(this.direction).applyQuaternion(this.upRotation.clone().invert());
    this.yaw=Math.atan2(-this.direction.x,-this.direction.z);
    this.pitch=Math.asin(MathUtils.clamp(this.direction.y,-1,1));
    this.rotate(0,0);
  }
  rotate(x:number,y:number){
    this.yaw-=x;this.pitch=MathUtils.clamp(this.pitch-y,-Math.PI*.48,Math.PI*.48);
    this.camera.quaternion.copy(this.upRotation).multiply(this.yawRotation.setFromEuler(this.euler.set(this.pitch,this.yaw,0,'YXZ')));
  }
  reset(){this.clear();this.camera.position.copy(this.startPosition);this.camera.quaternion.copy(this.startQuaternion);this.syncLook();}
  clear(){this.move.set(0,0);this.look.set(0,0);this.keys.clear();this.lift.clear();}
  update(seconds:number){
    if(!this.enabled)return;
    const dt=MathUtils.clamp(seconds,0,.1);
    this.rotate(this.look.x*1.8*dt,this.look.y*1.8*dt);
    const key=(...codes:string[])=>codes.some(c=>this.keys.has(c))?1:0;
    // Forward motion stays in the viewer's horizontal plane; lift is explicit.
    this.movement.set(this.move.x+key('KeyD','ArrowRight')-key('KeyA','ArrowLeft'),
      key('KeyE','Space')-key('KeyQ','ControlLeft','ControlRight')+(this.lift.has(1)?1:0)-(this.lift.has(-1)?1:0),
      this.move.y+key('KeyS','ArrowDown')-key('KeyW','ArrowUp'));
    if(this.movement.lengthSq()>1)this.movement.normalize();
    this.yawRotation.setFromEuler(this.euler.set(0,this.yaw,0,'YXZ'));
    this.movement.applyQuaternion(this.yawRotation).applyQuaternion(this.upRotation);
    const boost=key('ShiftLeft','ShiftRight')?3:1;
    this.camera.position.addScaledVector(this.movement,this.baseSpeed*this.speed*boost*dt);
  }
}
