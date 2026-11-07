/** Signed screen-space stick movement, with an isotropic dead zone and bounded travel. */
export function stickVector(dx:number,dy:number,radius:number){
  const length=Math.hypot(dx,dy),travel=Math.min(length,Math.max(1,radius));
  const ux=length>0?dx/length:0,uy=length>0?dy/length:0;
  const magnitude=Math.max(0,(travel/Math.max(1,radius)-.08)/.92);
  return {x:ux*magnitude,y:uy*magnitude,knobX:ux*travel,knobY:uy*travel};
}
