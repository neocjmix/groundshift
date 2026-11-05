# One object along the existing panorama path

The user redirected the experiment on 2026-11-05 to one object visible before,
during and after passing it. They asked to publish the first result promptly,
then update detailed measurements separately. Diffusion is used only to add
whole intermediate images before depth estimation. It does not fill masks in
a depth warp or repair a trained GS render in this experiment.

## Input and ordering

The target is the stationary white electric scooter with a light blue quilted
handlebar cover, beside a black-and-white scooter. All nine previously acquired
Beijing panoramas show it. They come from Cicero101 / Mapillary via Wikimedia
Commons under CC BY-SA 4.0; the pinned source inventory remains in
[`scripts/samples/mapillary-beijing.json`](../scripts/samples/mapillary-beijing.json).
The camera path passes along one side, giving front/side/rear views, not complete
360-degree coverage. The original 7680×3840 panoramas remain local.

1. Manually select the same approximate target center in the first and last
   panoramas. Triangulate the two bearings with the previously estimated rig
   poses. This selects a viewing direction; it does not invent a new camera.
2. Reproject each panorama toward that target at 512×512 with a 45° horizontal
   field of view. The nine original crops and their analytical projection
   intrinsics are retained.
3. Add seven intermediate images between each adjacent pair using Practical-RIFE
   4.25 on MLX/Metal, then run **whole-frame image-to-image diffusion** on those
   56 initial images. The nine real crops are copied unchanged. This is a small
   local img2img experiment, not a video diffusion model or pose-conditioned
   multiview generator. No masks or depth images enter generation.
4. Estimate the nine original cameras with CPU PyCOLMAP and fix their recovered
   poses as anchors. Register the generated images into that connected model,
   using known perspective intrinsics and additional exhaustive feature matches.
   Generated views receive estimated image-based poses, not positions assigned
   by interpolation time. The first unconstrained sequential reconstruction split
   into three components; this anchored retry retains the original front-to-rear
   coverage in one coordinate frame.
5. Predict relative depth for all 65 images with Depth Anything V2 Small on MPS.
6. Fit each prediction to sparse SfM inverse camera-Z. Refine its scale/offset
   to increase neighboring feature correspondences within 3 pixels and reduce
   clipped reprojection error. These are internal fitting observations, not an
   independent depth validation set.
7. Backproject calibrated depth, keep points agreeing with a nearby original
   photograph's depth and color, merge in the estimated common frame, and voxel
   downsample. Manually observed bounding rectangles in original frames 0, 32
   and 64 define a visual-hull selection around the white scooter. This is an
   approximate object selection, not semantic segmentation or collision data.
   An image whose relative depth cannot obtain a positive scale fit is excluded
   from point fusion, with a FAIL entry, rather than silently flipping its depth.
   Its successfully registered RGB can still participate in GS training.
8. Use the dense points as Brush initialization. Train locally on Metal, then
   publish both the context export and a Gaussian-center selection for the
   white scooter. Display cropping does not correct inaccurate Gaussian geometry.

## Bounded model choice

[PlayCanvas capture guidance](https://github.com/playcanvas/developer-site/blob/main/docs/user-manual/gaussian-splatting/creating/taking-photos.md)
describes 50–100 photographs for small objects and more for larger subjects.
We use 65 as a bounded first-run budget, not a universal minimum or evidence
that generated views equal independent photographs. The medium-sized scooter
and incomplete capture arc remain limits.

[Segmind Tiny-SD](https://huggingface.co/segmind/tiny-sd) is a distilled image
diffusion model under CreativeML OpenRAIL-M. Revision
`cad0bd7495fa6c4bcca01b19a723dc91627fe84f` is pinned. Its model card and
[Diffusers img2img interface](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/img2img)
were checked before use. The [official MPS instructions](https://huggingface.co/docs/diffusers/optimization/mps)
support Apple Silicon and attention slicing. We use fp16, sequential images,
strength 0.2, guidance 3, seed 41, and 30 requested steps (six denoising steps).
The compact model avoids another attempt to acquire the previously blocked
large video diffusion model. Its output can change details and does not enforce
consistent 3D geometry. All computation runs on the local M2 / 16 GB Mac.

## Reproduction

The stages intentionally use the existing separate model environments. Use a
fresh job directory and preserve failed reports when retrying. The download
requires the pinned Tiny-SD repository in `data/tools/object-diffusion-models`.

```sh
job=data/jobs/object-focus-NEW
data/tools/venv/bin/python scripts/object-focus.py prepare "$job"
PYTHONPATH=data/tools/rife-mlx data/tools/rife-mlx/.venv/bin/python \
  scripts/object-focus.py interpolate "$job"
HF_HUB_DISABLE_XET=1 data/tools/diffusion-venv/bin/python \
  scripts/object-focus.py diffuse "$job"

# Original-only point cloud shown by the comparison selector:
data/tools/colmap-venv/bin/python scripts/estimate-poses.py \
  --images "$job/originals/images" --output "$job/poses-real" \
  --camera-model PINHOLE --camera-params 618.0386719675123,618.0386719675123,256,256 \
  --single-camera --fix-intrinsics --guided-matching --max-image-size 512 \
  --max-features 4096 --provenance "$job/originals/provenance.json"
HF_HOME=data/tools/depth-hf-cache data/tools/diffusion-venv/bin/python \
  scripts/infer-relative-depth.py "$job/depth-real" "$job"/originals/images/*.png
data/tools/colmap-venv/bin/python scripts/fuse-object-depth.py \
  "$job/poses-real/dataset" "$job/depth-real" "$job/fusion-real-focused"

data/tools/colmap-venv/bin/python scripts/estimate-poses.py \
  --images "$job/augmented/images" --output "$job/poses" \
  --camera-model PINHOLE --camera-params 618.0386719675123,618.0386719675123,256,256 \
  --single-camera --fix-intrinsics --matching sequential --overlap 10 \
  --guided-matching --max-image-size 512 --max-features 4096 \
  --provenance "$job/augmented/provenance.json"
# Preserve the unconstrained attempt and register into the real-image seed:
mv "$job/poses" "$job/poses-unanchored"
data/tools/colmap-venv/bin/python scripts/register-object-views.py "$job"
HF_HOME=data/tools/depth-hf-cache data/tools/diffusion-venv/bin/python \
  scripts/infer-relative-depth.py "$job/depth" "$job"/augmented/images/*.png
data/tools/colmap-venv/bin/python scripts/fuse-object-depth.py \
  "$job/poses/dataset" "$job/depth" "$job/fusion"
data/tools/venv/bin/python scripts/reconstruct.py \
  "$job/fusion/dataset" "$job/training" --steps 5000 \
  --resolution 512 --max-splats 150000 --title 'Scooter object focus' --id scooter-context
data/tools/venv/bin/python scripts/publish-object-focus.py "$job"
```

Render the new world previews through the actual local browser, then run
`publish-object-focus.py "$job" --finish`, which adds those previews and updates
the chronological lab index. The explicit publication spec includes only
selected source crops, generated images, relative-depth previews, a compact
point cloud, public metadata and world artifacts. The full panoramas, model
weights, raw depth arrays and detailed logs remain local.

## Result-first evidence

Generation completed: 9 observed + 56 generated images, **757.964 seconds** for
the sequential MPS img2img job. Original-only depth inference and fusion also
executed: nine registered original cameras and **41,533** selected dense points.
These are actual execution observations, not image-quality acceptance.

The anchored reconstruction registered **47 / 65** RGB images, including all
nine originals and 38 synthetic images. Eighteen synthetic views failed camera
registration and do not enter training. Depth calibration accepted **34** maps;
13 registered synthetic maps were excluded from point fusion (12 could not fit
a positive depth scale and one lacked enough sparse pairs). The fused object
initialization contains **93,595 points**. Original poses remain fixed during
the anchored registration. These partial outcomes stay visible in the report;
they do not satisfy a 65-camera acceptance claim.

Brush completed 5,000 steps on the **Apple M2 / Metal** adapter in **610.514 s**
using the 47 registered RGB views and the 93,595-point initialization. It exported
**93,941 Gaussians / 8,643,223 bytes**. The process's recorded peak memory footprint
was 915,784,496 bytes; this is not a system-wide unified-memory measurement.
Selecting Gaussian centers inside the three observed object rectangles retained
**93,101 Gaussians** in the focused display artifact.

Actual local Chrome rendering of both exports and the interactive point cloud
is **PASS**. Screenshots show a recognizable scooter and blue cover, with blurred,
streaked surrounding geometry; this is not a clean complete object reconstruction.
The lab's newest/oldest ordering also executed successfully in Chrome. TypeScript
and the production build passed during packaging. Broader regression checks and
public-origin verification follow publication, per the result-first instruction.
Independent depth/pose accuracy and comparative quality measurements remain
**NOT RUN**. Build success and GPU execution do not imply improved visual quality.

Actual stage reports, failed attempts and screenshots are retained under
`data/jobs/object-focus-20261105/`. Browser evidence is recorded separately in
`browser-local.json`; the training job's original `browserRendering: NOT RUN`
field is intentionally not rewritten as if training itself verified a browser.

One early generation invocation ran before its model download completed and
failed without producing images. Its report/log are preserved with a
`diffuse-download-race-failure` name. The pinned download completed and generation
was restarted. No cloud computation or paid inference was used.
