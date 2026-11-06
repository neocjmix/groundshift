import { parseStreamIndex,type StreamIndex } from './world';
export { parseStreamIndex };
export type { StreamIndex };
export type StreamChunk=StreamIndex['chunks'][number];
export type LoadedStream={index:StreamIndex;urls:Map<string,string>};

/** Ordered route neighborhoods in the shared viewer frame; no metric assumption. */
export function nearbyChunks(index:StreamIndex,position:readonly number[]):string[]{
  if(position.length!==3||!position.every(Number.isFinite))throw new Error('Finite viewer-world position required');
  const d=index.chunks.map(c=>Math.min(...c.anchors.map(a=>a.reduce((s,x,i)=>s+(x-position[i])**2,0))));
  const current=d.indexOf(Math.min(...d));
  return index.chunks.map((c,i)=>({id:c.id,d:Math.abs(i-current),distance:d[i]})).sort((a,b)=>a.d-b.d||a.distance-b.distance).slice(0,index.maxResidentChunks).map(c=>c.id);
}

export type StreamStats={resident:number;splats:number;residentBytes:number;transferredBytes:number;requested:number;evicted:number;cancelled:number;pending:number;wanted:string[];loaded:string[];errors:string[]};
type Resource={dispose:()=>void};

/** One fetch/decode owner at a time. Late/obsolete decodes are always disposed.
 * Encoded bytes are transient. Evicted resources have no JS LRU cache.
 */
export class ChunkStream<T extends Resource>{
  private resources=new Map<string,T>();
  private wanted:string[]=[];
  private pending?:{id:string;abort:AbortController};
  private dead=false;
  private failures=new Map<string,string>();
  private transferredBytes=0;private requested=0;private evicted=0;private cancelled=0;
  constructor(private source:LoadedStream,private operations:{load:(chunk:StreamChunk,url:string,signal:AbortSignal,onBytes:(n:number)=>void)=>Promise<T>;show:(resource:T)=>void;hide:(resource:T)=>void;changed?:(stats:StreamStats)=>void}){}
  update(position:readonly number[]){if(this.dead)return;this.select(nearbyChunks(this.source.index,position));}
  select(ids:string[]){
    if(this.dead)return;
    if(ids.length>this.source.index.maxResidentChunks||new Set(ids).size!==ids.length||ids.some(id=>!this.source.index.chunks.some(c=>c.id===id)))throw new Error('Invalid residency selection');
    if(ids.length===this.wanted.length&&ids.every((id,i)=>id===this.wanted[i]))return;
    this.wanted=[...ids];
    if(this.pending&&!ids.includes(this.pending.id)&&!this.pending.abort.signal.aborted){this.pending.abort.abort();this.cancelled++;}
    for(const [id,r] of this.resources)if(!ids.includes(id)){this.operations.hide(r);r.dispose();this.resources.delete(id);this.evicted++;}
    this.emit();this.pump();
  }
  retry(){this.failures.clear();this.pump();}
  stats():StreamStats{
    const rows=this.source.index.chunks.filter(c=>this.resources.has(c.id));
    return {resident:rows.length,splats:rows.reduce((n,c)=>n+c.splats,0),residentBytes:rows.reduce((n,c)=>n+c.bytes,0),transferredBytes:this.transferredBytes,requested:this.requested,evicted:this.evicted,cancelled:this.cancelled,pending:this.pending?1:0,wanted:[...this.wanted],loaded:[...this.resources.keys()],errors:[...this.failures.values()]};
  }
  private emit(){this.operations.changed?.(this.stats());}
  private pump(){
    if(this.dead||this.pending)return;
    const id=this.wanted.find(id=>!this.resources.has(id)&&!this.failures.has(id));if(!id)return;
    const chunk=this.source.index.chunks.find(c=>c.id===id)!,abort=new AbortController();this.pending={id,abort};this.requested++;this.emit();
    void this.operations.load(chunk,this.source.urls.get(id)!,abort.signal,n=>{this.transferredBytes+=n;}).then(r=>{
      if(this.dead||abort.signal.aborted||!this.wanted.includes(id)){r.dispose();return;}
      this.resources.set(id,r);this.operations.show(r);
    }).catch(e=>{if(!this.dead&&!abort.signal.aborted)this.failures.set(id,`${id}: ${e instanceof Error?e.message:String(e)}`);}).finally(()=>{this.pending=undefined;this.emit();this.pump();});
  }
  dispose(){this.dead=true;this.pending?.abort.abort();for(const r of this.resources.values()){this.operations.hide(r);r.dispose();}this.resources.clear();}
}
