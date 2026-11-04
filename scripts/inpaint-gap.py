#!/usr/bin/env python3
"""Complete a geometric warp's holes locally; this is NOT novel-view validation.

White mask pixels are synthetic, black pixels are preserved exactly after the
explicit working-resolution resize. No camera poses are inferred or exported.
Model downloads are pinned, ungated, safetensors-only, and under 3 GB.
"""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
MODEL = "stable-diffusion-v1-5/stable-diffusion-inpainting"
REVISION = "8a4288a76071f7280aedbdb3253bdb9e9d5d84bb"
LICENSE = "CreativeML OpenRAIL-M"
WEIGHT_BYTES = 2740652750
MODEL_FILES = ["model_index.json", "**/*.json", "tokenizer/merges.txt",
               "**/*.fp16.safetensors"]


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_inputs(image_path, mask_path, max_edge):
    from PIL import Image
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    with Image.open(mask_path) as source:
        if source.mode not in ("1", "L"):
            raise ValueError("Mask must be a grayscale binary image: 0 preserved, 255 synthetic")
        mask = source.convert("L")
    if image.size != mask.size:
        raise ValueError("Reference and mask must have identical dimensions")
    histogram = mask.histogram()
    if any(histogram[1:255]):
        raise ValueError("Mask contains nonbinary pixels; only 0 and 255 are accepted")
    if not histogram[255] or not histogram[0]:
        raise ValueError("Mask requires both a nonempty hole and preserved reference pixels")
    original_size = image.size
    ratio = min(1, max_edge / max(image.size))
    size = tuple(int(side * ratio) // 8 * 8 for side in image.size)
    if min(size) < 64:
        raise ValueError("Working image dimensions must each be at least 64 pixels")
    if size != image.size:
        image = image.resize(size, Image.Resampling.LANCZOS)
        mask = mask.resize(size, Image.Resampling.NEAREST)
    histogram = mask.histogram()
    if not histogram[255] or not histogram[0]:
        raise ValueError("Resizing removed either the mask hole or preserved reference")
    return image, mask, {"originalSize": list(original_size), "workingSize": list(size),
                         "syntheticPixels": histogram[255],
                         "syntheticFraction": histogram[255] / (size[0] * size[1])}


def compose_preserving_reference(generated, reference, mask):
    from PIL import Image
    if generated.size != reference.size:
        raise ValueError("Diffusion output dimensions differ from reference")
    return Image.composite(generated.convert("RGB"), reference, mask)


def infer(args, image, mask, report):
    # Standard HTTP avoids the Xet worker cancellation delay observed on this Mac.
    # An explicitly configured transport still takes precedence.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    import torch
    from diffusers import StableDiffusionInpaintPipeline
    from huggingface_hub import snapshot_download

    report["versions"] = {package: importlib.metadata.version(package) for package in
                          ("torch", "diffusers", "transformers", "huggingface-hub", "Pillow")}
    if not torch.backends.mps.is_available():
        raise RuntimeError("Apple Metal/MPS is unavailable; no automatic CPU or cloud fallback")
    report["device"] = "mps"
    report["downloadTransport"] = "http" if os.environ["HF_HUB_DISABLE_XET"] == "1" else "hub-default"
    report["modelDownload"] = "RUNNING"
    write_json(args.output / "report.json", report)
    started = time.monotonic()
    snapshot = snapshot_download(MODEL, revision=REVISION, token=False,
                                 cache_dir=str(args.cache), allow_patterns=MODEL_FILES,
                                 local_files_only=args.offline)
    report["modelDownload"] = "PASS"
    report["downloadSeconds"] = time.monotonic() - started
    files = sorted(Path(snapshot).rglob("*.safetensors"))
    total = sum(path.stat().st_size for path in files)
    if total != WEIGHT_BYTES:
        raise ValueError(f"Pinned FP16 weight set has unexpected size: {total} bytes")
    report["model"]["downloadedWeightBytes"] = total
    write_json(args.output / "report.json", report)
    print(f"Loaded pinned snapshot metadata; {total} bytes of FP16 weights", flush=True)
    pipeline = StableDiffusionInpaintPipeline.from_pretrained(
        snapshot, torch_dtype=torch.float16, variant="fp16", use_safetensors=True,
        local_files_only=True,
    ).to("mps")
    pipeline.enable_attention_slicing()
    pipeline.vae.enable_slicing()
    generator = torch.Generator(device="cpu").manual_seed(args.seed)
    torch.mps.synchronize()
    started = time.monotonic()
    report["gpuInference"] = "RUNNING"
    write_json(args.output / "report.json", report)
    def completed_step(_pipeline, index, _timestep, callback_kwargs):
        report["denoisingStepsExecuted"] = index + 1
        return callback_kwargs
    output = pipeline(prompt=args.prompt, negative_prompt=args.negative_prompt,
                      image=image, mask_image=mask, width=image.width, height=image.height,
                      num_inference_steps=args.steps, guidance_scale=args.guidance,
                      strength=args.strength, generator=generator,
                      callback_on_step_end=completed_step)
    torch.mps.synchronize()
    report["inferenceSeconds"] = time.monotonic() - started
    report["mpsAllocatedBytesAfterInference"] = torch.mps.current_allocated_memory()
    report["mpsDriverAllocatedBytesAfterInference"] = torch.mps.driver_allocated_memory()
    report["memoryMeasurementNote"] = "MPS allocations after inference are not peak GPU usage"
    report["safetyFlagged"] = bool(output.nsfw_content_detected and any(output.nsfw_content_detected))
    if report["safetyFlagged"]:
        raise RuntimeError("Model safety checker flagged this result; no completed image exported")
    report["gpuInference"] = "PASS"
    return output.images[0]


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("reference", type=Path, help="Geometry-warped RGB image, not a panorama")
    result.add_argument("mask", type=Path, help="Binary grayscale PNG: white=hole, black=preserve")
    result.add_argument("output", type=Path, help="New local job directory; existing paths are rejected")
    result.add_argument("--prompt", required=True)
    result.add_argument("--negative-prompt", default="distorted geometry, duplicate objects, text, watermark")
    result.add_argument("--seed", type=int, default=0)
    result.add_argument("--steps", type=int, default=20)
    result.add_argument("--guidance", type=float, default=7.5)
    result.add_argument("--strength", type=float, default=0.99)
    result.add_argument("--max-edge", type=int, default=512)
    result.add_argument("--cache", type=Path, default=ROOT / "data/tools/diffusion-models")
    result.add_argument("--offline", action="store_true", help="Use only already cached model files")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if not (1 <= args.steps <= 100 and 64 <= args.max_edge <= 512 and
            0 <= args.seed < 2**32 and math.isfinite(args.guidance) and
            0 <= args.guidance <= 20 and math.isfinite(args.strength) and
            0 < args.strength <= 1 and args.steps * args.strength >= 1):
        print("Invalid settings: steps 1..100, max-edge 64..512, seed uint32, guidance 0..20, "
              "strength (0,1] with at least one effective denoising step", file=sys.stderr)
        return 2
    if args.output.exists():
        print("Output directory already exists; refusing to overwrite evidence", file=sys.stderr)
        return 2
    args.output.mkdir(parents=True)
    started = time.monotonic()
    report = {
        "schemaVersion": 1, "status": "RUNNING", "createdAt": datetime.now(timezone.utc).isoformat(),
        "operation": "synthetic-masked-2d-completion", "synthetic": True,
        "limits": "This is a partial diffusion step, not pose-conditioned or multi-view-consistent synthesis. "
                  "Generated pixels are not observed geometry. A seed does not guarantee cross-view consistency.",
        "geometryValidation": "NOT RUN", "multiViewConsistency": "NOT RUN",
        "browserRendering": "NOT RUN", "gpuInference": "NOT RUN", "modelDownload": "NOT RUN",
        "model": {"repository": MODEL, "revision": REVISION, "license": LICENSE,
                  "licenseUrl": f"https://huggingface.co/{MODEL}/blob/{REVISION}/README.md",
                  "format": "safetensors", "variant": "fp16", "expectedWeightBytes": WEIGHT_BYTES},
        "settings": {"seed": args.seed, "steps": args.steps, "guidance": args.guidance,
                     "strength": args.strength, "maxEdge": args.max_edge,
                     "prompt": args.prompt, "negativePrompt": args.negative_prompt},
    }
    def cancelled(_signum, _frame):
        raise KeyboardInterrupt("Inpainting interrupted")
    previous = signal.signal(signal.SIGTERM, cancelled)
    code = 1
    try:
        write_json(args.output / "report.json", report)
        with (args.output / "inference.log").open("w", buffering=1) as log:
            with redirect_stdout(log), redirect_stderr(log):
                try:
                    image, mask, metadata = prepare_inputs(args.reference, args.mask, args.max_edge)
                    report["input"] = {**metadata,
                                       "referenceSha256": sha256(args.reference), "maskSha256": sha256(args.mask)}
                    image.save(args.output / "reference.png")
                    mask.save(args.output / "mask.png")
                    write_json(args.output / "report.json", report)
                    generated = infer(args, image, mask, report)
                    completed = compose_preserving_reference(generated, image, mask)
                    output = args.output / "completed.png"
                    completed.save(output)
                    report["output"] = {"file": output.name, "sha256": sha256(output),
                                        "bytes": output.stat().st_size,
                                        "unmaskedPixelsPreserved": True}
                    report["status"] = "PASS"
                    code = 0
                except BaseException as error:
                    report["status"] = "CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL"
                    report["error"] = f"{type(error).__name__}: {error}"
                    if report["gpuInference"] == "RUNNING":
                        report["gpuInference"] = report["status"]
                    if report["modelDownload"] == "RUNNING":
                        report["modelDownload"] = report["status"]
                    traceback.print_exc()
    finally:
        signal.signal(signal.SIGTERM, previous)
        report["elapsedSeconds"] = time.monotonic() - started
        report["processPeakRssBytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
        write_json(args.output / "report.json", report)
    print(json.dumps({"status": report["status"], "gpuInference": report["gpuInference"],
                      "report": str(args.output / "report.json")}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
