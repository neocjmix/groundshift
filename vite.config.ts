import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {patchBufferedSparkWorker,isSparkWorkerModule} from './build/spark-buffered-decode.ts';

export default defineConfig({
  plugins: [{
    name:'spark-2.4-buffered-decoder',enforce:'pre',
    async load(id){
      if(!isSparkWorkerModule(id))return;
      // Pin the original file before Vite strips its source-map comment in dev.
      const source=await readFile(id.split(/[?#]/,1)[0],'utf8');
      if(createHash('sha256').update(source).digest('hex')!=='5ae86ab35d4ceb655db486dcc336299775bb314c280d7e5b39f64e4539f8e0e9')
        throw new Error('Unexpected Spark distribution: revalidate the buffered decoder workaround before upgrading.');
      return {code:patchBufferedSparkWorker(source),map:null};
    },
  },react()],
  // Keep dev mode on the same patched module as production builds.
  optimizeDeps:{exclude:['@sparkjsdev/spark']},
  build: { rollupOptions: { input: {
    main: "index.html",
    lab: "experiments/lab/index.html",
    object: "experiments/object-focus/index.html",
    objectReal: "experiments/object-real/index.html",
    objectNoDepth: "experiments/object-nodepth/index.html",
    panoramicDepth: "experiments/panoramic-depth/index.html",
    panoramicPair: "experiments/panoramic-pair/index.html",
    panoramicCalibration: "experiments/panoramic-calibration/index.html",
    perspectiveOverlap: "experiments/perspective-overlap/index.html",
    stereoAnchors: "experiments/stereo-anchors/index.html",
    roadThirdView: "experiments/road-third-view/index.html",
    street: "experiments/street/index.html",
    modelSelection: "experiments/model-selection/index.html",
    finalQuality: "experiments/final-quality/index.html",
    tangentBackground: "experiments/tangent-background/index.html",
    compression: "experiments/compression/index.html",
    touristStreaming: "experiments/tourist-streaming/index.html",
  } } },
  server: { host: "127.0.0.1", port: 4317, strictPort: true },
  preview: { host: "127.0.0.1", port: 4317, strictPort: true },
});
