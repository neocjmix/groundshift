# Railway viewer deployment

**Live:** [Observed road anchors](https://groundshift-viewer-production.up.railway.app/experiments/stereo-anchors/) · [Perspective coverage and overlap](https://groundshift-viewer-production.up.railway.app/experiments/perspective-overlap/) · [Calibration and perspective-depth control](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-calibration/) · [Adjacent panorama comparison](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-pair/) · [One-panorama depth comparison](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-depth/) · [Without monocular depth](https://groundshift-viewer-production.up.railway.app/experiments/object-nodepth/) · [Real-only scooter comparison](https://groundshift-viewer-production.up.railway.app/experiments/object-real/) · [Chronological lab](https://groundshift-viewer-production.up.railway.app/experiments/lab/) · [Scooter experiment](https://groundshift-viewer-production.up.railway.app/experiments/object-focus/) · [Observation room](https://groundshift-viewer-production.up.railway.app/) · [Depth-guided scene report](https://groundshift-viewer-production.up.railway.app/experiments/depth-warp/) · [Photo depth maps](https://groundshift-viewer-production.up.railway.app/experiments/depth-v2/) · [65-frame panorama report](https://groundshift-viewer-production.up.railway.app/experiments/video-4to6/) · [My desk](https://groundshift-viewer-production.up.railway.app/?world=/worlds/desk/world.json) · [Estimated-camera dozer](https://groundshift-viewer-production.up.railway.app/?world=/worlds/independent/world.json) · [Supplied-camera dozer](https://groundshift-viewer-production.up.railway.app/?world=/worlds/reconstructed/world.json) · [Houseplant](https://groundshift-viewer-production.up.railway.app/?world=/worlds/sample/world.json)

The user explicitly designates Railway as an **observation surface**, not a production quality gate. Viewer changes, every distinct exported trial, and sanitized experiment evidence ship in the same workflow regardless of quality. Reconstruction, camera estimation and training remain local. Private original inputs, raw job logs and model weights stay on the Mac; explicitly licensed public comparison crops are included with attribution. The hosted viewer can open a private world folder directly in the browser, without uploading it.

## Third observed panorama road diagnostics — 2026-11-06 KST

[New public report](https://groundshift-viewer-production.up.railway.app/experiments/road-third-view/)
adds actual third-RGB overlays,24 deterministic real-image examples, interactive
291-old/44-new sparse triangulations and frozen-calibration comparisons.35 lab
entries:22 prior Gaussian scenes and13 reports. All earlier outputs remain.
[Native experiment and limitations](ROAD_THIRD_VIEW.md). Execution/publication
are separate from full-street geometry, which remains **NOT ACCEPTED**.

| Item | Verified value |
|---|---|
| Implementation | `4d125f280f79dd9f1a62fdb452d9b46b8bae5757` |
| Release | [viewer-road-third-view-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-road-third-view-2026-11-06) |
| Archive | `groundshift-road-third-view-20261106.tar.gz`,337,976,806 bytes |
| SHA-256 | `d512f227c301bfc1da6a52fcc2248c2587d5ca30e0e8677b4679fa5c91f1e11a` |
| Static archive | 561 `www/` files,416,556,684 bytes |
| Staged inventory | 564 files,416,557,371 bytes including three support files |
| Pointer commit | `3d8654d91782e92a7d0beaaf8c5922c772aef217` |
| Railway deployment | `1e6d8e96-9e61-4ce8-8c25-dd3987a320d9`, SUCCESS at04:29:28 UTC |
| Trigger | Explicit connector request for existing branch-backed service, no commit pin |

**PASS:** every archive member matches the curated inventory; public GitHub
re-download matches size/hash(85.075s); Railway checksum log reports
`/tmp/viewer.tar.gz: OK` at04:28:52 UTC. Health returns200/`ok`.514 prior packaged
world/experiment data hashes are unchanged; compiled HTML/bundle references and
appended lab timeline are separately updated. All103 pinned scooter/input hashes
and21 pre-execution protocol hashes remain unchanged.

**PASS:** TypeScript/lint/build, JS166 tests, Python199 distinct passes across two
environments. Three HDR checks **NOT RUN**. Nine local headed Chrome156 checks
pass(30.8s), with manual sparse-cloud/overlay/screenshot inspection. All250
selected public file sizes/hashes match(43.728s), including all12 new report
assets/entry, earlier panorama reports, compiled bundles, lab/catalog and preserved
scooter assets. Full561-file public recrawl **NOT RUN**. All nine public headed
Chrome156 checks pass(CLI rounded1.4m); real cloud/source/color/orbit/reset,
measured subsets, diagnostic images, downloads and lab ordering are exercised.
Simulated failure/race checks are labeled separately in the suite. Manual review
of public sparse-cloud/overlay/report screenshots confirms actual rendering;
this is not an accuracy acceptance gate.
[Sanitized release evidence](evidence/road-third-view-release.json) and
[public rendered cloud screenshot](evidence/road-third-view-browser.png).

Rollback remains the prior immutable `viewer-stereo-anchors-2026-11-06` release,
archiveSHA `30844c802fff4546dd14a9672e4e62b7e3534d8390ca335e14b810a65db7c0b0`,
previous deployment `b02ac482-b711-41db-90a0-f6d5451019dc`.
Automatic push deployment remains unverified; the explicit trigger above was used.
No raw source photographs, private footage, weights or raw job logs were uploaded.

## Observed road anchors and calibration — 2026-11-06 KST

[New public report](https://groundshift-viewer-production.up.railway.app/experiments/stereo-anchors/)
exposes five cloud controls and20 evidence images. It retains SIFT-only failures,
the inadequate256px stereo search and the512px correction that recovers291 road
candidates. The lab has34 entries (22 prior GS scenes,12 reports). All previous
reports/worlds remain. [Native results and limits](STEREO_ANCHORS.md).
Execution/publication **PASS**; full P2 geometry **NOT ACCEPTED**.

| Item | Verified value |
|---|---|
| Implementation | `1cd6913b91aaf749a0064448199631a70500bbf1` |
| Release | [viewer-stereo-anchors-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-stereo-anchors-2026-11-06) |
| Archive | `groundshift-stereo-anchors-20261106.tar.gz`,336,387,809 bytes |
| SHA-256 | `30844c802fff4546dd14a9672e4e62b7e3534d8390ca335e14b810a65db7c0b0` |
| Static archive | 547 `www/` files,414,570,400 bytes |
| Staged inventory | 550 files,414,571,087 bytes including three support files |
| Pointer commit | `1ca35a0c48442aece9fb5ab95a712790bd7a428e` |
| Railway deployment | `b02ac482-b711-41db-90a0-f6d5451019dc`, SUCCESS at03:12:58 UTC |
| Trigger | Explicit connector request for existing branch-backed service, no commit pin |

**PASS:** full archive readback matches every curated inventory member; public
GitHub re-download matches bytes/hash (81.225s); Railway build log reports
`/tmp/viewer.tar.gz: OK` at03:12:15 UTC. Health is200/`ok`. All236 selected public
file hashes/sizes match, including all75 new report assets/entry, earlier panorama
reports, lab, common bundles, catalog and preserved scooter assets. All332 checked
prior static experiment source files retain their hashes, excluding the appended
lab timeline. Full547-file public recrawl **NOT RUN**.

Seven targeted **headed Chrome156** public checks PASS; CLI reports **1.3min**
(rounded). This covers all five actual clouds, rendered pixels, source/camera
controls, diagnostic images, match gallery, prior panorama reports, chronological
lab and simulated-failure recovery. No public retries were required. Public
screenshots were inspected: recognizable lower scene, but crop wedges/strips and
offset layers remain. Pixel/rendering PASS is not geometry PASS. Local checks
PASS in28.2s. Full historical browser regression **NOT RUN**.

TypeScript, lint, production build,166 JS tests and190 distinct Python tests PASS;
three unrelated HDR tests **NOT RUN**. Nine new tests include a real CPU SGBM
execution on a synthetic known320px shift, separate from real-panorama evidence.
All103 baseline hashes are unchanged. New depth-model inference, pose refinement,
fusion and GS training **NOT RUN**; prior MPS predictions are reused.

Local evidence: `data/jobs/stereo-validation-20261106/` contains archive/release
readbacks, GitHub digest, Railway status/log,236 public hashes, health, no-overwrite
checks and local/public browser evidence. Matching, disparity, calibration and
raw diagnostic jobs are listed in [the experiment](STEREO_ANCHORS.md).
[Compact evidence](evidence/stereo-anchors.json). Raw1024px crops, disparity/raw
depth arrays, logs, private inputs/URLs and model weights are excluded from the
archive. The previous perspective-overlap release below remains the rollback
package. Push-only autodeploy remains unverified.

## Dense perspective coverage and overlap — 2026-11-06 KST

[New public report](https://groundshift-viewer-production.up.railway.app/experiments/perspective-overlap/)
compares four actual spherical cloud controls: level crops, level plus downward
crops, same-center disagreement filtering and the existing ERP control. All22
earlier GS scenes and prior reports remain; the lab has33 chronological entries
(22 scenes,11 reports). [Measurements and limitations](PERSPECTIVE_OVERLAP.md).
Execution/publication **PASS**, P2 geometry **NOT ACCEPTED**; fusion/GS **NOT RUN**.

| Item | Verified value |
| --- | --- |
| Implementation | `e146c8bdcc3a36b618e2171f8edc2bd15d5361fd` |
| Release | [viewer-perspective-overlap-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-perspective-overlap-2026-11-06) |
| Archive | `groundshift-perspective-overlap-20261106.tar.gz`,318,838,080 bytes |
| SHA-256 | `29c22636d18d3c197c58289c3402d8674214a3861ddf49b32d1ab7f047f6a83c` |
| Static archive | 472 `www/` files,378,434,557 bytes |
| Staged inventory | 475 files,378,435,244 bytes including three support files |
| Deployment-pointer commit | `e0febee172c5c38eda5d9d7a8211932089b3c4e2` |
| Railway deployment | `8fa29bf9-31a0-4bc7-a201-3f83f0da086c`, SUCCESS at02:29:56 UTC |
| Trigger | Explicit connector request for the existing branch-backed service; no commit pin |

**PASS:** every archive member matches the curated inventory; public GitHub
re-download matches length/hash; Railway build log reports
`/tmp/viewer.tar.gz: OK` at02:29:23 UTC. Health returns200/`ok`. All161 selected
public file sizes/hashes match (including all48 new report assets/entry, prior
panorama pages, lab, shared bundles, catalog and preserved scooter assets).
All285 prior static experiment source files checked are unchanged, excluding
the intentionally appended lab timeline. Full472-file public recrawl **NOT RUN**.

Six targeted **headed Chrome156** public checks PASS in59.1s. All four clouds
render actual colored pixels; source/camera changes and diagnostic images work;
the prior pair/one-panorama and calibration reports, chronological ordering and
simulated-error recovery remain operational. Public screenshots were inspected:
crop wedges and stretched points remain despite recognizable pavement and
objects. No public test retry was required. Full historical browser suite
**NOT RUN**. Local targeted checks also PASS (20.5s); the initial local path/test
failures and corrections are retained separately.

TypeScript, lint, production build,166 JS tests and181 distinct Python tests
across the two existing environments PASS; three unrelated HDR checks are
**NOT RUN**. All103 frozen baseline hashes remain unchanged. Actual native
inference and CPU measurements are in the experiment document.

Local evidence: `data/jobs/perspective-overlap-input-20261106/`, including archive
readback, GitHub asset/digest, download, Railway status/log, health,161 public
hashes, initial/final local and final public browser evidence. Numerical arrays,
calibration/projected holdout rows and PLYs remain in
`data/jobs/perspective-overlap{,-audited,-verified}-20261106/`; new model inference
is in `data/jobs/perspective-overlap-inference-20261106/`.
[Compact evidence](evidence/perspective-overlap.json). Original images, weights,
raw arrays and logs are excluded from the archive. The previous calibration
release below remains the rollback target. Push-only autodeploy is unverified.

## Common calibration and perspective depth — 2026-11-06 KST

The [new report](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-calibration/)
shows the original/common784 calibration comparison, actual photo feature-error
mosaics and an additional DAV2 perspective-depth control on 12 actual local MPS
inputs. High-parallax held-out median pixel errors improve from about 7px to
2.2–2.6px in that control. New displayed clouds belong to the common-fit ERP
experiment; perspective dense fusion and new GS remain **NOT RUN**.
All 22 previous GS scenes remain. The chronological lab has 32 entries: 22 scenes,
ten reports. [Measurements and limits](PANORAMIC_CALIBRATION.md).

| Item | Verified value |
| --- | --- |
| Experiment/report source | `3fee797` |
| Release | [viewer-panoramic-calibration-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-panoramic-calibration-2026-11-06) |
| Archive | `groundshift-panoramic-calibration-20261106.tar.gz`, 309,450,561 bytes |
| SHA-256 | `1e486d418be4c0391e033a2f6fd2fb43e580d34baa1f588817094d5b00dee15f` |
| Static archive contents | 424 `www/` files, 355,408,740 bytes |
| Staged inventory | 427 files, 355,409,427 bytes including three deployment-support files |
| Deployment-pointer commit | `461eb00` |
| Railway deployment | `7563f716-a903-4609-b2ef-d4325dcb60d5` — SUCCESS at 2026-11-06 00:13:47 UTC |
| Trigger | Explicit connector request for existing branch-backed service, no commit pin |

**PASS:** full local archive readback matches its curated inventory; GitHub
re-download matches byte length and SHA-256; Railway build log independently
reports `/tmp/viewer.tar.gz: OK` at 00:12:59 UTC. `/healthz` is 200/`ok`. All 113
selected new/shared public files match staged sizes/hashes, covering new and
prior panorama reports, lab, bundles, catalog and preserved scooter assets.
A full 424-file public recrawl is **NOT RUN**.

Five targeted headed Chrome 156 tests pass at the public origin in 50.5s: actual
original/common cloud pixels and controls, perspective images and numeric
tables, parallax/longitude strata, simulated 503 recovery, lab sorting and
preserved pair/one-panorama rendering. Actual public screenshots were inspected;
source-colored layers remain offset and perspective output is not a fused cloud.
Existing bounded 60-second remote asset waits were sufficient; no public retry
was needed in this release. The full historical browser suite is **NOT RUN**.

TypeScript, lint, build and 166 JS tests pass. Python discovers 175 tests in each
existing environment, skips 5/31, and executes 172 distinct tests across their
union. Three unrelated HDR/FFmpeg tests are **NOT RUN**. Thirteen new camera,
calibration and depth-conversion tests are included. All 103 frozen baseline
hashes are unchanged, and expected no-overwrite rejections preserve existing
reports. Native inference and runtime measurements are in the experiment doc.

Local evidence: `data/jobs/panoramic-calibration-input-20261106/` (release,
Railway status/checksum, 113-file hashes, health, logs and browser evidence),
`data/jobs/panoramic-calibration-20261106/`,
`data/jobs/panoramic-perspective-depth-20261106/`, and
`data/jobs/panoramic-perspective-control-audited-20261106/`.
[Compact record](evidence/panoramic-calibration.json). Original-resolution
inputs, raw arrays, weights, private URLs and local logs are excluded from the
archive. Documentation-only changes retain this release and its rollback
predecessor below. Push-triggered autodeploy remains unverified.

## Adjacent panorama depth — 2026-11-06 KST

The [two-panorama report](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-pair/)
compares actual locally inferred DA²/DAV2 clouds in the preserved fixed-rig frame.
It offers source colors, individual clouds, capture cameras, directional range/RGB
comparisons and regional limitations. All 22 previous GS scenes remain; the lab
has 31 entries (22 scenes, nine reports), newest first. [Experiment](PANORAMIC_PAIR_P1.md).
No fusion or Gaussian training occurs, and geometry is not accepted for fusion.

| Item | Verified value |
| --- | --- |
| Experiment/report source | `73e63e6` |
| Release | [viewer-panoramic-pair-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-panoramic-pair-2026-11-06) |
| Archive | `groundshift-panoramic-pair-20261106.tar.gz`, 287,123,649 bytes |
| SHA-256 | `d0000f6be2998163665c31900cbb9ae144dc160fd5d29406d09581aff008e2ac` |
| Static archive contents | 410 `www/` files, 326,969,233 bytes |
| Local inventory | 413 files, 326,969,920 bytes including three deployment-support files |
| Deployment-pointer commit | `5192031` |
| Railway deployment | `ff2b8ff3-64aa-43af-acf6-b4eeaeebad12` — SUCCESS at 2026-11-05 20:39:08 UTC |
| Trigger | Explicit connector request for the existing branch-backed service; no commit pin |

**PASS:** every local archive file matches its curated inventory; re-downloaded
GitHub release bytes/hash match; Railway build logs show `/tmp/viewer.tar.gz: OK`
at 20:38:35 UTC. `/healthz` returns 200/`ok`. All 99 selected new/shared public
files match their staged sizes/hashes, including both panorama reports, lab,
shared bundles, catalog and preserved scooter assets. A full 410-file public
recrawl and full historical browser regression are **NOT RUN**.

The first public targeted Chrome attempt failed three 5-second assertions while
cloud downloads were still pending. Its logs/traces are retained. After using an
explicit bounded 60-second remote asset wait, all three targeted tests passed:
real point-cloud pixels and controls, image decoding, delayed-response protection,
simulated HTTP503 recovery, lab ordering, and the preserved one-panorama render.
The pixel checks exclude the overlaid status-text band, and actual public
screenshots were separately inspected. Cloud offsets, stretching and partial
coverage remain; rendering PASS is not geometry PASS. No web artifact was
changed to address the test timeout.

TypeScript, lint, production build and 166 JS tests pass. Both Python environments
run 162 tests (5 / 31 skips); their union executes 159 distinct tests, including
22 new pair/sparse geometry tests. Three unrelated HDR/FFmpeg tests are **NOT RUN**.
All 103 frozen baseline file hashes remain unchanged. Large raw arrays, original
panoramas, weights and logs stay local.

Evidence: `data/jobs/panoramic-pair-20261106/` (inference/calibration/pair logs,
archive/release readback, 99-file public hashes, initial failed traces and final
public screenshots) and `data/jobs/panoramic-pair-ui-20261106/` (earlier manual
local browser inspection). [Compact record](evidence/panoramic-pair-p1.json).
Documentation/test-only updates retain this immutable archive and its rollback
predecessor below. Push-triggered autodeploy remains unverified.

## One-panorama full-sphere depth — 2026-11-06 KST

The [new P0/P1 report](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-depth/)
shows one real panorama, DA² and DAV2-Small raw-depth visualizations, explicit
SfM radial calibration, conservative masks and interactive colored point clouds.
Both models actually execute on M2 MPS; no Gaussian training occurs. The existing
22 GS scenes remain unchanged. The chronological lab now has 30 entries:
22 scenes and eight reports. [Experiment](PANORAMIC_DEPTH_P1.md) ·
[model/license findings](PANORAMIC_DEPTH_MODELS.md) · [baseline preservation](PANORAMIC_BASELINE.md).

| Item | Verified value |
| --- | --- |
| Experiment/report source | `5336744` |
| Release | [viewer-panoramic-depth-2026-11-06](https://github.com/neocjmix/groundshift/releases/tag/viewer-panoramic-depth-2026-11-06) |
| Archive | `groundshift-panoramic-depth-20261106.tar.gz`, 277,842,996 bytes |
| SHA-256 | `312eade1493ba7e289e37cad7c7d68b59c19f7a0eaf0b87e6d154054e1c53d66` |
| Static archive contents | 379 `www/` files, 311,508,601 bytes |
| Local package inventory | 382 files, 311,509,288 bytes including three deployment-support files |
| Deployment-pointer commit | `04964ab` |
| Railway deployment | `b7a76e45-d253-4dd9-b6d6-3acc36bb6a42` — SUCCESS at 2026-11-05 19:59:29 UTC |
| Trigger | Explicit connector request for the existing branch-backed service |

**PASS:** pinned archive checksum verified in Railway build logs; health endpoint
returns `ok`; all 68 selected new/shared public files match staged bytes and
SHA-256 hashes. Headed Chrome156 actually renders both models' point clouds,
switches filtered/full data, capture/overview views and point size, decodes source,
depth, range and mask images, verifies lab sorting/newest entry and opens the
preserved scooter report. Public cloud/report screenshots were inspected with
no page errors. Downloadable PLYs are ordinary colored points, not GS exports.

TypeScript, lint, build and 166 JS tests pass. Python suites each ran 140 tests,
with five OpenCV-environment skips and 31 PyCOLMAP-environment skips; 137 distinct tests
execute across their union. Three unrelated HDR/FFmpeg tests remain NOT RUN in
both environments. The 34 new spherical/calibration tests are included in that
total. The full historical browser regression suite and a 379-file public recrawl
are NOT RUN. Inference/browser PASS does not establish geometry acceptance.
Independent geometric accuracy and cross-panorama consistency are NOT RUN.

Existing baseline 103 file hashes were checked again after execution and remained
unchanged. Evidence lives under `data/jobs/panoramic-baseline-20261106/`,
`data/jobs/panoramic-depth-{da2,dav2}-20261106/` and
`data/jobs/panoramic-depth-input-20261106/`. A compact measurement record is
tracked at [evidence/panoramic-depth-p1.json](evidence/panoramic-depth-p1.json).
Raw logs, original-resolution panoramas, model weights and absolute local paths
are not in this archive. Documentation-only commits retain this release.

## Scooter without learned depth — 2026-11-05

The [new comparison](https://groundshift-viewer-production.up.railway.app/experiments/object-nodepth/)
keeps the exact nine real training image files and camera matrices, removes
learned-depth inference/calibration/fusion, and initializes from 115 triangulated
SfM object points. M2 Metal training takes 116.339 seconds for 5,000 steps and
exports 569 full / 237 object Gaussians. The observed result is strongly blurred
and stretched, with no recognizable-complete-object acceptance. Both outputs
are published unchanged. [Method and limitations](OBJECT_NO_DEPTH.md).

The catalog now has 22 scenes and the chronological laboratory has 29 entries
(22 scenes, seven reports). Previous results remain accessible.

| Item | Verified value |
| --- | --- |
| Viewer/report source | `bad9de4` |
| Release | [viewer-object-nodepth-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-object-nodepth-2026-11-05) |
| Archive | `groundshift-object-nodepth-20261105.tar.gz`, 271,912,916 bytes |
| SHA-256 | `38fdfbe601a9941e8310e29c321dacd9c4082caf3fb79128a88a5a3505d58d26` |
| Static archive contents | 359 `www/` files, 295,673,111 bytes |
| Local package inventory | 362 files, 295,673,798 bytes including three deployment-support files outside `www/` |
| Deployment-pointer commit | `95d6ce9` |
| Railway deployment | `659f40c5-1317-4979-ac79-68cf091d89cd` — SUCCESS at 12:39:36 UTC |
| Trigger | Explicit existing-service connector request for the latest branch |

**PASS:** actual local M2 Metal training, exact training image/camera equality,
TypeScript, production build, lint and 165 JS tests. Python suites each ran 106
tests, with five dependency skips in OpenCV and 31 in PyCOLMAP. Local Chrome
rendered both worlds; the report's initial comparison-image wait timed out, but
an unchanged rerun passed. These tests do not replace native execution evidence.

Railway verified the archive checksum (`/tmp/viewer.tar.gz: OK`).
**Public PASS:** all 64 selected new/shared public files match staged byte lengths
and SHA-256 values, and `/healthz` returns `ok`. Headed Chrome 156 renders both
new worlds (60 fps displayed at the sampled home views), decodes both comparison
previews, operates the original-image selector and point-cloud selector, checks
newest/oldest lab ordering and opens the previous report's new comparison link.
The public summary has nine observed images, zero generated images and zero
depth maps, with both input-equality flags true. Actual public screenshots were
inspected; no page errors occurred. FPS is a sampled UI counter, not a controlled
benchmark. The prior report and current report use the same display camera
parameters; no quantitative quality claim is made from the screenshots.

**FAIL:** this result does not achieve a recognizable complete scooter; substantial
blurring/stretched splats remain. **NOT RUN:** independent geometry accuracy,
quantitative quality comparison, full historical browser regression and an
all-359-file public recrawl. Intentionally omitted stages are not test failures.

Evidence: `data/jobs/object-no-depth-20261105/` retains input SHA records,
`training/job.json`, native logs, browser screenshots, `browser-public.json`,
`public-files.json`, `release.json`, Python logs and `railway-deployment.json`.
Documentation-only updates do not replace the deployed archive.

## Real-only scooter comparison — 2026-11-05

The [new comparison](https://groundshift-viewer-production.up.railway.app/experiments/object-real/)
removes all intermediate image generation: **nine real images, zero RIFE frames,
zero diffusion frames**. The same original-image camera solution and relative-depth
predictions are reused; nine-map fusion and 5,000-step M2 Metal training run again.
The native training takes 160.298 s and exports 46,807 Gaussians, with 43,268 in
the object selection. Both new worlds are in the 20-scene catalog, and the lab
lists 26 entries (20 scenes, six reports). [Method, control limits and evidence](OBJECT_REAL_ONLY.md).

| Item | Verified value |
| --- | --- |
| Viewer/report source | `301c4be` |
| Release | [viewer-object-real-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-object-real-2026-11-05) |
| Archive | `groundshift-object-real-20261105.tar.gz`, 266,917,532 bytes |
| SHA-256 | `16fa51ef8275314ac46111387a4814c696056d160489b5a50769fec25dbda42d` |
| Static payload | 335 files, 289,569,944 bytes |
| Deployment-pointer commit | `305426d` |
| Railway deployment | `3d43f792-2338-43d2-94d0-863e992b1b86` — SUCCESS |
| Trigger | Explicit existing-service connector request for the latest branch |

**PASS:** local M2 Metal execution, TypeScript, production build, lint and all
165 JS tests. Python tests ran in both available environments: 106 with 31 skips
in PyCOLMAP, and 106 with five skips in OpenCV. Native training is separately
proven by its actual adapter log and export, not these tests.

**Public PASS:** Railway checked the pinned archive (`/tmp/viewer.tar.gz: OK`)
and reached SUCCESS at 11:30:27 UTC. All **62 selected new/shared public files**
matched the staged byte lengths and SHA-256 values; `/healthz` returned `ok`.
Headed Chrome 156 rendered both new worlds, decoded the comparison images,
operated the nine-frame selector and point-cloud comparison, and checked lab
newest/oldest ordering. It also opened the preceding 65-frame report and its new
comparison link. The nine-frame public summary has zero synthetic records.
Actual public render/report screenshots were inspected, with no page errors.

This was a focused check after publication, not an all-335-file recrawl or rerun
of the full historical browser suite. Geometry accuracy and matched-camera
quality improvement remain **NOT RUN**. The post-run byte-equality control found
COLMAP preprocessing differences confined to the one-pixel image border;
interior pixels, original camera solution and training options matched. This
limitation is recorded in [the experiment](OBJECT_REAL_ONLY.md), rather than
calling the run a perfect pixel-identical control.

Evidence: `data/jobs/object-focus-real-only-20261105/` contains `ablation.json`,
`control-check.json`, native reports/logs, `browser-public.json`, `public-files.json`,
`railway-deployment.json` and actual screenshots. The initially misunderstood
RIFE-only trial was cancelled during pose estimation, before training; it is not
part of the result. Documentation-only updates do not replace this archive.

## Object-focused scooter observation release — 2026-11-05

The [chronological lab](https://groundshift-viewer-production.up.railway.app/experiments/lab/)
lists all 18 worlds and five reports, with newest/oldest sorting. The
[object experiment](https://groundshift-viewer-production.up.railway.app/experiments/object-focus/)
shows all 65 candidate images, relative-depth previews, original-only and
augmented point clouds, and both new Gaussian exports. The local result is
recognizable but blurred and streaked. Publication is not a quality pass.

| Item | Value |
| --- | --- |
| Viewer implementation / publication metadata | `68ab2d3` / `a3551c8` |
| Release | [viewer-object-focus-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-object-focus-2026-11-05) |
| Archive | `groundshift-object-focus-20261105.tar.gz`, 253,063,372 bytes |
| Archive SHA-256 | `40508f73cd0a87714d556cc305e21d46444eaf5eea8f0ce8ddb261025e0866d5` |
| Static payload | 300 files, 272,548,845 bytes; 18 scene entries |
| Deployment-pointer commit | `5d32ce9` |
| Railway deployment | `d3cf2adb-b133-4923-a894-63184246132c` — SUCCESS |
| Trigger | Existing-service connector request for the latest branch |

The result-first local run completed 56 whole-image MPS diffusion candidates
in 757.964 s, registered 47/65 cameras (all nine real photographs), and accepted
34 depth maps for a 93,595-point object initialization. Brush trained 5,000
steps on Apple M2 Metal in 610.514 s and exported 93,941 Gaussians; object-center
selection retained 93,101. Eighteen images failed registration and 13 registered
synthetic depth maps failed calibration. These exclusions are visible rather
than described as full registration. See [method and reproduction](OBJECT_FOCUS_EXPERIMENT.md).

Local TypeScript/build, actual Chrome rendering of both new worlds, interactive
point clouds and lab ordering passed before publication. Railway verified the
archive checksum in its build log and reached SUCCESS at 08:42:40 UTC.

**Post-publication PASS:** both new GS worlds render in headed Chrome 156 at the
public origin; their actual screenshots and the experiment page were inspected.
The image/depth selector, point-cloud display and newest/oldest lab ordering
executed without page errors. All **163 new/shared public files** matched staged
lengths and SHA-256 values; `/healthz` returned `ok`, and every lab-card thumbnail
returned HTTP 200. The shared-file check is not an all-300-file recrawl.
Lint and **165 JS tests** passed. The PyCOLMAP environment ran **106 Python tests,
31 skipped**; the OpenCV environment ran **106, five skipped**. Dependency-specific
skips are not GPU validation. The new native stages separately executed on the
actual M2 as recorded above.

The old full browser regression suite and independent geometry/comparative
quality measurements are **NOT RUN** for this release. Focused public checks
were performed after the user could already open the result. Raw evidence is
retained under ignored `data/jobs/object-focus-20261105/`: `browser-public.json`,
`public-files.json`, `railway-deployment.json`, stage reports, test logs and actual
render screenshots. This documentation update does not change the deployed archive.

## Depth-guided generated-view observation release — 2026-11-05

The [depth-guided comparison page](https://groundshift-viewer-production.up.railway.app/experiments/depth-warp/)
places three licensed real 512px crops, corrected stereo, raw and
source-consistent depth warps, the MPS inpainted image and two matched
Chrome-rendered GS comparisons side by side. The new
[Gaussian scene](https://groundshift-viewer-production.up.railway.app/?world=/worlds/beijing-depth/world.json)
is the 16th catalog entry. Its 10,000-step M2 Metal execution **PASS**ed, but
3D visual quality improvement **FAIL**ed: direction-01 MAE 38.900→39.874 and
direction-03 MAE 23.903→26.028 against withheld real RGB. The scene remains
visible because this service is an observation surface. The image-generation
pose and sparse initialization used all-image SfM, so this is an appearance
holdout, not independent geometry evidence. See [the local method,
measurements and reproduction commands](DEPTH_WARP_EXPERIMENT.md).

| Item | Verified value |
| --- | --- |
| Viewer/report source | `e8c4203` (core warp code `7c85279`) |
| Release | [viewer-depth-warp-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-depth-warp-2026-11-05) |
| Archive | `groundshift-depth-warp-20261105.tar.gz`, 204,273,508 bytes |
| Archive SHA-256 | `bc1c75ccfdbcd7cc27f5b972ac15f9eab9d7286ca9699b98a5fa6c0d3e5a3aca` |
| Static payload | 142 `www/` files, 219,096,620 bytes; 16 scene entries |
| Deployment-pointer commit | `672db60` |
| Railway deployment | `c7b440f4-ae49-43c2-98bc-6e51937e3033` — SUCCESS |
| Actual trigger | Explicit latest-branch Railway connector request; push-only autodeploy was not relied on |

**Local PASS:** TypeScript, lint, 165 JS tests, production build,
28 headed Chrome tests including all 16 scene renders and the new report.
The PyCOLMAP environment ran 106 Python tests with 31 dependency-specific
skips; the OpenCV environment ran 106 with five skips. The depth-calibrated
source warp, inpainting on MPS and Brush training on Metal executed separately.
The augmented job took 979.402 s, exported 150,000 splats in a 13,800,652-byte
PLY and logged the Apple M2 Metal adapter. Its actual two-direction Chrome
renders were inspected: geometry remained blurred or doubled and both matched
photo errors increased. Package contents passed a private-path text scan,
and each of the 142 archived web files matched the staged length and SHA-256.
The fresh GitHub release download matched the local archive length and hash.

**Railway/public PASS:** The build log verified `/tmp/viewer.tar.gz: OK`;
the new container reached SUCCESS with no pending work. All 142 public files
matched the staged byte length and SHA-256; `/healthz` returned 200/`ok`.
Five missing/private-source paths returned 404, including the local job
report, raw depth and model-weight names. All 28 public headed Chrome tests
passed in 4.8 minutes, including decoded report images, actual splat rendering
and reload of every catalog scene, gallery controls, camera paths, video
playback and error recovery. The public report screenshot was inspected.
Raw evidence is retained locally under ignored `data/validation/deployment/`
as `depth-warp-archive.json`, `railway-depth-warp-http.json` and
`railway-depth-warp-browser.json`. Successful publication does not change
the **FAIL** visual-quality or **NOT RUN** independent-geometry verdicts.

## Three-photo depth observation release — 2026-11-05

The earlier [depth report](https://groundshift-viewer-production.up.railway.app/experiments/depth-v2/)
shows three licensed observed 512px crops beside local M2/MPS relative-depth
predictions. The 15 Gaussian worlds and previous experiment reports remain
available. Depth prediction and its internal sparse-point ordering check are
**PASS**; metric depth, cross-view consistency and depth-assisted GS improvement
are **NOT RUN**. See [the local experiment](DEPTH_EXPERIMENT.md).

| Item | Verified value |
| --- | --- |
| Viewer/report source | `19c1d539f21efb79a904b8e1d239823d536da5d1` |
| Release | [viewer-depth-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-depth-2026-11-05) |
| Archive | `groundshift-depth-20261105.tar.gz`, 184,298,462 bytes |
| Archive SHA-256 | `59107b247c429ec4153f534c357711fc2410e23b8dd7eae9564261a7e8d03941` |
| Static payload | 120 `www/` files, 198,141,306 bytes; 15 scene entries and eight depth-report files |
| Deployment-pointer commit | `a43958fc1944b56d95499393c15b7aba81217a80` |
| Railway deployment | `9aa61c0c-eb21-4eab-9937-3188b04411b1` — SUCCESS |
| Actual trigger | Explicit latest-branch connector trigger; no push-triggered deployment appeared before it |

**Local PASS:** TypeScript, lint, 165 JS tests, production build and all 26
headed Chrome cases including the new six-image depth report and every actual
Gaussian scene. The available Python environments each ran 102 native tests:
the OpenCV environment had five missing-dependency skips, the PyCOLMAP
environment had 44; the actual three-image depth inference and sparse-point
check completed separately. The local archive readback matched every selected
file's exact length and SHA-256; the fresh GitHub release download matched the
local archive byte for byte. Railway's build log reported
`/tmp/viewer.tar.gz: OK` at the pinned checksum, and the service reached
SUCCESS with no pending work.

**Public HTTP PASS:** all 120 public files matched exact length and SHA-256,
`/healthz` returned 200/`ok`, and nine private/missing paths returned 404,
including depth arrays and raw inference logs. The first public headed-Chrome
depth case timed out at its 5-second image readiness assertion while the full
file crawl was running. Direct requests then returned all six images with 200,
the complete hash crawl passed, and the same public page passed after a test-only
30-second image wait. The deployed page and archive were unchanged for that
retry. The screenshot was inspected; it shows all three real photos paired with
three relative-depth maps. Evidence is retained in ignored
`data/validation/deployment/railway-depth-http.json` and the public Playwright
test output. **All 26 public headed-Chrome cases passed** in 5.5 minutes,
including actual render and reload of all 15 scenes, gallery controls, both
older reports, MP4 play/seek, camera-path controls and error recovery. The 15
public scene screenshots were inspected together in
`data/validation/deployment/depth-public-scenes-contact.jpg`; the older
Beijing scenes still visibly streak or blur. Browser success does not change
their recorded quality failures or prove a depth-assisted GS world exists.

## Two-endpoint panorama observation release — 2026-11-05

The new catalog contains **15 distinct scenes**, including both matched
10,000-step Beijing Gaussian worlds. The new
[65-frame panorama report](https://groundshift-viewer-production.up.railway.app/experiments/video-4to6/)
contains the actual 2048×1024 H.264 video, 10 selected licensed or generated
comparison images, an exploratory MPS inpaint and clear LTX **NOT RUN** status.
The previous Mapillary report remains available and now lists 79 summarized
stages. The generated-view GS renders, but its visual quality **FAILS** to
improve the real-only baseline. Publication does not change that verdict.

| Item | Value |
| --- | --- |
| Viewer and experiment source | `8e4fc0c0a9b3420aa59b9fe8a823b974a4d1c037` |
| Release | [viewer-panorama-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-panorama-2026-11-05) |
| Archive | `groundshift-panorama-20261105.tar.gz`, 182,419,689 bytes |
| Archive SHA-256 | `1d7def29ae1cf39b7cdca927fa01e4c3aacc9c834c39d36831145118cd954ab3` |
| Static payload | 112 `www/` files, 196,253,479 bytes; 15 scene entries |
| Deployment-pointer commit | `d2e94c309cc1aa30662f17f658d8d79e1b794301` |
| Railway deployment | `0caccf5b-9e98-49dc-8160-4b3f6becd544` — SUCCESS; public browser verification below |
| Actual trigger | Explicit latest-branch connector trigger; push autodeploy did not appear before triggering |

**Local PASS:** TypeScript, lint, 165 JS tests, production build, 25 headed
Chrome tests (including all 15 actual scene renders and MP4 playback), and
native adapter tests in the available dependency-specific environments. Both
new Brush jobs ran 10,000 steps on the M2 Metal adapter and exported distinct
13,800,652-byte PLYs. The 65-frame RIFE/MLX video ran locally; LTX-2.3 video
diffusion was **NOT RUN** because model acquisition was impractical at the
observed transfer rate. The generated-view GS quality is **FAIL**: two matched
headed-Chrome target-direction renders had higher photo error and visible
streaking. See [the experiment record](PANORAMA_VIDEO_EXPERIMENT.md).

The 115-file local package inventory includes `Dockerfile`, `Caddyfile` and
`.dockerignore`; the release archive contains only its 112 `www/` files. Every
file in a local archive readback matched the curated inventory's exact size
and SHA-256. A fresh GitHub release download matched the local 182,419,689-byte
archive SHA-256. Railway's build log independently reported
`/tmp/viewer.tar.gz: OK`, followed by Caddy startup and deployment SUCCESS.
The large originals, model weights, source job reports and
private desktop footage are outside the archive. The report itself is rebuilt
from selected status fields and downscaled, attributed images. Remote archive
readback and public-origin checks are recorded below.

| Public observation check | Result | Evidence |
| --- | --- | --- |
| Railway build and health | PASS | Exact pointer commit deployed; archive checksum OK in build log; Caddy starts; `/healthz` returns 200/`ok` |
| Public file integrity | PASS | All 112 `www/` files match the release inventory's exact bytes and SHA-256 |
| Missing/private paths | PASS | Seven probes return genuine 404, including the raw video experiment training log and unshipped inference log |
| Public video playback and 15-scene rendering | PASS after one test-only retry | The first 25-case run had 24 PASS / 1 missing-manifest wording assertion FAIL. The public server correctly returned HTTP 404; the local Vite server instead returned HTML/200. After accepting both visible error states, that case passed on the public origin. All 25 distinct cases passed; a focused four-case rerun captured the new public video, both GS views and gallery |

The public-origin browser run covered 15 direct scene routes and reloads,
gallery filters/search, 390px mobile layout, the old Mapillary comparisons,
actual MP4 playback/seeking, and viewer controls/error recovery. The initial
test failure was an assertion about the missing-world message, not a broken
deployment. The application and release archive were unchanged for the
targeted retry. The four-case public capture rerun passed; the inspected
screenshots show the video and both real Gaussian canvases, including their
visible quality faults. Local evidence is retained in
`data/validation/deployment/railway-panorama-http.json`,
`panorama-public-{report,baseline,rife,gallery}.png` and the corresponding
`panorama-public-*-checks.json` files. The new release has no pending Railway
changes. Browser success does not make the synthetic scene geometrically
accurate or visually accepted.

## Previous 13-scene observation release — 2026-11-05

The observation catalog contains **13 distinct scenes**: the previous four and
nine additional exports, including all four Mapillary Gaussian variants, early
dozer trials, the proof rerun, partial-pose failure and initial desk trial. The
unchanged dozer camera-path re-export is represented by its existing scene and
explicit duplicate lineage. The comparison report publishes 10 licensed source /
warp / mask / gray-control / diffusion images, 72 summarized stage records and
per-image attribution. Visual quality does not exclude a result.

| Item | Value |
| --- | --- |
| Viewer source | `0870435a1367327dfe45e78331a505adb9d9608d` |
| Release | [viewer-observations-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-observations-2026-11-05) |
| Archive | `groundshift-observations-20261105.tar.gz`, 147,359,576 bytes |
| SHA-256 | `8cbb3335f30127be05f81904e792ae2190d5483bf3c9a564b6d25358c38ebb20` |
| Static payload | 89 files, 159,297,244 bytes |
| Deployment-pointer commit | `85bdd37e2fa1e9d26c803656e8dbaad63facd653` |
| Railway deployment | `f8f8c010-8774-4079-86e8-8ad138856424` — SUCCESS; public-browser verification recorded below |
| Deployment timing | Created 2026-11-04 23:48:04 UTC; SUCCESS 23:48:49 UTC (2026-11-05 KST) |
| Actual trigger | Explicit latest-branch connector trigger; push autodeploy remains unverified |

**Local PASS:** TypeScript, lint, 165 viewer/packager tests, production build,
22 headed Chrome tests in 1.9 minutes, and 102 distinct native-adapter tests
across their required environments. The OpenCV environment ran 102 with 19
missing-dependency skips; supplemental Pillow, PyCOLMAP and HDR-FFmpeg runs
executed every skipped test successfully (5 inpaint, 11 augmentation, 6 rig,
20 video tests, with overlap). This is 102 unique cases, not the sum of runs.
All 13 scene renders, desktop/mobile gallery, search/filter, report images,
sliders, history and return navigation were checked. The nine new canvas
previews were captured and visually inspected. No GPU training or inference
was repeated for publication; the measured existing binaries are unchanged.

The complete archive was read back locally: all 89 members exactly match their
public file inventory. The published archive was downloaded again and its
SHA-256 matched the local file. Every new Gaussian PLY matches the existing local job
SHA-256, and coordinates/navigation are unchanged. The report is rebuilt from
explicit selected fields and an image allowlist; raw job logs, private footage,
private frames, model weights and local paths are not included.

| Public observation check | Result | Evidence |
| --- | --- | --- |
| Railway build and health | PASS | Exact pointer commit deployed; archive checksum OK in build log; Caddy server starts and healthcheck succeeds |
| Public file integrity | PASS | All 89 files match expected byte length and SHA-256; `/healthz` returns 200/`ok` |
| Missing/private paths | PASS | Five probes return genuine 404s, including private job/video paths and an unshipped inference log |
| Source/comparison display | PASS | Public report manually inspected; GS case switch visibly updates input, mask, generated output and metrics |
| Full public render regression | PASS after one targeted retry | 18 distinct cases covered: initial run 17 PASS / 1 download-timeout FAIL; the 69 MB scene passes render and reload with a longer public-download wait |
| Individual visual inspection | PASS | All 13 public-origin scene screenshots inspected; visible output and quality limitations recorded separately |
| Report and gallery interactions | PASS | Both comparison cases, actual images/masks, slider endpoints, 72 history records, all 13 scene links, search/filter, return/history and 390px mobile layout |

The initial public headed Chrome run finished with **17 PASS / 1 FAIL** in
4.8 minutes. The 69 MB `beijing-20k` scene was still downloading at 52.4 MB when
the 30-second readiness assertion expired; it had not reached a render result.
Only that case was rerun, with a 90-second public readiness wait and 180-second
test limit. It passed actual rendering and reload in **55.5 seconds** (58.5-second
runner duration). Localhost retains its original 30/60-second limits. These
durations include network transfer, rendering and test actions; they are not
GPU or cold-cache benchmarks. No application code or scene bytes changed for
the retry. All 13 scene captures were individually inspected. No page errors
were captured by the scene/report tests. TypeScript and lint passed again after
the test-only change.

Raw evidence is retained locally under `data/validation/deployment/`:
`railway-observations-http.json`, `railway-observations-status.json`,
`railway-observations-final-logs.json`, `observations-public-browser.log`,
`observations-public-large-retry.log`, both corresponding browser output folders,
and `observation-public-visual-review.json`. The original failed attempt and trace
remain preserved. The public report screenshot is
`data/validation/deployment/railway-observations-overview.png`; these local
evidence files are excluded from Git. Final service readback reports live,
the same successful deployment, and no staged changes.

**Quality remains FAIL** for the Mapillary reconstruction/completion experiment;
generated-view multi-view consistency remains **NOT RUN**. Publication and browser
rendering PASS do not change those acceptance results. The final documentation
and test-timeout commit does not replace the immutable viewer archive above.

See [observation workflow](OBSERVATIONS.md) and [the comparison report](https://groundshift-viewer-production.up.railway.app/experiments/mapillary/index.html).
The four-world release below remains a rollback package and historical evidence.

## Previous four-world catalog release — PASS, 2026-11-05

The catalog release collects four usable worlds: Houseplant, the original supplied-pose dozer, the independently estimated 120-view dozer, and the user's reconstructed desk. Local checks, the curated package, downloaded release checksum, Railway deployment, all 31 public file hashes, and actual public rendering of all four scenes are **PASS**. The gallery and scene navigation were exercised on the public origin.

| Historical package | Verified value |
| --- | --- |
| Viewer source | `f78bd6b476cbd5369597ac42f77fee8264957c4e` |
| Deployment-pointer commit | `c2516d6bb8867e3b7151acb8223feb73ae4d2706` |
| Railway deployment | `638cd8cb-9a99-45bf-95dd-0d2700e33fa9` — SUCCESS |
| Deployment timing | Created 2026-11-04 15:52:43 UTC; succeeded 15:53:14 UTC (2026-11-05 KST) |
| Actual trigger | Explicit latest-branch connector trigger; GitHub push autodeploy was not observed |
| Release | [viewer-gallery-2026-11-05](https://github.com/neocjmix/groundshift/releases/tag/viewer-gallery-2026-11-05) |
| Archive | `groundshift-viewer-f78bd6b.tar.gz`, 31,014,851 bytes |
| Archive SHA-256 | `75d14a661283a9c5ca24e48de9b491d5d06cb7c3171a2dfd36dd4d5cffd012ff` |
| Static payload | 31 files, 35,174,566 bytes |

| Public check | Result | Observed evidence |
| --- | --- | --- |
| Build, service and integrity | PASS | Archive checksum verified in build logs; healthcheck passes; `/healthz` returns 200/`ok`; all 31 public file bytes and hashes match |
| Missing/private paths | PASS | Four tested paths return actual 404s |
| Four-scene gallery and rendering | PASS | All previews and all four actual scenes visually inspected; each selected scene reaches ready with one canvas |
| Desk playback and scene switching | PASS | Path advances to progress 16.316 with changed camera position/orientation; pause works; sidebar switches all four scenes |
| Return, category and search | PASS | Back to scenes leaves zero canvases; reconstruction category returns two cards; desk search returns one; clearing returns four |
| Captured console | PASS | No warnings or errors in the captured public-browser console |
| GitHub push-triggered autodeploy | NOT VERIFIED | No new deployment observed after the push; explicit connector trigger completed this release |

The public viewer showed a rolling 60 fps label for each scene on this M2 Mac. Those are observations with uncontrolled cache/session conditions, not a controlled benchmark. Public evidence is retained in `data/validation/deployment/railway-gallery-{http,browser}.json`, with inspected screenshots `railway-gallery.jpg` and `railway-gallery-{desk,independent,reconstructed,sample}.jpg`. These are public-origin captures; original private video frames were not copied into the repository. Final Railway status had no pending work or staged changes.


Local verification passed TypeScript, lint, **143 viewer/packager tests**, **47 Python tests** including real HDR pixel checks, the production build, and **11 headed Chrome tests in 48.9 seconds**. Desktop/mobile layouts and all selected previews were visually inspected. Home loads 321,212 uncompressed JavaScript bytes and makes no WebGL context or PLY request; viewer, camera-path and world-loading chunks load only after a scene is selected. These are local execution observations, not a claim about a fresh public client or hosted performance. This release reuses the previously verified native exports; it does not imply a new reconstruction run.

| Selected world | What it demonstrates | Quality / evidence boundary |
| --- | --- | --- |
| Houseplant | Licensed upstream Gaussian scene; M0 viewer | Viewer sample, not a Groundshift reconstruction |
| Dozer · supplied cameras | 40 photos plus supplied measured poses/sparse initialization; local Metal training | Recognizable early reconstruction; soft surroundings |
| Dozer · estimated cameras | 120 raw photos, supplied lens calibration only; locally recovered poses/points and Metal training | Separate independently estimated pose result; supplied lens calibration is explicit |
| My desk | 99 locally estimated views from one user recording, estimated intrinsics and new Metal training | Recognizable desk/computers; peripheral smearing, thin-object streaks and blurred screen text remain |

The earlier four-world release excluded the smaller 24-view dozer and initial 15-second desk trials. The observation release now includes them as experiments, retaining their measured limitations. A second independent original recording and an actual walking-route capture remain **NOT RUN**.

### Desk publication permission

The creator has explicitly authorized **public display of the derived desk worlds and their rendered viewer previews**, including earlier trials under the later instruction to publish every experiment in Groundshift. **All rights reserved; no open redistribution license is granted.** This permission covers the selected Gaussian scene, necessary camera/world metadata, provenance and preview. It does not publish or license the original MOV, extracted frames, private iCloud URL, location/probe metadata, absolute local paths or reconstruction logs. The public artifact cites this permission statement; no private source link or access token is exposed. [Local reconstruction evidence and limits](ORIGINAL_VIDEO.md).

## Earlier revisit deployed revision

| Item | Value |
| --- | --- |
| Project | Groundshift — `db649cd6-49db-4750-b86d-c3c4d14b213d` |
| Environment | production — `43346592-217f-414e-b2ad-334e09b37599` |
| Service | groundshift-viewer — `2c6ac4d5-37bb-4ea8-aee0-1e75a1abdf69` |
| Deployment | `40916425-e59e-4d5c-b6f8-38fd90bc2750` — SUCCESS, 2026-11-04 13:37 UTC |
| Pinned deployment source | `16f943b6a5c6ed4242a63589208ed9de81aa8d66` on `feat/local-viewer-reconstruction` |
| Locally built viewer source | `b06d583535599ca911b8efb601069c7775a1ca73` |
| Public package | [viewer-revisit-2026-11-04 prerelease](https://github.com/neocjmix/groundshift/releases/tag/viewer-revisit-2026-11-04) |
| Archive | `groundshift-viewer-b06d583.tar.gz`, 28,259,801 bytes, 18 static files |
| Archive SHA-256 | `2e26d090d378540530677083de5167ba484c7551fee2f9b94ee7380fa85d2025` |

`deploy/Dockerfile.github` downloads the locally built archive, checks its SHA-256, and copies only `www/` into the pinned official Caddy image. Runtime notices, world provenance, camera metadata and dataset licenses are included. Large assets are release attachments, not Git commits. Root `.dockerignore` excludes everything except the deployment files.

This earlier deployment was pinned to the listed commit. The connector accepted a new source request for `feat/local-viewer-reconstruction` without a commit pin (`commitSha: null`), and watch patterns `/deploy/**` and `/.dockerignore` are confirmed by settings readback. However, service configuration only returned the source repository, and no new deployment appeared for more than 90 seconds after the release-pointer push. **Push-triggered autodeploy is NOT VERIFIED.** The agent therefore explicitly triggered the latest branch revision through the connector; deployment `638cd8cb-9a99-45bf-95dd-0d2700e33fa9` succeeded and its full static inventory matches publicly. No cause for the missing push trigger has been established. Source or documentation edits alone do not replace the archive consumed by `deploy/Dockerfile.github`; every viewer/scene release must update that archive URL and checksum. Retain each previous archive and deployment pointer for rollback.

The previous [viewer-2026-11-04 release](https://github.com/neocjmix/groundshift/releases/tag/viewer-2026-11-04)
and source `81adf61858673dedf9367196f4430ba8c5f24b16` remain available for rollback.
Its deployment was `00a9186e-8ae1-48b4-8371-a30072c65015`; archive
`groundshift-viewer-8c806e7.tar.gz`, SHA-256
`33b5e2c1ac2f4176cafc0593e43bd1d525dab8e0550f9a10046f2c8ee3e3dbf9`.

## Earlier revisit release verification

The earlier revisit release added camera-path navigation and the separately identified
[120-photo independent reconstruction](INDEPENDENT_RECONSTRUCTION.md). The
original Dozer PLY is unchanged; only its camera sequence metadata was added.
All 40 original camera matrices are unchanged. The smaller 24-view pipeline
experiment was not selected for publication because of its poor visual quality.

**PASS:** Railway build checksum, container health, all 18 public file hashes,
real 404s for missing/private paths, actual rendering of all three scenes, and
the new scene's play/pause, keyboard view selection and free look. Free look
changed camera rotation while preserving position. Actual public rendering is
shown in the [inspected screenshot](evidence/railway-independent-120.jpg).

The new scene displayed 75,397 Gaussians, 6.94 MB, 2.53 s load/decode and a
60 fps rolling label in the in-app Chromium browser on M2 Metal. This is one
observation with no native training active, not a controlled cold-cache or
GPU-only benchmark. The public file's SHA-256 matches the local native export:
`67f64ebeea5fc8cdae8ea65f01e0f4d060291d120bb5656311cad6bdd0b67229`.
Raw evidence: `data/validation/deployment/railway-revisit-{http,browser,logs}.json`.

Preparation passed TypeScript, lint, 118 viewer unit tests, 41 Python tests,
production build and four headed Chrome tests. Native image pipeline and
Metal training have separate execution reports; original walking-video
acceptance is still NOT RUN.

## Standing release workflow

Complete this sequence for viewer changes and all experiment outcomes already authorized for observation. Routine approval is not needed again; preserve explicit privacy and licensing limits.

1. Finish the change and run relevant TypeScript, lint, automated, production-build and browser checks. Verify actual rendering for exported scenes. Inspect and report quality separately; FAIL quality is published rather than filtered out.
2. Inventory all exported worlds and experimental outcomes. Publish each distinct scene with public metadata and an actual render preview. Record failed/cancelled/unexecuted stages and duplicate-export lineage in the report. Keep downloaded samples, measured/supplied-pose reconstructions, original video and generated-input trials distinct.
3. Build the curated static package locally using the explicit inclusion flags below. Inspect its complete inventory for private source paths, URLs, footage, frames and raw logs. Only explicitly allowlisted licensed public crops/comparisons belong in the report. Do not upload the repository or raw `dist/` directory.
4. Archive only `www/`, record its SHA-256, publish it under a fresh GitHub release tag, then download it and compare the hash. Keep the prior archive available.
5. Update the release URL/checksum in `deploy/Dockerfile.github`, commit the reviewable deployment pointer, and push it to the connected branch as part of the same workflow. A source-code push without this step leaves the old package live.
6. Observe Railway's deployment history, revision and healthcheck. A source-connection response is insufficient evidence of push-triggered deployment. If the expected new deployment does not appear, explicitly trigger the latest intended branch revision through the connector, continue validation, and record which trigger actually worked. The standing instruction already authorizes this routine fallback.
7. Compare every public file against the curated inventory. Verify missing/private paths return 404. Open the public viewer, visually inspect all included worlds, and exercise changed navigation/catalog behavior.
8. Record the release tag, source/deployment revisions, archive hash, Railway deployment ID and public-browser evidence here. Report any failed or unexecuted gate accurately; completion requires a verified live result.

### Branch request and explicit deployment fallback

The requested source is `feat/local-viewer-reconstruction` without a commit pin, with watch paths `/deploy/**` and `/.dockerignore`. Keep repository root as the build context and `deploy/Dockerfile.github` as the Dockerfile path. Native reconstruction and the production web build stay local; Railway downloads the already validated static archive and runs Caddy.

Railway documents branch autodeploy and watch patterns, but this service did not visibly deploy the release-pointer push during observation. The connector accepted the branch request and returned `commitSha: null`; later settings readback confirmed the watch patterns but only exposed `source.repo`. That does not prove a functioning GitHub push trigger. Its cause is not diagnosed. See [GitHub autodeploys](https://docs.railway.com/deployments/github-autodeploys) and [watch paths](https://docs.railway.com/deployments/monorepo#watch-paths).

The working release procedure must observe a new deployment and use an explicit latest-revision connector trigger when needed. Record that fallback rather than calling webhook autodeploy successful. The standing user instruction is to finish verified deployment in the same workflow; it does not depend on this unverified automatic trigger. Ordinary source/docs work must still produce a fresh archive and update the deployment pointer before any release is complete.

## Restore scene assets in a fresh checkout

The catalog and preparation recipe are tracked; generated scenes and comparison
images are ignored. `npm run sample` supplies only Houseplant's Gaussian asset.
For the current 22-world observation surface, restore the immutable panoramic-depth
release in a **fresh checkout**. The commands verify the archive before copying
the named world folders and public experiment assets. Existing files in these paths
would be replaced; keep any personal variants elsewhere.

```sh
(
  set -e
  gs_release_dir=$(mktemp -d)
  gs_archive=groundshift-panoramic-calibration-20261106.tar.gz
  curl --fail --location --output "$gs_release_dir/$gs_archive" \
    "https://github.com/neocjmix/groundshift/releases/download/viewer-panoramic-calibration-2026-11-06/$gs_archive"
  printf '%s  %s\n' \
    '1e486d418be4c0391e033a2f6fd2fb43e580d34baa1f588817094d5b00dee15f' \
    "$gs_release_dir/$gs_archive" | shasum -a 256 -c -
  tar -xzf "$gs_release_dir/$gs_archive" -C "$gs_release_dir"
  for gs_world in sample reconstructed independent desk beijing-10k beijing-generated beijing-depth beijing-20k beijing-2k beijing-video-baseline beijing-video-rife dozer-smoke dozer-proof dozer-partial dozer-24 desk-15s scooter-object scooter-context scooter-real-object scooter-real-context scooter-nodepth-object scooter-nodepth-context; do
    mkdir -p "public/worlds/$gs_world"
    cp -R "$gs_release_dir/www/worlds/$gs_world/." "public/worlds/$gs_world/"
  done
  mkdir -p public/experiments
  cp -R "$gs_release_dir/www/experiments/." public/experiments/
  # Vite serves these tracked HTML entries from experiments/.
  rm -f public/experiments/lab/index.html public/experiments/object-focus/index.html public/experiments/object-real/index.html public/experiments/object-nodepth/index.html public/experiments/panoramic-depth/index.html
  cp "$gs_release_dir/www/worlds/catalog.json" public/worlds/catalog.json
)
npm ci
npm run dev
```

The earlier 13-world extraction/copy procedure was executed in an isolated fresh
directory and matched its inventory. The updated 22-world command above has not
yet been rerun in a fresh checkout; package preparation read all 382 staged files.
Do not substitute the historical restore evidence for a current restore test.

This restores display assets only. It neither downloads the private original
video nor repeats reconstruction. Desk creator-authorized display terms remain
separate from the open sample licenses. The earlier four-world archive remains
available in its historical release entry above.

## Prepare a curated package locally

After restoring the assets above, or generating and checking the same selected public artifacts locally, build the full observation release:

```sh
npm run package:viewer -- --include-reconstruction --include-independent --include-desk --include-experiments
```

The first three flags select the existing worlds; `--include-experiments` includes every world and report file explicitly listed in `scripts/observation-worlds.json`. See `python3 scripts/prepare-observations.py --render-previews` for regeneration from local jobs. The default `npm run package:viewer` includes only Houseplant and still requires its `preview.jpg`. The catalog is filtered to included scenes, so a smaller curated package does not advertise missing worlds or an absent report.

The command builds locally and prints a fresh staging directory under `data/deploy/viewer-<timestamp>/`. It copies only HTML, hashed bundles, icon, runtime notices, the selected catalog, scene assets, previews, manifests, camera metadata and credits. It checks ordinary files/directories and public provenance, rejects symlink escapes and common private references, and preflights inputs before creating output. This is a practical publication boundary, not a substitute for inspecting scene content. Source datasets, native tools, private footage and job logs are excluded. A SHA-256 inventory stays beside the staging directory, outside any upload.

The staging directory contains `Dockerfile`, `Caddyfile`, `.dockerignore` and `www/`. To prepare the release attachment, substitute the exact printed path and a fresh archive name:

```sh
COPYFILE_DISABLE=1 tar -czf data/deploy/groundshift-viewer-<revision>.tar.gz \
  -C data/deploy/viewer-<timestamp> www
shasum -a 256 data/deploy/groundshift-viewer-<revision>.tar.gz
```

Compare the archive contents against the staging inventory before publishing. The inventory JSON is retained beside the local staging directory; it is not part of the public `www/` archive. Re-download the published archive and verify the checksum before connecting Railway.

## Railway configuration

The Railway connector created the project/service, configured it, and attached `neocjmix/groundshift` at the pinned commit. The local Railway CLI token and saved login were expired; this did not block the connector. GitHub CLI authentication was valid, so a GitHub release supplied the curated files without requiring another login.

Apply these settings through the Railway connector or service settings:

- Dockerfile path: `deploy/Dockerfile.github`; repository root as build context.
- Healthcheck: `/healthz`, timeout 60 seconds.
- Restart: `ON_FAILURE`, maximum 3 retries.
- Public domain target: port 8080. Caddy listens on Railway's `PORT` (default 8080), on all interfaces.
- No custom start/build command, volume, database, bucket, secret or GPU service is required.

Railway rejected configuring a `railway.json` path for this new service. Its current [Infrastructure as Code documentation](https://docs.railway.com/infrastructure-as-code) says Config as Code is deprecated, unavailable to new services, and stops being read for legacy services on 2026-12-01. The unused JSON configuration was removed; this one service uses direct settings without adding an IaC dependency.

Railway terminates HTTPS. Missing manifests/assets return genuine HTTP 404s. Hashed bundles use immutable caching; HTML, manifests and scene paths revalidate. Use **Open world folder** for private local artifacts. Loading arbitrary localhost HTTP URLs from an HTTPS website is subject to browser mixed-content, CORS and local-network restrictions.

### Alternative: authenticated CLI upload

This path is available for a future session with valid CLI authentication. Set the service's Dockerfile path to `Dockerfile` before uploading the curated directory, keeping the healthcheck/restart/domain settings above:

```sh
railway up data/deploy/viewer-<timestamp> --path-as-root --no-gitignore \
  --project db649cd6-49db-4750-b86d-c3c4d14b213d \
  --environment production --service 2c6ac4d5-37bb-4ea8-aee0-1e75a1abdf69
```

`--no-gitignore` is only appropriate with the curated staging directory and `--path-as-root`. Never apply it to the repository root. The current deployment used the connector/GitHub route, not this CLI upload.

## Initial public verification — 2026-11-04

| Check | Result | Evidence |
| --- | --- | --- |
| Railway container build/start/health | PASS | Build log verifies archive checksum, starts Caddy and passes `/healthz`; deployment SUCCESS |
| HTTPS and static file integrity | PASS | All 14 decoded public files match the local SHA-256 inventory; root and health return 200 |
| Licenses, manifests, cache headers | PASS | JSON parses; credits/notices reachable; immutable hashed bundles and no-cache world/HTML responses |
| Missing/private paths | PASS | Missing JSON/PLY, `/.env`, `/data/jobs/dozer-1500/job.json` return 404 |
| Houseplant actual rendering | PASS | Leaves and pot visible in [public-origin screenshot](evidence/railway-houseplant.jpg) |
| Local dozer actual rendering | PASS | Excavator, road and cones visible in [public-origin screenshot](evidence/railway-dozer.jpg); direct deep link also verified |
| Orbit, zoom, reset, scene replacement | PASS | Actual camera-position changes and return to initial coordinates; one canvas after replacement |
| Browser errors | PASS | No errors in captured browser console |
| Railway CLI upload | NOT RUN | Invalid local authentication; deployment used the connected Railway plugin |
| Other devices and load/stress testing | NOT RUN | No cross-device or capacity claim |

Public-browser checks used the Codex in-app Chromium browser on this M2 Mac, 1280 × 720 CSS viewport. Runtime reported `ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)`. Observed rolling frame-rate labels were 60 fps for both scenes. Load + decode displayed 2.54 seconds for Houseplant and 5.14 seconds for dozer; these are single observations, not controlled cold-cache benchmarks. Browser/edge caches were not forcibly cleared, and dozer loaded after Houseplant. These measurements are separate from the original localhost Chrome results.

Raw HTTP hashes, browser details/camera positions and Railway build/runtime logs are retained locally in `data/validation/deployment/railway-{http,browser,logs}.json`. Earlier local Caddy validation remains in `local.json`. TypeScript, lint, 86 unit tests and the production build passed during package preparation; the subsequent packaging-only adjustment passed syntax and inventory checks, with unchanged `www/` hashes.

Current references: [Railway CLI root/ignore behavior](https://docs.railway.com/cli/up), [Railway Caddy deployment](https://railway.com/guides/caddy), [IaC and Config as Code deprecation](https://docs.railway.com/infrastructure-as-code), [Caddy file server](https://caddyserver.com/docs/caddyfile/directives/file_server). The Docker image is pinned to the verified available `2.11.7-alpine` manifest digest; Caddy's current release was 2.11.8 when checked, but that Docker tag was not yet available.
