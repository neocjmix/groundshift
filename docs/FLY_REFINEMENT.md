# Fly controls and nearby detail — 2026-11-07

The viewer now uses a floating movement stick on the lower left, swipe-to-look
on the scene, and rise/descend buttons on the right. The Paris native-LoD viewer
also has a larger, still bounded detail budget. This changes navigation and
serving of the existing Gaussian artifact; it does not retrain the scene.

[Open Paris](https://groundshift-viewer-production.up.railway.app/?world=/worlds/paris-58m-lod/world.json)
· [Observation report](https://groundshift-viewer-production.up.railway.app/experiments/tourist-streaming/)
· [Compact evidence](evidence/fly-refinement.json)
· [Previous Fly implementation and retained history](FLY.md)

## Mobile control change

- Touch within the lower-left region to create the movement stick at that exact
  point. Forward/backward and strafe remain relative to camera heading.
- Swipe the scene to look. The right joystick is removed; right-side ↑/↓ buttons
  are 52px and support press-and-hold height movement.
- The activation region covers the lower 55% of the left 45% of the viewport,
  with margins for the stick and device safe areas. Origins stay at least 76px
  above the bottom in portrait, or 62px in short landscape viewports. This leaves
  actual travel space for backward movement rather than clamping the origin away
  from the finger.
- Independent pointer owners allow movement and look together. Release, pointer
  cancellation, blur, hidden-document and resize handling clear held movement.
  The zone is hidden for a fine primary pointer so it does not intercept desktop
  mouse look. WASD, mouse, Q/E, Shift, speed, reset and exit remain available.

The reported vertical offset was real: the former CSS grid contained an empty
span and a knob in separate implicit rows. At a 390×844 viewport the visual knob
was **16.078125px below** the pad center used by input math. Absolute centering
removes that discrepancy. In actual Chrome touch input, an origin at
(115.75,760) produced exactly that pad and knob center, with no neutral drift.
A downward drag below the activation region still moved backward under pointer
capture. Forward and backward displacements from the same heading had a
normalized dot product of −1.0. Re-touching creates a fresh origin.

[FlyControls](../src/FlyControls.tsx) uses stable refs and direct visual transforms
for transient input. [Stick math](../src/floating-stick.ts) applies a radial dead
zone and bounded travel; it does not schedule React renders for pointer samples.
There is still no collision, inferred floor, gravity or metric walking speed.

## Why waiting did not sharpen the old LoD view

The original configuration capped selection at 350,000 Gaussians and residency
at eight 65,536-slot pages. Spark keeps coarser hierarchy parents when these
budgets prevent refinement. Its fetcher stops beyond its page priority budget,
so zero pending requests does **not** mean that all visible detail has arrived.

The existing Paris source has 800,000 Gaussians. The derived hierarchy contains
1,048,377 entries across 16 chunks. The selected configuration is:

| Setting | Previous | Selected |
| --- | ---: | ---: |
| Selection budget | 350,000 | 800,000 |
| Resident page limit | 8 | 14 |
| Resident slots | 524,288 | 917,504 |
| Concurrent fetchers | 2 | 2 |

Standard traversal and the existing packed decode remain in use. Merely growing
the pool while retaining the 350k selection ceiling still blurred the start
view. Twelve pages improved it but retained more error; 16 pages were a full
hierarchy diagnostic, not the chosen streaming setting. Dynamic traversal,
aggressive foveation and extended decode did not justify changing their defaults.

Actual fixed-camera, 768×768 Chrome renders of unchanged assets gave:

| Start-view measurement against whole SPZ | Previous 8 pages / 350k | Selected 14 pages / 800k |
| --- | ---: | ---: |
| Selected Gaussians | 349,915 | 670,968 |
| Mean absolute RGB difference, 0–255 | 3.3222 | 1.3248 |
| Central-region RGB difference, 0–255 | 5.4777 | 1.4709 |
| Central horizontal-edge contrast ratio | 0.7743 | 0.9945 |

These compare two ways of rendering the **same reconstructed scene**, not
accuracy against photographs or surveyed geometry. Other diagnostic views and
alternative settings remain in the local evidence. Source blur, ghosting and
uncovered areas still exist.

With an explicit **250ms delay per RADC request fixture**, the fixed-view
diagnostic progressed through 52,788, 156,893, 262,144 and eventually 670,968
selected entries. Residency stayed within 14 pages. Actual fetch/decode call
counts increased 14→16→17→19→21 across start, side, near side, end and return
views, with page contents changing. Those times describe the latency fixture,
not public network performance. An earlier `window.fetch`-only counter missed
Spark's other request path; its zero arrays are retained as failed instrumentation
and are not treated as network evidence.

The tradeoff is **75% more resident slots**. Actual GPU memory and isolated frame
cost are NOT MEASURED. Fourteen of this small scene's sixteen chunks is most of
the hierarchy, so this is a nearby-detail fix with limited initial bandwidth
savings; hierarchy bytes can exceed the whole SPZ. It does not establish that a
kilometer-scale scene or a physical phone fits this budget.

Primary implementation references: pinned
[Spark renderer budgets](https://github.com/sparkjsdev/spark/blob/ffe210dc0a45d0515a06c9235878108112827d61/src/SparkRenderer.ts#L182-L218),
[page priority limit](https://github.com/sparkjsdev/spark/blob/ffe210dc0a45d0515a06c9235878108112827d61/src/SplatPager.ts#L588-L629),
and [LoD traversal](https://github.com/sparkjsdev/spark/blob/ffe210dc0a45d0515a06c9235878108112827d61/rust/spark-rs/src/lod_tree.rs#L480-L526).

## Graphics failure ownership

An unchanged forced-context-loss test exposed a residual asynchronous failure:
rendering recovered after Retry, but the page emitted an uncaught `undefined`.
[Three r180's GPU fence wait](https://github.com/mrdoob/three.js/blob/r180/src/utils.js#L90-L108)
rejects without a value on `WAIT_FAILED`. That rejection can occur before the
browser dispatches `webglcontextlost`, when the previous handler would dispose
Spark. Spark's pending-job cancellation catch only drops errors after disposal.

A bounded timing fixture caused **real** `WEBGL_lose_context` immediately before
an outstanding `clientWaitSync`. It captured WAIT_FAILED before the context-loss
event and reproduced the uncaught rejection 3/3 times. The viewer now owns its
renderer instance's `readRenderTargetPixelsAsync` rejection: it marks the scene
failed and disposes the owner before rethrowing to Spark's existing cancellation
handling. Any readback failure is visible as a scene error. No global rejection
suppression or fake success is used. The same real GPU fault then recovered
3/3 times with zero uncaught errors.

## Validation and retained failures

| Check | Current recorded result |
| --- | --- |
| TypeScript and complete lint | PASS |
| Complete unit suite | PASS, 215, including 3 floating-stick tests |
| Repaired immutable-package Fly cases | PASS, 3/3 in 22.5s |
| Exact pending-readback fault before repair | FAIL, 3/3 uncaught errors |
| Same fault after repair, including Exit/Retry | PASS, 3/3, no uncaught errors |
| Mobile portrait and landscape screenshot inspection | PASS, actual Chrome/CDP touch |
| Local fixed-camera LoD diagnostics | PASS execution; measured limits above |
| Maintained diagnostic script reproduction | PASS, 12/12 views in 28.2131205s, no errors |
| Actual application LoD acceptance | PASS, 1 case in 41.2s (suite 43.9s), no page errors |
| Final public Fly interaction | PASS, 3/3 in 42.8s, including pending-readback fault/recovery |
| Final public LoD interaction | PASS, refinement + native gsplat + compact cases, no page errors |
| App release file integrity / Railway status | PASS, all 6 changed public files match; Railway SUCCESS |
| Physical iPhone/Safari and Android | NOT RUN |
| Isolated GPU memory, reconstruction, geometry accuracy | NOT RUN |

The new mobile test initially failed because its CDP partial `touchEnd` listed
the remaining finger instead of the ending finger. An independent DOM event
capture identified that test protocol mistake; the corrected test then verified
that releasing movement leaves swipe look active. This is separate from the
real GPU readback defect, which reproduced on an unchanged sample case. Both
failures are retained rather than removed from the record.

The actual application LoD test also exposed a separate UI obstruction: the
streaming status panel intercepted the Zoom button through 290 traced click
retries. The panel now sits above the zoom controls (`bottom: 8rem`); the actual
application test then clicked Zoom and completed the whole-SPZ comparison. This was a real input
blocker, separate from the renderer-budget diagnosis.

The final local application check observed 681,830 selected entries and 14 pages
at the start. Requests grew 15→18→20 at start, end and return while resident
chunk sets changed within the same limit. The same-camera zoom comparison with
whole SPZ had mean RGB difference 1.322785, central difference 2.351454 and
central edge ratio 0.945790, passing the declared ≤4 / ≤3 / ≥0.9 checks.
Return-to-start pixels matched exactly (mean difference 0). These are actual
viewer controls and rendering, with cache disabled and an explicit 250ms/chunk
latency fixture; they are not a public network or physical-phone benchmark.

The final public refinement check repeated the same zoom measurements and exact
return match on Railway. It selected 681,830→555,653→681,830 entries and made
15→18→20 requests across start, end and return, staying within 14 pages. The
separate native gsplat and compact paging cases also passed their existing
whole-SPZ comparison: mean RGB differences 1.381511 and 1.199949 respectively,
with no page errors. All public cases used actual headed Chrome; the refinement
case retains the explicit latency fixture. Test duration and the viewer's FPS
label are not isolated performance benchmarks.

An earlier return screenshot failed the existing <0.2 difference criterion with
about 0.943. Camera, output dimensions and resident chunk set matched. Waiting
30 additional displayed frames after selection/network quiescence produced two
identical returns. The test now waits for those frames; the product and the
threshold were not changed for this finding. This supports a test-settling
explanation but does not prove the internal timing cause of the earlier image.
The original failed image and trace remain available locally.

The repaired immutable Fly run covered native fullscreen and desktop pointer
lock, WASD/mouse, drag fallback, reset/exit, floating origins, backward motion,
simultaneous movement/swipe, independent release, active touch cancellation,
resize clearing, right lift, and 390×844 / 844×390 layouts. Native fullscreen and
pointer-lock denial cases are explicit fixtures. Mobile input is actual CDP
simulated touch in installed Chrome 156.0.8078.81, not a physical iPhone test.
The deterministic readback timing trigger was subsequently promoted into the
maintained sample browser case. All three final public Fly cases passed in
42.8s with zero uncaught page errors. Actual public desktop, portrait and
landscape screenshots were inspected. These interaction screenshots can show
ongoing detail loading; the separate settled LoD comparison determines detail
acceptance.

## Reproduce and evidence

```sh
npm run typecheck
npm run lint
npm test
npm run build
npx playwright test tests/browser/fly.pw.mjs tests/browser/lod-refinement.pw.mjs
node scripts/diagnose-lod.mjs data/validation/NEW_LOD_DIAGNOSTIC_DIRECTORY
```

[Fly browser checks](../tests/browser/fly.pw.mjs),
[application refinement check](../tests/browser/lod-refinement.pw.mjs), and
[fixed-camera diagnostic](../scripts/diagnose-lod.mjs) retain real screenshots
and machine-readable evidence. The diagnostic refuses to overwrite its output.
During asynchronous publication, serve a frozen package using
`npm run preview -- --port 4347 --outDir PACKAGE/www` and set
`GS_BASE_URL=http://127.0.0.1:4347`. Public checks use the Railway origin.

[Paged-world preparation](../scripts/prepare-paged-world.py) now defaults to
917,504 resident slots (14 pages) and an 800,000 selection budget. Explicit
`--max-paged-splats` and `--lod-splat-count` options retain reproducible alternate
serving budgets. New canonical derivatives live under
`data/jobs/fly-detail-20261107/paris-58m-lod/world` and
`data/jobs/fly-detail-20261107/paris-58m-lod-compact/world`; original jobs remain
untouched. Across the 257 world files, only the two paging manifests changed for
the detail-budget release; the following clearance increment changed six app
files. Gaussian/source asset hashes remain unchanged. Restore ignored public
assets from the pinned archives using [DEPLOYMENT.md](DEPLOYMENT.md) before
running local browser checks or preparing another package.

Local raw evidence stays in ignored `data/validation/fly-mobile-20261107/` and
`data/validation/fly-detail-20261107/`. The compact checked-in record excludes raw
logs and machine paths. Previous worlds, original sources and rollback packages
remain preserved; publication is separate from quality acceptance.

## Public observation report

The final public report and chronological lab checks passed2/2 in14.0s.
They decoded all seven comparison images, switched original photographs,
checked the876-point route and private-HD exclusion, and checked mobile overflow.
Two preceding attempts exceeded the default5s expectation while a route body
or source image was queued. Responses were HTTP200 and no application exception
was recorded. The maintained report test now explicitly allows30s for network
readiness; all semantic assertions are unchanged. The two5s failures are retained
and are not evidence of passing a5s responsiveness target.

Evidence: `data/validation/fly-detail-20261107/browser-report-public-r3/`,
with earlier failures in `browser-report-public/` and `browser-report-public-r2/`.
