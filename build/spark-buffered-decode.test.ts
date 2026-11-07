import {readFileSync} from 'node:fs';
import {describe,it,expect} from 'vitest';
import {bufferedBranch,directBranch,patchBufferedSparkWorker,isSparkWorkerModule} from './spark-buffered-decode';

describe('pinned buffered decoder workaround',()=>{
  it('matches the exact ESM module including Vite dev cache queries',()=>{
    expect(isSparkWorkerModule('/node_modules/@sparkjsdev/spark/dist/spark.module.js?v=abc')).toBe(true);
    expect(isSparkWorkerModule('/node_modules/@sparkjsdev/spark/dist/spark.module.js')).toBe(true);
    expect(isSparkWorkerModule('/node_modules/other/dist/spark.module.js')).toBe(false);
  });
  it('changes exactly the known fileBytes branch in the installed distribution',()=>{
    const source=readFileSync('node_modules/@sparkjsdev/spark/dist/spark.module.js','utf8');
    const before=bufferedBranch.replaceAll('\n','\\n'), after=directBranch.replaceAll('\n','\\n');
    const result=patchBufferedSparkWorker(source);
    expect(result.replace(after,before)).toBe(source);
    expect(result).not.toContain(before);
    expect(result.split(after)).toHaveLength(2);
  });
  it('rejects package drift, duplicate matches and accidental double application',()=>{
    const source=bufferedBranch.replaceAll('\n','\\n');
    expect(()=>patchBufferedSparkWorker('upgraded worker')).toThrow();
    expect(()=>patchBufferedSparkWorker(source+source)).toThrow();
    expect(()=>patchBufferedSparkWorker(patchBufferedSparkWorker(source))).toThrow();
  });
  it('decodes buffered bytes exactly once without any stream read and preserves progress and errors',()=>{
    // Execute the actual replacement branch with observable decoder calls.
    const decode=new Function('fileBytes','decoder','sendStatus','url',directBranch+' throw new Error("URL stream branch remains upstream"); }');
    const bytes=new Uint8Array([1,2,3]),progress:unknown[]=[],pushed:unknown[]=[];
    const result={numSplats:65536};
    expect(decode(bytes,{push:(v:unknown)=>pushed.push(v),finish:()=>result},(v:unknown)=>progress.push(v))).toBe(result);
    expect(pushed).toEqual([bytes]);expect(progress).toEqual([{loaded:3,total:3}]);
    const failure=new Error('decode failed');
    expect(()=>decode(bytes,{push:()=>{throw failure;},finish:()=>result},()=>{})).toThrow(failure);
  });
});
