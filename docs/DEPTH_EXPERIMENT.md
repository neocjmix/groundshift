# Relative-depth diagnostic on three public panoramas

The user suggested estimating depth from photographs before trying more
interpolated views. This initial local diagnostic was not a reconstructed world
or a demonstrated GS improvement. The [observation page](https://groundshift-viewer-production.up.railway.app/experiments/depth-v2/)
shows the three observed crops beside their predicted depth maps.

## Input and model

Use the same CC-BY-SA-4.0 Beijing panorama sequence and attribution recorded in
[the sample manifest](../scripts/samples/mapillary-beijing.json). The inputs are
the real photos numbered 4, 5 and 6, each projected into the same 512 × 512
view 02 by the existing fixed-rig preparation. Photo 5 participates in this
diagnostic; it is not a held-out depth ground truth.

The pinned model is
[`depth-anything/Depth-Anything-V2-Small-hf`](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf)
at revision `5426e4f0f36572d16453bbda7a8389317b1bef99`. The small model is
Apache-2.0; upstream explicitly documents MPS device selection and describes
its output as **relative depth**, not meters. [Official upstream](https://github.com/DepthAnything/Depth-Anything-V2).
Only the model code and inference run locally on the M2; model weights are not
in Git or Railway.

## Executed local run

```sh
HF_HOME=data/tools/depth-hf-cache /usr/bin/time -l \
  data/tools/diffusion-venv/bin/python scripts/infer-relative-depth.py \
  data/jobs/mapillary-depth-v2-3views-20261105 \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset/images/pano_000004_view_02.png \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset/images/pano_000005_view_02.png \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset/images/pano_000006_view_02.png
data/tools/colmap-venv/bin/python scripts/check-depth-against-sfm.py \
  data/jobs/mapillary-depth-v2-3views-20261105 \
  data/jobs/mapillary-beijing-rig-poses-v2/dataset/sparse
```

The three-view cached-model run took **3.361 s** inside the Python job, with
per-image MPS inference **1.168 / 0.624 / 0.650 s**. `/usr/bin/time -l`
measured **7.58 s** whole command elapsed, **517,373,952 bytes** maximum RSS
and **1,619,919,952 bytes** peak process memory footprint. These are observed
whole-process values, not isolated GPU allocation or general benchmarks. The
preceding one-image cold download/smoke run took 35.123 s of model load plus
inference and is preserved separately; it was not used for the three-view
timing.

For each camera, the diagnostic samples the depth model at COLMAP sparse
feature positions and compares the ordering against inverse positive camera-Z
of the corresponding SfM 3D points. The model output is closer-is-larger and is
normalized **separately for each displayed image**.

| Real photo | Sparse feature observations | Rank correlation with inverse SfM Z |
| --- | ---: | ---: |
| 4 | 317 | 0.876 |
| 5 | 312 | 0.888 |
| 6 | 281 | 0.913 |

**PASS:** Apple MPS inference on all three real photos, finite 512 × 512 depth
arrays, inspected visual depth separation, and positive internal depth-order
agreement. **NOT RUN in this initial diagnostic:** metric calibration, independent depth ground truth,
cross-view consistency, depth-guided reprojection to a new position, GS training
with this depth, and browser rendering of a new depth-assisted GS world. All-image
SfM estimated the comparison points from the same photographs, so correlation
is not an independent accuracy score. A high rank correlation does not prove
that a bike contour or occluded surface is geometrically correct.

The raw arrays, local source images, model weights and run logs remain under
ignored `data/`. The public report includes only three selected licensed crops,
their depth visualizations and a sanitized summary with per-photo source links.
The subsequent [bounded comparison](DEPTH_WARP_EXPERIMENT.md) calibrated relative
inverse depth against sparse SfM points on the two endpoint views, warped their
*observed* pixels to photo 5's existing estimated camera, and measured coverage
and errors against a corrected same-direction stereo result. A stronger multi-view model such as
[Depth Anything 3](https://github.com/ByteDance-Seed/Depth-Anything-3)
supports pose-conditioned depth, but its official examples target CUDA; Apple
MPS behavior on this Mac is **NOT RUN**. Its small checkpoint does not directly
export Gaussian splats; upstream limits that branch to giant models.
