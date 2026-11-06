# Twenty tangent views and presentation backgrounds

## Current viewer decision — 2026-11-07

The user reports that the wider directional coverage gives a substantially
better sense of being inside a world. This is a user-observed exploration
improvement, separate from the old six-horizontal-view photo-error screen;
neither establishes accurate geometry. The older `street-final-hires` remains
the photo-error reference, while the new tangent GS remains an experience
candidate with broader directional inputs.

The user rejects **both panorama and depth-shell background completion**:
horizontal translation makes the background disagree with GS and the experience
is worse. The live viewer therefore removes the background selector, renderer
and HTTP/local background loading. It ignores even archived `background`
references, while still loading their GS and real camera path. The current
public manifest omits that reference. Background math/format tests and the
previous comparison images/archives remain historical evidence, not a live
feature. No new depth inference, camera estimation or training is performed;
the original tangent and reference PLY/camera hashes are preserved.

Everything below describes the completed experiment before that product
decision, including the now-rejected background treatment. New viewer checks
and deployment evidence are recorded separately from its original training.

Viewer-removal validation: TypeScript, lint, production build and all 180 JS
tests PASS. The five previous optional-loading cases are replaced by three
contracts proving no HTTP metadata request, no read of absent/malformed local
background files and only one GS object URL. Eight targeted actual local headed
Chrome cases PASS in 42.965s, with no skips/flaky/failing cases. They cover the
unchanged real tangent scene, an archived-reference fixture using that same real
scene/poses, substantial GS-only pixels, translation, upward/downward free look,
no background controls or metadata/image/mesh requests, viewer recovery and
camera-path regression. The previous full 79-case run remains historical;
the complete current 80-case suite is NOT RUN.

The initial build caught an obsolete background setter in the retry button;
it was removed before the successful production retry and deployment. A stale
package attempt after that failed build correctly stopped at the preservation
guard without producing or uploading an overlay. Both failed logs are retained
locally. No depth inference or native training ran for this removal; preserved
PLY/camera hashes prove preservation, not execution of a new training run.

The GS-only release is live. Four targeted actual public Chrome cases PASS in
152.619s, including the real scene with and without a fixture legacy reference;
each records zero background requests and page errors, actual translation/free
look and 993,176 GS-only colored pixels with UI hidden. All 21 changed public
files match the package's size/SHA inventory. Ordinary extraction of nine
checksum-pinned archives restores all 1,122 composed files in 4.837s. This is a
local restoration plus incremental public checks, not a fresh full public-file
scan or complete 80-case public browser run. Tangent and photo-reference PLY,
cameras, previews and license files retain all eight checked hashes, and the
tangent asset transform/navigation are identical. Historical background files
remain unreferenced evidence. [Viewer-removal evidence](evidence/gs-only-viewer.json).

**Executed result:** the new local Metal scene renders, but does not replace
`street-final-hires`. Its held-view RGB error is 7.32% worse at 512 output and
6.72% worse at 1024, with zero of six held directions improving at either
resolution. Some facade ghosting looks reduced; road seams and thin/near
objects remain problematic. Presentation backgrounds are evaluated separately.
[Public observation and comparisons](https://groundshift-viewer-production.up.railway.app/experiments/tangent-background/)
retain this result regardless of quality.

User-authorized2026-11-06 after the previously closed same-data campaign. This
is one bounded reopening, not permission for another model/parameter sweep.
Preserve every earlier source, pose, seed, world and observation. Work directory:
`data/jobs/street-tangent-background-20261106/`.

## Declared configuration

- Same nine licensed7680×3840 Mapillary/Wikimedia original ERP photographs and
  preserved all-nine fixed-rig SfM. Physical5 RGB stays withheld from training,
  calibration-image inference, point colors and presentation backgrounds.
- Twenty directions from the outward face normals of an icosahedron. Each is
  a true square pinhole reprojection,1024×1024,80° horizontal/vertical FOV, from
  original pixels. Analytically verify full-sphere coverage and overlap. All
  twenty directions at one sphere share exactly one real camera center.
- Pinned DAV2 Small, Apache-2.0, executed locally on MPS **after** reprojection.
  Request1036 neural input (multiple14); record the actual model tensor size,
  not merely the output image size. If that causes a concrete memory/platform
  failure, retain its evidence and permit one explicit518-input recovery before
  training. No silent checkpoint, device or resolution substitution.
- Fit relative inverse camera-Z against training SfM anchors with deterministic
  withheld track IDs. Jointly constrain overlapping crops using
  `inverseRadial = cosToCropForward * (scale * raw + offset)`; raw camera-Z-like
  predictions must not be directly equated across differently rotated cameras.
  Unanchored/unidentifiable regions remain unsupported. No arbitrary metres.
- One calibrated spherical range per ray; retain disagreement diagnostics and
  discard invalid/nonpositive/unsupported range. Geometry initialization uses
  ERP vertical band.25–.85 and each center's training-SfM P99 range cap; upper
  sky and the masked lower15% are not assigned fabricated finite distances.
  All20 RGB directions remain training inputs with the same nadir-only mask. Shared SfM anchors tie physical
  centers; compare neighboring-center agreement without claiming ground truth.
- One Brush0.3.0 Metal run:8,000 steps,1024 max resolution,800k cap,SH1,seed42.
  New initialization capped at180k dense points plus preserved non5 sparse seed.
  Same native budget as `street-final-hires`, no factorial attribution.

## Presentation completion is a separate treatment

Expose GS-only (default), original-panorama background, and background plus a
coarse depth-textured shell if practical. Use only the eight non5 sources. The
background panorama follows orientation without translation, with known near
object/parallax and source-switch artifacts. Mesh triangles use calibrated
estimated depth and reject invalid samples/depth discontinuities. They are
display surfaces, not measured floors, collision or recovered invisible sides.
Select by actual camera-center proximity. The known bottom15% camera artwork
is replaced in display textures by smoothed column-color extrapolation fading
to a uniform tone; these are explicitly nonobserved presentation pixels. They
do not enter depth, training RGB, point positions or collision. No diffusion.

World/background geometry is explicit right-handed viewer Y-up. Original ERP
local rays are `(+cos(lat)sin(lon), -sin(lat), +cos(lat)cos(lon))`, the existing
CV convention; panorama-to-world includes the actual world asset transform.
Mesh UV is `(u,1-v)` with ordinary vertically flipped image textures. Never
apply the asset transform twice or confuse camera-Z with radial distance.

## Evidence, deployment and stopping

Reuse the same75 evaluation cameras and source references as the last run.
Compare actual GS-only renders at512 output, plus1024 detail where practical.
Measure background completion separately; its colored pixels and source-photo
coverage cannot prove a Gaussian scene rendered or improve GS-only acceptance.
Inspect branches/railings, walls, road, far region, movement and background
source transitions. Physical5 poses/sparse geometry remain all-nine estimates;
this is appearance withholding, not independent geometry truth.

Publish plan/input/depth/scene evidence as soon as each is deployable, with
unexecuted stages NOT RUN. Continue local execution while a deployment agent
publishes. Reuse the existing checksum-pinned static archive/overlay mechanism.
Record native/model timings, bytes, memory, failures and test/browser scopes.
Finish with one actual exported candidate and honest comparison, or retain a
concrete blocker. No additional same-data training search after seeing the result.

Primary basis: [360MonoDepth](https://manurare.github.io/360monodepth/),
[official DAV2 model/interface/license](https://github.com/DepthAnything/Depth-Anything-V2),
[Three.js background API](https://threejs.org/docs/pages/Scene.html).
This implementation reuses DAV2 and our explicit calibration; it does not claim
to reproduce the complete360MonoDepth optimization or adopt its model.

## Reproduce the declared run

First follow [local setup](M1.md), [street preparation](STREET_CONCLUSION.md)
and [the preserved 1024 baseline](FINAL_QUALITY.md). This bounded script reuses
the nine hash-pinned originals, fixed-rig poses, training-colored sparse anchors,
512px evaluation crops and the previous 1024px native export. It deliberately
requires those preserved jobs; it is not a general street-import command.
Use the existing `data/tools/diffusion-venv` PyTorch/Transformers MPS environment
for depth inference and `data/tools/depth-hf-cache` model cache. This environment
name is historical; no diffusion model runs here. CPU preparation/calibration
uses `data/tools/venv`. The Small checkpoint revision is
`5426e4f0f36572d16453bbda7a8389317b1bef99`; both Small weights and implementation
are Apache-2.0. Other DAV2 sizes have different checkpoint terms and are not
substituted. Original sample attribution remains Cicero101 / Mapillary via
Wikimedia Commons, CC BY-SA 4.0; see `scripts/samples/mapillary-beijing.json`.

Always choose a **new** job directory. The following shows the executed job's
name; rerunning into its completed output directories is rejected:

```sh
data/tools/venv/bin/python scripts/prepare-tangent.py data/jobs/street-tangent-background-20261106
```

Invoke the existing inference CLI with its exact ordered list of 160 crops:

```python
import json, os, subprocess
from pathlib import Path
job = Path('data/jobs/street-tangent-background-20261106')
images = json.loads((job / 'inputs-tangent/inference-inputs.json').read_text())
env = dict(os.environ, HF_HOME=str(Path('data/tools/depth-hf-cache').resolve()))
subprocess.run(['data/tools/diffusion-venv/bin/python', 'scripts/infer-relative-depth.py',
                str(job / 'depth'), *images, '--input-size', '1036'],
               env=env, check=True)
```

```sh
data/tools/venv/bin/python scripts/reconstruct-tangent.py fusion data/jobs/street-tangent-background-20261106
data/tools/venv/bin/python scripts/diagnose-tangent.py data/jobs/street-tangent-background-20261106
data/tools/venv/bin/python scripts/reconstruct.py data/jobs/street-tangent-background-20261106/datasets/tangent data/jobs/street-tangent-background-20261106/training-tangent --steps 8000 --resolution 1024 --max-splats 800000 --title 'Street tangent20' --id street-tangent20
node scripts/prepare-street-evaluation.mjs data/jobs/street-tangent-background-20261106 baseline tangent
data/tools/venv/bin/python scripts/reconstruct-tangent.py background data/jobs/street-tangent-background-20261106
node scripts/render-street.mjs data/jobs/street-tangent-background-20261106/render-config.json data/jobs/street-tangent-background-20261106/renders
data/tools/venv/bin/python scripts/measure-street.py data/jobs/street-tangent-background-20261106 data/jobs/street-tangent-background-20261106/renders data/jobs/street-tangent-background-20261106/evaluation --baseline-model baseline
```

For the second, 1024-output comparison, double `w`, `h`, `fl_x`, `fl_y`, `cx`
and `cy` in each of those same 75 evaluation cameras; point each reference to
the same-named `street-final-quality-20261106/inputs-hires/images/` crop.
Keep both model PLYs and camera matrices unchanged. Render to `renders-detail/`
and pass that new config with `measure-street.py --config ...` to write
`evaluation-detail/`. Rendered RGBA, metrics, source references and interpolation
metadata are retained locally. Do not run these GPU render batches concurrently
with native training.

After both render batches finish, `scripts/review-tangent.py JOB` recreates the
four labeled comparison sheets in a new `visual-review/` directory. Existing
output is never overwritten; `--output NEW_DIRECTORY` permits an independent
reproduction. The committed helper was executed and all four resulting JPEG
hashes match the original local review sheets.

For targeted math tests:

```sh
data/tools/venv/bin/python -m unittest discover -s scripts/tests -p test_tangent_geometry.py -v
```

Full Python checks use both the main and existing PyCOLMAP environments; record
their union of actual successes, not the sum including skips. Set
`GROUNDSHIFT_HDR_FFMPEG` to the existing zimg-enabled FFmpeg for the real HDR test.
Viewer checks are `npm run typecheck`, `npm run lint`, `npm test` and
`npm run build`; browser checks use the immutable packaged viewer stage and
`GS_BASE_URL`, including `tests/browser/tangent-background.pw.mjs`.

## Actual execution and comparison

Preparation took 31.212168s: 160 real crops, eight physical centers, exactly zero
translation between the 20 cameras at each center. All 145,800 sampled sphere
rays are covered, with 1–5 supporting crops, mean 2.6253. This measures angular
coverage only. It creates no new physical viewpoint or independently observed
hidden surface.

Pinned DAV2 Small actually ran on MPS for all 160 crops in 110.918779s;
the sum of individual inference calls is 93.045021s. Every recorded model input
was `[1,3,1036,1036]`; the output arrays are 1024px. No fallback, substitute
checkpoint or new diffusion ran. The cached model startup and these single-run
timings are not cold-start or controlled hardware benchmarks. Neural-process
peak memory was not reliably isolated; do not use a controller's resource
counter as total inference/unified-memory usage.

CPU calibration/fusion took 16.866375s. It accepted 136 crop fits and retained
24 unsupported/rejected cases without inventing ranges. Each physical sphere
has 306,207–311,066 supported pixels out of 524,288, within the declared geometry
band/cap; this is not full-sphere valid depth. Voxel fusion yielded 618,158
points; the native seed contains 180,000 selected dense points plus the
unchanged 3,124 non5-colored sparse points. All 103 frozen baseline hashes
still match after training.

The additional paired diagnostic uses the **same rays and same valid crop
membership** before and after fitting. At all eight centers its median
log-range spread decreases: .0877→.0683, .0798→.0604, .0874→.0625,
.0837→.0577, .0726→.0507, .0615→.0486, .0562→.0476 and .0580→.0500.
These are internal same-center disagreements. Neighbor-center reprojections
retain invalid samples, occlusion/dynamic-object ambiguity and substantial
error tails; no independent range truth or global geometric acceptance follows.
The original unpaired validity-changing diagnostics remain retained and are
not presented as matched before/after improvement.

Brush 0.3.0 explicitly selected **Apple M2 / Metal**. One declared 8,000-step
training/export completed in **1188.250442s**, without native retry or parameter
change: 800,000 Gaussians, **73,600,652 bytes**, SHA-256
`b9213464d654d8fbda1721a1a86415fa4670cb50c4b9ce5107791b7906f94a3e`.
`time -l` records maximum resident set 872,415,232 bytes and peak process memory
footprint 2,669,135,216 bytes. These are process counters, not complete unified
GPU/system memory measurements. Historical baseline timing is not a controlled
speed comparison.

Actual headed Chrome 156 / Spark / M2 rendering produced the same 75 cameras
per model at each output resolution: **300 GS-only matched frames**, plus one
early preview. The 512/1024 render batches took 34.994s / 81.607s, and their
metric/video stages 5.952s / 23.843s. Browser startup and screenshot overhead
are included; these times are not interactive FPS. Route videos encode 49
actual interpolated-view frames at 6fps; 6fps is the movie rate.

| Same-pose appearance measurement | Prior 1024/800k best | New tangent20 |
|---|---:|---:|
| 512 output: held-level mean RGB MAE ↓ |24.414430|26.202616|
| 512 output: held-level mean PSNR, dB ↑ |17.482927|17.057205|
| 512 output: alpha≥.95 fraction |.271452|.233072|
| 1024 output: held-level mean RGB MAE ↓ |24.344902|25.980609|
| 1024 output: held-level mean PSNR, dB ↑ |17.458603|17.085358|
| 1024 output: alpha≥.95 fraction |.296076|.253768|

The predefined appearance screen **FAILS** at both resolutions. Per-direction
MAE includes holes composited on 127 gray, selected from the same ERP band
.40–.85. No background-photo pixels enter these measurements.

| Held yaw |512 prior|512 tangent|1024 prior|1024 tangent|
|---|---:|---:|---:|---:|
|0°|32.197243|33.362213|32.492513|33.443098|
|60°|27.199403|28.064662|27.164417|27.925213|
|120°|19.874534|22.599588|19.577743|22.219396|
|180°|24.393888|27.973858|24.407985|27.806499|
|240°|21.796957|23.344170|21.509818|22.898012|
|300°|21.024554|21.871203|20.916939|21.591435|

Direct review covers all six held directions, seven route samples, two lateral
extrapolations and three native-1024 detail patches. Some wall/column overlap
is reduced and the street remains recognizable. Branches, fence/railings and
scooters still blur or double; pavement shows broad triangular seams/smears,
and the far region remains softer than photographs. The path samples are
display interpolation, and lateral views are deliberate extrapolation, not
proof of a continuous measured point cloud or recovered walking floor.
Physical5 RGB is appearance-withheld, while all-nine estimated geometry is
shared. Resolution, crop distribution, neural input size and initialization
changed together, so this run cannot isolate a cause of the regression.

**Decision:** retain the previous `street-final-hires` as the overall incumbent
and preserve the new `street-tangent20` as an inspectable alternative. Better
internal overlap and broader angular sampling did not establish better GS
appearance. This single user-reopened training is finished; no additional
same-data crop/model/step/filter search is authorized. Future quality work
should obtain new physical capture evidence. Independent geometry, collision
and unrestricted walking remain **NOT ACCEPTED**.

## What the background modes actually accomplish

Actual same-pose canvas captures cover physical views 1, 4, 5 and 9 in all
three modes, plus upward/downward free look. The source selector changes
p01→p04→p04→p09; the withheld fifth photograph never becomes a background.
Wall/sky/road orientation is consistent with the GS route in the inspected
captures. This is a visual convention check, not measured pose accuracy.
Panorama translation/parallax is deliberately approximate; the coarse shell
cannot establish invisible surfaces or remove all source-switch artifacts.

At the ordinary route views the effect is often subtle because the GS already
covers most of the canvas. Looking downward, clear-color-like display pixels
decrease from 2.6291% to .8397% with the panorama and .8380% with the shell;
pixels with all channels below 15 instead increase from 2.1240% to 2.2887%.
These are two explicitly different screenshot diagnostics, **not** geometric
coverage. A dark-colored photograph or Gaussian can remain dark after the
background is added. No general dark-pixel reduction or visual breakthrough
is claimed. The shell shows no established advantage over the simpler panorama
in these sampled views; retain both for observation with GS-only as default.

The downward view still reveals orange/black nadir contamination. A read-only
source diagnostic finds that p01's orange artwork extends to ERP v≈.835,
above the fixed .85 mask/fill boundary; p04's starts below that boundary.
The fixed lower15% rule therefore does **not** remove the complete artwork at
every source. Moreover, a training loss mask does not force all Gaussians in
that region to become transparent. Rendering a photograph behind them cannot
erase opaque foreground artifacts. This limitation is preserved and published;
the declared single training is not extended into another mask/crop sweep.

## Validation and retained failures

- **PASS:** 10 new tangent math tests; 243 distinct Python cases across the
  two dependency environments (main 241 successes/2 skips; PyCOLMAP 214
  successes/29 skips; union 243 actual successes, no failures).
- **PASS:** TypeScript, lint, production build and 182 JS tests, including
  background transforms, safe assets, seams, selection and resource cleanup.
- **PASS:** full immutable-native-package headed Chrome suite, **79/79**,
  0 skipped/flaky/failing, 243.164s. This covers all35 actual scene deep links
  and reloads, new GS-only pixels before any background request, all three
  background modes, camera movement, source/error handling and report history.
- **PASS:** 12 additional same-pose background captures and six off-axis
  captures; all reviewed directly. Screenshots exclude UI overlays from pixel
  counts. The reproduction helper regenerates four matched GS comparison
  sheets with identical file hashes.
- **PASS:** actual targeted public headed Chrome GS/background case,
  31.041s, 989,694 counted GS-only colored pixels, no page errors. Public
  interaction is separate from packaged-file integrity and GS quality.
- **FAIL, retained:** the first measured-report public check exposed horizontal
  overflow on mobile after metric/video content appeared. The earlier full
  79-case suite used the native-export phase before that content existed;
  it does not prove the later measured layout. The failure and subsequent
  targeted repair evidence are recorded in deployment history.
- **PASS after repair:** the scoped text-wrap fix and both additional
  background-limit comparison sheets are deployed. Two actual public report
  cases pass in 18.090s, including 390px layout, all decoded comparison images,
  the four measured values and actual video decoding. All nine changed public
  files match their size/SHA inventory. No native scene or background asset
  changed for this repair.
- **PASS final publication:** Railway deployment
  `41cf2731-9060-487f-9d67-d80442906a14` succeeds. The final two changed JSON
  paths match their public size/SHA inventory, and one final public report case
  passes in 12.686s. GS comparisons and background limitations now precede the
  retained input/depth diagnostic images. There are 35 worlds, 17 reports and
  52 timeline entries. Fresh ordinary extraction of all eight pinned archives
  reproduces all 1,117 composed file hashes in 4.440s. Public checks verify each
  increment's changed paths; this is not a fresh complete 1,117-file public scan.
- **FAIL, retained:** the first local Python test wrapper wrote its report to
  an incorrectly concatenated historical job path after unittest execution.
  A corrected runner generated the final two-environment results above; raw
  failed controller logs remain local. No failed attempt was relabeled PASS.
- **NOT RUN:** complete 79-case public suite, repeated training/hardware
  benchmarks, independent geometry truth, real-floor/collision/free-walking
  acceptance, another model/parameter/native training configuration.

Selected licensed derivatives: [six held directions](evidence/tangent-held-512.jpg),
[native1024 detail](evidence/tangent-detail-1024.jpg),
[same-pose background comparison](evidence/tangent-background-route.jpg) and
[up/down limitations](evidence/tangent-background-limits.jpg). Photographs are
Cicero101 / Mapillary via Wikimedia Commons, CC BY-SA 4.0; these comparison
derivatives retain that license and the
[source/transform attribution](https://groundshift-viewer-production.up.railway.app/experiments/tangent-background/ATTRIBUTION.txt).
[Sanitized machine-readable evidence](evidence/tangent-background.json) and
[deployment/rollback history](DEPLOYMENT.md) record exact scopes. Original full
panoramas, weights, native PLY and raw logs remain outside Git.
