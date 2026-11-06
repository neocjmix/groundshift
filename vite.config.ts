import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
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
  } } },
  server: { host: "127.0.0.1", port: 4317, strictPort: true },
  preview: { host: "127.0.0.1", port: 4317, strictPort: true },
});
