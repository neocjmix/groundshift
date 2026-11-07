import {useCallback,useEffect,useRef,type PointerEvent} from 'react';
import type {FlyNavigation} from './fly-navigation';
import {stickVector} from './floating-stick';

type Controls={getMotion:()=>FlyNavigation|null;onExit:()=>void;onReset:()=>void;detail:string;disabled:boolean};
/** The activation zone leaves space below every origin for a full backward drag. */
function Joystick({getMotion}:{getMotion:Controls['getMotion']}){
  const owner=useRef<{id:number;x:number;y:number;radius:number}|null>(null);
  const knob=useRef<HTMLSpanElement>(null),pad=useRef<HTMLDivElement>(null),zone=useRef<HTMLDivElement>(null);
  const reset=useCallback(()=>{
    const previous=owner.current;owner.current=null;
    getMotion()?.move.set(0,0);
    if(zone.current){zone.current.dataset.active='false';if(previous&&zone.current.hasPointerCapture(previous.id))zone.current.releasePointerCapture(previous.id);}
    if(knob.current){knob.current.style.setProperty('--stick-x','0px');knob.current.style.setProperty('--stick-y','0px');}
  },[getMotion]);
  useEffect(()=>{
    const clear=()=>{if(document.hidden)reset();};
    window.addEventListener('blur',reset);window.addEventListener('resize',reset);document.addEventListener('visibilitychange',clear);
    return()=>{window.removeEventListener('blur',reset);window.removeEventListener('resize',reset);document.removeEventListener('visibilitychange',clear);reset();};
  },[reset]);
  const move=(e:PointerEvent<HTMLDivElement>)=>{
    const start=owner.current;if(!start||start.id!==e.pointerId)return;
    const {x,y,knobX,knobY}=stickVector(e.clientX-start.x,e.clientY-start.y,start.radius);
    if(knob.current){knob.current.style.setProperty('--stick-x',`${knobX}px`);knob.current.style.setProperty('--stick-y',`${knobY}px`);}
    getMotion()?.move.set(x,y);
  };
  return <div ref={zone} className="fly-move-zone" role="group" aria-label="Move joystick area" data-active="false"
    onPointerDown={e=>{
      if(owner.current!==null||e.pointerType==='mouse')return;
      e.preventDefault();e.stopPropagation();
      const box=e.currentTarget.getBoundingClientRect(),size=pad.current?.offsetWidth??112;
      owner.current={id:e.pointerId,x:e.clientX,y:e.clientY,radius:size*.34};
      if(pad.current){pad.current.style.left=`${e.clientX-box.left}px`;pad.current.style.top=`${e.clientY-box.top}px`;}
      e.currentTarget.dataset.active='true';e.currentTarget.setPointerCapture(e.pointerId);move(e);
    }}
    onPointerMove={move} onPointerUp={e=>{if(owner.current?.id===e.pointerId)reset();}}
    onPointerCancel={e=>{if(owner.current?.id===e.pointerId)reset();}} onLostPointerCapture={e=>{if(owner.current?.id===e.pointerId)reset();}}
    onContextMenu={e=>e.preventDefault()}>
    <span className="fly-move-hint">이 영역을 누르고 이동</span>
    <div ref={pad} className="fly-pad" aria-hidden="true"><span className="fly-knob" ref={knob}/></div>
  </div>;
}
function Lift({direction,getMotion}:{direction:1|-1;getMotion:Controls['getMotion']}){
  const owner=useRef<number|null>(null);
  const clear=useCallback(()=>{owner.current=null;getMotion()?.lift.delete(direction);},[direction,getMotion]);
  useEffect(()=>{
    const hidden=()=>{if(document.hidden)clear();};
    window.addEventListener('blur',clear);document.addEventListener('visibilitychange',hidden);
    return()=>{window.removeEventListener('blur',clear);document.removeEventListener('visibilitychange',hidden);clear();};
  },[clear]);
  return <button aria-label={direction===1?'Fly up':'Fly down'} className="fly-lift-button"
    onPointerDown={e=>{if(owner.current!==null)return;e.preventDefault();owner.current=e.pointerId;e.currentTarget.setPointerCapture(e.pointerId);getMotion()?.lift.add(direction);}}
    onPointerUp={e=>{if(owner.current===e.pointerId)clear();}} onPointerCancel={e=>{if(owner.current===e.pointerId)clear();}} onLostPointerCapture={e=>{if(owner.current===e.pointerId)clear();}}
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
    <p className="fly-help">왼쪽 터치로 이동 · 화면 스와이프로 시선<span>WASD 이동 · 마우스 클릭/드래그 시선 · Q/E 높이 · Shift 빠르게 · Esc 나가기</span></p>
    <div className="fly-touch-controls" inert={disabled}>
      <Joystick getMotion={getMotion}/>
      <div className="fly-lift"><Lift direction={1} getMotion={getMotion}/><Lift direction={-1} getMotion={getMotion}/></div>
    </div>
  </div>;
}
