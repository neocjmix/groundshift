import {useCallback,useEffect,useRef,type PointerEvent} from 'react';
import type {FlyNavigation} from './fly-navigation';

type Controls={getMotion:()=>FlyNavigation|null;onExit:()=>void;onReset:()=>void;detail:string;disabled:boolean};
function Joystick({label,kind,getMotion}:{label:string;kind:'move'|'look';getMotion:Controls['getMotion']}){
  const owner=useRef<number|null>(null),knob=useRef<HTMLSpanElement>(null),pad=useRef<HTMLDivElement>(null);
  const reset=useCallback(()=>{owner.current=null;if(knob.current)knob.current.style.transform='translate(0px,0px)';getMotion()?.[kind].set(0,0);},[getMotion,kind]);
  useEffect(()=>{
    const clear=()=>{if(document.hidden)reset();};
    window.addEventListener('blur',reset);document.addEventListener('visibilitychange',clear);
    return()=>{window.removeEventListener('blur',reset);document.removeEventListener('visibilitychange',clear);reset();};
    // getMotion reads a stable ref; input belongs to this mounted pad only.
  },[reset]);
  const move=(e:PointerEvent<HTMLDivElement>)=>{
    if(owner.current!==e.pointerId)return;
    const box=e.currentTarget.getBoundingClientRect(),radius=box.width*.34;
    let x=(e.clientX-box.left-box.width/2)/radius,y=(e.clientY-box.top-box.height/2)/radius;
    const length=Math.hypot(x,y);if(length>1){x/=length;y/=length;}
    if(knob.current)knob.current.style.transform=`translate(${x*radius}px,${y*radius}px)`;
    getMotion()?.[kind].set(Math.abs(x)<.08?0:x,Math.abs(y)<.08?0:y);
  };
  return <div className={'fly-stick fly-stick-'+kind}>
    <span>{label}</span><div ref={pad} className="fly-pad" role="group" aria-label={label+' joystick'}
      onPointerDown={e=>{if(owner.current!==null)return;e.preventDefault();owner.current=e.pointerId;e.currentTarget.setPointerCapture(e.pointerId);move(e);}}
      onPointerMove={move} onPointerUp={e=>{if(owner.current===e.pointerId)reset();}}
      onPointerCancel={e=>{if(owner.current===e.pointerId)reset();}} onLostPointerCapture={e=>{if(owner.current===e.pointerId)reset();}}
      onContextMenu={e=>e.preventDefault()}><span className="fly-pad-cross"/><span className="fly-knob" ref={knob}/></div>
  </div>;
}
function Lift({direction,getMotion}:{direction:1|-1;getMotion:Controls['getMotion']}){
  const clear=()=>getMotion()?.lift.delete(direction);
  return <button aria-label={direction===1?'Fly up':'Fly down'} className="fly-lift-button"
    onPointerDown={e=>{e.preventDefault();e.currentTarget.setPointerCapture(e.pointerId);getMotion()?.lift.add(direction);}}
    onPointerUp={clear} onPointerCancel={clear} onLostPointerCapture={clear}
    onKeyDown={e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();getMotion()?.lift.add(direction);}}}
    onKeyUp={clear} onBlur={clear} onContextMenu={e=>e.preventDefault()}>{direction===1?'↑':'↓'}</button>;
}
export default function FlyControls({getMotion,onExit,onReset,detail,disabled}:Controls){
  return <div className="fly-ui" aria-label="Fly controls">
    <div className="fly-toolbar"><div className="fly-title"><strong>Fly</strong><small>{detail}</small></div>
      <label className="fly-speed">속도<select aria-label="Fly speed" defaultValue={String(getMotion()?.speed??1)} onChange={e=>{const motion=getMotion();if(motion)motion.speed=Number(e.target.value);}}>
        <option value="0.25">0.25×</option><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option>
      </select></label>
      <button aria-label="Reset Fly position" onClick={onReset} title="시작 위치로">↺</button>
      <button aria-label="Exit Fly" onClick={onExit}>나가기 ×</button>
    </div>
    <div className="fly-reticle" aria-hidden="true"/>
    <p className="fly-help">왼손 이동 · 오른손 시선<span>WASD 이동 · 마우스 클릭/드래그 시선 · Q/E 높이 · Shift 빠르게 · Esc 나가기</span></p>
    <div className="fly-touch-controls" inert={disabled}>
      <Joystick label="이동" kind="move" getMotion={getMotion}/>
      <div className="fly-lift"><Lift direction={1} getMotion={getMotion}/><Lift direction={-1} getMotion={getMotion}/></div>
      <Joystick label="시선" kind="look" getMotion={getMotion}/>
    </div>
  </div>;
}
