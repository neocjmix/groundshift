import { lazy, Suspense, useEffect, useRef, useState, type MouseEvent } from "react";
import type { LoadedWorld } from "./load-world";
import { parseSceneCatalog, type CatalogScene } from "./catalog";

const Viewer = lazy(() => import("./Viewer"));
const samplePath = "/worlds/sample/world.json";
const locationPath = () => new URLSearchParams(window.location.search).get("world");
const sceneUrl = (path: string) => `/?world=${encodeURIComponent(path)}`;
const experimentReport = "/experiments/mapillary/index.html";
const videoExperimentReport = "/experiments/video-4to6/";
const depthExperimentReport = "/experiments/depth-v2/";
const depthWarpReport = "/experiments/depth-warp/";
const categories = {
  capture: "Personal capture",
  reconstruction: "Local reconstruction",
  sample: "Sample scene",
  experiment: "Experiments",
};
const plainClick = (event: MouseEvent<HTMLAnchorElement>) =>
  event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;

export default function App() {
  const [path, setPath] = useState(locationPath() || samplePath);
  const [request, setRequest] = useState({ path: locationPath(), revision: 0 });
  const [localMode, setLocalMode] = useState(false);
  const [world, setWorld] = useState<LoadedWorld | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(Boolean(locationPath()));
  const [scenes, setScenes] = useState<CatalogScene[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [catalogRevision, setCatalogRevision] = useState(0);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sortOrder, setSortOrder] = useState("newest");
  const sequence = useRef(0);
  const folderInput = useRef<HTMLInputElement>(null);
  const viewerOpen = Boolean(request.path) || localMode;
  const experimentCount = scenes.filter((scene) => scene.category === "experiment").length;
  const videoExperimentAvailable = scenes.some((scene) => scene.id === "beijing-video-rife");
  const depthWarpAvailable = scenes.some((scene) => scene.id === "beijing-depth");
  const selectedScene = scenes.find((scene) => scene.manifestPath === request.path);

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/worlds/catalog.json", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Scene collection: HTTP ${response.status}`);
        return parseSceneCatalog(await response.json());
      })
      .then((catalog) => {
        if (!controller.signal.aborted) setScenes(catalog.scenes);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted)
          setCatalogError(cause instanceof Error ? cause.message : String(cause));
      })
      .finally(() => { if (!controller.signal.aborted) setCatalogLoading(false); });
    return () => controller.abort();
  }, [catalogRevision]);

  useEffect(() => {
    if (!request.path) return;
    const controller = new AbortController();
    const current = ++sequence.current;
    const selectedPath = request.path;
    void import("./load-world").then(({ loadWorld }) => loadWorld(selectedPath, controller.signal))
      .then((result) => {
        if (current === sequence.current) setWorld(result);
        else result.release?.();
      })
      .catch((cause: unknown) => {
        if (current === sequence.current && !controller.signal.aborted)
          setError(cause instanceof Error ? cause.message : String(cause));
      })
      .finally(() => {
        if (current === sequence.current) setLoading(false);
      });
    return () => controller.abort();
  }, [request]);
  useEffect(() => () => world?.release?.(), [world]);

  useEffect(() => {
    const restore = () => {
      const nextPath = locationPath();
      ++sequence.current;
      setWorld(null);
      setLocalMode(false);
      setError("");
      setLoading(Boolean(nextPath));
      setPath(nextPath || samplePath);
      setRequest((previous) => ({ path: nextPath, revision: previous.revision + 1 }));
    };
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  const load = (value: string | null) => {
    ++sequence.current;
    setWorld(null);
    setLocalMode(false);
    setLoading(Boolean(value));
    setError("");
    setPath(value || samplePath);
    setRequest((previous) => ({ path: value, revision: previous.revision + 1 }));
    const url = value ? sceneUrl(value) : "/";
    if (window.location.pathname + window.location.search !== url)
      window.history.pushState(null, "", url);
  };
  const follow = (event: MouseEvent<HTMLAnchorElement>, value: string | null) => {
    if (!plainClick(event)) return;
    event.preventDefault();
    load(value);
    window.scrollTo({ top: 0 });
  };
  const openFolder = async (files: File[]) => {
    if (!files.length) return;
    const current = ++sequence.current;
    setWorld(null);
    setLocalMode(true);
    setRequest((previous) => ({ path: null, revision: previous.revision + 1 }));
    window.history.pushState(null, "", "/");
    setLoading(true);
    setError("");
    try {
      const { loadLocalWorld } = await import("./load-world");
      const result = await loadLocalWorld(files);
      if (current === sequence.current) setWorld(result);
      else result.release?.();
    } catch (cause) {
      if (current === sequence.current)
        setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      if (current === sequence.current) setLoading(false);
    }
  };
  const visibleScenes = scenes.filter((scene) =>
    (filter === "all" || scene.category === filter) &&
    `${scene.title} ${scene.description} ${scene.detail} ${categories[scene.category]}`
      .toLowerCase().includes(search.trim().toLowerCase()),
  ).sort((a, b) => {
    if (!a.createdAt) return b.createdAt ? 1 : 0;
    if (!b.createdAt) return -1;
    return (Date.parse(a.createdAt) - Date.parse(b.createdAt)) * (sortOrder === "oldest" ? 1 : -1);
  });
  const catalogStatus = <>
    {catalogLoading && <p className="manifest-status" role="status">Opening the collection…</p>}
    {catalogError && <div className="manifest-error" role="alert">
      <strong>Couldn’t load the scene collection</strong><p>{catalogError}</p>
      <button onClick={() => {
        setCatalogLoading(true); setCatalogError(""); setCatalogRevision((value) => value + 1);
      }}>Try again</button>
    </div>}
  </>;
  const importControls = <div className="import-controls">
    <button className="folder-button" onClick={() => folderInput.current?.click()}>
      <span>＋</span> Open world folder
    </button>
    <p className="folder-hint">Choose a folder with <code>world.json</code> and its scene asset. Files stay on this device.</p>
    <details className="source-picker">
      <summary>Load from a URL</summary>
      <form onSubmit={(event) => { event.preventDefault(); load(path.trim()); }}>
        <label htmlFor="world-url">World manifest URL</label>
        <input id="world-url" value={path} onChange={(event) => setPath(event.target.value)} placeholder="/worlds/my-world/world.json" required />
        <button type="submit">Load world →</button>
      </form>
    </details>
  </div>;

  return <div className="app">
    <header className="app-header">
      <a className="brand" href="/" aria-label="Groundshift home" onClick={(event) => follow(event, null)}>
        <span className="brand-symbol">g<span>s</span></span>
        <span>groundshift<span className="brand-caption">REAL PLACES, REVISITED.</span></span>
      </a>
      <div className="header-right">
        {viewerOpen && <a className="collection-link" href="/" onClick={(event) => follow(event, null)}>← Back to scenes</a>}
        {videoExperimentAvailable && <a className="collection-link" href={videoExperimentReport}>65-frame video ↗</a>}
        {experimentCount > 0 && <a className="collection-link experiment-report-link" href={experimentReport}>Experiment report ↗</a>}
        {scenes.some(scene => scene.id === "scooter-object") && <a className="collection-link" href="/experiments/lab/">실험실 · 시간순 ↗</a>}
        <span className="local-badge"><span className="live-dot" /> Renders on your device</span>
      </div>
    </header>
    <input ref={folderInput} className="visually-hidden" type="file" multiple {...{ webkitdirectory: "" }} aria-label="Choose world folder"
      onChange={(event) => { void openFolder(Array.from(event.target.files || [])); event.target.value = ""; }} />
    {!viewerOpen ? <main className="collection-page">
      <div className="collection-intro">
        <div><span className="eyebrow">LOCAL RECONSTRUCTION / LIVE OBSERVATIONS</span>
          <h1>Groundshift observation room.</h1>
          <p>Explore the scenes we have made, including rough experiments. Visibility here does not mean visual-quality acceptance.</p>
        </div>
        <div className="collection-count"><strong>{String(scenes.length).padStart(2, "0")}</strong><span>exported scenes</span></div>
      </div>
      {experimentCount > 0 && <section className="experiment-overview" aria-labelledby="experiment-heading">
        <div><span className="eyebrow">CURRENT EXPERIMENT · MAPILLARY 360°</span>
          <h2 id="experiment-heading">Real photos, generated gaps, actual results.</h2>
          <p>Compare source photos, generated frames and Gaussian trials. Failed, cancelled and unrun stages stay visible with their evidence and limits. Generated scenery is assessed for plausibility, with real-place fidelity reported separately.</p>
        </div>
        {scenes.some(scene => scene.id === "scooter-object") && <a href="/experiments/lab/">실험실 · 최신 결과부터 <span aria-hidden="true">↗</span></a>}
        <a href={experimentReport}>Compare source, warp &amp; diffusion <span aria-hidden="true">↗</span></a>
        {videoExperimentAvailable && <a href={videoExperimentReport}>Watch 65-frame panorama <span aria-hidden="true">↗</span></a>}
        {videoExperimentAvailable && <a href={depthExperimentReport}>Inspect photo depth maps <span aria-hidden="true">↗</span></a>}
        {depthWarpAvailable && <a href={depthWarpReport}>Depth-guided scene experiment <span aria-hidden="true">↗</span></a>}
      </section>}
      <div className="collection-toolbar">
        <div className="collection-filters" role="group" aria-label="Filter scenes">
          <button aria-pressed={filter === "all"} onClick={() => setFilter("all")}>All scenes</button>
          {Object.entries(categories).map(([value, label]) => <button key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}</button>)}
        </div>
        <input className="scene-search" type="search" aria-label="Search scenes" placeholder="Search scenes…" value={search} onChange={(event) => setSearch(event.target.value)} />
        <select className="scene-sort" aria-label="Sort scenes by time" value={sortOrder} onChange={event => setSortOrder(event.target.value)}><option value="newest">최신순</option><option value="oldest">오래된 순</option></select>
      </div>
      {catalogStatus}
      <section className="scene-grid" aria-label="Scene collection">
        {visibleScenes.map((scene, index) => <a className="scene-card" key={scene.id} href={sceneUrl(scene.manifestPath)} onClick={(event) => follow(event, scene.manifestPath)}>
          <div className="scene-preview"><img src={scene.thumbnailPath} alt="" loading={index > 1 ? "lazy" : "eager"} /><span className="scene-open">Explore scene ↗</span></div>
          <div className="scene-card-copy"><span className={`scene-category category-${scene.category}`}>{categories[scene.category]}</span>
            <h2>{scene.title}<span aria-hidden="true">↗</span></h2>
            <p>{scene.description}</p><small>{scene.detail}</small>
            {scene.createdAt && <time dateTime={scene.createdAt}>{new Date(scene.createdAt).toLocaleString()}</time>}
          </div>
        </a>)}
      </section>
      {!catalogLoading && !catalogError && visibleScenes.length === 0 && <div className="collection-empty" role="status"><p>No scenes match this view.</p><button onClick={() => { setFilter("all"); setSearch(""); }}>Show all scenes</button></div>}
      <div className="collection-bottom">
        <div className="collection-note"><span className="eyebrow">OBSERVE, COMPARE, ITERATE</span><h2>Local computation. Visible outcomes.</h2><p>Reconstructions run on an Apple M2; Houseplant is a downloaded viewer sample. Each scene identifies its inputs and limits. Experimental results remain available regardless of quality, and previews show actual 3D renders.</p></div>
        {importControls}
      </div>
      <footer className="collection-footer"><span>GROUND SHIFT / OBSERVATION ROOM</span><span>What worked, what failed, what comes next.</span></footer>
    </main> : <main className="viewer-page">
      <aside className="sidebar">
        <div className="section-label">SAVED SCENES <span>{String(scenes.length).padStart(2, "0")}</span></div>
        {catalogStatus}
        <nav className="saved-scenes" aria-label="Saved scenes">
          {scenes.map((scene) => <a key={scene.id} href={sceneUrl(scene.manifestPath)} onClick={(event) => follow(event, scene.manifestPath)} aria-current={request.path === scene.manifestPath ? "page" : undefined}>
            <img src={scene.thumbnailPath} alt="" /><span><strong>{scene.title}</strong><small>{categories[scene.category]}</small></span>
          </a>)}
        </nav>
        {selectedScene?.category === "experiment" && <section className="experiment-context" aria-label="Experiment status">
          <strong>Experiment output</strong>
          <p>{selectedScene.description}</p>
          <p className="experiment-detail">{selectedScene.detail}</p>
          <small>Inclusion does not imply visual-quality acceptance.</small>
          <a href={selectedScene.id.startsWith("scooter-real-") ? "/experiments/object-real/" : selectedScene.id.startsWith("scooter-") ? "/experiments/object-focus/" : selectedScene.id === "beijing-depth" ? depthWarpReport : selectedScene.id.startsWith("beijing-video-") ? videoExperimentReport : experimentReport}>Comparison &amp; stage history ↗</a>
        </section>}
        {importControls}
        {loading && <p className="manifest-status" role="status">Reading world manifest…</p>}
        {error && <div className="manifest-error" role="alert"><strong>Couldn’t open this world</strong><p>{error}</p><button onClick={() => load(samplePath)}>Open sample</button></div>}
        {world && <section className="world-info">
          <div className="section-label">ABOUT THIS WORLD</div><h2>{world.manifest.title}</h2><p>{world.manifest.provenance.attribution}</p>
          <a href={world.manifest.provenance.sourceUrl} target="_blank" rel="noreferrer">Source ↗</a>
          <a href={world.manifest.provenance.licenseUrl} target="_blank" rel="noreferrer">{world.manifest.provenance.license} ↗</a>
          <div className="coordinate-note">Y-up · Right-handed · {world.manifest.coordinates.unit === "meters" ? "Meters" : "Unscaled capture"}<br />Camera views · No collision geometry</div>
        </section>}
        <footer className="sidebar-footer"><span>GROUND SHIFT / OBSERVATION ROOM</span><p>What worked, what failed, what comes next.</p></footer>
      </aside>
      <section className="viewer-region" aria-label="World viewer">
        {world ? <Suspense fallback={<div className="empty-view" role="status"><span className="empty-mark">gs</span><p>Preparing the 3D viewer…</p></div>}><Viewer key={world.instanceId} world={world} /></Suspense> : <div className="empty-view"><span className="empty-mark">gs</span><p>{loading ? "Opening your world…" : "Open a world to begin exploring."}</p></div>}
      </section>
    </main>}
  </div>;
}
