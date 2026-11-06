# Groundshift (GS)

Revisit real places as explorable 3D worlds.

**Latest actual result:** [Paris · first58m and native LoD streaming](https://groundshift-viewer-production.up.railway.app/experiments/tourist-streaming/)
· [Explore3D](https://groundshift-viewer-production.up.railway.app/?world=/worlds/paris-58m-lod/world.json).
24real12K panoramas → image-estimated poses → calibrated DAV2 → M2 Metal GS:
800k Gaussians in16min58s,15.92MB whole SPZ. Native LoD loads visible precision
with an eight-page pool and keeps coarse distant coverage. Public movement,
reverse and whole-scene comparison pass; strict16-view appearance preservation
fails,so this is useful bounded serving with detail loss. Simple nearest-region
streaming failed because visible distant geometry disappeared. All trials remain
observable. The selected876-source/2.185km GPS route is an expansion source;
**the full2.185km is NOT reconstructed**. [Measurements,failures and reproduction](docs/PARIS_STREAMING.md).

**Previous storage experiment:** [Same scene · SPZ compression](https://groundshift-viewer-production.up.railway.app/experiments/compression/)
· [Lightweight 3D](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-tangent20-spz/world.json).
The existing tangent20 scene becomes15.94MB from73.60MB (**78.35% less**),
retaining800k Gaussians,SH1,cameras and coordinates.201actual1024px M2 Chrome
renders show1.348/255 average codec RGB difference across67views; selected
detail/directional inspection shows no large appearance regression. This is
lossy storage quantization, with the native PLY preserved; no retraining or
geometry improvement. [Reproduction, actual measurements and limitations](docs/COMPRESSION.md).

**Previous nine-panorama reconstruction:** [20-direction GS · background completion withdrawn](https://groundshift-viewer-production.up.railway.app/experiments/tangent-background/)
· [New 3D trial](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-tangent20/world.json)
· [Preserved best result](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-final-hires/world.json).
Actual M2 reconstruction completed, but GS-only held-view error worsens by
7.32% at 512 output and 6.72% at 1024. Some facade overlap looks reduced;
road seams and thin/near-object ghosting remain. Keep the previous scene as
the photo-error reference. The user reports a substantially better sense of
being inside the wider-angle GS scene; the old horizontal-view metric does
not measure that experience. On 2026-11-07 the user rejected panorama and
depth-shell backdrops because translation misalignment harms exploration.
The live viewer now renders GS only, with no backdrop controls or loading;
historical comparisons remain available. [Execution, commands and evidence](docs/TANGENT_BACKGROUND.md).
This was one explicitly reopened experiment; the same-data sweep remains closed.

**Live demo:** [Final quality · 1024px result and comparison](https://groundshift-viewer-production.up.railway.app/experiments/final-quality/) · [Model comparison · four new pipelines](https://groundshift-viewer-production.up.railway.app/experiments/model-selection/) · [Street reconstruction · all seven results and conclusion](https://groundshift-viewer-production.up.railway.app/experiments/street/) · [Third real photo road check](https://groundshift-viewer-production.up.railway.app/experiments/road-third-view/) · [Observed road anchors](https://groundshift-viewer-production.up.railway.app/experiments/stereo-anchors/) · [Perspective coverage and overlap](https://groundshift-viewer-production.up.railway.app/experiments/perspective-overlap/) · [Calibration and perspective-depth comparison](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-calibration/) · [Adjacent panorama comparison](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-pair/) · [Full-sphere depth comparison](https://groundshift-viewer-production.up.railway.app/experiments/panoramic-depth/) · [Chronological experiment lab](https://groundshift-viewer-production.up.railway.app/experiments/lab/) · [Scooter comparison: real images only](https://groundshift-viewer-production.up.railway.app/experiments/object-real/) · [Without monocular depth](https://groundshift-viewer-production.up.railway.app/experiments/object-nodepth/) · [Browse all scenes](https://groundshift-viewer-production.up.railway.app/) · [Open my desk](https://groundshift-viewer-production.up.railway.app/?world=/worlds/desk/world.json). Choose **Camera path → Play path** to revisit reconstructed views. [Deployment and public-browser verification](docs/DEPLOYMENT.md).

Railway is the user's **observation surface**. The catalog includes every distinct exported trial regardless of visual quality, alongside My desk, both main dozer reconstructions and the Houseplant sample. The [Mapillary observation report](https://groundshift-viewer-production.up.railway.app/experiments/mapillary/index.html) shows real photos, geometric warps, diffusion outputs and failed/cancelled stages. The [two-endpoint panorama experiment](docs/PANORAMA_VIDEO_EXPERIMENT.md) generates 65 local M2/MLX frames and compares matched Gaussian worlds; its public report is released with the new artifacts. Publication is separate from quality acceptance; generated content and limitations stay visible. See [release verification](docs/DEPLOYMENT.md).

**Publish as results appear:** start each deployable result's Railway release
asynchronously and continue the work. Do not wait for the entire experiment or
all local tests. Pending checks stay NOT RUN and are updated afterward. See the
mandatory [agent instructions](AGENTS.md) and [publication order](docs/DEPLOYMENT.md).

## Vision
Anyone can record a memorable walk, reconstruct an explorable place, and revisit it later. Eventually separately recorded places can connect into a growing shared world. Pedestrian paths, alleys, corners and stairs matter more than driving routes. Recognizability and spatial continuity matter more than survey accuracy or geometric precision.

## First goal
On a 2022 M2 MacBook Air (16 GB), transform a short original walking video into a locally reconstructed 3D scene and revisit it in a browser. Start with path-constrained movement and free look; unrestricted movement comes later.

## Current result: a recognizable short street on M2

The [final same-data quality attempt](docs/FINAL_QUALITY.md) produces a visible
improvement: fresh1024px crops from the original ERP photos and an800k Gaussian
ceiling, keeping the same DAV2 seed, cameras and8,000 steps. Actual M2 Metal
training/export takes1455.651s and produces73.6MB. In300 matched browser renders,
held-level mean RGB error improves27.751→24.414 at512 output and
27.992→24.345 at1024 output; all six held directions improve at either
resolution. Windows, railings and the route look sharper, but branches/nearby
objects still ghost and walls can double. **Retain the new1024 result as the
best observed on these nine panoramas; quality tuning on this dataset is now
closed.** Resolution and capacity changed together, so their individual effects
are not isolated. Independent geometry and unrestricted walking remain
unaccepted. [Open new3D](https://groundshift-viewer-production.up.railway.app/?world=/worlds/street-final-hires/world.json)
· [Actual comparisons and movement](https://groundshift-viewer-production.up.railway.app/experiments/final-quality/).

[The completed alternative-model comparison](docs/MODEL_SELECTION.md) executes
PanDA-Small, DA3-Small, MoGe-2 Small and DA² on the same street, with four new
8,000-step Metal exports and375 actual matched Chrome renders including the
existing DAV2 control. **No clear qualitative breakthrough: retain DAV2.**
MoGe has the lowest new held-view color error,27.587 versus27.751 (0.6% reduction),
but wall/foliage ghosting persists and the one-run difference is not established
as significant. All four new scenes, depth evidence, failures and movement
videos are on the [model report](https://groundshift-viewer-production.up.railway.app/experiments/model-selection/).


[Seven actual local reconstructions and the conclusion](docs/STREET_CONCLUSION.md)
extend the scooter method to a continuous short street. Eight physical centers
supply96 real512px crops; panorama5 RGB is withheld from GS optimization, while
all-nine estimated camera/SfM geometry is reused. No diffusion or generated
intermediate training images. All7 Metal exports and525 matched actual browser
renders complete. Recommend calibrated depth initialization +8,000 steps:
409.759s,400,000 Gaussians,36.8MB; held-level mean RGB error27.751 versus sparse8k
35.541. At the same16k/400k budget, dense28.911 versus sparse32.212; doubling
steps did not beat dense8k. This is a pipeline comparison, not proof of learned
depth accuracy. Thin structures ghost, walls double and independent geometry /
unrestricted walking remain unverified. [Open the comparison and recommended3D](https://groundshift-viewer-production.up.railway.app/experiments/street/).

## Previous experiment: a third real photo checks road consistency

The [executed third-view check](docs/ROAD_THIRD_VIEW.md) independently matches
real photos5/6 against frozen4/5 road tracks:44/291 (15.1%) are supported,247
remain unconfirmed. Supported angular disagreement is0.069° median. On39 common
valid depth predictions, adding road anchors reduces radial disagreement with
5/6 stereo from0.430% to0.384%; previous-held6 points improve0.507%→0.243%.
Small local evidence, jointly estimated cameras, no independent depth truth.
No new inference, pose fitting, fusion or GS. Full P2 geometry NOT ACCEPTED.
[Observation](https://groundshift-viewer-production.up.railway.app/experiments/road-third-view/).

## Previous experiment: observed road correspondences and calibration

The [executed correspondence experiment](docs/STEREO_ANCHORS.md) retains five
cloud controls and actual match overlays. SIFT alone left the road unsupported.
Diagnosing a too-small stereo search range and expanding256→512px recovered291
road candidates; combined calibration improves matched road4→5 disagreement
from2.43% to0.45%. The reverse direction changes little; facade/far-depth problems
remain, including invalid historical holdout predictions. No new model inference,
fusion or GS training. [Observation](https://groundshift-viewer-production.up.railway.app/experiments/stereo-anchors/).

## Previous experiment: dense perspective coverage and overlap

The [executed two-panorama perspective experiment](docs/PERSPECTIVE_OVERLAP.md)
adds twelve real downward crops to cover the road, reuses the existing level
predictions and compares four spherical point-cloud controls. DAV2 Small ran
locally on M2 MPS. On matched source samples, road depth disagreement improves,
but facade disagreement and the overall error tail worsen. Disagreement filtering
also removes substantial facade coverage. P2 geometry remains NOT ACCEPTED;
fusion and new Gaussian training remain NOT RUN. The
[observation page](https://groundshift-viewer-production.up.railway.app/experiments/perspective-overlap/)
retains raw versus filtered clouds and both viewing directions.

## Previous experiment: shared calibration and perspective-depth control

The [street roadmap](docs/PANORAMIC_STREET_RECONSTRUCTION_PLAN.md) now has an
[executed common-track calibration study](docs/PANORAMIC_CALIBRATION.md).
Using the same 784 calibration tracks did not resolve the two-panorama ERP
mismatch. An additional local MPS DAV2 control on 12 real perspective crops
reduced high-parallax withheld-feature median errors from about 7px to
2.2–2.6px. The report shows actual photo displacement vectors, controls and
matched-view calibration clouds. These are internal SfM comparisons; dense
perspective overlap was evaluated in the next bounded experiment above; fusion
and new Gaussian training remain NOT RUN.
The [pair diagnostic](docs/PANORAMIC_PAIR_P1.md), [one-panorama result](docs/PANORAMIC_DEPTH_P1.md),
best scooter and all earlier observations remain available.
[Model/license findings](docs/PANORAMIC_DEPTH_MODELS.md).

## Preserved experiments: one object along the panorama path

The latest [no-learned-depth trial](docs/OBJECT_NO_DEPTH.md) keeps those same nine
real training images and camera matrices byte-identical, and removes depth
prediction, calibration and fusion. It starts from 115 triangulated object points
and trains 5,000 steps in 116.339 s on M2 Metal. The result renders but is severely
blurred and stretched; both exports are published for observation. The
[comparison page](https://groundshift-viewer-production.up.railway.app/experiments/object-nodepth/)
uses the same display camera as the preceding result.

The preceding [real-only ablation](docs/OBJECT_REAL_ONLY.md) removes all 56
intermediate images, including both RIFE interpolation and diffusion. The same
nine real crops, original camera solution, depth model and training settings
produce a separately trained world in 160.298 s on M2 Metal. Its
[comparison page](https://groundshift-viewer-production.up.railway.app/experiments/object-real/)
shows both results. The original augmented experiment below remains available.

The preceding observation is a single parked scooter viewed from nine existing
panorama positions. Whole-frame diffusion adds intermediate image candidates;
relative depth is calibrated against neighboring features and fused into the
Gaussian initialization. The [experiment record](docs/OBJECT_FOCUS_EXPERIMENT.md)
tracks actual camera/depth rejections and the result-first release. The new
chronological laboratory links images, depth, point clouds and Gaussian worlds,
with newest-first and oldest-first sorting. The actual local run used 47 of 65
candidate images, accepted 34 depth maps and trained 5,000 steps on M2 Metal.
Both exports render in Chrome. The scooter is recognizable but blurred and
streaked; independent geometry and comparative quality remain unmeasured.

## Earlier experiments: public 360° sequences

The user-directed experiments use a small licensed Mapillary panorama
sequence. The first tested an observed-image Gaussian baseline and local
diffusion-assisted gap completion; see [MAPILLARY_EXPERIMENT.md](docs/MAPILLARY_EXPERIMENT.md).
The follow-up puts photos 4 and 6 at the ends of a 65-frame equirectangular
sequence and compares real-only versus generated-midpoint Gaussian training;
see [PANORAMA_VIDEO_EXPERIMENT.md](docs/PANORAMA_VIDEO_EXPERIMENT.md).
The [depth-guided follow-up](docs/DEPTH_WARP_EXPERIMENT.md) calibrated two
observed crops to SfM sparse points, projected their RGB into a middle camera,
filled remaining pixels locally on MPS and trained one additional Metal GS
world. It improved projected coverage but **failed** the matched two-direction
3D render comparison; the resulting scene and evidence remain in the catalog.
Plausible generated scenery now matters more than exact street fidelity.
Generated pixels remain hypotheses, not new camera-pose measurements. The
executed RIFE model is optical-flow interpolation, not video diffusion; the
larger LTX diffusion candidate did not reach inference on this Mac.
The original-video path and earlier public worlds remain available.
Actual fixed-rig SfM, Metal Gaussian training, local MPS inpainting and generated-
image retraining have executed. The Mapillary scenes are published as experiments: the new gap-filled world has
**not passed visual-quality acceptance**. That outcome does not prevent observation.

## Constraints
- Free and open-source tools; no paid API or cloud GPU.
- Optimize for Apple Silicon and Metal today, not hypothetical CUDA parity.
- Avoid coupling application code to a particular reconstruction engine. Preserve an input/job boundary and a portable world artifact for a future CUDA worker.
- Do not prematurely build cloud services, user accounts, GIS, social features or automatic scene stitching.
- No fabricated benchmarks, camera poses, collision geometry or hardware test results.

## Run the M0 viewer

Requires Node.js 24+ and a WebGL2-capable browser. The validation machine uses Node 25.6.1 and Chrome 156 on Apple M2.

For the complete observation gallery, first [restore the scene assets and previews from the pinned release](docs/DEPLOYMENT.md#restore-scene-assets-in-a-fresh-checkout). The catalog is tracked; generated assets are ignored. Then run:

```sh
npm ci
npm run dev
```

Open **http://127.0.0.1:4317** and select a scene card. The gallery loads previews; the 3D viewer starts only after selection. For a minimal Houseplant-only M0 check, `npm run sample` supplies that splat and `http://127.0.0.1:4317/?world=/worlds/sample/world.json` opens it directly; this does not restore the full gallery. Once inside a scene, drag to orbit, scroll or use the buttons to zoom, right-drag to pan, and use **Reset view** to return to the manifest camera. The Houseplant example is a real captured Gaussian scene, licensed CC-BY-4.0; its downloader pins and checks the exact asset. See [sample provenance](docs/SAMPLES.md).

To replace the scene, choose **Open world folder** and select a folder containing `world.json` and its asset. Nothing is uploaded. Alternatively put an artifact under `public/worlds/my-world/` and open `/?world=/worlds/my-world/world.json`. See the [world format](docs/WORLD_FORMAT.md) for explicit axes, transform, orbit camera and attribution. No floor, collision or safe walking spawn is inferred.

Worlds with camera metadata also offer **Camera path**: play/pause, forward/backward, speed, checkpoint jumps and free look. Playback stops at unverified gaps; it interpolates recorded views without inventing a walking surface. See [revisit behavior and actual browser evidence](docs/REVISIT.md).

The viewer uses React, TypeScript, Vite, Three.js 0.180.0 and Spark 2.4.0. Loading, download progress, missing or corrupt files, invalid manifests, and graphics-context loss have visible states. Scene switches cancel fetches and release rendering resources. Local development serves code and scenes from this Mac. The [Railway deployment](docs/DEPLOYMENT.md) hosts a curated static viewer; reconstruction remains local. Viewer changes, all authorized exported trials and sanitized experiment evidence are packaged and deployed in the same workflow under the user’s standing instruction, regardless of quality.

## Checks

```sh
npm run typecheck
npm run lint
npm test
npm run test:native
npm run build
npm run test:browser
```

Browser tests launch installed **Google Chrome with a visible window**, serve the production build on `127.0.0.1:4318`, and save screenshots/measurements in ignored `test-results/`. Restore the observation assets and previews above for the complete gallery suite. Optional native-scene checks are explicitly skipped when their artifacts are absent; `npm run sample` alone supplies only the original sample splat. `HEADLESS=1 npm run test:browser` is available for automation but is not equivalent to the recorded headed hardware result. Automated pixel checks are supplemented by actual screenshot inspection.

Current final-quality checks: TypeScript/lint/build, **166 JS tests**,
**233 distinct Python tests**, **75 distinct local browser cases with passing
evidence**, **7 targeted public Chrome cases**, **300 matched actual GS renders**
and **1,046 public file hashes** pass. The initial local video-seek failure,
failed paused-callback retry and successful actual-playback repair are retained.
The complete75-case public suite is NOT RUN. [Evidence and limits](docs/FINAL_QUALITY.md).

Earlier model-comparison checks: TypeScript/lint/build, **166 JS tests**, **224 distinct Python tests**, **71 distinct local browser cases with passing evidence**, **11 focused public Chrome checks**, and **1,019 matching public file hashes**. The full71 public suite was not completed; network-timeout evidence and the focused retry are recorded in [DEPLOYMENT.md](docs/DEPLOYMENT.md). Publication precedes post-deployment verification.

Earlier street release checks: TypeScript/lint/build, **166 JS tests**, **217 distinct Python passes** across required environments, **61 full headed Chrome cases**, then **11 street checks on the final layout**, and **20 public headed Chrome cases**. All29 scenes render locally; all7 new scenes also render on the public origin, whose827 packaged file hashes match. Hardware training is recorded separately in the [street result](docs/STREET_CONCLUSION.md); exact public-origin checks and release hashes are in [DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Native reconstruction (M1)

The first local reconstruction is working: **40 licensed images + supplied measured camera poses and sparse point initialization → Brush on M2 Metal → PLY → this viewer**. A 1,500-step run took 80.35 seconds and exported 194,789 Gaussians (17.92 MB). The actual result was visually inspected in Chrome. See [installation, dataset acquisition and exact commands](docs/M1.md).

The backend is a local Python process adapter; the portable output is a directory of scene, manifest, camera metadata and provenance. No server, database or GPU abstraction is involved. The follow-up [CPU PyCOLMAP path](docs/COLMAP.md) now registers **120/120 raw photographs**, using only supplied lens calibration. All camera positions and sparse points are newly estimated locally. A separate 3,000-step Metal run produced 75,397 Gaussians in 155.06 seconds, and its browser result was visually verified. [Independent reconstruction evidence](docs/INDEPENDENT_RECONSTRUCTION.md). The original 16/40 failure and supplied-pose result remain preserved separately.

**M0: PASS. M1: PASS for both the supplied-pose and newly estimated-pose samples.** The latter requires actual lens calibration; calibration-free fisheye reconstruction remains unvalidated. See [validation and remaining limitations](docs/VALIDATION.md) for hardware evidence, screenshots and separately marked PASS / FAIL / NOT RUN results. Image quality is an early prototype: the excavator and surroundings are recognizable, with soft peripheral geometry. Camera-path controls work on real sample poses; original walking-video acceptance remains **NOT RUN**.

## Local video/image pipeline

The first **user-recorded original video** now works locally: a 24.8-second
indoor capture produced 99/99 estimated cameras and a 28,496-Gaussian scene in
4 min 38 s, with actual browser rendering and path playback verified. No sample
model, supplied poses or calibrated lens values were used. The original footage and processing evidence remain private. The creator has
authorized public display of the derived desk scene and preview; the desk now
renders in the public observation catalog, with path playback verified. [Evidence and remaining
visual limits](docs/ORIGINAL_VIDEO.md).

After installing the native tools, run the new [local pipeline command](docs/PIPELINE.md):

```sh
python3 scripts/build-world.py /absolute/path/to/walk.mov data/jobs/my-walk \
  --duration 15 --fps 4 --max-edge 960 --title "My walk" --id my-walk
```

It prepares frames, estimates cameras on CPU, requires full registration by
default, trains with Brush on Metal, and writes a viewer-ready world. Logs and
failures are preserved. Video provenance can be supplied with `--provenance`;
otherwise the artifact explicitly records an unspecified license and local file
source. Image directories require provenance. This is an implemented workflow,
not a claim that arbitrary footage reconstructs successfully. The FFmpeg checks
initially used synthetic fixtures and a licensed photo slideshow; the later
original indoor capture validates the full command. Walking-route acceptance
and a second independent recording remain outstanding. Tagged phone HDR needs
the [HDR-capable local FFmpeg](docs/HDR_TOOL.md), selected through `--ffmpeg`;
unsupported HDR input fails explicitly. [Frame extraction evidence](docs/VIDEO.md).

## Documentation
- [Actual Paris GS,native LoD,failed proximity streaming and measurements](docs/PARIS_STREAMING.md)
- [Paris tourist source selection and bounded lazy-serving experiment](docs/TOURIST_STREAMING.md)
- [SPZ compression, actual size/appearance evidence and reproduction](docs/COMPRESSION.md)
- [Alternative-model execution, licensing, measurements and reproduction](docs/MODEL_SELECTION.md)
- [Short-street result, controls, measurements and reproduction](docs/STREET_CONCLUSION.md)
- [Panoramic street roadmap and current limits](docs/PANORAMIC_STREET_RECONSTRUCTION_PLAN.md)
- [Vision](docs/VISION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Milestones](docs/IMPLEMENTATION.md)
- [Measured validation](docs/VALIDATION.md)
- [Reconstruction provenance and rerun evidence](docs/RECONSTRUCTION_PROOF.md)
- [Independent camera and scene reconstruction](docs/INDEPENDENT_RECONSTRUCTION.md)
- [Local reconstruction](docs/M1.md)
- [Optional CPU camera estimation](docs/COLMAP.md)
- [One-command local pipeline](docs/PIPELINE.md)
- [Original video reconstruction](docs/ORIGINAL_VIDEO.md)
- [HDR-capable local FFmpeg](docs/HDR_TOOL.md)
- [Video preparation](docs/VIDEO.md)
- [Camera-path revisit](docs/REVISIT.md)
- [Portable world format](docs/WORLD_FORMAT.md)
- [Information and processing topology](docs/INFORMATION_TOPOLOGY.md)
- [Observation publication and reproduction](docs/OBSERVATIONS.md)
- [Railway deployment](docs/DEPLOYMENT.md)
- [Agent instructions](AGENTS.md)

Groundshift source license selection remains pending; third-party code and samples retain their respective licenses. Large assets, datasets, generated output and local tools are excluded from Git. Use original or appropriately licensed images and review privacy before publishing footage or scenes.
