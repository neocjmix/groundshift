# Final quality attempt on the existing panoramas

Declared2026-11-06 before viewing the result. The user explicitly makes this the
**last quality campaign on these same nine source photographs**. Preserve the
best result afterward and move to new capture evidence or product work. Do not
turn a disappointing result into another model/filter/crop/budget/seed sweep.

## One actual native configuration

- Same nine licensed7680×3840 originals, source hashes and all-nine fixed-rig
  SfM. Eight training centers exclude panorama5 RGB as before.
-96 fresh1024×1024 real crops, with the exact same90° FOV, yaw/pitch and camera
  matrices. Extract directly from original ERP pixels, **not upscaled512 RGB**.
  Intrinsic pixel values scale by2; world positions and units never scale.
- Identical183,124-point DAV2 calibrated dense initialization and colors. No
  new depth prediction, new pose estimation or generated training photograph.
- Brush0.3.0 Metal,8,000 steps,800,000 Gaussian ceiling,SH1,seed42. Resolution
  and capacity change together as one practical quality probe; no factorial
  attribution or timing-speed claim. More steps alone already failed to improve
  the prior best, so this run does not repeat that search.
- Same angular nadir mask, regenerated on the1024 ray grid. Small sampling-edge
  differences are expected; do not pretend pixel masks are byte-identical.

Work directory: `data/jobs/street-final-quality-20261106/`. Each stage retains its
actual report/log. Source/previous worlds remain read-only. Mechanical failure
recovery must preserve this declared configuration and retain failed evidence;
no silent downscale or new quality budget.

## Evaluation and publication order

The incumbent is the actual512/400k DAV2 dense8k export, reused without claiming
retraining. Use the same75 evaluation cameras at512 output for direct comparison.
Also render both worlds at1024 with fresh1024 references to inspect fine detail;
do not compare an error measured at512 directly to one measured at1024.
Panorama5 appearance withholding still reuses all-nine estimated pose/sparse
geometry. No independent measured geometry, gravity, metric distance, collision
surface or unrestricted-walking claim.

Publish actual fresh input comparisons immediately with training RUNNING and
render/evaluation NOT RUN. Dispatch the native export as soon as it exists,
without waiting for full matched renders or all tests. Publish later measured
outcomes separately. A deployment sub-agent owns the static observation updates
while the main process trains, investigates and verifies.

## Geometry-preserving training: bounded investigation

The current released Brush path uses RGB/SSIM plus opacity/scale regularization;
the calibrated depth only initializes the scene. Inspect actual upstream
depth-supervision support and native interfaces before claiming an integration.
Keep this feasibility investigation distinct from the one declared standard
training. Do not silently substitute an unreleased engine, guessed metric depth,
or unverified renderer/backward implementation into the quality comparison.

## Reproduce in a fresh output directory

Prerequisites are the preserved source acquisition/rig/seed in
[STREET_CONCLUSION.md](STREET_CONCLUSION.md). The inputs command supports an
explicit resolution; its default remains512 for all historical workflows.

```sh
mkdir -p data/jobs/NEW
data/tools/venv/bin/python scripts/prepare-final-quality.py data/jobs/NEW
data/tools/venv/bin/python scripts/reconstruct.py data/jobs/NEW/datasets/hires \
  data/jobs/NEW/training-hires --steps 8000 --resolution 1024 \
  --max-splats 800000 --title 'Street final quality1024' --id street-final-hires
```

The source CLI's `--help` is retained with the actual job. For the common512
comparison, reuse the preserved baseline and render both actual exports:

```sh
node scripts/prepare-street-evaluation.mjs data/jobs/NEW baseline hires
node scripts/render-street.mjs data/jobs/NEW/render-config.json data/jobs/NEW/renders
data/tools/venv/bin/python scripts/measure-street.py data/jobs/NEW \
  data/jobs/NEW/renders data/jobs/NEW/evaluation --baseline-model baseline
```

For the separate1024 detail check, copy `render-config.json` to
`render-config-detail.json`, set top-level `resolution` to1024, multiply each
camera's `w`, `h`, `fl_x`, `fl_y`, `cx`, `cy` by2, and replace each non-null
reference with the same filename under `inputs-hires/images/`. Keep all camera
matrices and model paths unchanged. Render to a fresh `renders-detail/`, then
measure into `evaluation-detail/` with
`--config data/jobs/NEW/render-config-detail.json --baseline-model baseline`.
The renderer rejects inconsistent dimensions; the metric script uses the actual
intrinsics to select identical angular bands at either resolution. Encoding the
49 route frames at6fps is for inspection, not a measured rendering frame rate.

Actual outcomes, measurements, release verification and the stopping decision
are appended after execution, never assumed here.


### Actual upstream feasibility finding

[Depth-supervision PR497](https://github.com/ArthurBrussee/brush/pull/497) is open,
not merged, at pinned head `e658b9ccaeacf3aa303e1d0c334673eab51c2fb0`.
Its repository is Apache-2.0; no weights are involved. Current source adds
inverse-camera-depth L1 supervision and a fifth render channel with corresponding
native backward changes. The pinned source detaches the alpha normalization and
removes the depth contribution to opacity gradients. Those are **source
observations**, not gradient tests executed here.

The loader requires matching single-channelfloat32 TIFF,0 for invalid depth.
Our calibrated NaN holes would require explicit0 conversion. Nerfstudio's loader
still assigns `depth: None`; placing depth files beside the current
`transforms.json` would silently provide no supervision. A COLMAP export adapter
or actual loader change is necessary. Optional `--estimate-metric-scale` defaults
false. Existing fitted camera-Z remains in arbitrary SfM units and must not be
passed off as measured metres; radial range would need conversion first.

No fork releases/Actions artifacts were listed at inspection, and no Cargo
executable is installed in this environment. That is **not** evidence that the
branch cannot run on Metal. A source build, changed-dependency audit, input
adapter and actual native gradient/inference checks remain NOT RUN. The PR spans
37 files and contains unreleased backend changes, so it is not a clean
one-option ablation against our released0.3.0 baseline.

Decision: retain the executed official0.3.0 path for the one declared quality
run. Do not silently switch engines or extend this final campaign with a new
same-data regularization search. The useful implementation path is identified
for **new capture evidence**, with actual native validation still required.
Pinned API/source snapshots and byte hashes are retained locally in
`research/geometry-feasibility.json`. No structural-loss training or geometry
improvement is claimed.

## Actual outcome: comparative appearance improves; same-data tuning is closed

One declared training completed without changing the configuration or retrying.
Actual Brush0.3.0 log selects **Apple M2 / Metal**. The native job passes after
1455.650513s (24min15.651s), producing800,000 Gaussians /73,600,652 bytes,
SHA-256 `a5b51f48c24d075fc5d40df797fab3b17d936c92599172281b4cd9e0ebf04352`.
The preserved incumbent is400,000 Gaussians /36,800,652 bytes,
SHA-256 `b7544cc317f13f262dd7348199be077d85802cdd75ac175ee461ab8a8907816a`.
No new depth inference, camera estimation, diffusion or intermediate training
photograph ran in this campaign.

| Actual measurement | Existing512px /400k | New1024px /800k |
|---|---:|---:|
| Training and export, seconds |409.759063 (reused run)|1455.650513|
| Maximum resident set, bytes |317,669,376|666,107,904|
| Peak process memory footprint, bytes |1,299,235,776|2,386,281,696|
|512 output: mean held-level RGB MAE ↓ |27.750556|24.414430|
|512 output: mean held-level PSNR, dB ↑ |16.333515|17.482927|
|512 output: alpha≥.95 fraction |.224632|.271452|
|1024 output: mean held-level RGB MAE ↓ |27.991820|24.344902|
|1024 output: mean held-level PSNR, dB ↑ |16.204998|17.458603|
|1024 output: alpha≥.95 fraction |.236922|.296076|

All six held level directions improve in color error at both output resolutions.
At the common512 output this is a12.02% mean reduction; at1024 it is13.03%.
These are related views from one scene and one run, not independent trials or a
statistical-significance claim. Resolution and Gaussian capacity changed together;
this experiment does not isolate either effect. Process memory values come from
`time -l`; they are not total system usage, all unified-memory allocations or a
controlled hardware benchmark. Source input preparation took21.069s. Work ran
alongside static publication; historical/current timings are not controlled
speed comparisons.

Actual headed Chrome156 / Spark / Apple M2 Metal renders complete at75 matched
cameras per model at each resolution: **300 matched frames**, plus one early
actual preview.512 render batch34.693s;1024 batch83.184s. Those batch wall times
include browser/capture overhead and are not interactive FPS. The metric/video
stages took7.040s and20.831s. Each route video encodes49 actual interpolated-view
renders at6fps;6fps is the movie rate, not measured render performance.

Directly inspected sheets include six held directions, seven matched route
samples, two deliberate off-path samples and three full-resolution angular
detail patches. Windows, columns, railings, pavement and distant buildings look
sharper. Branches, scooters/near objects and some wall contours still smear or
double. Even the better1024 result is visibly below its real photo references.
The public report retains these failures alongside the improvement.

[Actual six-direction comparison](evidence/final-quality-held-512.jpg) ·
[Actual1024 detail patches](evidence/final-quality-detail-1024.jpg).
Rows are real reference / existing512-trained GS / new1024-trained GS. Images
derive from Cicero101's Mapillary photographs redistributed by Wikimedia
Commons under CC BY-SA4.0; per-source links, license and transformation credits
are retained in the [public attribution](https://groundshift-viewer-production.up.railway.app/experiments/final-quality/ATTRIBUTION.txt).

**Decision:** select `street-final-hires` as the best observed result on these
nine panoramas. Comparative appearance improvement PASS; independent measured
geometry and unrestricted walking NOT ACCEPTED. The user-directed **same-data
quality campaign is CLOSED**. Preserve this and all previous exports, and move
to new capture evidence or product use. Do not start another model, crop, seed,
filter, step, resolution or capacity sweep on these same sources automatically.

After native execution all103 pinned baseline input hashes still match. The
preserved original sources, poses, calibrated seed and incumbent native export
retain their checksums. Raw native/render logs and diagnostic images remain in
the local job; selected licensed comparison sheets and the derived world are
published, not original datasets, weights or raw logs.

## Validation and observation evidence

- **PASS:** TypeScript, lint, production build,166 JS tests and233 distinct
  Python cases across the two existing environments. The union includes the
  six new resolution/pose/withholding preparation contracts and three actual
  archive-overlay tests. Environment-specific skips are not counted as passes;
  the alternate environment executes those cases.
- **PASS:**75 distinct local headed Chrome cases have passing evidence,
  including all34 actual scene deep links/reloads and the new report, real
  images/metrics/video/mobile layout, failure fixtures and route movement.
  The full run was74PASS/1FAIL in228.220s. An old street-video test read the same
  canvas frame immediately after two `seeked` events. FFmpeg decoded different
  actual source frames; a paused-frame-callback retry also failed because no
  matching presentation callback arrived. Require actual playback and capture
  inside `requestVideoFrameCallback`, with media time within.2s of the requested
  position, then compare raw pixel SHA-256. That targeted test passes in10.396s,
  with actual times.833333/4.833333 and different hashes. No app or asset change;
  both failed traces remain local rather than being erased or reported PASS.
- **PASS:** seven targeted actual public headed Chrome cases, covering the
  new scene's substantial rendered pixels and camera-path change; source and
  comparison image decode; metric values; video decode/seek; mobile layout;
  gallery's34 decoded previews/no automatic WebGL; chronology; explicit error
  handling and shared old reports. New actual scene has279,644 counted colored
  pixels under the test definition and no captured page errors. This is a
  rendering/interaction check, not a quality or FPS benchmark.
- **PASS:** all1,046 composed public files match the phase3 size/SHA inventory,
 449.290s, no mismatches. The later verification-status publication changes
  only `experiments/final-quality/summary.json` and
  `experiments/lab/timeline.json`; its fresh readback is recorded in deployment
  evidence. Four missing/private-path probes return404.
- **PASS:** ordinary ordered extraction of the four checksum-pinned display
  layers into an empty directory reproduces all1,046 file hashes in4.593s.
  Full fresh-source/dependency/build reproduction of this current package is
  **NOT RUN**; historical restoration evidence is not silently reused as that
  claim.
- **NOT RUN:** complete75-case public suite, repeated native benchmarks,
  independent measured geometry, new depth-supervised training/gradient tests,
  other hardware, collision or unrestricted walking acceptance.

Actual public [viewer screenshot](evidence/final-quality-public.jpg) and
[measured report screenshot](evidence/final-quality-report-public.jpg) were
directly inspected; the report screenshot records the final
verified-publication phase and its actual validation scope. Machine-readable sanitized evidence is in
[final-quality.json](evidence/final-quality.json). Complete release chain,
incremental timing and restoration commands are in [DEPLOYMENT.md](DEPLOYMENT.md).
