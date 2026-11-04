# Mapillary panorama and diffusion experiment

The user redirected the next experiment from an iOS capture app to dense public
360° sequences, filling missing viewpoints with diffusion and using them for
Gaussian reconstruction. Computation stays on the M2 Air / 16 GB. No paid API,
hosted GPU, new account, or cloud reconstruction service is used.

Validation host: **Mac14,2 / Apple M2 / 17,179,869,184 bytes unified memory**,
macOS **26.6.2 (25G83)**. Native execution occurred on 2026-11-05 KST. Timing
reports use UTC timestamps; local clock time is nine hours ahead.

## Actual source

Nine consecutive **7680 × 3840** JPEG panoramas by **Cicero101**, from Mapillary
sequence `m4ks1Y6pR3fcIjBz9wXxWt`, publicly redistributed in this
[Wikimedia Commons category](https://commons.wikimedia.org/wiki/Category:Photographs_of_Beijing_from_Mapillary_(m4ks1Y6pR3fcIjBz9wXxWt)).
The capture is a Beijing residential courtyard/walkway on 2025-05-27,
05:11:05–05:11:13, one photograph per second. The source does not specify the
timestamp timezone. These are real captured panoramas, not generated samples.
They occupy **34,937,629 bytes**, verified against upstream SHA-1/size and pinned
SHA-256. Full image-level credits and immutable hashes are in
[`scripts/samples/mapillary-beijing.json`](../scripts/samples/mapillary-beijing.json).

The first 24 inspected candidates have approximate GPS inter-image distances
1.36–1.45 m (median 1.447 m). This is **not a globally densest-region result**,
survey accuracy, or a measured full camera pose. Nine selected images span about
11.3 m according to GPS. Visual inspection shows building facades, trees, parked
bikes and scooters; foliage, passing people and panorama stitching remain risks.
The yellow camera/nadir band is excluded by the horizontal 90° crops.

Source license is **CC-BY-SA-4.0**, confirmed on the actual file pages and
[Mapillary's official license explanation](https://help.mapillary.com/hc/en-us/articles/115001770409-CC-BY-SA-license-for-open-data).
Keep photographer and per-image links, mark modifications, and retain applicable
ShareAlike terms for derived imagery/worlds. Raw images stay ignored by Git and
are not part of the viewer release. The source license is not inferred from a
software repository's license.

Direct Graph API access without a token returned `Invalid OAuth 2.0 Access Token`.
The official developer page also required login. Commons provides an openly
published copy without borrowing credentials. The initial 12-image download
hit HTTP 429 after nine originals. It stopped, retained the failure, and the
accepted sample was explicitly reduced to the nine cached verified originals.
No alternate host or token was used to evade throttling. Cached reruns work
without requests; fresh downloads can still encounter source rate limits.

## Reproduce acquisition and projection

```sh
python3 scripts/fetch-mapillary-sample.py data/samples/mapillary-beijing
data/tools/venv/bin/python scripts/prepare-panoramas.py \
  data/samples/mapillary-beijing/images data/jobs/mapillary-beijing-crops \
  --provenance data/samples/mapillary-beijing/provenance.json
```

The existing image-preparation environment contains NumPy 2.5.4 and OpenCV
5.0.0.93; installation is documented in [M1.md](M1.md). Projection is mathematical
resampling, **not diffusion**. Each panorama supplies six overlapping 512²
pinhole views at yaw 0/60/120/180/240/300°, pitch 0°, 90° horizontal field of
view. Intrinsics are exactly `fx=fy=cx=cy=256` under the documented pixel-center
convention. The result is 54 images; crop-relative rotations are recorded in
`crops.json`. They are not world camera poses. No chronology is fabricated from
the order in which crops were written.

Preparation actually took **3.60 s**, process peak RSS **355,696,640 bytes**.
Whole-process memory is not isolated GPU memory. Source/output hashes,
calibration, errors and versions are retained in the job directory.

## Geometry acceptance matters before diffusion

The first ordinary, unconstrained perspective SfM run registered **54/54** views
in **17.55 s**, producing 4,230 sparse points and 0.666 px mean reprojection error.
However, independently estimated crop cameras from the same panorama diverged:
maximum within-panorama center deviation reached **14.45 arbitrary units**, with
median adjacent panorama-center separation only **1.33 units**. This fails the
physical co-location check even though registration and reprojection succeeded.
The resulting Brush job was deliberately cancelled after **21.21 s**; it is not
an accepted scene. A single-direction diagnostic also failed to initialize a
usable reconstruction. Both failures are retained.

The implemented correction is a virtual camera rig: six analytically known
relative rotations and zero relative translations at each physical capture.
Only the rig's world trajectory is estimated. The adapter follows
[COLMAP's rig documentation](https://colmap.github.io/rigs.html) and the installed
PyCOLMAP 4.2.1 `panorama.py` example. Intrinsics and sensor-to-rig transforms stay
fixed during optimization. This models an ideal stitched panorama; it does not
claim that the capture camera's physical lenses have zero separation or that
stitching errors disappear.

The corrected CPU run registered **54/54 views, 9 frames, 1 rig** in **14.14 s**,
with **3,232 sparse points** and **0.518 px** mean reprojection error. The maximum
within-panorama center difference is **4.53e-15** reconstruction units; maximum
relative-rotation element error is **9.99e-16**. These checks confirm the fixed
rig constraint, not the accuracy of estimated world geometry. Metric scale and
gravity remain unmeasured.

```sh
data/tools/colmap-venv/bin/python scripts/estimate-panorama-poses.py \
  data/jobs/mapillary-beijing-crops data/jobs/mapillary-beijing-rig-poses-v2 \
  --threads 4
data/tools/colmap-venv/bin/python scripts/holdout-panorama.py \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  data/jobs/mapillary-beijing-rig-holdout --panorama pano_000005
```

This withholds all six RGB crops of panorama 5 from Brush training, leaving
**48 training images**. Poses, geometry and initial point colors still use
all-image SfM. Removing points with fewer than two retained observations removes
68 points and leaves 3,164. Those observations can belong to overlapping virtual
cameras at one physical position; the filter is not proof of train-only
triangulation. This is an appearance holdout, not independent geometry evidence.

A separate CPU audit confirms that all 3,232 original points have observations
from at least two physical panoramas. Their best distinct-center triangulation
angle has a median of **7.09°**; **39.42%** are below 5°. After the holdout filter,
40 of 3,164 points have only one remaining physical panorama. These measurements
suggest limited parallax for many points, but do not establish the cause of
Gaussian streaks. The source hashes and full statistics are retained in
`data/research/panorama-geometry-diagnostics.json`.

## Actual Gaussian baseline

Brush 0.3.0 executed on the **Apple M2 / Metal** adapter, seed 42, SH degree 1,
512px images. All three runs consumed the same 48-image holdout dataset.

| Training | Time | Export | Process peak memory footprint |
| --- | ---: | ---: | ---: |
| 2,000 steps, 150k maximum splats | 42.36 s | 7,015 splats / 646,030 bytes | 424,788,736 bytes |
| 10,000 steps, 150k maximum splats | 323.81 s | 150,000 splats / 13,800,652 bytes | 974,439,216 bytes |
| 20,000 steps, 750k maximum splats | 1,522.91 s | 750,000 splats / 69,000,652 bytes | 1,583,662,016 bytes |

These are actual wall-clock observations while other local applications were
running, not isolated benchmarks. Process memory is not a separate VRAM meter.
The 10k PLY SHA-256 is
`a583198ae3a0c78894ea7f19119e99a59edafee485d21515a87576bfb37019e5`.

```sh
python3 scripts/reconstruct.py data/jobs/mapillary-beijing-rig-holdout \
  data/jobs/mapillary-beijing-rig-baseline-10000 \
  --steps 10000 --resolution 512 --max-splats 150000 \
  --title 'Beijing courtyard · captured panorama baseline' \
  --id mapillary-beijing-baseline
node scripts/render-posed-view.mjs \
  --dataset data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  --ply data/jobs/mapillary-beijing-rig-baseline-10000/world/scene.ply \
  --frame images/pano_000005_view_02.png --alpha-threshold 128 \
  --output data/jobs/mapillary-beijing-gap-render-10000
```

Headed Chrome/Spark rendered the actual PLY at recorded cameras. The Groundshift
viewer also displayed it, and zoom/reset were exercised. A captured UI reading
was 60 fps; this is an instantaneous display, not an FPS benchmark. **Rendering
PASS; visual quality FAIL** for the 10k baseline: recognizable trees, bikes and
facade still contain strong streaks and ghosting, including at training cameras.
The 2k-to-10k held-out view02 comparison improved full-image PSNR from **13.973
to 14.717 dB**, MAE from **36.251 to 32.926**. This improvement is from longer
Gaussian training, not diffusion.

The larger/longer 20k trial also executed on Metal and rendered in headed
Chrome. Its PLY SHA-256 is
`66378edc6ed799b783ba7ea455b34fb88670c7aa5c29157a9ed76aef105a78fd`.
It changes both training duration and capacity, so this is not an isolated
capacity ablation. On the same real held-out view02, full-image PSNR **worsened
from 14.717 to 12.684 dB**, and MAE **rose from 32.926 to 44.140**. Visible ghosting,
thin streaks and blurred/fragmented surfaces remain. The low-opacity mask grows
to **3.938%**. **Native export/render PASS; visual quality FAIL.** More computation
alone did not produce a usable improvement in this bounded trial.

```sh
python3 scripts/reconstruct.py data/jobs/mapillary-beijing-rig-holdout \
  data/jobs/mapillary-beijing-rig-baseline-20000 \
  --steps 20000 --resolution 512 --max-splats 750000 \
  --title 'Beijing courtyard · capacity experiment' --id mapillary-beijing-capacity
```

Evidence: `data/jobs/mapillary-beijing-rig-baseline-20000/{job.json,training.log,resources.txt}`,
`data/jobs/mapillary-beijing-gap-render-20000/`, and
`data/jobs/mapillary-beijing-capacity-comparison/report.json`. The first portion
of training overlapped local browser inspection and CPU tests; times are
observations, not controlled speed comparisons.

## Real-photo stereo warp

`scripts/warp-panorama-gap.py` rectifies observed panoramas 4 and 6 using their
estimated poses, estimates depth with OpenCV StereoSGBM, filters inconsistent
matches, and forward-warps with a z-buffer into panorama 5's camera. It reads
the target pose but **does not read target image pixels**. Tests also exercise
a missing target file. No depth is invented to fill failed matches.

The best tested lateral direction was view04, toward the building facade.
Original 512px/90° inputs left 82.7% holes. A bounded alternative recropped the
two original panoramas at 768px/120° while preserving their estimated poses;
the target remains 512px/90°. After correcting COLMAP corner-origin intrinsics
to OpenCV integer-center coordinates (`cx -= 0.5`, `cy -= 0.5`), this took
**1.683 s**, recovering **65,214 pixels / 24.877%** and leaving **75.123% holes**.
Known-pixel PSNR is **18.021 dB**, MAE **18.586**, against the separately loaded
real held-out photo. Earlier pre-correction trials remain local evidence.

**Coverage FAIL:** the recovered fragments can be sharp, but completing three
quarters of the target requires mostly generated appearance. Stereo depth and
poses are estimates. Filling black holes can improve PSNR without reconstructing
anything correctly, so diffusion comparisons include a neutral gray-fill control.
The [complete wide-FOV preparation and warp recipe](PANORAMA_WARP_REPRO.md) was
executed again; both source crops, the output warp and its mask matched the
selected corrected trial byte for byte.

## Local diffusion scope

The bounded candidate is `stable-diffusion-v1-5/stable-diffusion-inpainting`,
revision `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb`, using Diffusers on PyTorch MPS.
Its FP16 safetensors total 2,740,652,750 bytes. This is an ungated **open-weight**
model under **CreativeML OpenRAIL-M**, with use restrictions; it is not a plain
Apache/MIT model. Code, dataset and model licenses are separate. No custom model
training or cloud inference is involved.

`scripts/inpaint-gap.py` completes only white pixels of a supplied binary mask
and preserves the black-mask reference pixels exactly at the working resolution.
It records hashes, prompt, seed, revision, device, timing, memory observations
and failures. That is **masked 2D completion**, not a demonstrated pose-conditioned,
multi-view-consistent panorama generator. Generating several images with the
same seed does not establish consistent geometry.

`scripts/render-posed-view.mjs` can render a real Gaussian artifact from an
existing reconstructed dataset camera in headed Chrome. It exports RGBA, a grey
composite and a binary low-opacity mask. Low accumulated opacity is only an
experimental hole heuristic: it does not certify unknown geometry, nor catch
opaque but incorrect surfaces. These masks must not be labeled ground truth.

The intended comparison withholds an entire panorama's six crops from Gaussian
RGB training. Pose estimation may still use all photographs; if so, report the
result as an **appearance holdout with all-image SfM**, not an independent camera
or geometry benchmark. Exclude initialization points that lack two retained
image observations. A held-out PSNR change is photometric evidence only; inspect
nearby views and cross-view geometry before accepting generated training views.

## Evidence locations

All large/private intermediate files remain local under `data/`:

- `samples/mapillary-beijing/`: originals, acquisition report, attribution.
- `research/mapillary-candidates.json`: first 24 candidates and GPS spacing.
- `research/mapillary-access-report.json`: actual access checks and alternatives.
- `research/acquisition-planned12-failure.json`: original throttled request.
- `jobs/mapillary-beijing-crops/`: real projection and hash evidence.
- `jobs/mapillary-beijing-poses/`: failed co-location despite 54 registrations.
- `jobs/mapillary-beijing-baseline/`: cancelled unconstrained training.
- `jobs/mapillary-beijing-direction2-poses/`: failed single-direction diagnostic.

Final native, diffusion, browser and deployment results are recorded below only
after actual execution. An exported file alone does not establish visual quality.

## Diffusion installation and execution

The actual isolated environment uses Python 3.12, PyTorch 2.15.0, Diffusers
0.42.1, Transformers 5.22.1, Accelerate 1.15.0, Pillow 13.0.0, Safetensors 0.8.0,
and Hugging Face Hub 2.4.0. Installation does not require a new account:

```sh
python3.12 -m venv data/tools/diffusion-venv
data/tools/diffusion-venv/bin/python -m pip install \
  torch==2.15.0 diffusers==0.42.1 transformers==5.22.1 accelerate==1.15.0 \
  Pillow==13.0.0 safetensors==0.8.0 huggingface-hub==2.4.0
HF_HUB_DISABLE_XET=1 data/tools/diffusion-venv/bin/python scripts/inpaint-gap.py \
  data/jobs/mapillary-beijing-gap-render-10000/input.png \
  data/jobs/mapillary-beijing-gap-render-10000/mask.png \
  data/jobs/mapillary-beijing-gap-inpaint-gs10000-v2 \
  --prompt 'a documentary street photograph, continuous pavement, trees, railings and building surfaces, realistic natural daylight' \
  --steps 20 --seed 41 --max-edge 512
```

The first invocation downloads the pinned 2.74GB FP16 weights into
`data/tools/diffusion-models`; add `--offline` for cached execution. Outputs must
be new directories. The safety checker stays enabled. A pre-inference adapter
failure (`enable_vae_slicing` removed from the pipeline API) was retained and
fixed to the installed API, `pipeline.vae.enable_slicing()`.

Current upstream references:
[Diffusers MPS](https://huggingface.co/docs/diffusers/optimization/mps),
[inpainting API](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/inpaint),
[model card and license](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting).
Larger pose-conditioned alternatives were inspected, not run:
[ViewCrafter](https://github.com/Drexubery/ViewCrafter) documents CUDA dependencies
and a 23.5GB GPU sparse-view example; [SEVA](https://github.com/Stability-AI/stable-virtual-camera)
requires gated weights, CUDA dependencies and a noncommercial model license.
Neither has a verified local M2 path in this experiment. No claim of global
state-of-the-art coverage or proof that all such methods are impossible is made.

The first actual MPS run completed **19 denoising iterations** (20 configured,
strength 0.99) at 512² in **38.26 s inference / 44.96 s total**. MPS allocations
observed after inference were **2,759,261,952 bytes** and driver allocations
**5,202,690,048 bytes**; these are not peak measurements. On the view02 GS mask,
the completion mask covers **2.206%** of pixels. Hole MAE falls **59.43 → 55.47**, versus **68.23**
for a neutral gray fill. Full-image PSNR moves **14.717 → 14.737 dB**. Unmasked
pixels are exactly retained; opaque incorrect geometry remains unchanged.
**Native inference PASS; useful geometry improvement NOT demonstrated.**

The second MPS run consumed the corrected stereo view04 warp and completed
**75.123%** of its pixels in **39.57 s inference / 45.96 s total**, also 19 actual
iterations. Post-inference MPS/driver allocations were **2,759,261,952 /
4,128,948,224 bytes**. Comparing against the real view04 photograph:

| Hole treatment | Hole MAE (lower better) | Full-image PSNR (higher better) |
| --- | ---: | ---: |
| Black unfilled warp | 104.04 | 7.542 dB |
| Neutral gray fill | 57.65 | 12.388 dB |
| Local diffusion | 50.16 | 12.371 dB |

Diffusion has lower MAE but slightly **worse PSNR than plain gray fill**. Inspection
shows invented storefront signage, wall details and a person absent from the
target photograph. Known pixels are unchanged. **Inference PASS; faithful
missing-view recovery FAIL** for this trial. Multi-view consistency is **NOT RUN**;
a single completed target cannot establish it. View02 and view04 are separate
tests with different masks and reference images.

The original comparison sheet is retained at
`data/research/diffusion-comparison-local-only.jpg`. Under the subsequent observation-surface instruction, explicitly selected licensed crops and comparisons are included in the public report with attribution and modification labels. Detailed metrics and input/output
hashes are in `data/research/diffusion-experiment-summary.json` and the individual
job reports.

An inspected local comparison page is available at
`http://127.0.0.1:4317/data/research/mapillary-review.html` while the development
server is running. It switches between the two experiments and overlays the
generated and real images. Actual image loading, both case selectors and the
opacity control were checked in the browser. The initial report was local-only. Its sanitized public counterpart now belongs in the Railway observation package, including licensed source crops and generated outputs.

## Feed generated pixels back into Gaussian training

`scripts/augment-generated-view.py` is a small filesystem adapter, not a new
backend framework. It verifies the completed image hash, the original inpainting
input hashes and decoded working pixels, unchanged pixels outside the mask,
and the exact target camera matrix and intrinsics. It copies the 48 real training
images plus one generated view04, preserving the initialization and world
coordinates. It does not read the original target photograph. `synthetic-views.json`
records the model, settings, masks, hashes and limitations; original provenance
remains separately available. No resizing or camera-pose invention occurs.

```sh
HF_HUB_DISABLE_XET=1 data/tools/diffusion-venv/bin/python scripts/inpaint-gap.py \
  data/jobs/mapillary-beijing-stereo-gap-view04-widefov-v2/warp.png \
  data/jobs/mapillary-beijing-stereo-gap-view04-widefov-v2/mask.png \
  data/jobs/mapillary-beijing-gap-inpaint-stereo-widefov-v2 \
  --prompt 'a documentary street photograph, continuous pavement, trees, railings and building surfaces, realistic natural daylight' \
  --steps 20 --seed 41 --max-edge 512 --offline
data/tools/diffusion-venv/bin/python scripts/augment-generated-view.py \
  data/jobs/mapillary-beijing-rig-holdout \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  images/pano_000005_view_04.png \
  data/jobs/mapillary-beijing-gap-inpaint-stereo-widefov-v2 \
  data/jobs/mapillary-beijing-generated-augmentation-stereo-v2 \
  --source-reference data/jobs/mapillary-beijing-stereo-gap-view04-widefov-v2/warp.png \
  --source-mask data/jobs/mapillary-beijing-stereo-gap-view04-widefov-v2/mask.png
```

The original input PNG hashes differ from the saved working PNG hashes because
Pillow reencodes them. The adapter verifies both the original byte hashes and
pixel equality instead of pretending those files are byte-identical. The
768px/120° source cameras and the 512px/90° target have intentionally different
intrinsics; only the target calibration is used for the generated training view.
Adding the generated target to training invalidates its use as an independent
evaluation view. The final short augmented run is an execution test, not proof
of improved reconstruction quality.

The exported portable world also retains the model repository, revision, license
URL, seed, target, mask fraction and completed-image hash in provenance notes.
The model's terms remain distinct from the source photograph license. Earlier
prepared datasets remain unused evidence; the final run uses the `-v2` dataset.

```sh
python3 scripts/reconstruct.py data/jobs/mapillary-beijing-generated-augmentation-stereo-v2 \
  data/jobs/mapillary-beijing-generated-gs-smoke \
  --steps 2000 --resolution 512 --max-splats 150000 \
  --title 'Beijing · synthetic augmentation experiment' \
  --id mapillary-beijing-synthetic-experiment
```

The actual Metal run loaded **49 training views**, completed 2,000 steps in
**41.95 s**, and exported **7,014 splats / 645,938 bytes**. Process peak memory
footprint was **432,702,232 bytes**. Export SHA-256:
`9c20941184e0ded484c45b5660886c502231681cb7ed2e73473bf008fb6128c4`.
This closes the executable chain **observed panoramas → stereo warp → MPS
diffusion → generated-image dataset → Metal Gaussian export**. It is a short
integration run, not a demonstrated quality gain, and the generated target is
not treated as held-out evaluation after entering training.

The actual exported PLY rendered at the generated view04 camera in headed
Chrome/Spark, and the exported `world.json` loaded in the complete Groundshift
viewer. The visible image is blurred with thin streaks; it is **not an accepted
scene**. The portable manifest was also read back to verify its model/revision/
license/generated-image hash. Evidence is in
`data/jobs/mapillary-beijing-generated-gs-smoke/` and
`data/jobs/mapillary-beijing-generated-gs-render/`.

## Automated validation

| Check | Result | Scope |
| --- | --- | --- |
| TypeScript, ESLint, production build | PASS | Existing viewer; no UI source changes in this experiment |
| Vitest | PASS | 143 viewer/packager tests |
| Headed Chrome | PASS | 11 regression tests, 50.0 s; actual accepted-world rendering and controls |
| Python tests | PASS across the appropriate environments | 102 unique tests: main OpenCV environment executes 86 and skips 16; those 16 execute in the Pillow and PyCOLMAP environments |
| Inpainting-specific tests | PASS | 5 tests, including preserved pixels and truthful failed-inference reports |
| Native rig-specific tests | PASS | 6 tests, including actual PyCOLMAP database grouping and co-location checks |
| Augmentation-specific tests | PASS | 11 tests, including wrong pose, resized input, modified known pixels, corrupt hashes and portable provenance |
| Comparison / warp tests | PASS | 8 each, including actual SGBM, no-target-file operation and cancellation reporting |
| New Gaussian scene in browser | PASS for execution | Actual Chrome/Spark render plus full Groundshift zoom/reset; visual quality is a separate failed gate |
| Generated-image → Gaussian → viewer | PASS for execution | Actual 49-image Metal training, export, posed render and complete Groundshift viewer load; no quality-improvement claim |
| Pose-conditioned multi-view diffusion | NOT RUN | No suitable native implementation validated; 2D completion is explicitly narrower |

The targeted counts overlap the 102-test total; do not add them together.
Tests alone do not prove GPU execution. Separate native job reports contain
the actual Metal/MPS evidence. Logs are retained under
`data/research/{native-tests-panorama-final,inpaint-tests-final,rig-tests-final,augmentation-tests-final,compare-gap-tests-final,warp-gap-tests-final}.log`.

## Outcome, blockers and next steps

The complete local experimental path now executes with real licensed photographs:
acquisition, pinhole projection, fixed-rig SfM, observed-image Gaussian training,
stereo gap projection, MPS inpainting, explicit synthetic augmentation, Gaussian
retraining, portable export and actual browser viewing. The scene was not
downloaded as a prebuilt Gaussian asset; world poses and sparse points were
estimated here, and Metal training logs identify the Apple M2 adapter.

**The intended useful, coherent gap-filled 3D world is not complete.** Concrete
evidence limits the current approach:

1. Two-photo stereo leaves 75.12% of the chosen target unknown even with wider
   source crops. No depth has been invented to hide this coverage failure.
2. The executable 2D diffusion model fills appearance but invents details; it
   does not condition on all target cameras or enforce multi-view consistency.
3. More Gaussian capacity and longer training worsened the held-out view in the
   measured trial. Improving geometry/supervision comes before further brute-force
   training or more independently generated views.
4. Direct Mapillary-wide search still needs authorized API access; this is a
   suitable publicly mirrored sample, not an established global density maximum.

The next bounded experiment should use a more static facade segment with closer
physical capture spacing and a stronger depth/visibility estimate aligned to
the reconstructed cameras. Establish a better observed-image baseline first,
then assess geometry-conditioned completion on several overlapping withheld
physical positions. A supported MPS path and memory/license check are required
before adopting a larger multi-view diffusion model. iOS capture, CUDA ports,
cloud GPUs and platform services were not added.

**Publication policy changed by the user on 2026-11-05.** Railway is the observation surface, not a quality gate. The four Mapillary Gaussian trials, actual source/warp/diffusion comparisons, and unsuccessful stage history are included regardless of visual quality. Existing quality FAIL and NOT RUN outcomes remain unchanged. See [the current publication status and verified deployment](DEPLOYMENT.md).

Original private footage, model weights and raw execution logs remain local.
Large generated worlds and explicitly selected licensed comparison images use
release attachments; Git contains the reproducible preparation recipe, public
metadata, tests and documentation. Publication does not mean quality acceptance.
