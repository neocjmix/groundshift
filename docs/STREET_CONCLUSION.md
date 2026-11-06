# Short-street reconstruction: end-to-end result

2026-11-06. **A recognizable short street along the recovered route is feasible
on this M2.** Seven local Gaussian worlds and525 actual matched camera renders
complete. Recommend calibrated dense initialization +8,000 Metal steps: the
lowest observed mean withheld-view RGB error. Thin structures and off-route
stability remain limited; globally accurate full-sphere geometry is unproven.
[Railway release and public verification](DEPLOYMENT.md) PASS. Existing scooter/panorama experiments
and their immutable release remain preserved.

## Question and scope

Can the strongest scooter recipe make a continuous, recognizable short street
on the M2 MacBook Air16GB? The user asked to continue to an actual product
conclusion and publish every result, rather than stop after each local diagnostic.
This run therefore executes diagnostic Gaussian training despite the previous
P2 geometry gate being **NOT ACCEPTED**. It does not relabel that gate as passed.

The actual input is nine consecutive licensed360° photographs, not a downloaded
example GS. Their original7680×3840 bytes and jointly estimated fixed-rig camera
poses are reused. Eight physical centers train96 real512×512 pinhole crops:
six horizontal and six pitch−30° crops per center,90° FOV,60° yaw spacing.
Additional crops provide angular coverage, not additional camera baselines.
Physical panorama5 RGB is excluded from GS optimization and all seed colors.
Its camera and sparse geometry still come from all-nine SfM, so this is an
**appearance withholding comparison, not independent geometry ground truth**.
No diffusion or generated intermediate training photographs are used.

The camera positions, depth and point clouds remain in arbitrary SfM units.
DAV2's relative inverse-depth-like predictions are fitted to inverse camera-Z;
`Z=1/(a*prediction+b)`. Only positive finite fitted values contribute.
Pinhole camera-Z is converted through its ray to shared-world XYZ; spherical
consistency uses radial ray range. None of these values is labeled meters.
The portable world applies one documented display rotation to estimated
camera-up; it is not measured gravity. Camera-path interpolation is a viewer
control, not a reconstructed collision surface or a safe walking route.

## Executed stages and failures

- **PASS:** preserved all103 pinned scooter/source/implementation files. The
  initial protocol and original stereo implementation snapshots remain locally
  hash-verified; follow-up decisions are separate from that original protocol.
- **FAIL, corrected before training:** original COLMAP point colors could
  average in panorama5. Those colors were rejected. All variants use the same
  3,124 XYZ points recolored from actual non5 observed pixels, with nonzero-baseline
  support in at least two non5 physical centers. Geometry still uses all-nine SfM.
- **PASS:** pinned Depth Anything V2 Small executed96 predictions on local MPS
  in **12.924s**, including model load. This is one cached-weight run, not an
  installation/download benchmark. All96 inverse-camera-Z fits completed.
  Across crops, median held-anchor median absolute-relative error is **6.76%**;
  median held-anchor P90 is **25.42%**. These are correlated estimated-SfM checks,
  not independently measured depth accuracy.
- **FAIL, partial evidence explicitly retained:** CPU SGBM matching across seven
  non5 physical-neighbor pairs ×12 crop directions completed80/84 groups and
  produced96,667 observed triangulations in **31.437s**. Four rectifications
  (2/3 and8/9, level120°/300°) hit the epipolar horizon and stay failed/excluded.
  The first CLI mistakenly returned0 while the JSON correctly said FAIL; the
  retained executed-source snapshot proves that version. The current CLI returns
  failure. Fusion requires explicit `--allow-partial-stereo`; no thresholds were
  silently relaxed. Calibration uses count-balanced training stereo observations
  and original SfM anchors. Deterministic20% track IDs are excluded from fitting;
  this split is a calibration diagnostic, not independent geometry or a separate
  held-out point-cloud-training benchmark.
- **PASS, geometric quality NOT ACCEPTED:** initial depth candidates use ERP
  v=.40–.85, positive finite fits, per-center training-SfM P99 range caps and a
  voxel size of **0.0114016386 SfM units**, median adjacent baseline/120.
  This deliberately leaves the upper sphere unsupported. Known nadir v>.85 is
  ignored with official Brush masks in every run. Dense seeds keep180,000
  deterministic voxel samples plus3,124 shared sparse points.
- **PASS, procedural follow-up:** one primary crop is selected by angular
  centrality for every physical sphere ray before looking at depth. An invalid
  primary stays unsupported. Other-center tests then compare against one radial
  map per center, rather than accepting any overlapping crop. This reduces the
  dense voxel cloud from millions of overlapping samples to451,035; it does not
  independently establish surface truth or improve the appearance result here.
  Within the same physical sphere,29.14–36.02% of overlapping valid ray samples
  differ by more than10% across crop predictions. That is evidence of inconsistent
  estimated depth, not an independently measured error rate. Gaussian RGB fitting
  can hide some such inconsistency without making the underlying geometry true.
  All initial controls remain available.

## Matched native reconstructions

Same real RGB, camera matrices, masks, SH1, seed42,512 resolution and400,000
Gaussian ceiling. Inputs and seed sizes differ as stated. Total-step-dependent
optimizer schedules also change in16k runs; these are fresh runs, not resumes.
A final splat ceiling alone does not guarantee identical learned model capacity.

| Initialization | Seed points | Final Gaussians | Steps | Actual native time | Photo5 level MAE | Alpha≥.95 coverage |
|---|---:|---:|---:|---:|---:|---:|
| Sparse SfM | 3,124 | 112,080 | 8,000 | 216.811s | 35.541 | 11.784% |
| Calibrated crop depth, concatenate | 183,124 | 400,000 | 8,000 | 409.759s | 27.751 | 22.463% |
| Crop depth + other-center filter | 183,124 | 400,000 | 8,000 | 424.402s | 28.019 | 19.918% |
| Observed RGB stereo, no learned-depth seed | 99,230 | 400,000 | 8,000 | 418.133s | 28.450 | 15.592% |
| One depth per sphere ray + filter | 183,124 | 400,000 | 8,000 | 399.388s | 28.624 | 17.713% |
| Calibrated crop depth, longer budget | 183,124 | 400,000 | 16,000 | 868.068s | 28.911 | 20.671% |
| Sparse SfM, longer budget | 3,124 | 400,000 | 16,000 | 730.919s | 32.212 | 13.810% |

Exact native times, file sizes/hashes and macOS resource counters are retained in
each `training-*/job.json`, `training.log`, `resources.txt`; the public summary
includes sanitized counters and adapter evidence. All actual logs identify
**Apple M2 / Metal**. An8k400,000-splat export is36,800,652 bytes; sparse is
10,312,012 bytes. Recorded peak process footprint for the first four trials is
1,047,855,944–1,305,330,624 bytes. This is neither total system nor all-GPU peak
memory. Some CPU/report preparation overlapped training; thermal state was not
controlled. These are single executions, not controlled benchmark results.

The initial sparse run ended with112k splats while the other methods reached
400k. To avoid attributing an under-trained/smaller baseline entirely to depth,
the most promising dense method and the sparse control both run16,000 steps.
Both actually finish at400,000 Gaussians. Dense initialization improves4/6 held
level directions over sparse16k, mean MAE32.212→28.911, with6.86 percentage
points higher alpha-threshold coverage. This removes the smaller final model
and shorter training-budget explanation in this comparison, but initial point
count/type still differ; it does not isolate learned-depth accuracy.

**More steps did not improve the best observed result.** Dense16k is worse on
mean held appearance than dense8k (27.751→28.911), despite taking868.068s instead
of409.759s. Sparse16k improves over sparse8k, yet remains worse on this mean than
dense8k. Cross-view filtering and one-depth-per-sphere selection also did not
improve the best mean. Choose the simple dense8k pipeline for this dataset;
do not continue an unlimited step/filter search. Optimizer/refinement schedules
depend on total steps, so the8k→16k comparison does not isolate overfitting as
the cause. All controls and counterexamples remain inspectable.

## Rendering and interpretation

Each model is actually rendered with headed Chrome/Spark at the same75 cameras:
12 withheld-photo5 directions,12 training-photo4/6 directions,49 route frames
and two deliberate off-path cameras (±quarter estimated median baseline).
Route poses interpolate actual recovered centers/orientations and do not add
training photographs. The actual rendered movies are encoded at6fps; that
number is **not measured browser rendering FPS**.

MAE is decoded sRGB difference on fixed ERP-derived angular bands, including
holes composited on127 gray. The denominator is unchanged per view across
models; it does not discard low-opacity pixels to improve a score. Coverage is
the fraction with alpha≥.95, not independently measured visibility or coverage
of accurate geometry. RGB reference/camera participation is disclosed above.
The declared comparative appearance screen is lower MAE in at least3/6 held
level directions without a mean alpha-coverage drop greater than5 percentage
points. All four8k additions improve **6/6 directions** relative to sparse8k.
This passes the comparison screen; it does not approve P2 geometry.

Actual matched images and interpolated-path contact sheets show recognizable
building entrances, paving, trees and parked bicycles. Dense/stereo controls
resolve more detail than sparse8k. Rails/branches ghost, walls can double and
some areas stretch. A plausible image alone does not establish correct surface
positions or stable unrestricted free walking. Limited lateral displays have no
photographic reference; their accuracy is **NOT RUN**.

## Models, interfaces and licensing

Retain the actually working Apple-native backend. Upstream inspection is not
an execution or output-quality comparison of alternative engines.

| Candidate | Authoritative upstream finding | This run |
|---|---|---|
| [Brush0.3.0](https://github.com/ArthurBrussee/brush/releases/tag/v0.3.0) | Latest published release verified2026-11-06; Apache-2.0; actual local CLI/export already pinned. Official tagged importer supports `masks/<same-stem>.png`, white participates, black ignored. Training multiplies image error by the mask; ignored RGB is not forced transparent. | Native M2 Metal PASS |
| [DAV2 Small checkpoint](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf/tree/5426e4f0f36572d16453bbda7a8389317b1bef99) | Apache-2.0 pinned Small checkpoint; existing PyTorch/Transformers MPS environment. Larger checkpoints have different terms; not substituted. | MPS inference PASS |
| [InfiniSplat v2 installation](https://github.com/zju3dv/InfiniSplat/blob/main/InfiniSplat_v2/INSTALL.md), [license](https://github.com/zju3dv/InfiniSplat/blob/main/LICENSE) | Official path requires NVIDIA/CUDA; no documented MPS path. PRL v1 permits personal/evaluation without registration; organizational projects require registration. Checkpoint/dependency clearance incomplete because not adopted. | NOT RUN |
| [UniTriSplat](https://github.com/yipengzhu0809/UniTriSplat) | NVIDIA/CUDA extensions; no documented Metal backend. Original material MIT, derived3DGS files retain separate license, other dependencies separate. | NOT RUN |
| [GGPS](https://github.com/Insta360-Research-Team/GGPS) | CUDA toolkit/native CUDA submodules; no documented MPS training. Repository CC BY-NC4.0; checkpoint terms need separate clearance before adoption. | NOT RUN |

[Earlier model findings](PANORAMIC_DEPTH_MODELS.md) preserve PanDA/DA² license and
interface investigations. [Earlier ERP execution](PANORAMIC_DEPTH_P1.md) ran DA²
and the DAV2 ERP control; PanDA inference remains NOT RUN. This run actually uses
DAV2 Small perspective predictions, without silently substituting models.
Current upstream source snapshots and compatibility notes remain in
`data/jobs/street-conclusion-20261106/research/`. No CUDA port, hosted inference,
paid API, new account/service, engine registration or new framework was introduced.

Original photographs: **Cicero101 / Mapillary via Wikimedia Commons, CC BY-SA4.0**.
All nine source URLs, source hashes and acquisition metadata are in
`scripts/samples/mapillary-beijing.json`; acquire with
`scripts/fetch-mapillary-sample.py --help` and follow its existing reproducible
workflow. Release crops, visualizations, reconstructed worlds and rendered
movies identify the source and modifications. Originals/private footage,
checkpoints and raw job logs remain local and outside Git/release.

## Reproduce in fresh output directories

Prerequisites: [native setup](M1.md), [fixed-rig source/camera workflow](MAPILLARY_EXPERIMENT.md)
and [P0 baseline](PANORAMIC_DEPTH_P1.md). Actual installed versions: NumPy2.5.4,
Pillow13.0.0, OpenCV-headless5.0.0.93; separate Python3.12/PyCOLMAP4.2.1;
Torch2.15.0 MPS/Transformers5.22.1 in the existing depth environment.
Scripts validate hashes and refuse to overwrite previous jobs.
Set `GS_JOB` to a new directory; do not reuse this run's path.

```sh
GS_JOB=data/jobs/street-reproduction
mkdir "$GS_JOB"
data/tools/venv/bin/python scripts/prepare-street.py inputs "$GS_JOB/inputs"
data/tools/colmap-venv/bin/python scripts/prepare-street.py anchors "$GS_JOB/anchors-training-colors"
# Pass the exact96 training paths as separate argv values, never evaluation RGB.
HF_HOME="$PWD/data/tools/depth-hf-cache" data/tools/diffusion-venv/bin/python - "$GS_JOB" <<'PY'
import json,sys,subprocess
from pathlib import Path
p=Path(sys.argv[1])
subprocess.run([sys.executable,'scripts/infer-relative-depth.py',str(p/'depth'),
               *json.loads((p/'inputs/inference-inputs.json').read_text())],check=True)
PY
data/tools/venv/bin/python scripts/reconstruct-street.py baseline "$GS_JOB"
# Exit1 is expected only if the JSON records failed groups: inspect, do not hide.
data/tools/venv/bin/python scripts/stereo-street.py "$GS_JOB" "$GS_JOB/stereo"
data/tools/venv/bin/python scripts/reconstruct-street.py fusion "$GS_JOB" \
  --stereo "$GS_JOB/stereo" --allow-partial-stereo
data/tools/venv/bin/python scripts/fuse-street-sphere.py "$GS_JOB"
data/tools/venv/bin/python scripts/run-street-training.py "$GS_JOB" sparse dense filtered stereo
node scripts/prepare-street-evaluation.mjs "$GS_JOB"
node scripts/render-street.mjs "$GS_JOB/render-config.json" "$GS_JOB/renders"
data/tools/venv/bin/python scripts/measure-street.py "$GS_JOB" "$GS_JOB/renders" "$GS_JOB/evaluation"
data/tools/venv/bin/python scripts/run-street-training.py "$GS_JOB" sphere --series-name=-sphere
node scripts/prepare-street-evaluation.mjs "$GS_JOB" sphere --name render-config-sphere.json
node scripts/render-street.mjs "$GS_JOB/render-config-sphere.json" "$GS_JOB/renders-sphere"
data/tools/venv/bin/python scripts/measure-street.py "$GS_JOB" "$GS_JOB/renders-sphere" "$GS_JOB/evaluation-sphere" \
  --config "$GS_JOB/render-config-sphere.json" --reference-metrics "$GS_JOB/evaluation/view-metrics.json"
data/tools/venv/bin/python scripts/run-street-training.py "$GS_JOB" dense sparse --steps 16000 --suffix=-long
node scripts/prepare-street-evaluation.mjs "$GS_JOB" dense-long sparse-long --name render-config-long.json
node scripts/render-street.mjs "$GS_JOB/render-config-long.json" "$GS_JOB/renders-long"
data/tools/venv/bin/python scripts/measure-street.py "$GS_JOB" "$GS_JOB/renders-long" "$GS_JOB/evaluation-long" \
  --config "$GS_JOB/render-config-long.json" --baseline-model sparse-long
```

The exporter/importer boundary remains a filesystem dataset/job
and versioned portable world; GPU internals are not abstracted. Existing source
acquisition/rig estimation are prerequisites, not re-executed timings in this run.

`publish-street.py JOB --decision decision.json` publishes a reviewed conclusion
from these completed renders. It is intentionally a one-time append to the
existing local observation catalog, retaining every previous world. The decision
contains `completedAt`, actual `best`, per-model `modelQuality`, `repair`, and
`verdict` (`state/title/summary/works/limits/recommendation`). Do not invent a
verdict from process exit status. Publish after reviewing actual matched images
and motion. Pack with the existing explicit observation allowlist.

## Validation

**PASS:** TypeScript, lint,166 JS tests. Python217 tests discovered in each of
two complementary environments: OpenCV215 pass/2 PyCOLMAP skips; PyCOLMAP188
pass/29 OpenCV skips; **217 distinct tests pass in their required environment**.
All three HDR checks actually ran with the existing custom FFmpeg9 binary with
zscale+tonemap; Homebrew8.0.1 lacks zscale and would skip them. New tests cover
rigid coordinate projection, radial/camera-Z conversion, deterministic splits,
voxel aggregation, real-center depth/color support, explicit partial-stereo
failure handling, photometry/opacity and unchanged hole denominators. Existing
sphere/seam tests remain included. Synthetic tests are distinct from native
scene/model/render execution.

All seven native exports and actual75-view render batches **PASS**, using headed
Chrome156 / ANGLE Metal Apple M2. Qualitative review sampled matched, interpolated
and off-path frames of every model; it does not approve every surface in every
frame. All61 production-browser regression cases PASS in240.066s, including all29
actual gallery scenes and previous reports. After moving the recommended3D
button above the long explanation, all11 street cases PASS again in57.6s on
the final build, including the initial viewport CTA, actual video decode/seek,
reference/metric selectors, mobile, on-demand3D and all7 actual route renders.
The explicit503 scenario is a labeled fixture. All827 public file hashes match
in274.268s and all20 targeted public headed Chrome checks PASS in227.532s,
including actual rendering of all7 new models. All seven public screenshots,
the report and sampled rendered motion frames were inspected; thin branches /
rails visibly streak and walls can double. The full61-case public suite is
NOT RUN (the full suite passed locally). [Release evidence](evidence/street-release.json)
and [actual public viewport](evidence/street-public.jpg) supplement the
[native measurements](evidence/street-conclusion.json). The public report is
[/experiments/street/](https://groundshift-viewer-production.up.railway.app/experiments/street/).

A fresh tracked-source0801d91 checkout and the immutable archive, isolated
`npm ci --offline` (201 packages), build and package reproduce all830 staged
file hashes exactly. Development HTTP smoke also serves the tracked HTML,
transformed source module and matching summary after removing compiled copies
of all tracked Vite entries. That smoke is not a new GPU operation. Original
camera estimation and depth/training are not repeated by display restoration.
Independent surveyed geometry, collision/free-walk quality, different datasets,
longer street blocks and alternative CUDA engines are **NOT RUN**.

The first packaging attempt FAILed a privacy preflight: ASCII-escaped Korean
after `Quality:` matched the Windows-drive-path heuristic. Whitespace was added
in curated notes, the failure log/original candidate retained, and the package
rebuilt. The privacy guard and all native outputs stayed unchanged. The final827-file archive
passes full readback and retains524 prior world/report data hashes.
The historical Mapillary report test now compares its frozen16-scene release
set to its own stored summary, then verifies those links remain in the current
catalog; the expanded29-scene catalog and43-entry lab are tested separately.
