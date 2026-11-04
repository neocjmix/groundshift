import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { SparkRenderer, SplatMesh, SplatFileType } from "@sparkjsdev/spark";
import type { LoadedWorld } from "./load-world";

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
  const reset = useRef<() => void>(() => {});
  const zoom = useRef<(direction: number) => void>(() => {});
  const [status, setStatus] = useState<Status>({
    phase: "loading",
    message: "Loading scene…",
  });
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [attempt, setAttempt] = useState(0);

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
    let resize: ResizeObserver | undefined;
    let failCleanup: (() => void) | undefined;
    const started = performance.now();
    const fail = (error: unknown) => {
      if (!disposed && !failed) {
        failed = true;
        abort.abort();
        renderer?.setAnimationLoop(null);
        setStatus({
          phase: "error",
          message: error instanceof Error ? error.message : String(error),
        });
      }
    };
    const run = async () => {
      renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false });
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
      reset.current = () => {
        if (!controls) return;
        // OrbitControls.reset() does not clear pending damping deltas.
        const damping = controls.enableDamping;
        controls.enableDamping = false;
        controls.update();
        controls.reset();
        camera.position.fromArray(pose.position);
        camera.up.fromArray(pose.up).normalize();
        controls.target.fromArray(pose.target);
        controls.update();
        controls.enableDamping = damping;
      };
      reset.current();
      controls.saveState();
      zoom.current = (direction) => {
        if (!controls) return;
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
      spark = new SparkRenderer({ renderer });
      scene.add(spark);
      resize = new ResizeObserver(() => {
        if (!renderer) return;
        const { width, height } = container.getBoundingClientRect();
        renderer.setSize(width, height);
        camera.aspect = width / Math.max(height, 1);
        camera.updateProjectionMatrix();
      });
      resize.observe(container);
      const response = await fetch(world.assetUrl, { signal: abort.signal });
      if (!response.ok)
        throw new Error(
          `Scene asset: HTTP ${response.status}. Download the sample or check the asset path.`,
        );
      if (response.headers.get("content-type")?.includes("text/html"))
        throw new Error("The scene URL returned a web page instead of a Gaussian asset. Check the asset path and download the sample if needed.");
      const total = Number(response.headers.get("content-length"));
      const chunks: Uint8Array[] = [];
      let received = 0;
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
        fileName: world.manifest.assets[0].path,
        fileType: {
          ply: SplatFileType.PLY,
          spz: SplatFileType.SPZ,
          splat: SplatFileType.SPLAT,
          ksplat: SplatFileType.KSPLAT,
          sog: SplatFileType.PCSOGSZIP,
        }[world.manifest.assets[0].format],
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
      const count = mesh.splats?.getNumSplats() ?? 0;
      if (count === 0)
        throw new Error("The asset contains no renderable Gaussians.");
      const transform = world.manifest.coordinates.assetToWorld;
      mesh.position.fromArray(transform.position);
      mesh.quaternion.fromArray(transform.quaternion);
      mesh.scale.setScalar(transform.scale);
      scene.add(mesh);
      const gl = renderer.getContext();
      const debug = gl.getExtension("WEBGL_debug_renderer_info");
      const gpu = debug
        ? String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL))
        : String(gl.getParameter(gl.RENDERER));
      const loadMs = performance.now() - started;
      let last = performance.now();
      let frames = 0;
      let totalFrames = 0;
      renderer.setAnimationLoop(() => {
        if (!renderer || disposed || failed) return;
        try {
          controls?.update();
          renderer.render(scene, camera);
          totalFrames++;
          // A render submission is not visual acceptance; acceptance uses screenshots.
          if (totalFrames === 3)
            setStatus({ phase: "ready", message: "Scene loaded" });
          frames++;
          const now = performance.now();
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
        } catch (error) {
          fail(error);
        }
      });
    };
    void run().catch(fail);
    return () => {
      disposed = true;
      abort.abort();
      renderer?.setAnimationLoop(null);
      resize?.disconnect();
      controls?.dispose();
      if (!meshPending) mesh?.dispose();
      spark?.dispose();
      failCleanup?.();
      renderer?.dispose();
      renderer?.forceContextLoss();
      renderer?.domElement.remove();
      reset.current = () => {};
      zoom.current = () => {};
    };
  }, [world, attempt]);

  return (
    <div className="scene-shell" data-phase={status.phase}>
      <div ref={mount} className="canvas-mount" />
      <div className="scene-topline">
        <span className="live-dot" /> WORLD VIEW{" "}
        <span className="topline-separator">/</span> {world.manifest.id}
      </div>
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
            Drag to orbit <span>·</span> Scroll to explore <span>·</span>{" "}
            Right-drag to pan
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
