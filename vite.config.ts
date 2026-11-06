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
  } } },
  server: { host: "127.0.0.1", port: 4317, strictPort: true },
  preview: { host: "127.0.0.1", port: 4317, strictPort: true },
});
