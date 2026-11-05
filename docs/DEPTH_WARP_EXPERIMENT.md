# Depth-calibrated observed-pixel warp and one generated view

This follow-up uses the same licensed Beijing Mapillary/Commons sequence as
[the relative-depth diagnostic](DEPTH_EXPERIMENT.md). Its direct inputs are
the **one-based panorama files** `pano_000004` and `pano_000006`, with
`pano_000005` as the appearance target. These map to zero-based source
manifest entries **3, 5 and 4**, respectively. The separate
[65-frame RIFE trial](PANORAMA_VIDEO_EXPERIMENT.md) used zero-based original entries
4 and 6, with entry 5 as target; its results and 48-real-image GS baseline are
not interchangeable with this trial.

## Experiment and evidence boundary

The target photo's RGB was withheld from depth calibration, reprojection,
masked diffusion and GS training. The existing **all-image** fixed-rig SfM
model nevertheless used that photo for its estimated camera and sparse
initialization. Consequently this is an appearance holdout, not an independent
geometry or genuinely unknown-pose test. Relative model depth and SfM depth
are in arbitrary scale; no metric camera baseline, GPS alignment, gravity or
true depth is asserted.

The local 512×512 depth map from each endpoint was sampled at the corresponding
PyCOLMAP sparse features. A robust Huber fit mapped each source's relative
depth to **inverse camera Z**. A deterministic 20% point-ID holdout measured
internal calibration residuals; those same photographs produced both
predictor input and SfM points, so this is not external ground truth. Observed
RGB pixels were backprojected through calibrated Z and projected to the
existing middle camera with a z-buffer. At overlapping projected pixels, a
conservative gate retained values only when the two source depths agreed
within 20% and RGB mean absolute difference was at most 32/255. A pixel
provided by only one source passed the gate without cross-view verification.
No target RGB was read by that process.

| Same 512×512 target direction | Projected support | MAE against actual photo on own support | Shared-pixel comparison |
| --- | ---: | ---: | --- |
| Corrected 512px stereo, observed RGB | 36,078 / 262,144 (13.76%) | 30.97 / 255 | Baseline |
| Learned depth, raw observed RGB | 259,156 (98.86%) | 38.32 / 255 | Stereo 30.88 vs depth 49.85 on 35,889 common pixels |
| Learned depth, source-consistent observed RGB | 172,193 (65.69%) | 26.48 / 255 | Stereo 27.47 vs depth 33.90 on 15,320 common pixels |

The support masks differ: the 26.48 versus 30.97 own-support errors **cannot**
be read as a depth win. On the common pixels, stereo was better. The raw 98.86%
coverage is a projection count, not 98.86% correct pixels; visual inspection
showed doubled bicycles and streaks. The conservative mask left 34.31% to
generate, and even its singly sourced pixels were not mutually verified.
These numbers came from the retained local reports, not from a benchmark claim.

Stable Diffusion 1.5 Inpainting on MPS filled only the mask (20 configured
steps; 19 denoising steps executed; seed 41). The GPU inference measured
59.657 s and the job 70.246 s; `/usr/bin/time` was not used for this stage.
The unmasked pixels were preserved exactly. Against the separately opened
actual target photo, full-image MAE was **39.395** for the generated completion
and **39.929** for a flat 128-gray fill. PSNR was **12.366 dB** for generation
and **12.745 dB** for gray. This is a small MAE gain with a PSNR loss and does
not prove visual plausibility or multiview consistency. The model license is
[CreativeML OpenRAIL-M](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting/blob/8a4288a76071f7280aedbdb3253bdb9e9d5d84bb/README.md).

## Reproduce the bounded local stages

Use the sample acquisition and fixed-rig pose instructions in
[Mapillary experiment](MAPILLARY_EXPERIMENT.md) and
[relative-depth diagnostic](DEPTH_EXPERIMENT.md) first. These commands write
new ignored `data/jobs/` directories; use fresh output names for a rerun.
The PyCOLMAP environment additionally needs Pillow.

```sh
data/tools/venv/bin/python scripts/warp-panorama-gap.py \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  data/jobs/mapillary-depth-stereo-view02-corrected-20261105 \
  --left pano_000004_view_02.png --right pano_000006_view_02.png \
  --target pano_000005_view_02.png

data/tools/colmap-venv/bin/python scripts/warp-learned-depth.py \
  data/jobs/mapillary-depth-v2-3views-20261105 \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset/sparse \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  data/jobs/mapillary-depth-warp-view02-v3-20261105

data/tools/venv/bin/python scripts/evaluate-warp-coverage.py \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset/images/pano_000005_view_02.png \
  data/jobs/mapillary-depth-stereo-view02-corrected-20261105 \
  data/jobs/mapillary-depth-warp-view02-v3-20261105 \
  data/jobs/mapillary-depth-warp-comparison-20261105

HF_HUB_DISABLE_XET=1 data/tools/diffusion-venv/bin/python scripts/inpaint-gap.py \
  data/jobs/mapillary-depth-warp-view02-v3-20261105/warp-consistent.png \
  data/jobs/mapillary-depth-warp-view02-v3-20261105/mask-consistent.png \
  data/jobs/mapillary-depth-inpaint-view02-20261105 \
  --prompt 'a plausible residential courtyard with trees, fence, parked bicycles and scooters, continuous walkway, natural daylight, coherent photographic details' \
  --steps 20 --seed 41 --max-edge 512 --offline

data/tools/diffusion-venv/bin/python scripts/augment-generated-view.py \
  data/jobs/mapillary-beijing-rig-holdout \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  images/pano_000005_view_02.png \
  data/jobs/mapillary-depth-inpaint-view02-20261105 \
  data/jobs/mapillary-depth-augmented-view02-20261105 \
  --source-reference data/jobs/mapillary-depth-warp-view02-v3-20261105/warp-consistent.png \
  --source-mask data/jobs/mapillary-depth-warp-view02-v3-20261105/mask-consistent.png

python3 scripts/reconstruct.py \
  data/jobs/mapillary-depth-augmented-view02-20261105 \
  data/jobs/mapillary-depth-gs-10000-20261105 \
  --steps 10000 --resolution 512 --max-splats 150000 \
  --title 'Beijing · depth-guided generated view' \
  --id mapillary-beijing-depth-generated
```

The comparison baseline is
`data/jobs/mapillary-beijing-rig-baseline-10000/world/scene.ply`,
trained on the **same 48 actual photo crops with panorama 5 RGB withheld**,
for 10,000 Metal steps at 512px and a 150,000-splat cap. Each generated
RGB file must carry an existing, explicit target camera; it cannot estimate
one from its own appearance. View 02 of panorama 5 becomes a training view
in the augmented dataset, so the independent appearance comparison uses
other withheld panorama-5 directions.

The augmented 49-image Brush 0.3.0 job **PASS**ed on the logged Apple M2
Metal adapter. It completed 10,000 steps in **979.402 s**, exported
**150,000 splats** in a **13,800,652-byte PLY**, and reported a whole-process
peak memory footprint of **975,455,024 bytes**. These figures describe this
single run, not a general benchmark or a claim about image quality. The
baseline and augmented scenes have the same training step, resolution and
splat cap; they differ by the one synthetic target-direction crop.

## Actual headed Chrome render comparison

Both PLYs were rendered with the same existing SfM camera for two photo-5
directions **01 and 03**. These RGB crops were not in either GS training set.
The renderer was Chrome/WebGL/Three.js/Spark; all four renders returned
**PASS**, with nonzero Gaussian pixels. The photo-5 pose and sparse
initialization still came from all-image SfM, so this is not a fully
independent novel-pose test. The generated direction 02 itself was included
in augmented training and was not used as an independent GS score.

| Held-out RGB direction | Real-only GS MAE / PSNR | +1 generated-view GS MAE / PSNR | Visual observation |
| --- | ---: | ---: | --- |
| 01 | 38.900 / 13.929 dB | 39.874 / 13.849 dB | Leaves, fence and motorbike remain streaked; augmented result looks softer |
| 03 | 23.903 / 17.309 dB | 26.028 / 16.884 dB | Building, steps and trees recognizable; augmented result has stronger ghosting |

**Metal training and browser rendering PASS; improvement FAIL.** The visual
inspection agrees with the higher RGB error on both directions. Scene-level
plausibility remains subjective: the rendered courtyard is recognizable as a
place, but blurred geometry, double edges and near-field distortions remain.
One masked generated crop did not add a new measured camera or consistent 3D
constraints. The source-agreement gate reduced clearly contradictory
projections but did not certify singly sourced pixels, and the diffusion fill
has no multiview consistency objective. A more complex model or more generated
frames is not justified by this run alone.

The exact render comparison can be repeated with the stored world files:

```sh
node scripts/render-posed-view.mjs \
  --dataset data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  --ply data/jobs/mapillary-beijing-rig-baseline-10000/world/scene.ply \
  --frame images/pano_000005_view_03.png --alpha-threshold 128 \
  --output data/jobs/mapillary-depth-render-view03-baseline
node scripts/render-posed-view.mjs \
  --dataset data/jobs/mapillary-beijing-rig-poses-v2/dataset \
  --ply data/jobs/mapillary-depth-gs-10000-20261105/world/scene.ply \
  --frame images/pano_000005_view_03.png --alpha-threshold 128 \
  --output data/jobs/mapillary-depth-render-view03-generated
data/tools/venv/bin/python scripts/compare-gap.py \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset/images/pano_000005_view_03.png \
  data/jobs/mapillary-depth-render-view03-baseline/input.png \
  data/jobs/mapillary-depth-render-view03-generated/input.png \
  data/jobs/mapillary-depth-render-view03-comparison
```

Repeat for `view_01` using fresh output directories. The render script
uses local port 4326, so run its invocations sequentially.

The public observation release contains only selected licensed 512px crops,
generated images, rendered results, sanitized metrics and the derived world.
Original 7680×3840 photos, raw depth arrays, model weights and training logs
remain local under ignored `data/`.
