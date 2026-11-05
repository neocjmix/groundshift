# Two-endpoint panorama interpolation experiment

[Open the Railway observation report](https://groundshift-viewer-production.up.railway.app/experiments/video-4to6/)
to play the generated video and inspect both exported Gaussian worlds.

The user changed the target on 2026-11-05: **a plausible generated scene matters
more than faithful reproduction of the exact street**. This experiment retains
honest provenance and distinguishes a visually plausible 2D sequence from a
measured 3D camera path. The sample is three consecutive public Beijing
Mapillary panoramas by Cicero101, mirrored on Wikimedia Commons. Their
provenance, individual original URLs and CC-BY-SA-4.0 license are in
[`scripts/samples/mapillary-beijing.json`](../scripts/samples/mapillary-beijing.json).
Inputs are zero-based photographs **4** and **6**; photo **5** is withheld from
interpolation and later shown for comparison. These are an approximately
two-second segment in the small nine-photo sample, not the globally densest
Mapillary location. Source photographs are 7680×3840 equirectangular images.

## What actually ran

1. Locally resize photos 4 and 6 to 2048×1024 with Lanczos, without yaw
   adjustment. Photo 5's pixels are not read in this preparation or generation.
2. Generate a 65-frame sequence by recursively predicting each temporal
   midpoint with Practical-RIFE 4.25 on Apple MLX/Metal. The model is
   optical-flow video-frame interpolation, **not diffusion** and not a model
   that invents a measured novel camera pose. A 128-pixel horizontally wrapped
   input margin gives the neural model panorama-seam context.
3. Blend only the generated frames' left/right 64-pixel boundary bands. This
   repairs a visible midpoint seam. Copy the observed first and last frames
   byte-for-byte. Encode a 2048×1024 H.264 MP4 at 24 fps.
4. Reserve real panorama 5's six RGB crops from Gaussian training. Reuse its
   **measured all-image SfM** six-camera rig pose as a pose proxy for the
   generated midpoint. Reproject the generated panorama into six 512×512,
   90° pinhole views. Train a matched real-only 48-view baseline and a
   48-real-plus-6-generated Brush/Metal world, then compare actual browser
   rendering. The generated pixels did not estimate or validate this pose.

At 2048×1024, 65 frames are intentionally more than the three selected
quarter/middle/three-quarter stills. The other generated frames remain video
observations; they are not silently treated as 65 measured camera positions.

| Gate | Result | Evidence / limit |
| --- | --- | --- |
| Endpoint input preparation | PASS | `preparation.json`; source SHA-256 checks, 2048×1024 RGB, no yaw change |
| RIFE Metal interpolation | PASS | 65 decoded frames; inference 191.997 s, complete job 205.464 s |
| Video encode | PASS | 65 H.264 frames, 24 fps, 2.708 s; MP4 7,242,910 bytes before seam repair |
| Periodic seam repair | PASS for edge equality | Midpoint first/last column MAE 44.222 → 0.000; spatial quality is not guaranteed by this metric |
| Final video | PASS | 7,175,540 bytes; SHA-256 `d6c8d961f07b9ecf8447b3bc6c33407d0e9216878cc2f18b40a788e30b429be0` |
| LTX-2.3 video diffusion | NOT RUN | Model download did not complete; no inference or output |
| Exploratory MPS bicycle inpaint | PASS for inference, FAIL for repair quality | One 512×512 crop; SD1.5 inpainting 28 denoising steps, 95.036 s inference, 104.807 s job. Foreground bicycle remains distorted; output was excluded from the video and GS training |
| Midpoint training dataset | PASS | 48 real + 6 synthetic crops; target #5 pixels not read in augmentation |
| Matched baseline GS | PASS for Metal training/export; quality FAIL | 48 observed crops, 10,000 steps, 150,000 splats, 1,107.156 s; 13,800,652-byte PLY |
| RIFE-augmented GS | PASS for Metal training/export; quality FAIL | 48 observed + 6 generated crops, 10,000 steps, 150,000 splats, 1,112.224 s; 13,800,652-byte PLY |
| Local browser GS rendering | PASS | Headed Chrome: both PLYs rendered at the same two estimated target-rig camera directions; 11 experiment previews captured from actual canvas output |
| Public browser rendering and video playback | PASS after one test-only retry | Public-origin headed Chrome: all 15 scenes render/reload; MP4 plays and seeks. The first 25-case run had 24 PASS / 1 wording assertion FAIL for a correct missing-world 404; the corrected case passed without changing the deployed app. New video/GS/gallery screenshots were inspected |

The RIFE process used a measured 4,219,438,688-byte peak macOS memory footprint
and 736,673,792-byte peak resident set size (`rife-run.log`, `/usr/bin/time -l`).
These are **whole-process** values; neither is an isolated Metal allocation.
The 65 generated frames and reports remain in ignored
`data/jobs/mapillary-video-4to6-20261105/`. They are not committed. Selected
licensed stills and the resulting video are explicitly allowlisted in the
[Railway observation release](DEPLOYMENT.md).

The matched real-only PLY SHA-256 is
`b31559b5c9f77fb2bdf4be359b37e65126a79e702ecaa93ff84716c67956644a`;
the generated-view PLY SHA-256 is
`c3b7fb7177bf991772616d6da578470607284130c6845243175d4d134bde5967`.
Both local Brush reports identify the Apple M2 Metal adapter. The generated-
view job's whole-process peak memory footprint was 985,105,224 bytes and
maximum resident set was 239,190,016 bytes. These are not isolated GPU
allocations. Training and resource logs remain in each ignored job directory.

The visual result preserves buildings, trees and walkway across selected
quarter/mid/three-quarter frames, but nearby bicycles visibly double or melt.
The original orange nadir cover remains. The 64-pixel blend removes the
midpoint edge jump numerically. The selected 2D frames read as one broad
residential scene, but near-field objects and temporal coherence are not
accepted as clean. **The 3D plausibility improvement FAILS** after browser
rendering: both worlds show streaked or soft geometry, and the added generated
views do not make either inspected direction more convincing.

Both PLYs were rendered in headed Chrome at the same all-image SfM target-rig
directions; the separately held-out real photo #5 crops provided a bounded
pixel diagnostic. At view 02, the real-only versus generated-view GS renders
had MAE **32.801 → 35.343** and PSNR **14.699 → 14.022 dB**. At view 04,
MAE **34.404 → 40.402** and PSNR **15.165 → 13.789 dB**. This comparison
was computed on 512×512 gray-composited rendered pixels with no alignment or
exposure adjustment. It is **not** a geometry score and exact-photo fidelity
is not the new primary goal; visible blur/streaking is the reason for the
quality FAIL. Local render/comparison reports are retained under the same
ignored job root.

The optional MPS inpaint targeted one 512×512 crop's foreground ghost with an
elliptical mask. The fixed seed-42 run used 30 requested steps, strength 0.95,
and executed 28 denoising steps. The model was the pinned
[`stable-diffusion-v1-5/stable-diffusion-inpainting`](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting)
revision `8a4288a76071f7280aedbdb3253bdb9e9d5d84bb` under CreativeML
OpenRAIL-M. The output preserved unmasked pixels, but visual inspection found
the bicycle still implausibly bent. Its actual `report.json`, mask, reference
and completion remain in the ignored local job directory; only sanitized
comparison JPEGs are destined for the observation report. This is a partial
2D result, not a video-diffusion or multi-view solution.

After frame generation, the separately loaded real photo #5 was resized to
2048×1024 for a diagnostic. A simple 50/50 endpoint crossfade gives 30.407
MAE / 14.240 dB PSNR; the seam-repaired RIFE midpoint gives 23.822 MAE /
15.437 dB PSNR. The raw RIFE midpoint was 24.159 MAE / 15.256 dB. This
pixel comparison supports a bounded improvement over simple blending; it is
**not** a measure of scene plausibility, temporal coherence or 3D geometry.
The exact hashes are retained in ignored `midpoint-comparison.json`.

## Why the diffusion model changed

The planned LTX-2.3-MLX two-stage candidate was checked against the current
upstream [CLI](https://github.com/dgrauet/ltx-2-mlx) and installed locally at
code revision `747b30ef10e92a011e85b2aa0f6c4ee86ced5218` (MIT).
Its two endpoint guide syntax, `--low-ram`, spatial tiling and 16 GB support
were verified with `generate --help`. The pinned q8 weights revision is
`69f8f11996b7b2ee54e82d0db7a5acad14b8685d`. Even omitting audio and
unneeded pack components, the six required q8 weight files total
**49,986,854,521 bytes** before the separate Gemma text encoder. The model
weights carry the [LTX-2 Community License Agreement](https://github.com/Lightricks/LTX-2/blob/main/LICENSE-2),
not the MIT code license. A direct 10 MiB range request transferred only
5,720,941 bytes in 30 seconds and timed out. The large weight fetch was
stopped early rather than consuming days of network time and disk space.
No LTX GPU inference was executed. The CLI can be retried when weights are
locally accessible; no LTX result is represented as generated here.

The smaller [RIFE MLX implementation](https://github.com/xocialize/rife-mlx)
at `764b89be56497fb26243d1de75f2957f3889e5d3` and the
[RIFE 4.25 converted weights](https://huggingface.co/mlx-community/RIFE-4.25)
at `6b650eaa5664aab280119511fe944861491aa15e` were checked as MIT.
The 22,674,262-byte model downloaded and ran on the actual M2 Metal GPU.
RIFE is a practical visual/temporal fallback, not a claim that the intended
video diffusion hypothesis was tested.

## Reproduce locally

Use an M-series Mac with Python 3.12, FFmpeg, `uv`, and the existing Brush
0.3.0 installation described in [reconstruction setup](M1.md).
The source acquisition command is in [the Mapillary experiment](MAPILLARY_EXPERIMENT.md).
The commands below create new directories and do not overwrite earlier jobs.

```sh
git clone https://github.com/xocialize/rife-mlx.git data/tools/rife-mlx
git -C data/tools/rife-mlx checkout 764b89be56497fb26243d1de75f2957f3889e5d3
uv venv --python 3.12 data/tools/rife-mlx/.venv
uv pip install --python data/tools/rife-mlx/.venv/bin/python -e data/tools/rife-mlx
data/tools/rife-mlx/.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download('mlx-community/RIFE-4.25',
    revision='6b650eaa5664aab280119511fe944861491aa15e',
    local_dir='data/tools/rife-model',
    allow_patterns=['config.json', 'model.safetensors', 'README.md'])
PY
data/tools/rife-mlx/.venv/bin/python scripts/prepare-video-interpolation.py \
  data/samples/mapillary-beijing/images/004_679966948337536.jpg \
  data/samples/mapillary-beijing/images/006_1392394161982828.jpg \
  data/jobs/mapillary-video-4to6-new --width 2048
data/tools/rife-mlx/.venv/bin/python scripts/interpolate-panorama-rife.py \
  data/jobs/mapillary-video-4to6-new/first.png \
  data/jobs/mapillary-video-4to6-new/last.png \
  data/jobs/mapillary-video-4to6-new/rife-65 \
  --weights data/tools/rife-model --levels 6 --wrap 128 --scale 0.5 --fps 24
data/tools/rife-mlx/.venv/bin/python scripts/repair-panorama-seam.py \
  data/jobs/mapillary-video-4to6-new/rife-65 \
  data/jobs/mapillary-video-4to6-new/rife-65-periodic --band 64
```

With the original 54-view SfM dataset already estimated locally, the matched
Gaussian comparison follows:

```sh
data/tools/colmap-venv/bin/python scripts/holdout-panorama.py \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  data/jobs/mapillary-video-4to6-new/holdout-real5 --panorama pano_000006
data/tools/venv/bin/python scripts/augment-interpolated-panorama.py \
  data/jobs/mapillary-video-4to6-new/holdout-real5 \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  data/jobs/mapillary-video-4to6-new/rife-65-periodic/frames/frame_032.png \
  data/jobs/mapillary-video-4to6-new/augmented-real48-periodic6 \
  --target pano_000006 \
  --generation-report data/jobs/mapillary-video-4to6-new/rife-65-periodic/report.json
data/tools/venv/bin/python scripts/reconstruct.py \
  data/jobs/mapillary-video-4to6-new/holdout-real5 \
  data/jobs/mapillary-video-4to6-new/gs-real48-10000 \
  --steps 10000 --resolution 512 --max-splats 150000 \
  --title 'Beijing 4→6 · real 48 baseline' --id beijing-video-baseline
data/tools/venv/bin/python scripts/reconstruct.py \
  data/jobs/mapillary-video-4to6-new/augmented-real48-periodic6 \
  data/jobs/mapillary-video-4to6-new/gs-rife6-10000 \
  --steps 10000 --resolution 512 --max-splats 150000 \
  --title 'Beijing 4→6 · RIFE 6-view GS' --id beijing-video-rife
```

The experiment deliberately does not assign poses to the other 64 frames.
The next quality-first trial should first find a **locally downloadable,
M2-executable generative video or view model** that actually invents plausible
details; RIFE's flow interpolation alone cannot repair occlusions. On this
hardware, model acquisition size and Metal memory must be checked before a
long download. Then test a few overlapping perspective views for consistency,
register only views that localize against observed sparse geometry, and train
a new world only if the image sequence is coherent. More Brush steps or
unverified synthetic camera positions are not a justified fix. The
photographic target #5 pose used here makes this an appearance test with
geometry leakage, not independent 3D reconstruction proof.
