import type {PagedSplatsFetcher} from '@sparkjsdev/spark';
import {resolveAssetUrl,type PagedIndex} from './world';
export type RadTransfer={requested:number;bytes:number;pending:number;errors:string[]};

/** Native Spark owns page selection/eviction; this adapter only pins public bytes. */
export function radFetcher(index:PagedIndex,baseUrl:string,stats:RadTransfer):PagedSplatsFetcher{
  let root:Uint8Array|undefined;
  async function get(path:string,signal:AbortSignal){
    const pin=index.files.find(f=>f.path===path);if(!pin)throw new Error('Undeclared RAD chunk '+path);
    stats.requested++;
    stats.pending++;
    try{
      const r=await fetch(resolveAssetUrl(baseUrl,path),{signal});if(!r.ok)throw new Error('RAD HTTP '+r.status);
      if(r.headers.get('content-type')?.includes('text/html'))throw new Error('RAD URL returned HTML');
      const bytes=new Uint8Array(await r.arrayBuffer());stats.bytes+=bytes.length;
      if(bytes.length!==pin.bytes)throw new Error('RAD byte length mismatch');
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
      if(hash!==pin.sha256)throw new Error('RAD checksum mismatch');signal.throwIfAborted();return bytes;
    }catch(e){if(!signal.aborted&&!stats.errors.includes(String(e))){stats.errors.push(String(e));stats.errors.splice(0,Math.max(0,stats.errors.length-5));}throw e;}
    finally{stats.pending--;}
  }
  return {fetchRange:async(signal,offset,bytes)=>{root??=await get(index.root,signal);return root.slice(offset,offset+bytes);},fetchChunkFile:(signal,path)=>get(path,signal),fetchChunkById:async()=>{throw new Error('Chunked RAD requires declared filenames');}};
}
