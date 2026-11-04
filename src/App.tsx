import { useEffect, useRef, useState } from "react";
import Viewer from "./Viewer";
import { loadLocalWorld, loadWorld, type LoadedWorld } from "./load-world";

const samplePath = "/worlds/sample/world.json";
const initialPath =
  new URLSearchParams(window.location.search).get("world") || samplePath;

export default function App() {
  const [path, setPath] = useState(initialPath);
  const [request, setRequest] = useState({ path: initialPath, revision: 0 });
  const [world, setWorld] = useState<LoadedWorld | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const sequence = useRef(0);
  const folderInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    const current = ++sequence.current;
    void loadWorld(request.path, controller.signal)
      .then((result) => {
        if (current === sequence.current) setWorld(result);
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

  const openFolder = async (files: File[]) => {
    if (!files.length) return;
    const current = ++sequence.current;
    setLoading(true);
    setError("");
    try {
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
  const load = (value: string) => {
    setLoading(true);
    setError("");
    setPath(value);
    setRequest((previous) => ({
      path: value,
      revision: previous.revision + 1,
    }));
  };

  return (
    <div className="app">
      <header className="app-header">
        <a className="brand" href="/" aria-label="Groundshift home">
          <span className="brand-symbol">
            g<span>s</span>
          </span>
          <span>
            groundshift
            <span className="brand-caption">REAL PLACES, REVISITED.</span>
          </span>
        </a>
        <span className="local-badge">
          <span className="live-dot" /> On your Mac
        </span>
      </header>
      <main>
        <aside className="sidebar">
          <div className="intro">
            <span className="eyebrow">YOUR WINDOW BACK</span>
            <h1>
              Some places
              <br />
              stay with you.
            </h1>
            <p>
              Step back into a captured world.
              <br />
              Take a look around.
            </p>
          </div>
          <div className="section-label">
            OPEN WORLD <span>01</span>
          </div>
          <button className="sample-card" onClick={() => load(samplePath)}>
            <span className="sample-glyph">❋</span>
            <span>
              <strong>The small things</strong>
              <small>Plant study · Sample scene</small>
            </span>
            <span className="arrow">↗</span>
          </button>
          <button
            className="folder-button"
            onClick={() => folderInput.current?.click()}
          >
            <span>＋</span> Open world folder
          </button>
          <input
            ref={folderInput}
            className="visually-hidden"
            type="file"
            multiple
            {...{ webkitdirectory: "" }}
            aria-label="Choose world folder"
            onChange={(event) => {
              void openFolder(Array.from(event.target.files || []));
              event.target.value = "";
            }}
          />
          <p className="folder-hint">
            Choose a folder with <code>world.json</code> and its scene asset.
            Files stay on this device.
          </p>
          <details className="source-picker">
            <summary>Load from a local server</summary>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                load(path.trim());
              }}
            >
              <label htmlFor="world-url">World manifest URL</label>
              <input
                id="world-url"
                value={path}
                onChange={(event) => setPath(event.target.value)}
                placeholder="/worlds/my-world/world.json"
                required
              />
              <button type="submit">Load world →</button>
            </form>
          </details>
          {loading && (
            <p className="manifest-status" role="status">
              Reading world manifest…
            </p>
          )}
          {error && (
            <div className="manifest-error" role="alert">
              <strong>Couldn’t open this world</strong>
              <p>{error}</p>
              <button onClick={() => load(samplePath)}>Open sample</button>
            </div>
          )}
          {world && (
            <section className="world-info">
              <div className="section-label">ABOUT THIS WORLD</div>
              <h2>{world.manifest.title}</h2>
              <p>{world.manifest.provenance.attribution}</p>
              <a
                href={world.manifest.provenance.sourceUrl}
                target="_blank"
                rel="noreferrer"
              >
                Source ↗
              </a>
              <a
                href={world.manifest.provenance.licenseUrl}
                target="_blank"
                rel="noreferrer"
              >
                {world.manifest.provenance.license} ↗
              </a>
              <div className="coordinate-note">
                Y-up · Right-handed ·{" "}
                {world.manifest.coordinates.unit === "meters"
                  ? "Meters"
                  : "Unscaled capture"}
                <br />
                Orbit view · No collision geometry
              </div>
            </section>
          )}
          <footer className="sidebar-footer">
            <span>GROUND SHIFT / 001</span>
            <p>A little closer to being there.</p>
          </footer>
        </aside>
        <section className="viewer-region" aria-label="World viewer">
          {world ? (
            <Viewer key={world.instanceId} world={world} />
          ) : (
            <div className="empty-view">
              <span className="empty-mark">gs</span>
              <p>
                {loading
                  ? "Opening your world…"
                  : "Open a world to begin exploring."}
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
