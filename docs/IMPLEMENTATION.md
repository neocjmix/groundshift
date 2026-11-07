# Implementation plan

Each milestone must report PASS / FAIL / NOT RUN. Build success does not prove GPU training or visual rendering.

## Current status — 2026-11-07

Viewer UX follow-up:[Fly](FLY.md) adds a mobile floating movement stick/swipe look and desktop
WASD/mouse fullscreen exploration,explicit lift/speed/reset/exit,with no
collisions or inferred ground. It shares the existing renderer and paging
session and changes no world artifact or native reconstruction. Actual input
and deployment checks are recorded separately from geometry acceptance.

New-data/serving result,2026-11-07: [Paris first58m](PARIS_STREAMING.md)
executes144/144SfM views,480DAV2 predictions and one8k/768px/800k Metal run
(1018.286s). WholeSPZ15.92MB is preserved. Nearest3spatial regions pass bounded
loading/reverse/retry but **FAIL** visual coverage; the complete union is exact.
Official native RAD/LoD initially ran with a524,288-slot/eight-page
pool and public start/end/reverse/whole-control checks **PASS**. The follow-up
[detail repair](FLY_REFINEMENT.md) uses917,504slots/fourteen pages and800k
selection after the former limits proved permanently coarse nearby. Initial strict16-view
appearance screen **FAILS**,with native mean3.63/255,worst7.99; no independent
geometry acceptance. Compact encoding saves only1.19% over nativeRAD. The
selected876sources/2.185km are the expansion route,**not** the reconstructed
extent; only24HD images/GPS58m are processed. Full2km serving remains NOT RUN.

Storage/serving follow-up,2026-11-07: [SPZ compression](COMPRESSION.md)
retains the same tangent20 reconstruction,800k Gaussians,SH1 and genuine poses,
reducing73.60→15.94MB (78.35%). Local CPU/WASM conversion and all positions
pass;201actual M2 renders across67views pass the declared codec difference
screen. Selected visual inspection shows no large appearance regression.
The original PLY and all prior observations remain. No quality training is
reopened, and independent geometry/GPU-memory improvement is not claimed.

User decision, 2026-11-07: the wider-angle tangent GS gives a substantially
better sense of presence in the user's observation, despite worse horizontal
photo-error metrics. Panorama/depth-shell backgrounds are withdrawn because
they misalign during translation and degrade exploration. The viewer renders
GS only and ignores archived background references without fetching them.
Original GS bytes, camera poses and historical comparisons are retained. This
is a viewer change, with no new reconstruction/training.

The explicitly user-reopened [tangent/background trial](TANGENT_BACKGROUND.md)
is executed: 160 real 1024px crops in 20 directions, DAV2 Small MPS at actual
1036px neural input, anchored/overlap-calibrated spherical initialization and
one 8k/800k Metal export in 1188.250s. In 300 actual matched GS-only renders,
held MAE worsens 24.414→26.203 at 512 output and 24.345→25.981 at 1024;
zero of six held directions improves. Retain `street-final-hires`, while
preserving the new renderable trial and its failures. Optional panorama/depth
backgrounds were presentation only and are now withdrawn. This bounded reopening is finished; it does
not authorize another quality sweep on the same sources.

[Final same-data quality campaign](FINAL_QUALITY.md) complete: one1024/800k/8k
Metal export,1455.651s,73.6MB,300 matched browser renders. Same512-output
held-view MAE improves27.751→24.414; actual windows/railings look sharper while
branch/near-object ghosting and wall doubling remain. Retain this new result as
the best observed on these nine sources. **Same-data quality tuning is CLOSED**;
no automatic parameter/model/filter follow-up. Fresh inputs, native world and
measurements publish separately as each becomes available. Geometry supervision
was investigated from pinned upstream source, not executed.

The [completed model-family comparison](MODEL_SELECTION.md) adds four real
8k Metal GS exports (PanDA-Small,DA3-Small,MoGe-2 Small,DA²) and375 actual matched
renders including the reused DAV2 control. MoGe's mean withheld color error is
27.587 versus27.751, a0.6% reduction with no clear qualitative breakthrough.
Retain DAV2 as incumbent; MoGe is the most promising new candidate. Native
execution passes; accurate geometry and unrestricted walking remain unaccepted.


The [completed short-street run](STREET_CONCLUSION.md) trains7 real-image worlds
locally on M2 Metal and renders525 matched camera views. Recommend dense8k:
409.759s,400k Gaussians, held mean MAE27.751. Same16k/400k control: dense28.911,
sparse32.212; more steps did not beat the8k dense result. A recognizable short
route is feasible; P2 accurate geometry and unrestricted walking remain
unaccepted. The user's end-to-end instruction explicitly permits diagnostic
training past the earlier stop-before-training gate. Existing best scooter,
originals, poses and all prior worlds remain preserved. Public release details
are in [DEPLOYMENT.md](DEPLOYMENT.md).

The earlier [observed-correspondence follow-up](STEREO_ANCHORS.md) runs local CPU SIFT and fixed-pose stereo. A256→512px search-range correction yields291 road candidates; combined calibration improves matched road4→5 disagreement2.43%→0.45%. Reverse-road/facade and invalid far predictions remain limitations. Five cloud controls are inspectable. In that bounded run P2 geometry was NOT ACCEPTED; new inference, fusion and GS were NOT RUN. The preceding [dense perspective](PERSPECTIVE_OVERLAP.md), [calibration control](PANORAMIC_CALIBRATION.md) and baseline artifacts remain.

The latest direction is the [panoramic street plan](PANORAMIC_STREET_RECONSTRUCTION_PLAN.md).
The bounded [P0/P1 run](PANORAMIC_DEPTH_P1.md) preserves the best scooter result,
executes two depth models on one ERP and exports calibrated spherical clouds.
The [adjacent-pair follow-up](PANORAMIC_PAIR_P1.md) now measures both directions and exposes regional bias. That bounded run included no fusion or Gaussian training; the later diagnostic street run above preserves its geometry limitations.

The preceding user direction prioritized a visible one-object result and immediate
Railway publication. The latest user instruction requires immediate asynchronous
deployment of each small publishable result. Check basic package integrity and
authorized contents, dispatch deployment, then continue browser checks,
regressions and detailed quality comparisons in parallel. Pending validation is
NOT RUN; completing every local check is not a prerequisite to publication.
The [object-focused experiment](OBJECT_FOCUS_EXPERIMENT.md) keeps whole-frame
diffusion before depth estimation, then calibrates and fuses depth for GS
initialization. The chronological lab lists experiments and worlds by recorded
completion time, newest first, with an oldest-first option.

| Milestone / acceptance boundary | Result | Evidence |
| --- | --- | --- |
| Explicitly reopened tangent/background experiment | PASS for actual DAV2 MPS, one Metal export and 300 matched GS-only renders; comparative appearance screen FAIL | [Tangent/background](TANGENT_BACKGROUND.md): 20 directions per center do not add physical viewpoints; 136/160 depth fits accepted; preserve prior best and publish the new trial regardless. Background and geometric acceptance remain separate. |
| Final same-data quality attempt | PASS for actual Metal export/300 matched renders and comparative appearance; geometry NOT ACCEPTED | [Final quality](FINAL_QUALITY.md): fresh1024px crops,800k cap, unchanged DAV2 seed/poses,8k steps; same-data quality campaign CLOSED. |
| Alternative depth/geometry model families | PASS for4 actual MPS/Metal exports and375 actual renders; major quality gain NOT ESTABLISHED | [Model selection](MODEL_SELECTION.md); corrected strict loads, PanDA cancelled attempt/one repair, DepthMaster dependency blocker, mixed-condition timings. |
| Short street, real images and calibrated dense initialization | PASS for7 actual Metal exports/525 renders; recognizable route, geometric quality partial | [Seven controls and conclusion](STREET_CONCLUSION.md); same16k/400k budget comparison,61 full local browser cases plus11 final-layout checks. |
| Observed correspondences and road calibration | PASS for actual CPU execution and seven local/seven public headed Chrome checks; P2 NOT ACCEPTED | [Matched evidence](STEREO_ANCHORS.md): SIFT-only failures, inadequate256px stereo search, successful512px retry, five cloud controls and invalid-depth counts. No new GPU operation. |
| Dense perspective coverage and overlap | PASS for actual MPS/CPU execution and six local/six public headed Chrome checks; P2 geometry NOT ACCEPTED | [Measured controls](PERSPECTIVE_OVERLAP.md): two physical panoramas, augmented/filtered/level/ERP point clouds. Road calibration lacks sparse anchors; filtering is not uniformly beneficial. No fusion or new GS. |
| Common-track calibration and perspective input control | PASS for actual CPU/MPS execution and targeted local browser; independent geometry NOT RUN | [Measured results](PANORAMIC_CALIBRATION.md): common calibration alone brings no consistent improvement; local perspective depth reduces withheld-feature reprojection errors. No new GS. |
| Adjacent-pair P1 / P2 diagnostic | PASS for actual MPS execution, pair projection and local browser; geometry not accepted for fusion | [Two-panorama results](PANORAMIC_PAIR_P1.md): 1,001 shared sparse tracks, weak median 1.94° parallax, 3.6–5.1% median pair range differences; regional bias and unsupported road calibration remain. |
| P0 + one-panorama P1 | PASS for preserved baseline, actual MPS inference, projection tests and public browser inspection; global geometry NOT RUN | DA² 2.570 s / DAV2 1.408 s; 1,195 calibration + 326 withheld SfM tracks; colored clouds and [limitations](PANORAMIC_DEPTH_P1.md). No new GS training. |
| M0 licensed sample, controls, errors, replaceable artifact and actual M2 rendering | PASS | 165 viewer/packager tests, 25 local headed Chrome tests, inspected desktop/mobile views; original M0 hardware evidence in [VALIDATION.md](VALIDATION.md) and current release checks in [DEPLOYMENT.md](DEPLOYMENT.md) |
| M1 local image input, obtained real camera poses, native Metal training, PLY export and viewer rendering | PASS | 40-image dozer dataset, 1,500 steps, 80.35-second job, 194,789 splats; [M1.md](M1.md) |
| New CPU pose estimation and training on raw images | PASS with supplied lens calibration | 120/120 newly estimated poses, 30,468 new sparse points, 3,000 Metal steps and actual browser inspection; [evidence](INDEPENDENT_RECONSTRUCTION.md). Earlier 16/40 failure remains recorded |
| User-requested static Railway observation surface | PASS for actual public tangent GS/background rendering;35 GS scenes and17 reports | Plan, inputs, depth, native world and measurements dispatch asynchronously.79/79 full local native-phase cases pass; actual targeted public GS/three-mode interaction passes. The later measured-report mobile failure and scoped repair are recorded separately in [DEPLOYMENT.md](DEPLOYMENT.md). Full79 public suite NOT RUN; push-only autodeploy unverified. |
| Scooter without learned depth | PASS for local Metal execution and public Chrome rendering; recognizable object quality FAIL | Identical nine RGB files and cameras; depth inference/calibration/fusion removed. 115 triangulated object points → 5,000 Metal steps in 116.339 s → 569 full / 237 selected Gaussians. [OBJECT_NO_DEPTH.md](OBJECT_NO_DEPTH.md). Public deployment and file checks passed. |
| Real-only scooter ablation | PASS for local Metal training and public Chrome rendering; quality comparison NOT RUN | All intermediate image generation removed. Nine real crops → nine calibrated depth maps → 41,533 initial points → 5,000 Metal steps in 160.298 s. [OBJECT_REAL_ONLY.md](OBJECT_REAL_ONLY.md) |
| One-object crops → whole-frame diffusion → calibrated depth → point fusion → GS | PASS for executed pipeline/export/rendering; partial camera/depth rejection; quality gain NOT RUN | Nine real crops + 56 MPS img2img candidates → 47 registered cameras → 34 accepted depth maps → 93,595 initial points → 5,000 M2 Metal steps. Focused export has 93,101 Gaussians; recognizable but blurred/streaked. [OBJECT_FOCUS_EXPERIMENT.md](OBJECT_FOCUS_EXPERIMENT.md) |
| Two-endpoint panorama generation and GS comparison | PASS for local 65-frame MLX interpolation, Metal exports and Chrome rendering; 3D quality FAIL | Two licensed photos → 65 2048×1024 frames; matched real-only and generated-view GS worlds both ran 10,000 Metal steps. At two held-out real-photo views, generated-view GS had higher pixel error and visibly streaked geometry. Full video diffusion NOT RUN; [PANORAMA_VIDEO_EXPERIMENT.md](PANORAMA_VIDEO_EXPERIMENT.md) |
| Three-view learned-depth diagnostic | PASS for M2/MPS inference and internal sparse-depth ordering; GS gain NOT RUN | Depth Anything V2 Small ran on three observed 512px panorama crops. Rank correlation with all-image SfM inverse camera-Z was 0.876–0.913; this is not independent depth accuracy or multi-view consistency. [DEPTH_EXPERIMENT.md](DEPTH_EXPERIMENT.md) |
| Original user video → local scene | PASS for indoor desk capture | 99/99 newly estimated cameras, 4,000 Metal steps, inspected browser result; [evidence](ORIGINAL_VIDEO.md) |
| M2 original walking video | NOT RUN for walking acceptance | Real indoor video pipeline works; an actual walking-route capture remains outstanding |
| M3 camera-path controls on real sample | PASS for sample behavior | Actual supplied camera poses, interpolation/free look and gap tests; [REVISIT.md](REVISIT.md). Original walking-route continuity remains NOT RUN |
| M4 local video/image command | PASS for one original video; full milestone NOT RUN | Full private video command completed in 277.57 s; a second independently recorded input remains outstanding; [PIPELINE.md](PIPELINE.md) |

Implementation decisions: use the official Brush arm64 release, optional PyCOLMAP CPU wheels instead of requiring the Homebrew executable, and supplied measured poses for the first M1 acceptance run. Undistort the sample's actual fisheye images before Brush because its released importer does not handle their distortion. Preserve reconstruction internals in the native process and use the explicit v1 world format at the viewer boundary. These decisions keep the initial local-only design intact.

The earlier four-world 2026-11-05 catalog update added the accepted desk artifact alongside both dozer reconstructions and Houseplant. It passed 143 viewer/packager tests, 47 Python tests including actual HDR conversion, and 11 headed Chrome checks. In that earlier release, source footage and superseded trials remained local; the creator authorized public display of the derived desk scene. That historical Railway release passed all 31 public file hashes, all four scene renders and public gallery controls. The following observation release expanded it to 13 scenes and 72 stage records; the current catalog contains35 scenes under the policy below. Regression checks do not imply another native reconstruction execution.

## Observation publication policy — 2026-11-05

The user's latest instruction replaces the earlier usable-scene release filter.
Railway is an observation surface: all distinct exported trials are published,
including poor-quality or superseded results, with failed/cancelled stage evidence
and real/generated image comparisons. Execution, rendering and quality remain
separate PASS / FAIL / NOT RUN boundaries. Reconstruction remains local and private
inputs/model weights are not release files. See [current deployment evidence](DEPLOYMENT.md).

**Immediate asynchronous publication — user instruction, 2026-11-06:** ship
each deployable partial result as it appears; never wait for the whole
experiment or all local tests. Assign a deployment sub-agent or background
process, and continue the next experiment/implementation/validation concurrently.
Publish provisional evidence and explicit FAIL/NOT RUN labels, then update the
observation surface as later checks finish. Preserve prior outputs in each
incremental package. Minimum build/content/integrity checks protect the package;
full quality, rendering and regression checks follow dispatch and are reported
honestly. A final comparison publisher's requirement for complete reviewed
metrics must not prevent an earlier scene or provisional report from shipping
through the existing observation catalog/package workflow. This supersedes
older validation-before-release sequencing.

## User-directed panorama experiment

The user-directed Mapillary work uses a small consecutive licensed 360° sample,
reports actual spacing without claiming a global density maximum, and keeps
observed and generated pixels distinct. The first nine-panorama experiment
executed local fixed-rig SfM, stereo/inpainting, generated-image retraining and
browser viewing; it did not produce an accepted scene. The follow-up placed
two source panoramas at the ends of a 65-frame MLX interpolation, withheld the
middle photograph's RGB for comparison, and added the generated midpoint as
six Gaussian training views. This run established a working 2D video and two
working exported worlds, but did not improve the 3D scene. See
[the first experiment](MAPILLARY_EXPERIMENT.md) and
[the two-endpoint result](PANORAMA_VIDEO_EXPERIMENT.md). The current blocker is
useful geometric/appearance consistency between physical capture positions,
not an unexecuted GPU pipeline. Exact street fidelity is secondary to plausible
generated scenery; invented camera poses remain prohibited.

## M0 — Viewer
Create React + TypeScript + Vite viewer using Three.js and Spark. Load a licensed sample splat, support orbit/reset and errors. Verify actual rendering on M2 MacBook Air (16 GB), record FPS, browser, asset size.

## M1 — Local reconstruction
Verify current Brush build and Metal support, output formats, COLMAP macOS CPU alignment. Train on a small licensed multi-view dataset. Render result in viewer. Record commands, logs, duration, peak memory and failures. Evaluate another native Metal trainer only if Brush fails in practice.

## M2 — Original walking video
Start with a steady 10–15 second recording and approximately 30–60 frames at 960px long edge, adjusting from real observations. Verify recognizable scene and reconstructed camera poses.

## M3 — Revisit interaction
Follow recovered camera path forward/backward with free look, reset and speed control. Verify spatial continuity. Do not invent floor/collision from splats. Free walking is deferred.

## M4 — One-command pipeline
Video path -> frame preparation -> reconstruction -> artifact validation -> viewer-ready files. Repeat with a second recording without manual 3D modeling.

## Evidence
Record machine, OS, tool versions, capture duration/resolution, frame count, alignment, training time, total time, peak memory, artifact size, browser FPS, visual issues and PASS/FAIL/NOT RUN.

## Deferred
Unrestricted navigation, connecting places, sharing, cloud CUDA workers, privacy
redaction. Missing-view generation is now the bounded experiment described above.
