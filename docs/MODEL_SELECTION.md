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

Actual execution outcomes and public-release evidence will be appended below.
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
    subprocess.run(['data/tools/venv/bin/python','scripts/seed-street-model.py',
        str(job),name],check=True)
    subprocess.run(['data/tools/venv/bin/python','scripts/reconstruct.py',
        str(job/'datasets'/name),str(job/('training-'+name)),
        '--steps','8000','--resolution','512','--max-splats','400000',
        '--title','Street model '+name,'--id','street-model-'+name],check=True)
# Reuse the previous actual export explicitly, without claiming a new training.
(job/'training-dav2').symlink_to((base/'training-dense').resolve(),target_is_directory=True)
PY
node scripts/prepare-street-evaluation.mjs data/jobs/NEW dav2 panda da3 moge da2
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
