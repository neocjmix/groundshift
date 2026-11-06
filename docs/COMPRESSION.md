# Same scene, smaller storage — 2026-11-07

[Live comparison](https://groundshift-viewer-production.up.railway.app/experiments/compression/)
· [SPZ](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-tangent20-spz/world.json)
· [preserved PLY](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-tangent20/world.json).

**Result:** storage-only SPZ quantization reduces the current full-direction
tangent20 scene from 73.60 MB to 15.94 MB, **78.35% less** (4.62× smaller).
All 800,000 Gaussians and SH degree1 remain. On 67 matched1024px views,
the active-pixel RGB mean absolute difference from PLY is1.348/255;
all views pass the declared codec screen. Direct overview, facade,
road, branch/railing and upward-view inspection shows no large appearance
regression. Fine numerical/edge/color differences exist. Retain SPZ as the
lightweight delivery candidate for this scene, with the original PLY intact.
This is not lossless compression or an improvement to reconstruction geometry.

No depth inference, camera fitting, Gaussian training, pruning, recentering,
new capture, synthetic training images or background completion ran.
The existing same-data quality campaign remains closed.

## Implementation and format choice

`scripts/compress-world.mjs` uses the already installed, pinned
`@sparkjsdev/spark` **2.4.0** `transcodeSpz` implementation in local Node CPU/WASM.
It converts float PLY directly, without first round-tripping through the
renderer's packed GPU representation. Exact arguments:

```js
{
  inputs: [{fileBytes, fileType: 'ply', pathOrUrl: 'scene.ply'}],
  maxSh: 1,
  fractionalBits: 15,
  opacityThreshold: 0,
  version: 3
}
```

No clip bounds or transform are supplied, so conversion uses identity raw-asset
coordinates. The existing `assetToWorld` and navigation metadata are copied
unchanged; `cameras.json` and source license are copied byte for byte.
The derived manifest has a separate ID and asset path; it cannot replace
the original model. Publishing and future conversion refuse a background-enabled
source or an existing output directory.

The current [official SPZ documentation](https://github.com/nianticlabs/spz)
describes v4/ZSTD as the newest format. The installed Spark writer exposes
v2/v3, so this run explicitly selects **v3/gzip**, not assumed-v4 support.
v3 keeps more accurate quaternion quantization than v2. SPZ uses signed24-bit
fixed-point positions and quantizes scale, rotation, alpha, DC color and SH
coefficients. Keeping SH degree does **not** retain its original float precision.
[Spark upstream](https://github.com/sparkjsdev/spark) and SPZ code are MIT;
the derived world retains Cicero101 / Mapillary / Wikimedia Commons
CC-BY-SA4.0 attribution. No new dependency, model weights or service is needed.

Position fractional precision is selected from actual bounds, keeping the
highest safe setting up to20bits without rescaling. Here max absolute position
is129.0622406006 arbitrary SfM units, so15bits fits signed24-bit. Step is
0.000030517578125; the maximum observed difference over **all2,400,000 position
components** is0.0000152587890625, exactly half a step. These are **not meters**.
Validation checks source property layout/finite values, SPZ header/payload size,
Gaussian count, SH degree, known flags and every signed position in source order.
Spark's `clippedCount` is deliberately ignored: installed2.4.0 returns a
hard-coded zero. Header flags=1 is retained and reported; no equivalence is
claimed for unrelated viewers' antialias handling.

## Actual execution measurements

Machine: Apple M2 /16GB; Node25.6.1; actual headed Chrome156.0.8078.81,
`ANGLE Metal Renderer: Apple M2`. Raw logs and all intermediate files remain local
under `data/jobs/street-spz-20261107/`.

| Item | Measured result |
| --- | --- |
| Original PLY | 73,600,652 bytes;800,000 Gaussians;SH1 |
| Lossless gzip6 control | 69,788,964 bytes; SHA-256 matches after decompression |
| SPZ v3 | 15,936,671 bytes;800,000 Gaussians;SH1 |
| Conversion only | 1.067132333 s |
| Full conversion/position checks/gzip control | 3.463214792 s |
| Node high-water RSS | 525,287,424 bytes; runtime/validation/gzip included, **not GPU memory** |
| Matched renders | 201 actual frames:67 each PLY/SPZ/PLY-repeat;113.784 s total harness execution |
| Mean active RGB difference | 1.347516189 /255 |
| Worst per-view mean RGB difference | 1.440409558 /255 |
| Minimum per-view active PSNR | 42.193433 dB |
| Reloaded PLY repeat control | Mean0.013525059;worst0.084780076 /255 |

Source PLY SHA-256:
`b9213464d654d8fbda1721a1a86415fa4670cb50c4b9ce5107791b7906f94a3e`.
SPZ SHA-256:
`9cb152e31fe4ae0eec76d53f8ce8b430118aa1e48db25282562eae558c6ca004`.

The matched renderer records local uncompressed HTTP download/decode separately:
PLY223.4/235.1ms, SPZ37.4/212.1ms; repeated PLY134.3/207.8ms.
These are one-run local observations, not controlled network benchmarks.
The production-preview app uses gzip, a different transfer condition.

Initial **public** cold-browser runs, cache explicitly disabled, SPZ then PLY:

| Format | Browser encoded asset body | Asset request duration | Page navigation → ready |
| --- | --- | --- | --- |
| SPZ | 15,936,671 bytes; no HTTP content encoding | 7.960 s | 12.226 s |
| PLY | 73,602,016 bytes; HTTP `zstd` | 25.052 s | 34.225 s |

Caddy's negotiated zstd here slightly expands the float PLY; this is the actual
browser result, not the separate gzip6 or earlier Python zstd9 control.
Network/server caching/concurrent local workloads were not controlled;
do not generalize this single pair into a guaranteed speedup.
Ready means three submitted frames; pixel screenshots separately confirm actual
rendering. No claim of proportional GPU-memory savings or higher FPS is made.

## Comparison protocol and observations

The original render configuration is frozen by SHA-256
`f030bada81484a9fdad2e03e944b95b792d2a9a8e1b317f1d441d9398a53fb9a`.
The script retains12 held camera views (panorama5 level/downward), adds6
explicit display rotations toward the poles and retains the49-frame interpolated
movement sequence. Panorama5 RGB was withheld from the original GS training;
existing all-nine SfM geometry was reused. This comparison evaluates **codec
error versus the original PLY**, not held-photo error or independent depth truth.
Display rotations and path interpolation are not new observed camera poses.

Before measuring, the heuristic screen requires every view's active RGB
MAE≤2/255 and PSNR≥35dB. A pixel is active when either scene's accumulated alpha
exceeds25/255. RGB is the actual straight-alpha render composited over127gray,
matching the existing render script. Empty sky does not dilute the active score.
Both sources use the same cameras/resolution/renderer/settling policy. A second
PLY load captures renderer variability; compression differences exceed that floor
but remain small. Full per-view rows and the repeat control are in the public
summary; original lossless PNGs remain local. Public JPEG figures and H.264 video
are convenient inspection media, **not the inputs to the numerical score**.

The three-column figures show PLY, SPZ and absolute RGB difference×8.
The native512px detail crop is not upscaled. Selected frames retain the existing
road smearing, wall overlap, distant-window blur and branch/railing ghosts;
compression neither fixes nor materially worsens those observed limitations.
The49-frame video puts both actual renders on the same path side by side.
Geometric accuracy and continuous point-cloud consistency are still unaccepted.

## Validation and preserved failures

| Check | Status |
| --- | --- |
| Local CPU/WASM conversion, all positions, count/SH and metadata | PASS |
| TypeScript, ESLint, production build | PASS |
| JS automated tests | PASS188, including8 new malformed/header/SH/coordinate tests |
| Headed matched M2 render comparison | PASS201frames/67views, no page errors |
| Local app rendering/movement/free look in PLY and SPZ | PASS2cases |
| Local report/mobile/discovery | Initial FAIL, repaired targeted retry PASS |
| Initial Railway export status and19changed public file hashes | PASS |
| Initial public report and both real formats, movement/free look | PASS3cases in54.8s |
| Measured-evidence release | PASS Railway SUCCESS;9changed file hashes; fresh12-layer1142file restore |
| Updated public report/video/mobile/discovery | PASS1case in9.7s; actual decoded frames0.6→2.3s change and are inspected |
| Full growing browser suite, native retraining, GPU-memory benchmarking | NOT RUN; not required to establish this bounded codec result |

[Sanitized evidence snapshot](evidence/compression.json) retains per-view metrics,
failure history, actual public timing fields and completed stage checks. The
conversion-time `measurement.visualQuality`/`browserRendering` NOT RUN values
remain immutable timestamps; the later top-level checks contain completed
follow-up evidence. Final verification-metadata release status is tracked in
[deployment](DEPLOYMENT.md), separately from the completed render/video checks.

Attempts01/02 fail in the new **validator**, because it initially rejects the
valid known flags=1 header; attempt02 retains the actual SPZ and expanded header
diagnostic. Accepting only the known flag and checking payload length fixes this;
attempt03 uses the same source/model/conversion configuration and passes.
The first local report test fails because the timeline has two legitimate links
to the same report. Selecting the first link repairs the test; its trace is
preserved. The first measured-publication package also rejects a loopback URL in
local timing metadata; the publisher now redacts that field and rejects private
references before packaging. No failed package was uploaded.

Vite emitted reload notifications for unrelated test artifacts during the first
comparison. All201frames complete, page errors are empty and the PLY repeat
floor is recorded. The renderer now disables HMR and ignores generated
data/dist/test directories for future reproduction; no metric improvement is
claimed from that mechanical change.

## Reproduce

Restore the current public observation assets following [deployment](DEPLOYMENT.md),
including `public/worlds/street-tangent20/`. `npm ci` supplies the pinned local
codec. Always choose a **new** output directory:

```sh
node scripts/compress-world.mjs public/worlds/street-tangent20 data/jobs/my-spz/world
npm test
npm run typecheck
npm run lint
npm run build
```

The converter writes `scene.spz`, `world.json`, genuine `cameras.json`, source
license and `compression.json`, retaining an explicit FAIL report if conversion
or validation fails. Open this folder with the viewer to inspect locally;
no upload is needed. `preview.jpg` is not required for local folder opening.

For an existing1024px frozen street render configuration:

```sh
node scripts/compare-compression.mjs public/experiments/compression/evaluation-cameras.json \
  public/worlds/street-tangent20/scene.ply data/jobs/my-spz/world/scene.spz data/jobs/my-spz/compare
data/tools/venv/bin/python scripts/review-compression.py data/jobs/my-spz/compare data/jobs/my-spz/inspection
npx playwright test tests/browser/compression.pw.mjs
GS_BASE_URL=https://groundshift-viewer-production.up.railway.app \
  npx playwright test tests/browser/compression.pw.mjs
```

The published sanitized camera configuration preserves the original estimated
matrices/intrinsics and display path, without local file references. It allows
the same comparison after restoring the public artifacts; no poses are guessed
in a fresh checkout. Its file hash differs from the original local configuration
because model paths and unused image references are removed. The render
comparison and converter do not need Brush, COLMAP or an inference GPU.
Figure/video assembly needs existing Pillow and free local FFmpeg/libx264.

The observation publisher accepts only the selected derivative, public evidence
and explicit report files. It updates the scene catalog and chronological lab.
Export goes live first with NOT RUN visual checks, then comparisons and completed
public checks ship in follow-up checksum-pinned overlays. The original native
world, all prior observations and rollback archives remain preserved.

Next: use this bounded result for serving work (first usable view, transfer and
resident-scene budgets), then spatial loading if needed. No further same-data
reconstruction quality sweep is authorized by this storage experiment.
