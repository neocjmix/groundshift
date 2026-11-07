import { Matrix4, Quaternion, Vector3 } from 'three';
import type { RouteIndex, RouteSegment, WorldManifest } from './world';

export type RouteStats={active:string|null;incoming:string|null;pending:string|null;wanted:string|null;resident:number;transitions:number;cancelled:number;errors:string[];phase:'loading'|'ready'|'transition'|'error'};
type Resource={dispose:()=>void};
type Entry<T>={segment:RouteSegment;resource:T};

/** Spark can finish an awaited LoD traversal after a route resource is released.
 * Its late update must not recreate that resource's disposed index texture. */
export function guardRoutePagedUpdates(paged:{update:(count:number,indices:Uint32Array)=>void;abortController:AbortController},released:()=>boolean){
  const update=paged.update.bind(paged);
  paged.update=(count,indices)=>{if(!released()&&!paged.abortController.signal.aborted)update(count,indices);};
}

/** Asset -> standalone viewer -> route viewer, including scale exactly once. */
export function routeAssetTransform(segment:RouteSegment,asset:WorldManifest['coordinates']['assetToWorld']){
  const matrix=(t:typeof asset)=>new Matrix4().compose(new Vector3(...t.position),new Quaternion(...t.quaternion),new Vector3().setScalar(t.scale));
  return matrix(segment.transform).multiply(matrix(asset));
}

/** Keep the current owner until another core is at least20% closer. */
export function routeOwner(index:RouteIndex,position:readonly number[],current?:string):RouteSegment{
  if(position.length!==3||!position.every(Number.isFinite))throw new Error('Finite route-world position required');
  const distances=index.segments.map(segment=>Math.min(...segment.anchors.map(a=>a.reduce((sum,value,k)=>sum+(value-position[k])**2,0))));
  const closest=distances.indexOf(Math.min(...distances)),previous=index.segments.findIndex(s=>s.id===current);
  return index.segments[previous>=0&&distances[previous]*.64<=distances[closest]?previous:closest];
}

/** Two real resources at most; failed or cancelled incoming work cannot erase
 * the primary. This owns transitions, not Spark's shared page/selection budget.
 */
export class RouteStream<T extends Resource>{
  private active?:Entry<T>;
  private incoming?:Entry<T>;
  private pending?:{segment:RouteSegment;abort:AbortController};
  private wanted?:RouteSegment;
  private dead=false;
  private failures=new Map<string,string>();
  private fadingAt:number|null=null;
  private loadedAt=0;
  private transitions=0;
  private cancelled=0;
  constructor(private index:RouteIndex,private operations:{
    load:(segment:RouteSegment,signal:AbortSignal)=>Promise<T>;
    show:(resource:T)=>void;hide:(resource:T)=>void;opacity:(resource:T,value:number)=>void;
    ready:(resource:T)=>boolean;error?:(resource:T)=>string|undefined;changed?:(stats:RouteStats)=>void;
  },private initialOwner?:string){}
  primary(){return this.active;}
  entries(){return [this.active,this.incoming].filter((v):v is Entry<T>=>v!==undefined);}
  update(position:readonly number[],now:number){
    if(this.dead)return;
    const wanted=routeOwner(this.index,position,this.active?.segment.id??this.initialOwner);
    if(this.wanted?.id!==wanted.id){
      this.wanted=wanted;
      if(this.pending&&this.pending.segment.id!==wanted.id&&!this.pending.abort.signal.aborted){this.pending.abort.abort();this.cancelled++;}
      if(this.incoming&&this.incoming.segment.id!==wanted.id)this.dropIncoming();
      this.emit();
    }
    if(this.incoming){
      const error=this.operations.error?.(this.incoming.resource);
      if(error){this.failures.set(this.incoming.segment.id,error);this.dropIncoming();this.emit();}
    }
    if(this.incoming){
      if(this.loadedAt===0)this.loadedAt=now;
      if(this.fadingAt===null&&this.operations.ready(this.incoming.resource)){this.fadingAt=now;this.emit();}
      if(this.fadingAt!==null){
        const fraction=Math.min(1,Math.max(0,(now-this.fadingAt)/300));
        if(this.active)this.operations.opacity(this.active.resource,1-fraction);
        this.operations.opacity(this.incoming.resource,fraction);
        if(fraction===1){
          if(this.active)this.release(this.active);
          this.active=this.incoming;this.incoming=undefined;this.fadingAt=null;this.loadedAt=0;this.transitions++;this.emit();
        }
      }else if(now-this.loadedAt>60000){
        this.failures.set(this.incoming.segment.id,'Incoming detail did not become ready within60s; current scene retained.');
        this.dropIncoming();this.emit();
      }
    }
    this.pump();
  }
  retry(){this.failures.clear();this.emit();this.pump();}
  stats():RouteStats{return {active:this.active?.segment.id??null,incoming:this.incoming?.segment.id??null,pending:this.pending?.segment.id??null,wanted:this.wanted?.id??null,
    resident:this.entries().length,transitions:this.transitions,cancelled:this.cancelled,errors:[...this.failures].map(([id,error])=>`${id}: ${error}`),
    phase:this.fadingAt!==null?'transition':this.failures.size?'error':this.active?'ready':'loading'};}
  private emit(){if(!this.dead)this.operations.changed?.(this.stats());}
  private release(entry:Entry<T>){this.operations.hide(entry.resource);entry.resource.dispose();}
  private dropIncoming(){if(this.incoming)this.release(this.incoming);this.incoming=undefined;this.loadedAt=0;this.fadingAt=null;if(this.active)this.operations.opacity(this.active.resource,1);}
  private pump(){
    if(this.dead||this.pending||this.incoming||!this.wanted||this.active?.segment.id===this.wanted.id||this.failures.has(this.wanted.id))return;
    const segment=this.wanted,abort=new AbortController();this.pending={segment,abort};this.emit();
    void this.operations.load(segment,abort.signal).then(resource=>{
      if(this.dead||abort.signal.aborted||this.wanted?.id!==segment.id){resource.dispose();return;}
      const entry={segment,resource};
      this.operations.opacity(resource,this.active?0:1);this.operations.show(resource);
      if(this.active)this.incoming=entry;else{this.active=entry;this.initialOwner=undefined;}
    }).catch(error=>{if(!this.dead&&!abort.signal.aborted)this.failures.set(segment.id,error instanceof Error?error.message:String(error));})
      .finally(()=>{this.pending=undefined;this.emit();this.pump();});
  }
  dispose(){this.dead=true;this.pending?.abort.abort();this.dropIncoming();if(this.active)this.release(this.active);this.active=undefined;}
}
