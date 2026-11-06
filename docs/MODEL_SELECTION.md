# Street model selection — 2026-11-06

The user asks for a broad but economical model comparison before more data or
parameter tuning. Preserve the current `street-dense` result as the reference.
This is a model-family comparison, not an exhaustive grid search or an isolated
architecture benchmark. All reconstruction remains on the M2 / 16GB Mac.

## Declared procedure

1. Verify official source, checkpoint terms, inference semantics and dependencies.
2. Run two non5 physical panoramas (4 and6), or their existing perspective crops,
   as an actual MPS feasibility check. Keep failed attempts and repairs.
3. Expand viable candidates to the same eight non5 physical centers. Prefer
   distinct approaches: PanDA-Small and DA² spherical depth; MoGe-2 Small point
   geometry; DA3-Small pose-conditioned multi-view depth. Investigate DepthMaster
   as another spherical candidate if a small device adaptation suffices.
4. At most four new full Gaussian runs: one standard 8,000-step / 400k-ceiling
   Brush run per selected family. No resolution, crop-count, filter or optimizer
   grid. Reuse the same96 real512px RGB, masks, estimated cameras, 3,124 sparse
   anchors, seed42, SH1, voxel spacing and up-to180k added dense points.
5. Inspect actual same-camera renders and route motion. Reuse the existing75
   evaluation cameras and fixed appearance metrics, with panorama5 RGB excluded
   from inference/seed colors/GS training. All-nine SfM still supplies geometry;
   this is not independent geometric ground truth. New-view consistency and
   visible wall/rail artifacts matter alongside withheld RGB error.
6. Publish every actual export and failed/unexecuted candidate, preserve all old
   worlds, and choose the practical recommendation after reviewing results.

Screening calibration residuals are correlated SfM diagnostics, not a model
quality leaderboard. They can expose unusable conversions, but a smaller
residual alone does not prove better Gaussian appearance. DA² already has
executed two-panorama diagnostics; it need not receive a full training budget
if new candidates offer more information within the four-run bound.

## Depth and camera contracts

- PanDA: affine relative radial depth. Fit scale **and offset** per physical
  sphere, before sampling its rays into perspective crops.
- DA²: positive scale-relative radial range. Fit scale only per sphere.
- MoGe-2: camera-Z from its official point-map recovery, with actual90° FOV.
  Align scale per crop to arbitrary SfM units. Retain native mask as evidence;
  do not silently add a model-specific seed filter.
- DA3-Small: direct relative camera-Z. Process all non5 centers jointly for each
  of12 ring/yaw directions, conditioning on the existing real OpenCV w2c/K.
  Preserve one fitted scale per multi-view group. Do not replace recovered
  poses with the model's predicted cameras.
- Calibration uses original SfM and count-balanced observed non5 stereo points,
  retaining the original deterministic held-track split. Earlier four failed
  stereo rectifications remain explicitly excluded. No metric conversion.

Native implementations may differ in input resolution, parameter count, context
and calibration freedom. Those differences are part of the practical pipeline
comparison and must be reported rather than disguised as matched architecture.

## Reproduction and evidence

Work directory: `data/jobs/model-selection-20261106/`, never overwrite an old
attempt. The local `research/` holds pinned Git/Hub metadata, original model
cards, acquisition logs and verified checkpoint byte counts/SHA-256 values.
Original images, checkpoints, upstream code and raw logs remain outside Git.

```sh
# Same prepared RGB/cameras/anchors as the completed street experiment.
PYTORCH_ENABLE_MPS_FALLBACK=0 data/tools/diffusion-venv/bin/python \
  scripts/infer-street-model.py panda data/jobs/NEW/panda
data/tools/venv/bin/python scripts/seed-street-model.py data/jobs/NEW panda
```

Completed execution outcomes are recorded below; release verification is recorded separately.
An imported module, successful download or static test is not model execution.

## Upstream findings and actual selection

Pinned identities, checkpoint byte counts and SHA-256 values are in
[`street-models.json`](../scripts/samples/street-models.json). Published checkpoint
licenses were checked separately from repository licenses. No weights or
upstream code are redistributed. Their training-data rights are not blanket
commercial clearance; this run does not download or retrain on those datasets.

| Candidate | Source / checkpoint | Actual local path and selection |
|---|---|---|
| [PanDA-Small](https://github.com/caozidong/PanDA/tree/211e4cc391474176fe6949baebfeac61ada7e44c) | Apache-2.0 code and [weights](https://huggingface.co/ZidongC/PanDA/blob/f1790c6105aa12a387afa9c1279ad28efa20c069/README.md) | Existing `infer_image` MPS device selection,1008×504 ERP. Ignore only checkpoint `epoch` metadata, strict learned-weight load. Selected for GS. |
| [DA²](https://github.com/EnVision-Research/DA-2/tree/d659838585f2bc9967c7e9367af573795271dbbb) | Apache-2.0 code/weights; earlier dependency audit retained | Unchanged existing MPS core,1092×546 ERP. Selected as the fourth GS family after DepthMaster's license blocker. |
| [MoGe-2 Small](https://github.com/microsoft/MoGe/tree/74fbce054ebed49800de42d0ad0e83495065719a) | MIT code and [checkpoint](https://huggingface.co/Ruicheng/moge-2-vits-normal/blob/26b477f41595707c5db6770294c0d1721e8ed4ed/README.md); included DINOv2 Apache-2.0 | Explicit **v2** core,1600 tokens,actual90° FOV,FP32 MPS; upstream focal-shift solver uses CPU SciPy. No silent GPU-operator fallback. MoGe-3's Triton/FlexGEMM path is not installed. Selected for GS. |
| [DA3-Small](https://github.com/ByteDance-Seed/Depth-Anything-3/tree/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4) | Apache-2.0 code and [checkpoint](https://huggingface.co/depth-anything/DA3-SMALL/blob/e08cab65ca0ec38e7826075418411ab90cab4da3/README.md) | Unchanged core forward,504px,FP32 MPS. Bypass optional export/CUDA GS imports. Restore safetensors-omitted aliases only when parameters are the **same Python object**, then strict weight loading. Actual pose normalization and ImageNet preprocessing retained. Selected for GS. |
| [DepthMaster](https://github.com/PolyU-VCLab/DepthMaster/tree/b6a80836343438f63c1b55883a8e7da94e29e6bc) | Repository and checkpoint say MIT, but `mirror_vgt/` explicitly migrates WorldMirror code | Two518px×6-face predictions actually completed on MPS after a small FlashAttention-import guard; another run stopped after5/8 predictions. **Adoption BLOCKED; GS NOT RUN.** See dependency finding below. |

### Corrected dependency finding: DepthMaster

Initial repository/checkpoint MIT labels were insufficient. The model's
`mirror_vgt` files explicitly identify their WorldMirror origin. The original
[Notice](https://github.com/Tencent-Hunyuan/HunyuanWorld-Mirror/blob/main/Notice.txt)
and [License](https://github.com/Tencent-Hunyuan/HunyuanWorld-Mirror/blob/main/License.txt)
use the Tencent community agreement, with South Korea outside its licensed
territory. No separate permission covering the migrated code was established.
This is an unresolved rights chain, not a legal ruling that all DepthMaster
material has the same license. Under this project's FOSS requirement, stop
additional execution/adoption and do not redistribute its outputs/code/weights.

The actual successful two-image smoke evidence remains local. Full inference
was terminated with SIGTERM after5 predictions; its pre-cancellation report,
external stop timestamp, observed process exit, raw arrays and source wrapper
snapshot are retained. This is **CANCELLED for dependency review**, not an MPS
execution failure or a completed eight-panorama result. The shipping CLI and
acquisition command block further DepthMaster use. DA² takes the fourth native
training slot. Future permission clarification could reopen this candidate.

### Other approaches screened without new inference

- [InfiniSplat v2](https://github.com/zju3dv/InfiniSplat/blob/main/InfiniSplat_v2/INSTALL.md),
  [UniTriSplat](https://github.com/yipengzhu0809/UniTriSplat) and
  [GGPS/PanoLOG](https://github.com/Insta360-Research-Team/GGPS): official current
  paths require NVIDIA/CUDA; no Metal port undertaken. NOT RUN.
- [SHARP](https://github.com/apple-aiml-research/ml-sharp): official Gaussian
  prediction supports MPS (its video renderer needs CUDA). Its
  [model license](https://github.com/apple-aiml-research/ml-sharp/blob/main/LICENSE_MODEL)
  restricts use to noncommercial scientific research and excludes product
  development. It is not an unrestricted FOSS replacement; independent
  single-image splats also need a separate multi-view integration experiment.
  NOT RUN; not incorrectly labeled CUDA-only.
- Larger DA3 variants and MoGe-3 are not automatically interchangeable with the
  selected Small/v2 checkpoints. No size×resolution×training grid is run.

Relevant added dependencies: OpenCV5.0.0.93 (Apache-2.0), SciPy1.18.1 (BSD),
OmegaConf2.4.0 (BSD), Addict2.4.0 (MIT), pinned `utils3d_moge` (MIT), Torch and
torchvision (BSD), existing einops (MIT), Hugging Face Hub/safetensors
(Apache-2.0). No optional Gradio/server/training packages, xFormers, CUDA
Gaussian renderer, paid service or new account is installed. Current package
versions and source snapshots remain in the local research evidence.

## Run the selected comparison again

Prerequisites are the existing [street inputs and native Brush setup](STREET_CONCLUSION.md#reproduce-in-fresh-output-directories),
including the licensed nine original images, fixed-rig poses, recolored anchors
and observed stereo job. The Torch environment used Python3.12, Torch2.15.0,
torchvision0.29.2 and existing Transformers5.22.1. Do not install the upstream
all-in-one dependency lists: they pull unrelated CUDA/training/application code.

```sh
data/tools/diffusion-venv/bin/pip install \
  opencv-python-headless==5.0.0.93 scipy==1.18.1 omegaconf==2.4.0 addict==2.4.0
python3 scripts/acquire-street-models.py panda da3 moge \
  --research data/jobs/NEW/research
# DA² remains the already audited pinned acquisition in PANORAMIC_DEPTH_P1.md.

/Library/Developer/CommandLineTools/usr/bin/git clone \
  https://github.com/EasternJournalist/utils3d-moge.git data/tools/utils3d-moge
/Library/Developer/CommandLineTools/usr/bin/git -C data/tools/utils3d-moge \
  checkout --detach 62f09d58509485564e24d5d9f6aac9ee9ebc0c37
data/tools/diffusion-venv/bin/pip install --no-deps ./data/tools/utils3d-moge
```

Reuse an existing dependency checkout only after verifying its revision. The
acquisition command preserves existing files and rejects mismatched checkpoints,
revisions and blocked candidates. Its direct public downloads require no login.

The following is the executed workflow expressed with a fresh output name.
Model inference reads the unchanged earlier input images; the new job carries
byte-identical input/anchor copies for the seed/training/evaluation commands.

```sh
python3 - <<'PY'
from pathlib import Path
import shutil, subprocess, os
base=Path('data/jobs/street-conclusion-20261106')
job=Path('data/jobs/NEW')
for name in ['inputs','anchors-training-colors']:
    shutil.copytree(base/name,job/name)
(job/'datasets').mkdir()
env=dict(os.environ,PYTORCH_ENABLE_MPS_FALLBACK='0')
for name in ['panda','da3','moge','da2']:
    subprocess.run(['data/tools/diffusion-venv/bin/python',
        'scripts/infer-street-model.py',name,str(job/name),
        '--research',str(job/'research')],check=True,env=env)
    variant='panda-supported' if name=='panda' else name
    seed=['data/tools/venv/bin/python','scripts/seed-street-model.py',str(job),name]
    if name=='panda':
        seed+=['--variant',variant,'--proximity-floor','0.46721203379743004']
    subprocess.run(seed,check=True)
    subprocess.run(['data/tools/venv/bin/python','scripts/reconstruct.py',
        str(job/'datasets'/variant),str(job/('training-'+variant)),
        '--steps','8000','--resolution','512','--max-splats','400000',
        '--title','Street model '+variant,'--id','street-model-'+variant],check=True)
# Reuse the previous actual export explicitly, without claiming a new training.
(job/'training-dav2').symlink_to((base/'training-dense').resolve(),target_is_directory=True)
PY
node scripts/prepare-street-evaluation.mjs data/jobs/NEW dav2 da3 moge da2 panda-supported
node scripts/render-street.mjs data/jobs/NEW/render-config.json data/jobs/NEW/renders
data/tools/venv/bin/python scripts/measure-street.py \
  data/jobs/NEW data/jobs/NEW/renders data/jobs/NEW/evaluation --baseline-model dav2
```

Use a desktop session with Chrome for the actual headed renderer. Review the
matched frames and motion before authoring a new `decision.json`. The publisher
is a one-time catalog append and refuses existing experiment/world destinations:

```sh
data/tools/venv/bin/python scripts/publish-model-selection.py \
  data/jobs/NEW --decision data/jobs/NEW/decision.json
```

The recorded experiment is never overwritten by these instructions. Native
training logs, failed attempts and runtime counters belong in each new job.

## Bounded PanDA repair

The first PanDA8k training was intentionally cancelled after **1320.265s** with
no final export. The original native terminal report (exit failure after our
SIGTERM) is retained alongside its explicit external-cancellation classification.
Actual process sampling found `SplatTrainer::step` / Metal submission and a
1.1GB current /1.2GB peak process footprint; a separate whole-GPU sample was84%
busy. AC power, low-power mode off, no recorded macOS thermal warning. These
observations do not give an iteration count or establish the slowdown's cause.

A concrete candidate pathology: the PanDA seed has172 points within0.1 SfM
units of an estimated camera, minimum0.0011; the baseline minimum is0.9344,
and the other selected seeds have no points within0.1. Extremely close points
can project to large splats; this is a **hypothesis**, not a proved kernel profile.

One repair was declared before another training: exclude dense candidates closer
to a training camera than **0.4672120338 SfM units**, half the observed baseline
minimum. Keep the same raw model, calibration, voxel spacing,180k dense sample
budget and3,124 sparse points. This is a numerical stability heuristic, not a
measured collision/free-space boundary. Preserve unmodified seeds and all failed
evidence; do not search floor values. DA3/MoGe/DA² proceed first. The repaired
variant is `panda-supported` and is disclosed as a pipeline repair, not a pure
model-only comparison. No completed8k model is discarded.

```sh
data/tools/venv/bin/python scripts/seed-street-model.py data/jobs/NEW panda \
  --variant panda-supported --proximity-floor 0.46721203379743004
```

Use the resulting `datasets/panda-supported` and a **new** native output folder.
The four-full-run bound remains; the cancelled attempt is separately accounted.

### Runtime confound found during the queue

At approximately10:40–10:44 UTC, CUA inspected this conversation's retained
Groundshift IAB pages. Seven pages had a canvas and reported `visibility=visible`,
including an older street viewer displaying56fps and several old point-cloud
reports. They were navigated to existing static reports/lab pages; zero canvas /
iframe counts were verified. No other application or unrelated browser tab was
changed. Source results remain intact and reachable.

These concurrent views are a plausible common GPU-contention source. Whole-GPU
utilization is not a per-process profile, and no matched isolated timing trial
was performed. In particular, do **not** infer that the original PanDA slowdown
was caused solely by close seeds, or rank models by these mixed-condition wall
times. The numerical repair remains disclosed separately. Quality comparisons
use the same saved cameras; runtime observations remain real but uncontrolled.


## Executed result and decision

**Four actual new GS exports; no clear qualitative breakthrough. Keep the existing
DAV2 pipeline as the incumbent. MoGe-2 Small is the most promising new candidate.**
The claim is about this fixed short-street input and these practical pipelines,
not a universal ranking of the models or all their possible settings.

| Pipeline | Full inference including load | Actual native8k time | Held-level MAE ↓ | Views better than DAV2 | Alpha≥.95 coverage |
|---|---:|---:|---:|---:|---:|
| DAV2 incumbent, reused export | Prior run12.924s; NOT RUN again | Prior409.759s | 27.750556 | — | 22.463% |
| DA3-Small | 66.516s /96 crops,12 joint groups | 1367.028s | 28.530537 | 2/6 | 19.353% |
| MoGe-2 Small | 142.559s /96 crops | 508.599s | 27.586708 | 4/6 | 20.973% |
| DA² | 83.619s /8 ERP | 451.129s | 28.109868 | 1/6 | 23.074% |
| PanDA-Small, repaired seeds | 16.610s /8 ERP | 453.772s | 29.911612 | 0/6 | 33.294% |

All four native exports contain400,000 Gaussians,36,800,652 bytes. Initial seeds
are183,124 points each. Native maximum recorded process footprints are
1.295–1.299GB; these are process counters, not all-GPU/system memory peaks.
The completed new native runs consumed2780.529s in total, plus1320.265s for the
cancelled original PanDA attempt. Timing includes the GPU-contention confound
above; do not interpret the table as controlled model-speed rankings.

Headed Chrome156.0.8078.81 reports `ANGLE Metal Renderer: Apple M2` and actually
renders **375 views in87.666s**:75 views for each of five models. Every model has
12 withheld-camera views,12 training-camera views,49 interpolated route frames
and2 off-path views. Six actual49-frame videos (five individual,one comparison)
were encoded at6fps; this playback rate is not measured viewer FPS. Appearance
measurement and encoding took15.129s. Checksum-linked raw render, native and
measurement reports remain in `data/jobs/model-selection-20261106/`.

Visual review compared all30 withheld horizontal frames,35 sampled route frames
and10 off-path frames in labeled contact sheets. The recognizable path, trees,
parked scooters and facade persist in each model, but elongated foliage,
ghosting around thin rails and doubled facade details remain. MoGe can look a
little cleaner in some directions; it does not visibly eliminate these defects.
PanDA fills more high-alpha pixels while worsening all six held color errors:
more opacity is not more accurate geometry. Off-path photographs are unavailable,
so those views have no reference-image accuracy claim.

MoGe reduces mean error by0.163849/255, **0.5904%** relative, with1.490 percentage
points lower alpha-threshold coverage. It passes the existing appearance screen
(at least3/6 directions improve and coverage drops no more than5 points), but
that screen is not geometric acceptance or statistical significance. Each
pipeline has one actual seed42 training run. No repeated-seed confidence estimate
was run. Do not replace the incumbent based on this tiny numerical difference.

The useful conclusion is that **changing among these four depth families alone
does not establish a large gain at the current camera/GS budget**. It does not
rule out a better model or an integrated geometry/training engine. Preserve
MoGe as one next candidate; avoid an exhaustive model-size/resolution grid.
A next useful bounded question is whether it maintains a single stable wall,
road and tree structure across neighboring centers, with actual cross-view
surface evidence. Simply extending these same8k runs or increasing opacity
is not evidence that the street geometry works.

## Validation and observation release

- PASS: MPS inference for all four selected models; Metal training/export for
  all four;375 actual headed Chrome renders; six encoded path-video exports
  and actual comparison-video decode/playback in the browser.
- FAIL, corrected: the two strict-checkpoint-loading smoke attempts described
  above. Failed outputs/logs remain alongside corrected executions.
- CANCELLED: original PanDA training and full DepthMaster inference, for the
  distinct reasons above. Neither is relabeled a completed export.
- PASS:166 distinct JS tests;224 distinct Python tests across required
  environments, including actual HDR conversion, spherical/depth contracts,
  rigid-frame proximity invariance and blocked-candidate behavior. An initial
  test discovery included an ignored archived checkout twice; current Vitest
  discovery is scoped to current source/tests. Skips in one Python environment
  are executed in the other, with exact per-test union evidence retained.
- PASS: TypeScript, lint and production build. All71 distinct local headed
  browser cases have passing evidence: the full initial suite passed70/71 in
  4.6min; one old-scene reload received404 while our concurrent packaging build
  temporarily replaced `dist/`. Serialize build/test, preserve the failure and
  rerun that case plus all six new/strengthened cases:7/7 PASS in22.5s. The final
  change also routes each new scene's history link to its correct model report.
  New cases exercise actual image/depth loading, video decode/playback,
  four real GS renders/route movement, mobile layout and explicit503 recovery.
- PASS: all103 frozen baseline file hashes remain unchanged.
- PASS after publication:11 focused public Chrome cases, including all four
  new real GS renders/path movement, decoded video/depth and33 gallery previews.
  A full public71-case run is NOT RUN to completion; its network timeout and
  focused retry are preserved in [DEPLOYMENT.md](DEPLOYMENT.md). Static tests are
  distinct from model execution and actual GS browser rendering.
- NOT RUN: independent measured geometry, repeated-seed significance, collision
  surfaces, unrestricted-walking acceptance, CUDA engine inference and model
  size/resolution grids. P2 geometry remains NOT ACCEPTED.

The new report preserves every export, candidate status, failed stage, actual
runtime, raw depth visualization and initialization PLY. The unmodified PanDA
initialization is a diagnostic download; the repaired initialization is linked
from its actual GS card. DepthMaster predictions/code/weights are excluded from
publication. Earlier worlds, report datasets and immutable releases remain.
