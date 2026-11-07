import { useCallback, useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { SparkRenderer, SplatMesh, SplatFileType,PagedSplats } from "@sparkjsdev/spark";
import { loadWorld,type LoadedWorld } from "./load-world";
import { advanceCameraPath, cameraPathGap, sampleCameraPath } from "./camera-path";
import "./Viewer.css";
import { ChunkStream,type StreamStats } from './streaming';
import {radFetcher,type RadTransfer} from './rad-fetcher';
import {FlyNavigation,flySpeed} from './fly-navigation';
import FlyControls from './FlyControls';
import {snapshotPagingDiagnostics,type PagingDiagnostics} from './paging-diagnostics';
import {RouteStream,routeAssetTransform,routeOwner,guardRoutePagedUpdates,type RouteStats} from './route-stream';
import {resolveAssetUrl} from './world';

const diagnosticVersion='safari-paging-20261107-v2';
const pagingPhaseLabel={network:'파일 수신 중',decode:'해독 또는 재시도 대기',lod:'세부 선택 중',upload:'GPU 전송 중',display:'화면 갱신 중',settled:'대기 작업 없음',initializing:'초기화 중',unknown:'상태 확인 중'};


type NavigationState = {
  mode: 'orbit' | 'camera-path' | 'fly';
  cursor: number;
  playing: boolean;
  speed: number;
  direction: 1 | -1;
};
type NavigationAction =
  | { type: 'mode'; mode: NavigationState['mode'] }
  | { type: 'seek'; cursor: number }
  | { type: 'step'; direction: 1 | -1 }
  | { type: 'play' }
  | { type: 'speed'; speed: number }
  | { type: 'direction'; direction: 1 | -1 };

function initialNavigation(world: LoadedWorld): NavigationState {
  return {
    mode: world.cameraPath ? world.manifest.navigation.mode : 'orbit',
    cursor: 0, playing: false, speed: 1, direction: 1,
  };
}

type SavedView = {
  navigation: NavigationState;
  position: THREE.Vector3; quaternion: THREE.Quaternion; target: THREE.Vector3;
  fov: number; yaw: number; pitch: number; flySpeed: number;
};

type Status = {
  phase: "loading" | "ready" | "error";
  message: string;
  progress?: number;
};
interface Metrics {
  fps: number;
  splats: number;
  bytes: number;
  loadMs: number;
  gpu: string;
  width: number;
  height: number;
}

export default function Viewer({ world }: { world: LoadedWorld }) {
  const mount = useRef<HTMLDivElement>(null);
  const shell = useRef<HTMLDivElement>(null);
  const fly = useRef<FlyNavigation|null>(null);
  const fullscreenAttempt=useRef(0);
  const cancelFullscreen=useCallback(()=>++fullscreenAttempt.current,[]);
  const getFly=useCallback(()=>fly.current,[]);
  const reset = useRef<() => void>(() => {});
  const savedView = useRef<SavedView|null>(null);
  const saveView = useRef<() => SavedView|null>(()=>null);
  const zoom = useRef<(direction: number) => void>(() => {});
  const navigate = useRef<(action: NavigationAction) => void>(() => {});
  const [navigation, setNavigation] = useState(() => initialNavigation(world));
  const [status, setStatus] = useState<Status>({
    phase: "loading",
    message: "Loading scene…",
  });
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [diagnostics,setDiagnostics]=useState<PagingDiagnostics|null>(null);
  const diagnosticHistory=useRef<PagingDiagnostics[]>([]);
  const [attempt, setAttempt] = useState(0);
  const [streamEnabled,setStreamEnabled]=useState(()=>new URLSearchParams(window.location.search).get('stream')!=='off');
  const [streamStats,setStreamStats]=useState<StreamStats|null>(null);
  const retryChunks=useRef<()=>void>(()=>{});
  const [pagingStats,setPagingStats]=useState<{selected:number;pages:number;bytes:number;requested:number;pending:number;errors:string[]}|null>(null);
  const [routeStats,setRouteStats]=useState<RouteStats|null>(null);
  const routeSelection=useRef<string|null>(null);
  const pagingBudget=world.manifest.route??world.manifest.paging;

  const switchLoadingMode=()=>{
    savedView.current=saveView.current();
    setStatus({phase:'loading',message:'Switching scene loading mode at the same viewpoint…'});
    setMetrics(null);setPagingStats(null);setDiagnostics(null);setStreamEnabled(v=>!v);
  };

  const downloadDiagnostics=()=>{
    const view=saveView.current();
    const report={version:diagnosticVersion,worldId:world.manifest.id,mode:streamEnabled?'lod':'whole',
      userAgent:navigator.userAgent,devicePixelRatio:window.devicePixelRatio,viewport:[window.innerWidth,window.innerHeight],
      view:view?{position:view.position.toArray(),quaternion:view.quaternion.toArray(),fov:view.fov,mode:view.navigation.mode,cursor:view.navigation.cursor}:null,
      renderer:metrics?.gpu??null,drawingBuffer:metrics?[metrics.width,metrics.height]:null,
      samples:diagnosticHistory.current,scope:'Device-local observations only. No upload. No visual-quality or completed-loading guarantee.'};
    if(world.route)Object.assign(report,{route:routeStats,mode:streamEnabled?'route-lod':'current-segment-whole'});
    const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='groundshift-paging-diagnostics.json';a.click();
    window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  };

  const exitFly=useCallback(()=>{
    cancelFullscreen();
    navigate.current({type:'mode',mode:'orbit'});
    // Exit must remain available even after a renderer/context error.
    fly.current?.clear();if(fly.current)fly.current.enabled=false;
    setNavigation(current=>({...current,mode:'orbit',playing:false}));
    if(document.pointerLockElement&&shell.current?.contains(document.pointerLockElement))document.exitPointerLock();
    if(document.fullscreenElement===shell.current)void document.exitFullscreen().catch(()=>{});
  },[cancelFullscreen]);
  const enterFly=()=>{
    navigate.current({type:'mode',mode:'fly'});
    mount.current?.querySelector('canvas')?.focus({preventScroll:true});
    const element=shell.current,token=cancelFullscreen();
    if(element?.requestFullscreen&&document.fullscreenEnabled){
      try{void element.requestFullscreen().then(()=>{
        if(token!==fullscreenAttempt.current&&document.fullscreenElement===element)void document.exitFullscreen().catch(()=>{});
      }).catch(()=>{/* Fixed viewport remains usable when native fullscreen is unavailable. */});}catch{/* Same viewport fallback. */}
    }
  };
  useEffect(()=>{
    if(navigation.mode!=='fly')return;
    const element=shell.current,previousOverflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    let hadFullscreen=document.fullscreenElement===element;
    const fullscreenChange=()=>{if(document.fullscreenElement===element)hadFullscreen=true;else if(hadFullscreen)exitFly();};
    const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')exitFly();};
    document.addEventListener('fullscreenchange',fullscreenChange);window.addEventListener('keydown',escape);
    return()=>{
      cancelFullscreen();document.body.style.overflow=previousOverflow;
      document.removeEventListener('fullscreenchange',fullscreenChange);window.removeEventListener('keydown',escape);
      if(document.fullscreenElement===element)void document.exitFullscreen().catch(()=>{});
    };
  },[navigation.mode,exitFly,cancelFullscreen]);

  useEffect(() => {
    const container = mount.current!;
    const abort = new AbortController();
    let disposed = false;
    let failed = false;
    let renderer: THREE.WebGLRenderer | undefined;
    let controls: OrbitControls | undefined;
    let spark: SparkRenderer | undefined;
    let mesh: SplatMesh | undefined;
    let meshPending = false;
    let totalFrames=0,lastRenderedMs:number|null=null;
    let previousDiagnostic:PagingDiagnostics|null=null;
    diagnosticHistory.current=[];
    let stream:ChunkStream<SplatMesh>|undefined;
    type RouteResource={mesh:SplatMesh;world:LoadedWorld;transfer:RadTransfer;dispose:()=>void};
    let route:RouteStream<RouteResource>|undefined;
    const radStats:RadTransfer={requested:0,bytes:0,pending:0,errors:[]};
    let resize: ResizeObserver | undefined;
    let failCleanup: (() => void) | undefined;
    let navigationCleanup: (() => void) | undefined;
    const started = performance.now();
    const fail = (error: unknown) => {
      if (!disposed && !failed) {
        failed = true;
        abort.abort();
        stream?.dispose();
        route?.dispose();
        fly.current?.clear();
        mesh?.paged?.dispose();
        renderer?.setAnimationLoop(null);
        // Stop Spark's pending worker/update jobs immediately on failure.
        // Leaving them alive until Retry can reject against a lost GL context.
        spark?.dispose();
        spark=undefined;
        setStatus({
          phase: "error",
          message: error instanceof Error ? error.message : String(error),
        });
      }
    };
    const run = async () => {
      renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false });
      // A pending GPU readback can reject before webglcontextlost is delivered.
      // Fail/dispose its owner before Spark observes that rejection; otherwise
      // it escapes the render-loop try/catch as an unhandled promise rejection.
      const readback=renderer.readRenderTargetPixelsAsync.bind(renderer);
      renderer.readRenderTargetPixelsAsync=async(...args)=>{
        try{return await readback(...args);}
        catch(error){
          fail(error instanceof Error?error:new Error('GPU readback failed. Retry the scene to restore rendering.',{cause:error}));
          throw error;
        }
      };
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
      renderer.setClearColor("#111614", 1);
      renderer.domElement.setAttribute(
        "aria-label",
        "Interactive Gaussian Splatting scene",
      );
      renderer.domElement.setAttribute("role", "img");
      renderer.domElement.tabIndex = 0;
      container.append(renderer.domElement);
      const onContextLost = (event: Event) => {
        event.preventDefault();
        fail(
          new Error(
            "The graphics context was lost. Retry the scene to restore rendering.",
          ),
        );
      };
      renderer.domElement.addEventListener("webglcontextlost", onContextLost);
      failCleanup = () =>
        renderer?.domElement.removeEventListener(
          "webglcontextlost",
          onContextLost,
        );
      const scene = new THREE.Scene();
      const pose = world.manifest.navigation.camera;
      const camera = new THREE.PerspectiveCamera(
        pose.fov,
        1,
        pose.near,
        pose.far,
      );
      camera.up.fromArray(pose.up).normalize();
      controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.minDistance = pose.near * 2;
      controls.maxDistance = pose.far * 0.8;
      const resetOrbit = () => {
        if (!controls) return;
        // OrbitControls.reset() does not clear pending damping deltas.
        const damping = controls.enableDamping;
        controls.enableDamping = false;
        controls.update();
        controls.reset();
        camera.position.fromArray(pose.position);
        camera.up.fromArray(pose.up).normalize();
        camera.fov = pose.fov;
        camera.updateProjectionMatrix();
        controls.target.fromArray(pose.target);
        controls.update();
        controls.enableDamping = damping;
      };
      resetOrbit();
      controls.saveState();
      const path = world.cameraPath;
      const saved=savedView.current;savedView.current=null;
      const nav = saved ? {...saved.navigation,playing:false} : initialNavigation(world);
      const flight=new FlyNavigation(camera,flySpeed(path,camera.position.distanceTo(controls.target)));
      fly.current=flight;
      let yaw = saved?.yaw ?? 0;
      let pitch = saved?.pitch ?? 0;
      const look = new THREE.Quaternion();
      const lookEuler = new THREE.Euler(0, 0, 0, 'YXZ');
      const publishNavigation = () => {
        if (!disposed && !failed) setNavigation({ ...nav });
      };
      const applyPath = () => {
        if (!path || nav.mode !== 'camera-path') return;
        const sample = sampleCameraPath(path, nav.cursor);
        nav.cursor = sample.cursor;
        camera.position.copy(sample.position);
        look.setFromEuler(lookEuler.set(pitch, yaw, 0, 'YXZ'));
        camera.quaternion.copy(sample.quaternion).multiply(look);
      };
      controls.enabled = nav.mode === 'orbit';
      applyPath();
      if(saved){
        camera.position.copy(saved.position);camera.quaternion.copy(saved.quaternion);
        camera.fov=saved.fov;camera.updateProjectionMatrix();controls.target.copy(saved.target);
        flight.speed=saved.flySpeed;
        if(nav.mode==='fly')flight.enter();
        publishNavigation();
      }
      saveView.current=()=>({navigation:{...nav},position:camera.position.clone(),quaternion:camera.quaternion.clone(),
        target:controls!.target.clone(),fov:camera.fov,yaw,pitch,flySpeed:flight.speed});
      reset.current = () => {
        if (disposed || failed) return;
        if (nav.mode === 'orbit') resetOrbit();
        else if(nav.mode==='fly')flight.reset();
        else {
          nav.cursor = 0;
          nav.playing = false;
          yaw = pitch = 0;
          camera.fov = pose.fov;
          camera.updateProjectionMatrix();
          applyPath();
          publishNavigation();
        }
      };
      navigate.current = (action) => {
        if (disposed || failed || !controls) return;
        if (action.type === 'mode') {
          const wasFly=nav.mode==='fly';
          if(action.mode==='camera-path'&&!path)return;
          flight.clear();flight.enabled=false;
          if(document.pointerLockElement===renderer?.domElement)document.exitPointerLock();
          nav.mode = action.mode;
          nav.playing = false;
          controls.enabled = nav.mode === 'orbit';
          if(nav.mode==='fly'){
            const position=camera.position.clone(),orientation=camera.quaternion.clone(),target=controls.target.clone();
            const damping=controls.enableDamping;controls.enableDamping=false;controls.update();controls.enableDamping=damping;
            camera.position.copy(position);camera.quaternion.copy(orientation);controls.target.copy(target);
            flight.enter();
          }
          else if (nav.mode === 'orbit') {
            if(wasFly){
              // Keep the explored position and heading when leaving Fly.
              camera.getWorldDirection(controls.target).multiplyScalar(Math.max(flight.baseSpeed*3,pose.near*10)).add(camera.position);
              controls.update();
            }else resetOrbit();
          }
        } else if(!path)return;
        else if (action.type === 'seek') {
          nav.cursor = sampleCameraPath(path, Math.round(action.cursor)).cursor;
          nav.playing = false;
        } else if (action.type === 'step') {
          nav.cursor = Math.max(0, Math.min(path.poses.length - 1,
            action.direction > 0 ? Math.floor(nav.cursor) + 1 : Math.ceil(nav.cursor) - 1));
          nav.playing = false;
        } else if (action.type === 'play') {
          const next = nav.direction > 0 ? Math.floor(nav.cursor) + 1 : Math.ceil(nav.cursor);
          nav.playing = !nav.playing && !cameraPathGap(path, next);
        } else if (action.type === 'speed') nav.speed = action.speed;
        else if (action.type === 'direction') {
          nav.direction = action.direction;
          nav.playing = false;
        }
        applyPath();
        publishNavigation();
      };
      const canvas = renderer.domElement;
      let drag: { id: number; x: number; y: number } | undefined;
      const pointerDown = (event: PointerEvent) => {
        if (!['camera-path','fly'].includes(nav.mode) || event.button !== 0 || drag || failed) return;
        event.preventDefault();
        canvas.focus();
        if(document.pointerLockElement===canvas)return;
        // Pointer capture is invalid once pointer lock owns the mouse. Capture
        // the fallback drag first, then let the lock release it if successful.
        canvas.setPointerCapture(event.pointerId);
        drag = { id: event.pointerId, x: event.clientX, y: event.clientY };
        if(nav.mode==='fly'&&event.pointerType==='mouse'){
          try{const request=canvas.requestPointerLock?.();if(request)void request.catch(()=>{});}catch{/* Drag look remains available. */}
        }
      };
      const pointerMove = (event: PointerEvent) => {
        if (!drag || drag.id !== event.pointerId) return;
        if(nav.mode==='fly'){
          if(document.pointerLockElement!==canvas)flight.rotate((event.clientX-drag.x)*.003,(event.clientY-drag.y)*.003);
          drag={id:drag.id,x:event.clientX,y:event.clientY};return;
        }
        if(nav.mode!=='camera-path')return;
        yaw -= (event.clientX - drag.x) * 0.004;
        pitch = THREE.MathUtils.clamp(pitch - (event.clientY - drag.y) * 0.004, -Math.PI * 0.45, Math.PI * 0.45);
        drag = { id: drag.id, x: event.clientX, y: event.clientY };
        applyPath();
      };
      const pointerUp = (event: PointerEvent) => {
        if (drag?.id === event.pointerId) {
          drag = undefined;
          if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
        }
      };
      const keyDown = (event: KeyboardEvent) => {
        if (nav.mode !== 'camera-path' || failed) return;
        if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
        event.preventDefault();
        if (event.key === 'ArrowLeft') yaw += 0.05;
        if (event.key === 'ArrowRight') yaw -= 0.05;
        if (event.key === 'ArrowUp') pitch += 0.05;
        if (event.key === 'ArrowDown') pitch -= 0.05;
        pitch = THREE.MathUtils.clamp(pitch, -Math.PI * 0.45, Math.PI * 0.45);
        applyPath();
      };
      const flyKeys=new Set(['KeyW','KeyA','KeyS','KeyD','KeyQ','KeyE','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Space','ControlLeft','ControlRight','ShiftLeft','ShiftRight']);
      const flightKeyDown=(event:KeyboardEvent)=>{
        if(nav.mode!=='fly'||failed||event.metaKey||event.altKey||!flyKeys.has(event.code))return;
        const target=event.target instanceof Element?event.target:null;
        if(target?.closest('input,select,textarea,[contenteditable="true"]')||(event.code==='Space'&&target?.closest('button')))return;
        event.preventDefault();flight.keys.add(event.code);
      };
      const flightKeyUp=(event:KeyboardEvent)=>flight.keys.delete(event.code);
      const mouseLook=(event:MouseEvent)=>{if(nav.mode==='fly'&&document.pointerLockElement===canvas)flight.rotate(event.movementX*.002,event.movementY*.002);};
      const releaseInput=()=>{flight.clear();drag=undefined;};
      const pointerLockChange=()=>{releaseInput();};
      const visibilityChange = () => {
        if (document.hidden) {
          releaseInput();
          nav.playing = false;
          publishNavigation();
        }
      };
      canvas.addEventListener('pointerdown', pointerDown);
      canvas.addEventListener('pointermove', pointerMove);
      canvas.addEventListener('pointerup', pointerUp);
      canvas.addEventListener('pointercancel', pointerUp);
      canvas.addEventListener('lostpointercapture',pointerUp);
      canvas.addEventListener('keydown', keyDown);
      document.addEventListener('visibilitychange', visibilityChange);
      window.addEventListener('keydown',flightKeyDown);window.addEventListener('keyup',flightKeyUp);
      window.addEventListener('blur',releaseInput);document.addEventListener('mousemove',mouseLook);
      document.addEventListener('pointerlockchange',pointerLockChange);
      navigationCleanup = () => {
        canvas.removeEventListener('pointerdown', pointerDown);
        canvas.removeEventListener('pointermove', pointerMove);
        canvas.removeEventListener('pointerup', pointerUp);
        canvas.removeEventListener('pointercancel', pointerUp);
        canvas.removeEventListener('lostpointercapture',pointerUp);
        canvas.removeEventListener('keydown', keyDown);
        document.removeEventListener('visibilitychange', visibilityChange);
        window.removeEventListener('keydown',flightKeyDown);window.removeEventListener('keyup',flightKeyUp);
        window.removeEventListener('blur',releaseInput);document.removeEventListener('mousemove',mouseLook);
        document.removeEventListener('pointerlockchange',pointerLockChange);
        if(document.pointerLockElement===canvas)document.exitPointerLock();
        flight.enabled=false;flight.clear();if(fly.current===flight)fly.current=null;
      };
      zoom.current = (direction) => {
        if (!controls) return;
        if (nav.mode !== 'orbit') {
          camera.fov = THREE.MathUtils.clamp(camera.fov * (direction > 0 ? 0.8 : 1.25), 15, 110);
          camera.updateProjectionMatrix();
          return;
        }
        const offset = camera.position.clone().sub(controls.target);
        offset.setLength(
          THREE.MathUtils.clamp(
            offset.length() * (direction > 0 ? 0.8 : 1.25),
            controls.minDistance,
            controls.maxDistance,
          ),
        );
        camera.position.copy(controls.target).add(offset);
        controls.update();
      };
      spark = new SparkRenderer({ renderer,...(pagingBudget&&streamEnabled?{maxPagedSplats:pagingBudget.maxPagedSplats,lodSplatCount:pagingBudget.lodSplatCount,numLodFetchers:2,...(world.route?{lodCleanupTimeoutMs:0}:{})}:{} )});
      scene.add(spark);
      resize = new ResizeObserver(() => {
        if (!renderer) return;
        const { width, height } = container.getBoundingClientRect();
        renderer.setSize(width, height);
        camera.aspect = width / Math.max(height, 1);
        camera.updateProjectionMatrix();
      });
      resize.observe(container);
      let count=0,received=0;
      let assetWorld=world;
      let assetMatrix:THREE.Matrix4|undefined;
      if(world.route&&!streamEnabled){
        const segment=world.route.index.segments.find(s=>s.id===routeSelection.current)??routeOwner(world.route.index,camera.position.toArray());
        assetWorld=await loadWorld(resolveAssetUrl(world.route.baseUrl,segment.world),abort.signal);
        if(assetWorld.route||assetWorld.streaming||!assetWorld.paging||assetWorld.manifest.assets[0].format!=='spz'||assetWorld.manifest.coordinates.unit!==world.manifest.coordinates.unit)throw new Error('Route segments require standalone RAD/SPZ worlds in the same declared units');
        assetMatrix=routeAssetTransform(segment,assetWorld.manifest.coordinates.assetToWorld);
        routeSelection.current=segment.id;
      }
      if(world.route&&streamEnabled){
        setPagingStats(null);setStreamStats(null);
        const source=world.route;
        route=new RouteStream(source.index,{
          load:async(segment,signal)=>{
            const loaded=await loadWorld(resolveAssetUrl(source.baseUrl,segment.world),signal);
            if(loaded.route||loaded.streaming||!loaded.paging||loaded.manifest.assets[0].format!=='spz'||loaded.manifest.coordinates.unit!==world.manifest.coordinates.unit)throw new Error('Route segments require standalone RAD/SPZ worlds in the same declared units');
            const transfer:RadTransfer={requested:0,bytes:0,pending:0,errors:[]};
            const fetcher=radFetcher(loaded.paging.index,loaded.paging.baseUrl,transfer);
            const prior={requested:0,bytes:0,pending:0};
            const aggregate=()=>{for(const key of ['requested','bytes','pending'] as const){const n=transfer[key]-prior[key];radStats[key]+=n;prior[key]=transfer[key];}for(const error of transfer.errors)if(!radStats.errors.includes(error))radStats.errors.push(error);radStats.errors=radStats.errors.slice(-5);};
            const track=async<T,>(operation:()=>Promise<T>)=>{const promise=operation();aggregate();try{return await promise;}finally{aggregate();}};
            const paged=new PagedSplats({fileType:SplatFileType.RAD,fetchSource:{
              fetchRange:(...args)=>track(()=>fetcher.fetchRange(...args)),
              fetchChunkFile:(...args)=>track(()=>fetcher.fetchChunkFile(...args)),
              fetchChunkById:(...args)=>track(()=>fetcher.fetchChunkById(...args)),
            }});
            const resource=new SplatMesh({paged});
            let released=false;
            guardRoutePagedUpdates(paged,()=>released);
            const disposeResource=()=>{if(released)return;released=true;paged.dispose();spark?.pager?.removeSplats(paged);scene.remove(resource);resource.dispose();};
            signal.addEventListener('abort',disposeResource,{once:true});
            try{
              await Promise.all([resource.initialized,paged.getRadMeta()]);signal.throwIfAborted();
              resource.applyMatrix4(routeAssetTransform(segment,loaded.manifest.coordinates.assetToWorld));
              return {mesh:resource,world:loaded,transfer,dispose:()=>{signal.removeEventListener('abort',disposeResource);disposeResource();}};
            }catch(error){signal.removeEventListener('abort',disposeResource);disposeResource();throw error;}
          },
          show:r=>scene.add(r.mesh),hide:r=>scene.remove(r.mesh),opacity:(r,value)=>{r.mesh.opacity=value;},
          ready:r=>r.transfer.pending===0&&r.mesh.numSplats>=Math.min(131072,r.world.paging!.index.sourceSplats*.2),
          changed:stats=>{if(disposed||failed)return;routeSelection.current=stats.active;setRouteStats(stats);},
        },routeSelection.current??undefined);
        retryChunks.current=()=>route?.retry();
        route.update(camera.position.toArray(),performance.now());
      }else if(world.paging&&streamEnabled){
        setPagingStats(null);setStreamStats(null);
        mesh=new SplatMesh({paged:new PagedSplats({fileType:SplatFileType.RAD,fetchSource:radFetcher(world.paging.index,world.paging.baseUrl,radStats)})});
        meshPending=true;try{await mesh.initialized;}finally{meshPending=false;if(disposed||failed)mesh.dispose();}
        if(disposed||failed)return;
        const transform=world.manifest.coordinates.assetToWorld;mesh.position.fromArray(transform.position);mesh.quaternion.fromArray(transform.quaternion);mesh.scale.setScalar(transform.scale);scene.add(mesh);
      }else if(world.streaming&&streamEnabled){
        setStreamStats(null);
        const source=world.streaming;
        stream=new ChunkStream(source,{
          load:async(chunk,url,signal,onBytes)=>{
            const response=await fetch(url,{signal});
            if(!response.ok)throw new Error(`Chunk HTTP ${response.status}`);
            if(response.headers.get('content-type')?.includes('text/html'))throw new Error('Chunk URL returned HTML');
            const parts:Uint8Array[]=[];let length=0;const reader=response.body?.getReader();
            if(!reader)throw new Error('Chunk response has no readable body');
            for(;;){const {done,value}=await reader.read();if(done)break;length+=value.length;onBytes(value.length);if(length>chunk.bytes){await reader.cancel();throw new Error('Chunk exceeds declared bytes');}parts.push(value);}
            if(length!==chunk.bytes)throw new Error('Chunk byte length mismatch');
            const bytes=new Uint8Array(length);let at=0;for(const part of parts){bytes.set(part,at);at+=part.length;}parts.length=0;
            const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
            if(hash!==chunk.sha256)throw new Error('Chunk checksum mismatch');
            signal.throwIfAborted();
            const resource=new SplatMesh({fileBytes:bytes,fileType:SplatFileType.SPZ});
            try{await resource.initialized;if(resource.numSplats!==chunk.splats)throw new Error('Chunk Gaussian count mismatch');}
            catch(error){resource.dispose();throw error;}
            const transform=world.manifest.coordinates.assetToWorld;resource.position.fromArray(transform.position);resource.quaternion.fromArray(transform.quaternion);resource.scale.setScalar(transform.scale);
            return resource;
          },
          show:resource=>scene.add(resource),hide:resource=>scene.remove(resource),
          changed:stats=>{if(disposed||failed)return;count=stats.splats;received=stats.transferredBytes;setStreamStats(stats);},
        });
        retryChunks.current=()=>stream?.retry();
        stream.update(camera.position.toArray());
      }else{
      setStreamStats(null);
      const response = await fetch(assetWorld.assetUrl, { signal: abort.signal });
      if (!response.ok)
        throw new Error(
          `Scene asset: HTTP ${response.status}. Download the sample or check the asset path.`,
        );
      if (response.headers.get("content-type")?.includes("text/html"))
        throw new Error("The scene URL returned a web page instead of a Gaussian asset. Check the asset path and download the sample if needed.");
      const total = Number(response.headers.get("content-length"));
      const chunks: Uint8Array[] = [];
      const reader = response.body?.getReader();
      if (!reader)
        throw new Error("This browser could not stream the scene file.");
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        received += value.byteLength;
        if (!disposed && !failed)
          setStatus({
            phase: "loading",
            message: `Downloading scene · ${(received / 1e6).toFixed(1)} MB`,
            progress: total > 0 ? Math.min(received / total, 1) : undefined,
          });
      }
      if (disposed || failed) return;
      if (!received) throw new Error("The scene asset is empty.");
      const bytes = new Uint8Array(received);
      let offset = 0;
      for (const chunk of chunks) {
        bytes.set(chunk, offset);
        offset += chunk.byteLength;
      }
      chunks.length = 0;
      setStatus({
        phase: "loading",
        message: "Decoding Gaussians and preparing GPU…",
      });
      mesh = new SplatMesh({
        fileBytes: bytes,
        fileName: assetWorld.manifest.assets[0].path,
        fileType: {
          ply: SplatFileType.PLY,
          spz: SplatFileType.SPZ,
          splat: SplatFileType.SPLAT,
          ksplat: SplatFileType.KSPLAT,
          sog: SplatFileType.PCSOGSZIP,
        }[assetWorld.manifest.assets[0].format],
      });
      meshPending = true;
      try {
        await mesh.initialized;
      } finally {
        meshPending = false;
        // Spark's decoder cannot be cancelled. Keep its owner alive until it
        // settles so dispose can reach the buffers created during decoding.
        if (disposed || failed) mesh.dispose();
      }
      if (disposed || failed) return;
      count = mesh.splats?.getNumSplats() ?? 0;
      if (count === 0)
        throw new Error("The asset contains no renderable Gaussians.");
      const transform = assetWorld.manifest.coordinates.assetToWorld;
      if(assetMatrix)mesh.applyMatrix4(assetMatrix);
      else{mesh.position.fromArray(transform.position);mesh.quaternion.fromArray(transform.quaternion);mesh.scale.setScalar(transform.scale);}
      scene.add(mesh);
      }
      const gl = renderer.getContext();
      const debug = gl.getExtension("WEBGL_debug_renderer_info");
      const gpu = debug
        ? String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL))
        : String(gl.getParameter(gl.RENDERER));
      let loadMs = performance.now() - started;
      let readyPublished=false;
      let last = performance.now();
      let lastFrame = last;
      let lastNavigationUpdate = last;
      let frames = 0;

      renderer.setAnimationLoop(() => {
        if (!renderer || disposed || failed) return;
        try {
          const now = performance.now();
          const elapsed = Math.min((now - lastFrame) / 1000, 0.1);
          lastFrame = now;
          if (nav.mode === 'camera-path' && path) {
            if (nav.playing) {
              const next = advanceCameraPath(path, nav.cursor, elapsed * nav.speed * nav.direction);
              nav.cursor = next.cursor;
              if (next.stopped) nav.playing = false;
              if (next.stopped || now - lastNavigationUpdate >= 100) {
                publishNavigation();
                lastNavigationUpdate = now;
              }
            }
            applyPath();
          } else if(nav.mode==='fly')flight.update(elapsed);
          else controls?.update();
          if(stream){
            stream.update(camera.position.toArray());
            renderer.domElement.dataset.stream=JSON.stringify(stream.stats());
          }
          if(route){
            route.update(camera.position.toArray(),now);
            renderer.domElement.dataset.route=JSON.stringify({...route.stats(),segments:route.entries().map(e=>({id:e.segment.id,selected:e.resource.mesh.numSplats,opacity:e.resource.mesh.opacity}))});
          }
          renderer.render(scene, camera);
          if(pagingBudget&&streamEnabled){
            count=spark?.activeSplats??0;received=radStats.bytes;
            const residentChunks=spark?.pager?.pageToSplatsChunk.flatMap(page=>page?[page.chunk]:[])??[];
            const stats={selected:count,pages:residentChunks.length,residentChunks,selectionTarget:pagingBudget.lodSplatCount,bytes:radStats.bytes,pending:radStats.pending,requested:radStats.requested,errors:[...radStats.errors],capacity:pagingBudget.maxPagedSplats,sourceSplats:world.paging?.index.sourceSplats??route?.entries().reduce((sum,e)=>sum+e.resource.world.paging!.index.sourceSplats,0)??0,
              ...(route?{segmentPages:route.entries().map(e=>({id:e.segment.id,chunks:spark?.pager?.pageToSplatsChunk.flatMap(p=>p&&p.splats===e.resource.mesh.paged?[p.chunk]:[])??[]}))}:{})};
            renderer.domElement.dataset.paging=JSON.stringify(stats);
            if(totalFrames%30===0)setPagingStats(stats);
          }
          totalFrames++;lastRenderedMs=now;
          // A render submission is not visual acceptance; acceptance uses screenshots.
          if (!readyPublished&&totalFrames >= 3&&count>0){
            readyPublished=true;loadMs=performance.now()-started;
            setStatus({ phase: "ready", message: "Scene loaded" });
          }
          frames++;
          if (now - last >= 1000) {
            setMetrics({
              fps: (frames * 1000) / (now - last),
              splats: count,
              bytes: received,
              loadMs,
              gpu,
              width: renderer.domElement.width,
              height: renderer.domElement.height,
            });
            last = now;
            frames = 0;
          }
          renderer.domElement.dataset.cameraPosition = camera.position
            .toArray()
            .join(",");
          renderer.domElement.dataset.frameCount = String(totalFrames);
          renderer.domElement.dataset.cameraQuaternion = camera.quaternion.toArray().join(',');
          renderer.domElement.dataset.navigationMode = nav.mode;
          renderer.domElement.dataset.cameraFov = String(camera.fov);
          renderer.domElement.dataset.pathProgress = String(nav.cursor);
        } catch (error) {
          fail(error);
        }
      });
    };
    const diagnosticTimer=pagingBudget&&streamEnabled?window.setInterval(()=>{
      if(disposed)return;
      const sample=snapshotPagingDiagnostics({spark,paged:route?.primary()?.resource.mesh.paged??mesh?.paged,network:radStats,nowMs:performance.now(),
        frameCount:totalFrames,lastFrameMs:lastRenderedMs,visibility:document.visibilityState,previous:previousDiagnostic});
      previousDiagnostic=sample;
      diagnosticHistory.current.push(sample);
      if(diagnosticHistory.current.length>120)diagnosticHistory.current.shift();
      if(renderer)renderer.domElement.dataset.pagingDiagnostics=JSON.stringify(sample);
      setDiagnostics(sample);
    },500):undefined;
    void run().catch(fail);
    return () => {
      disposed = true;
      if(diagnosticTimer!==undefined)window.clearInterval(diagnosticTimer);
      abort.abort();
      stream?.dispose();
      route?.dispose();
      renderer?.setAnimationLoop(null);
      resize?.disconnect();
      controls?.dispose();
      navigationCleanup?.();
      if (!meshPending) mesh?.dispose();
      spark?.dispose();
      failCleanup?.();
      renderer?.dispose();
      renderer?.forceContextLoss();
      renderer?.domElement.remove();
      saveView.current = () => null;
      reset.current = () => {};
      zoom.current = () => {};
      navigate.current = () => {};
      retryChunks.current=()=>{};
    };
  }, [world, attempt,streamEnabled,pagingBudget]);

  const pathGap = world.cameraPath ? cameraPathGap(world.cameraPath,
    navigation.direction > 0 ? Math.floor(navigation.cursor) + 1 : Math.ceil(navigation.cursor)) : null;

  return (
    <div ref={shell} className={'scene-shell'+(navigation.mode==='fly'?' is-fly':'')} data-phase={status.phase}>
      {navigation.mode==='fly'&&<FlyControls getMotion={getFly} onExit={exitFly} onReset={()=>reset.current()}
        disabled={status.phase!=='ready'} detail={pagingBudget&&pagingStats?.pending?'주변 세부 불러오는 중…':metrics?`자유 이동 · ${metrics.fps.toFixed(0)} fps`:world.manifest.title}/>}
      <div ref={mount} className="canvas-mount" />
      {pagingBudget&&<details className="paging-inspector" aria-label="Loading diagnostics">
        <summary>로딩 상태 · {streamEnabled?pagingStats?.selected.toLocaleString()??'…':'전체'}{streamEnabled?'점':''}</summary>
        <div className="paging-inspector-body">
          <strong>{streamEnabled?'LoD 스트리밍':'전체 SPZ 비교'}</strong>
          {world.route&&<><p>현재 구간: {routeStats?.active??routeSelection.current??'준비 중'}{routeStats?.incoming?` → ${routeStats.incoming}`:''}</p>
            <small>최대 두 구간·{pagingBudget.maxPagedSplats/65536}페이지 공용 풀. 현재 구간의 먼 GS를 유지하며, 전체 경로의 먼 풍경을 모두 상주시키지는 않습니다.</small>
            {routeStats?.errors.map(error=><p role="alert" key={error}>{error}</p>)}
            {streamEnabled&&Boolean(routeStats?.errors.length)&&<button onClick={()=>retryChunks.current()}>구간 다시 시도</button>}</>}
          {streamEnabled&&diagnostics&&<>
            <p>{pagingPhaseLabel[diagnostics.phase]} · {diagnostics.heartbeat.state==='rendering'?'화면 갱신 중':diagnostics.heartbeat.state==='hidden'?'백그라운드':diagnostics.heartbeat.state==='paused'?'화면 갱신 대기':'첫 화면 대기'}</p>
            <p>수신 {(diagnostics.network.bytes! / 1e6).toFixed(2)}MB · 상주 {diagnostics.selection.residentPages??'?'} / {(diagnostics.runtime.maxPagedSplats??0)/65536}페이지</p>
            <p>선택 {diagnostics.selection.traversed?.toLocaleString()??'?'} · 표시 {diagnostics.selection.active?.toLocaleString()??'?'}</p>
            {Object.values(diagnostics.stages).some(s=>s.state==='waiting')&&<p role="status">10초 이상 진행 변화가 없습니다. 느린 처리인지 오류인지는 아직 확정할 수 없습니다.</p>}
          </>}
          <button disabled={status.phase==='loading'||Boolean(world.route&&streamEnabled&&!routeStats?.active)} onClick={switchLoadingMode}>{streamEnabled?(world.route?'같은 위치 · 현재 구간 SPZ 비교':'같은 위치 · 전체 SPZ 비교'):'같은 위치 · LoD로 복귀'}</button>
          <button onClick={downloadDiagnostics}>진단 JSON 저장</button>
          <small>대기 작업이 없어도 원본 장면의 흐림은 남을 수 있습니다. 진단은 이 기기에 저장하며 자동 전송하지 않습니다. {diagnosticVersion}</small>
        </div>
      </details>}
      {world.route&&<div className="stream-panel" aria-label="Route streaming status">
        <strong>{streamEnabled?'연속 경로 · 구간 LoD':'현재 구간 전체 SPZ 비교'}</strong>
        <span>현재 {routeStats?.active??routeSelection.current??'준비 중'} · {world.route.index.segments.length}개 실제 장면</span>
        {streamEnabled&&routeStats&&<span>{routeStats.pending||routeStats.incoming?'다음 구간 준비 중':'현재 구간 유지'} · 전환 {routeStats.transitions}회 · 상주 {routeStats.resident}/2구간</span>}
        {streamEnabled&&pagingStats&&<span>표시 {pagingStats.selected.toLocaleString()}점 · {pagingStats.pages}/{pagingBudget!.maxPagedSplats/65536}페이지 · {(pagingStats.bytes/1e6).toFixed(2)}MB 수신</span>}
        <small>독립 재구성의 접합부는 어긋날 수 있습니다. 비교는 현재 구간만 대상으로 합니다.</small>
        {Boolean(routeStats?.errors.length)&&<><p role="alert">{routeStats!.errors.join('; ')}</p><button onClick={()=>retryChunks.current()}>구간 다시 시도</button></>}
      </div>}
      {world.paging&&<div className="stream-panel" aria-label="Native LoD paging status">
        <strong>{streamEnabled?'LoD 스트리밍':'전체 SPZ 비교'}</strong>
        <button onClick={switchLoadingMode}>{streamEnabled?'전체 SPZ로 비교':'LoD 스트리밍으로 전환'}</button>
        {streamEnabled&&pagingStats&&<><span>표시 {pagingStats.selected.toLocaleString()}점 · 상주 {pagingStats.pages}페이지 / {world.manifest.paging!.maxPagedSplats/65536}페이지 한도</span><span>파일 수신합 {(pagingStats.bytes/1e6).toFixed(2)}MB · 요청 {pagingStats.requested}회 · 원본 {world.paging.index.sourceSplats.toLocaleString()}점</span>
        {pagingStats.errors.length>0&&<><p role="alert">최근 페이지 오류: {pagingStats.errors.join('; ')}</p><button onClick={()=>{setStatus({phase:'loading',message:'Reconnecting LoD pages…'});setAttempt(v=>v+1);}}>페이지 다시 연결</button></>}</>}
        <small>먼 영역은 거친 GS로 유지하고 가까운 영역을 정밀하게 읽습니다. 사진 배경이 아닙니다.</small>
      </div>}
      {world.streaming&&<div className="stream-panel" aria-label="Spatial streaming status">
        <strong>{streamEnabled?'구간 로딩':'전체 로딩 비교'}</strong>
        <button onClick={switchLoadingMode}>{streamEnabled?'전체 로딩으로 비교':'구간 로딩으로 전환'}</button>
        {streamEnabled&&streamStats&&<><span>상주 {streamStats.resident}/{world.streaming.index.chunks.length}구간 · {streamStats.splats.toLocaleString()}점 · 누적 전송 {(streamStats.transferredBytes/1e6).toFixed(2)}MB</span><span>해제 {streamStats.evicted}회 · {streamStats.pending?'주변 구간 불러오는 중…':'주변 구간 준비됨'} · 파일 합 {(streamStats.residentBytes/1e6).toFixed(2)}MB (GPU 메모리 아님)</span>
        {streamStats.errors.length>0&&<><p role="alert">구간 오류: {streamStats.errors.join('; ')}</p><button onClick={()=>retryChunks.current()}>구간 다시 시도</button></>}</>}
        <small>가까운 구간과 인접 구간만 표시합니다. 멀리 보이는 장면은 빠질 수 있습니다.</small>
      </div>}
      <div className="scene-topline">
        <span className="live-dot" /> WORLD VIEW{" "}
        <span className="topline-separator">/</span> {world.manifest.id}
      </div>
      <div className="path-panel" aria-label="Navigation controls">
          <div className="path-mode" role="group" aria-label="Navigation mode">
            <button aria-pressed={navigation.mode === 'orbit'} disabled={status.phase !== 'ready'}
              onClick={() => navigate.current({ type: 'mode', mode: 'orbit' })}>Orbit</button>
            <button aria-label="Fly" aria-pressed={navigation.mode === 'fly'} disabled={status.phase !== 'ready'} onClick={enterFly}>Fly ↗</button>
            {world.cameraPath&&<button aria-pressed={navigation.mode === 'camera-path'} disabled={status.phase !== 'ready'}
              onClick={() => navigate.current({ type: 'mode', mode: 'camera-path' })}>Camera path</button>}
          </div>
          {navigation.mode === 'camera-path' && world.cameraPath && (
            <>
              <label className="path-progress">Jump to recorded view
                <input type="range" min={0} max={world.cameraPath.poses.length - 1} step={1}
                  aria-label="Recorded camera view" value={Math.floor(navigation.cursor)}
                  disabled={status.phase !== 'ready' || world.cameraPath.poses.length < 2}
                  onChange={(event) => navigate.current({ type: 'seek', cursor: Number(event.target.value) })} />
              </label>
              <div className="path-actions">
                <button aria-label="Previous recorded view" disabled={status.phase !== 'ready' || navigation.cursor <= 0}
                  onClick={() => navigate.current({ type: 'step', direction: -1 })}>← Previous</button>
                <button disabled={status.phase !== 'ready' || (!navigation.playing && Boolean(pathGap))}
                  onClick={() => navigate.current({ type: 'play' })}>{navigation.playing ? 'Pause path' : 'Play path'}</button>
                <button aria-label="Next recorded view" disabled={status.phase !== 'ready' || navigation.cursor >= world.cameraPath.poses.length - 1}
                  onClick={() => navigate.current({ type: 'step', direction: 1 })}>Next →</button>
              </div>
              <div className="path-options">
                <label>Direction <select aria-label="Path direction" value={navigation.direction}
                  onChange={(event) => navigate.current({ type: 'direction', direction: Number(event.target.value) as 1 | -1 })}>
                  <option value={1}>Forward</option><option value={-1}>Backward</option>
                </select></label>
                <label>Speed <select aria-label="Path speed" value={navigation.speed}
                  onChange={(event) => navigate.current({ type: 'speed', speed: Number(event.target.value) })}>
                  <option value={0.25}>0.25 views/s</option><option value={0.5}>0.5 views/s</option>
                  <option value={1}>1 view/s</option><option value={2}>2 views/s</option>
                </select></label>
              </div>
              <p className="path-position">View {(navigation.cursor + 1).toFixed(1)} / {world.cameraPath.poses.length}
                {' · '}{Number.isInteger(navigation.cursor) ? 'Recorded pose' : 'Interpolated pose'}</p>
              <p className="path-note">
                {pathGap ?? 'Straight segments between estimated poses; no recovered walking surface.'}
                {pathGap && '. Use Previous / Next to jump between recorded views.'}
              </p>
              {world.cameraPath.sequenceNotes && <details className="path-provenance"><summary>Sequence evidence</summary><p>{world.cameraPath.sequenceNotes}</p></details>}
            </>
          )}
        </div>
      {world.cameraPathError && <p className="path-warning" role="status">{world.cameraPathError}</p>}
      {status.phase !== "ready" && (
        <div
          className="scene-overlay"
          role={status.phase === "error" ? "alert" : "status"}
        >
          <div className="state-card">
            <span
              className={
                status.phase === "loading" ? "spinner" : "error-symbol"
              }
            >
              {status.phase === "error" ? "!" : ""}
            </span>
            <h2>
              {status.phase === "error"
                ? "Scene unavailable"
                : "Bringing this world into view"}
            </h2>
            <p>{status.message}</p>
            {status.progress !== undefined && (
              <progress max={1} value={status.progress} />
            )}
            {status.phase === "error" && (
              <button
                onClick={() => {
                  setStatus({
                    phase: "loading",
                    message: "Downloading scene…",
                  });
                  setMetrics(null);
                  setNavigation(initialNavigation(world));
                  setAttempt((value) => value + 1);
                }}
              >
                Retry scene
              </button>
            )}
          </div>
        </div>
      )}
      <div className="scene-bottom">
        <div className="scene-caption">
          <span className="eyebrow">A PLACE TO RETURN TO</span>
          <h2>{world.manifest.title}</h2>
          <p>
            {navigation.mode === 'camera-path' ? 'Drag or use arrow keys on the scene to look around · Position follows camera poses' : <>
              Drag to orbit <span>·</span> Scroll to explore <span>·</span>{" "}Right-drag to pan
            </>}
          </p>
        </div>
        <div className="camera-controls" aria-label="Camera controls">
          <button
            aria-label="Zoom in"
            title="Zoom in"
            onClick={() => zoom.current(1)}
            disabled={status.phase !== "ready"}
          >
            +
          </button>
          <button
            aria-label="Zoom out"
            title="Zoom out"
            onClick={() => zoom.current(-1)}
            disabled={status.phase !== "ready"}
          >
            −
          </button>
          <button
            className="reset-button"
            aria-label="Reset view"
            onClick={() => reset.current()}
            disabled={status.phase !== "ready"}
          >
            ↺ <span>Reset view</span>
          </button>
        </div>
      </div>
      <details className="render-details">
        <summary>
          Render details {metrics && <span>{metrics.fps.toFixed(0)} fps</span>}
        </summary>
        {metrics ? (
          <dl>
            <dt>Gaussians</dt>
            <dd>{metrics.splats.toLocaleString("en-US")}</dd>
            <dt>Scene file</dt>
            <dd>{(metrics.bytes / 1e6).toFixed(2)} MB</dd>
            <dt>Load + decode</dt>
            <dd>{(metrics.loadMs / 1000).toFixed(2)} s</dd>
            <dt>Drawing buffer</dt>
            <dd>
              {metrics.width} × {metrics.height}
            </dd>
            <dt>Renderer</dt>
            <dd>{metrics.gpu}</dd>
            <dt>Frame rate</dt>
            <dd>Rolling 1 s, includes browser scheduling</dd>
          </dl>
        ) : (
          <p>Measurements appear after the scene starts rendering.</p>
        )}
      </details>
    </div>
  );
}
