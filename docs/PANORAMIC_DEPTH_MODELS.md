# Panoramic depth candidates: bounded P1 selection

Upstream inspection: 2026-11-06. This is the model/interface/licensing record for
[the panoramic street plan](PANORAMIC_STREET_RECONSTRUCTION_PLAN.md), not a
quality ranking or an inference benchmark. Actual executions and measurements
belong in the experiment report. No model weights or upstream training datasets
are redistributed in Git or the static observation package.

## Selection

**DA² is the primary full-sphere candidate.** Its output is explicitly
scale-invariant *radial distance*, which needs a multiplicative scale rather
than an arbitrary interpretation of relative inverse depth. Its current source
has an MPS path and a PyTorch attention fallback when xFormers is unavailable.
The official code and checkpoint each declare Apache-2.0. The larger checkpoint
is a resource risk to measure on the M2, not proof that it will fit or run fast.

**PanDA-Small is the bounded smaller alternative.** Its official checkpoint
card now explicitly declares Apache-2.0; the plan's checkpoint-license unknown
is resolved at the inspected revision. Its output is affine-invariant radial
depth, so direct multiplication by rays gives only a diagnostic shell until
scale **and offset** are calibrated. **Depth Anything V2 Small on ERP** remains
an intentionally out-of-distribution control. These are distinct models; an
execution of one must not be reported as execution of another.

| Candidate | Published checkpoint bytes | Predicted quantity | Apple implementation finding |
| --- | ---: | --- | --- |
| DA² | 1,378,513,064 | Positive radial distance; scale unknown, not meters | Current README gives macOS installation adjustment; inference disables autocast on MPS; no required custom CUDA kernel in model forward |
| PanDA-Small | 99,538,561 | Affine-normalized radial depth, normally 0–1; larger is farther | Model `infer_image` selects MPS, but stock `run_image.py` unconditionally calls `.cuda()`; a small explicit device wrapper is necessary |
| DAV2-Small | 99,218,434 for native `.pth` | Relative inverse-depth-like score; larger is nearer | Existing Groundshift Transformers/MPS route already used; ERP has no single pinhole camera-Z convention |

Sizes above are Hub file metadata, **not runtime memory measurements**. DA²'s
default inference budget is about 0.6 million pixels, and PanDA's reference
training/inference size is 1008×504. Neither runs the full 7680×3840 source
through its transformer by default. Upsampling a predicted map restores array
dimensions, not lost depth detail.

## Exact sources and checkpoint identities

| Model | Code revision | Weights revision and file | Separately checked license |
| --- | --- | --- | --- |
| DA² | [`d659838585f2bc9967c7e9367af573795271dbbb`](https://github.com/EnVision-Research/DA-2/tree/d659838585f2bc9967c7e9367af573795271dbbb) | [`haodongli/DA-2@0d55ccb5e46b8ed4715fae3a4c04fc897f1689f3`](https://huggingface.co/haodongli/DA-2/tree/0d55ccb5e46b8ed4715fae3a4c04fc897f1689f3), `model.safetensors` | [Code Apache-2.0](https://github.com/EnVision-Research/DA-2/blob/d659838585f2bc9967c7e9367af573795271dbbb/LICENSE), [checkpoint card Apache-2.0](https://huggingface.co/haodongli/DA-2/blob/0d55ccb5e46b8ed4715fae3a4c04fc897f1689f3/README.md) |
| PanDA-Small | [`211e4cc391474176fe6949baebfeac61ada7e44c`](https://github.com/caozidong/PanDA/tree/211e4cc391474176fe6949baebfeac61ada7e44c) | [`ZidongC/PanDA@f1790c6105aa12a387afa9c1279ad28efa20c069`](https://huggingface.co/ZidongC/PanDA/tree/f1790c6105aa12a387afa9c1279ad28efa20c069), `panda_small.pth` | [Code Apache-2.0](https://github.com/caozidong/PanDA/blob/211e4cc391474176fe6949baebfeac61ada7e44c/LICENSE), [checkpoint card Apache-2.0](https://huggingface.co/ZidongC/PanDA/blob/f1790c6105aa12a387afa9c1279ad28efa20c069/README.md) |
| DAV2-Small, existing baseline | Native upstream [`a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`](https://github.com/DepthAnything/Depth-Anything-V2/tree/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf) | Existing scooter uses [`depth-anything/Depth-Anything-V2-Small-hf@5426e4f0f36572d16453bbda7a8389317b1bef99`](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf/tree/5426e4f0f36572d16453bbda7a8389317b1bef99), Transformers conversion | [Small checkpoint Apache-2.0](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf/blob/5426e4f0f36572d16453bbda7a8389317b1bef99/README.md); upstream explicitly licenses Base/Large/Giant differently, CC-BY-NC-4.0 |

Hub LFS SHA-256 identifiers, to compare against an actual local download:

```text
DA² model.safetensors
d8ea568fc3dfb7d7432e5b763de499dd03fb6dc1c2020d84639f35e2dfa4f78e
PanDA panda_small.pth
2e21ad36025f070959765ea31b9056cc8639d1a80d0344d785506f3ff6100c0d
```

Native DAV2's `.pth` is a separate distribution from the existing baseline:
`depth-anything/Depth-Anything-V2-Small@03876f8651c73a60fe4c2c48294e09fcb6838fcf`,
`depth_anything_v2_vits.pth`, SHA-256
`715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378`.
Do not attribute that hash or its preprocessing to the existing HF baseline.

## Actual inference contracts

DA²'s [`SphereViT`](https://github.com/EnVision-Research/DA-2/blob/d659838585f2bc9967c7e9367af573795271dbbb/src/da2/model/spherevit.py)
takes `config` from [`configs/infer.json`](https://github.com/EnVision-Research/DA-2/blob/d659838585f2bc9967c7e9367af573795271dbbb/configs/infer.json).
`SphereViT.from_pretrained(local_checkpoint_directory, config=config).to('mps').eval()`
accepts RGB float `[B,3,H,W]` in 0–1 and returns `[B,H,W]`. ImageNet normalization
is internal. Default `min_pixels=580000`, `max_pixels=620000`, sphere width 1092,
height 546. The forward pass rescales and rounds network dimensions to multiples
of 14. Keep the sphere configuration consistent with the input dimensions;
using the default 1092×546 input avoids silently mismatched angular embeddings.

The [`distance head`](https://github.com/EnVision-Research/DA-2/blob/d659838585f2bc9967c7e9367af573795271dbbb/src/da2/model/vit_w_esphere.py)
exponentiates clipped log-distance and divides by the 98th percentile. The
[`point-cloud helper`](https://github.com/EnVision-Research/DA-2/blob/d659838585f2bc9967c7e9367af573795271dbbb/src/da2/utils/d2pc.py)
multiplies these values by unit sphere rays. The [paper, §1 and §3.2](https://arxiv.org/html/2509.26618v5)
explicitly distinguishes ray distance from camera-Z and trains with scale
alignment. **Raw values are dimensionless, not metric distances.** One panorama
does not establish their common scale with another panorama or with SfM.

PanDA's [`make_model`](https://github.com/caozidong/PanDA/blob/211e4cc391474176fe6949baebfeac61ada7e44c/networks/panda.py)
can construct Small using `midas_model_type='vits', fine_tune_type='inference',
max_depth=1.0, lora=True, train_decoder=True, lora_rank=4`. Load the published
state dictionary strictly, stripping `module.` only when actually present; use
`.to('mps')` rather than the stock CLI's unconditional CUDA call. The model
offers `infer_image(BGR_uint8, input_size=504)` with ImageNet normalization and
resize-to-multiple-of-14 processing. Its [paper, Eq. 1](https://openaccess.thecvf.com/content/CVPR2025/papers/Cao_PanDA_Towards_Panoramic_Depth_Anything_with_Unlabeled_Panoramas_and_Mobius_CVPR_2025_paper.pdf)
subtracts the second percentile then divides by the 2–98 percentile span during
training: scale **and offset** were removed. Its
[`saver.py`](https://github.com/caozidong/PanDA/blob/211e4cc391474176fe6949baebfeac61ada7e44c/saver.py)
uses depth as radial distance, but that convenience export does not recover
the missing offset. Do not reinterpret its optional metric-finetuned indoor
checkpoints as the same model or as established outdoor metric depth.

DAV2's original perspective output is a relative inverse-depth-like score,
not radial distance. On a full ERP there is no single optical axis, so neither
`1 / prediction` nor a pinhole `Z / cos(angle)` conversion is justified without
an explicit fitted model and suitable sparse observations. Preserve raw ERP
scores, show them as an OOD diagnostic, and report calibration failure when
evidence does not support backprojection. The existing crop calibration in
[DEPTH_EXPERIMENT.md](DEPTH_EXPERIMENT.md) is not full-sphere calibration.

The upstream export coordinate systems are different: DA²'s helper has Z up,
whereas PanDA's helper has Y up and reversed longitude. Groundshift should
project each raw scalar map using its own tested ERP unit-ray convention and
record that convention, rather than copying an unexplained helper transform.

## Dependencies and installation scope

DA²'s [upstream environment](https://github.com/EnVision-Research/DA-2/blob/d659838585f2bc9967c7e9367af573795271dbbb/src/pyproject.toml)
pins Python-package versions including Torch 2.5.0, torchvision 0.20.0,
xFormers 0.0.28.post2 and a specific utils3d commit. The README's tested system
is Ubuntu/CUDA/RTX 3090, and its macOS note explicitly removes xFormers. The
current [`infer.py`](https://github.com/EnVision-Research/DA-2/blob/d659838585f2bc9967c7e9367af573795271dbbb/infer.py)
disables autocast on MPS, while `infer.sh` still supplies CUDA/FP16 Accelerate
configuration. Call the explicit FP32 model interface for this experiment;
do not present the shell script as a verified Mac command.

The core model path uses Torch/torchvision, einops and Hugging Face Hub; no
hosted inference, model API key, diffusion inference or training framework is
needed. Public model downloads do not require creating an account. Optional
Open3D/Gradio/training/export dependencies are not a reason to replace the
existing local file writer and browser viewer. Record actual installed
versions in each execution manifest; the upstream training pins are not
automatically the versions executed by Groundshift.

License checks of relevant direct dependencies: [Torch](https://github.com/pytorch/pytorch/blob/v2.5.0/LICENSE)
and [torchvision](https://github.com/pytorch/vision/blob/v0.20.0/LICENSE) use BSD
licenses; [einops](https://github.com/arogozhnikov/einops/blob/main/LICENSE) MIT;
[Hugging Face Hub](https://github.com/huggingface/huggingface_hub/blob/main/LICENSE)
and [safetensors](https://github.com/huggingface/safetensors/blob/main/LICENSE)
Apache-2.0. DA²'s pinned
[utils3d](https://github.com/EasternJournalist/utils3d/blob/3913c65d81e05e47b9f367250cf8c0f7462a0900/LICENSE)
is MIT. Its optional export helper imports
[`plyfile`, GPL-3.0-or-later](https://pypi.org/project/plyfile/); it is not a
permissive library merely because DA² is Apache-2.0. Model code/weights remain
local and are not bundled into the static viewer. This is a direct-dependency
inspection, not a complete transitive binary license inventory.

## Training-data terms: commercial clearance remains incomplete

The publisher's checkpoint license is separately recorded above. It does not
relicense the training images or establish permission to reproduce the training
pipeline. These candidates are being evaluated locally; **none is declared
fully cleared for future commercial training-data use by this investigation**.

- DA²'s [paper](https://arxiv.org/html/2509.26618v5) names Hypersim, Virtual
  KITTI2, MVS-Synth, UnrealStereo4K, 3D-Ken-Burns, Dynamic Replica and Structured3D,
  plus FLUX.1-dev-based panoramic outpainting in data curation. Its
  [derived dataset card](https://huggingface.co/datasets/haodongli/DA-2) says
  Apache-2.0, but the original [Virtual KITTI2 owner](https://europe.naverlabs.com/proxy-virtual-worlds-vkitti-2/)
  explicitly restricts the dataset to CC-BY-NC-SA-3.0. Do not infer that the
  derived dataset card overrides original data terms. The other source data
  and curation-model chains are not fully audited here; none is downloaded.
- PanDA's [paper](https://openaccess.thecvf.com/content/CVPR2025/papers/Cao_PanDA_Towards_Panoramic_Depth_Anything_with_Unlabeled_Panoramas_and_Mobius_CVPR_2025_paper.pdf)
  names Structured3D/Deep360 supervised data and ZInD/360+x unlabeled data.
  [Structured3D](https://structured3d-dataset.org/) has separate dataset
  [Terms of Use](https://drive.google.com/file/d/13ZwWpU_557ZQccwOUJ8H5lvXD7MeZFMa/view),
  not the MIT license of its code. The original linked PDF was downloaded and
  text-extracted: clauses 1–2 limit use to noncommercial research/education and
  prohibit redistribution of downloaded data. [Deep360](https://github.com/nju-ee/MODE-2022)
  links separately hosted data; its BSD code license alone does not establish
  dataset redistribution rights. The additionally linked
  [Diverse360 card](https://huggingface.co/datasets/Any360D/Diverse360) has no
  license metadata. ZInD/360+x image-rights chains remain unverified. Do not
  redistribute these datasets based on PanDA's Apache checkpoint card.
- DAV2 Small's permissive checkpoint license is explicit. Its pretraining and
  pseudo-label data chain is not a blanket license for all training sources.
  Keep the existing Small baseline, and do not silently move to an NC larger
  checkpoint or assume a source-image license changes after inference.

The experiment's actual Mapillary/Commons panorama remains subject to the
existing CC-BY-SA-4.0 provenance. Model checkpoint terms, source-photo terms,
and the license for Groundshift's own scripts are separate records.

Upstream text/code/API snapshots used for this investigation are retained
locally under `data/jobs/panoramic-depth-research-20261106/`. Model execution,
download checksums, unsupported operators and memory limits must be recorded
by the actual run; static source inspection is not an MPS PASS.
