# Sample data

## M0: a real captured Houseplant

The default world uses Marcel Padilla's **Houseplant**, a photographic Gaussian Splatting reconstruction. It has 113,648 splats and is 3,636,736 bytes. The small scan exercises actual splat decoding and browser rendering without introducing a large scene download.

Acquire the exact asset:

```sh
node scripts/fetch-sample.mjs
```

The script downloads one file from a pinned GitHub revision, verifies its byte count and SHA-256, and saves it as `public/worlds/sample/plant.splat`. A verified existing file is reused; an existing file with a different hash is preserved and reported as an error. The download is the only remote step. Viewing subsequently uses the local file. Git ignores the binary.

The world manifest is [`public/worlds/sample/world.json`](../public/worlds/sample/world.json). Attribution, source metadata, and the original license are next to it. The viewer must keep the manifest's attribution visible when this sample is loaded.

## Provenance and license

The [author's dataset page](https://marcelpadilla.com/Gaussian_Splat_Object_Dataset/) identifies captured objects as CC-BY-4.0. We checked the [specific Houseplant metadata](https://github.com/marcelpadilla/splats/blob/c3e5ec0a8ddb3ab26f28a067a29d272fe1a23411/data/plant/meta.json) and the [license scope](https://github.com/marcelpadilla/splats/blob/c3e5ec0a8ddb3ab26f28a067a29d272fe1a23411/LICENSE), which explicitly covers the plant capture and reconstruction. Other objects in that repository have different licenses; this selection does not imply that the entire dataset is freely reusable.

The asset bytes remain unmodified. Groundshift applies a display transform and authors an orbit camera. Attribution: **Houseplant by Marcel Padilla, Gaussian Splat Objects Dataset, CC-BY-4.0**. See the [retained attribution](../public/worlds/sample/ATTRIBUTION.md) and [license](https://creativecommons.org/licenses/by/4.0/).

Pinned revision: `c3e5ec0a8ddb3ab26f28a067a29d272fe1a23411`.

SHA-256: `ce9d490b18f16d6730d832227bf541431b8b1a5d167c5a3fe89af4f324c0d8fd`.

## Coordinates and limitations

Upstream metadata explicitly declares asset up as `-y` and units as nonmetric COLMAP reconstruction scale. Groundshift defines a right-handed, +Y-up viewer world. A uniform scale of 1 and quaternion `[1, 0, 0, 0]` (x, y, z, w) rotate the asset 180 degrees about X. This maps `[x, y, z]` to `[x, -y, -z]`; no scale calibration or floor inference is performed.

Directly reading the downloaded 32-byte `.splat` records gives center bounds of approximately `[-0.25860846, -0.5, -0.30487591]` to `[0.25860846, 0.5, 0.30487591]`. Their center is `[0, 0, 0]`. The initial orbit camera `[0.9, 0.45, 1.7]` looks at that center with a 50-degree vertical field of view. It is an authored inspection view based on measured bounds, not a recovered pose or a claim that the origin is a safe walking location.

The sample has only SH degree 0, so it has no view-dependent shading. It is an object scan, not a walkable environment. No source image set or capture trajectory is included with this selected sample; M1 needs a separately licensed image dataset. Rendering this prebuilt sample does not validate local reconstruction.

## Renderer sources checked

- [Spark repository and license](https://github.com/sparkjsdev/spark): MIT; Three.js integration and WebGL2 renderer.
- [Spark SplatMesh](https://sparkjs.dev/docs/splat-mesh/): constructor loading progress, `initialized` promise, disposal, bounds, and transforms. Use uniform scale for this ordinary SplatMesh path.
- [Spark loading documentation](https://sparkjs.dev/docs/loading-splats/): `.splat` file-type inference from the extension and the documented loader error path.

These are integration references. Successful decoding, GPU rendering, and visual quality must be measured separately and recorded in the validation report.

## M1: raw images for independent pose estimation

The first dozer reconstruction used supplied poses and sparse geometry, as documented in [M1](M1.md). A separate acquisition mode provides source JPEGs for an independent image-to-pose experiment:

```sh
python3 scripts/fetch-reconstruction-sample.py \
  --unposed --frames 120 --image-scale 2 \
  --output data/datasets/dozer-unposed-120
```

This path needs only the Python standard library. It selects 120 evenly spaced filenames from the 359 upstream `dozer/images_2` images, including both endpoints. The source files are 1504 × 1000. It copies each decoded ZIP member byte-for-byte, preserving its original lens distortion and any JPEG/EXIF metadata. These are the distribution's half-resolution source photographs, not sensor-raw files or Groundshift-undistorted training images.

The selection comes directly from the ZIP directory. This mode never loads or copies the archive's camera calibration, `transforms.json`, COLMAP camera models, supplied extrinsics, or sparse points. The previously downloaded posed dataset and its cache remain separate; their presence is not an input to this selection. Pass only the new `images/` folder and its `provenance.json` to [local pose estimation](COLMAP.md) when testing unknown poses and intrinsics.

The new directory contains:

- `images/`: unchanged source JPEGs, each checked against its archive byte count and CRC.
- `selected-frames.json`: ordered filenames, zero-based indices in the full sorted source list, original filename sequence numbers, archive member paths, CRCs, sizes, and SHA-256 hashes.
- `provenance.json` and `LICENSE`: source and license information; no camera data.
- `acquisition.json`: settings, measured acquisition duration, resolution, input-byte totals, and final file hashes. It explicitly records that supplied poses, calibration, and geometry were not used.

Acquisition remains pinned to [NerfBaselines revision `6a638951a007c8b47eb8a0301d48b04d18e955cf`](https://huggingface.co/datasets/nerfbaselines/nerfbaselines-data/tree/6a638951a007c8b47eb8a0301d48b04d18e955cf/nerfstudio). The distribution provides a dataset-level [Apache-2.0 license](https://huggingface.co/datasets/nerfbaselines/nerfbaselines-data/blob/6a638951a007c8b47eb8a0301d48b04d18e955cf/nerfstudio/LICENSE), retained locally. HTTP ranges retrieve the selected JPEGs without downloading the full 1.35 GB ZIP. Use a new output directory; existing directories are preserved and rejected.

`--unposed` allows 4–359 images and source scale factors 1, 2, 4, or 8. Its default scale is 2. The existing posed mode remains the default and retains its 4–100-image range and scale factor 4. The unposed path does not imply successful alignment, training, or browser quality; those require separate execution and verification.

The 2026-11-04 acquisition completed in 73.045 seconds. It saved 120 JPEGs totaling 11,590,078 bytes at 1504 × 1000, selecting source sequence numbers 1 through 359 at intervals of three or four. **PASS:** all 120 saved JPEGs match their ZIP CRCs and unchanged cached member bytes, all 123 prepared-file SHA-256 values match `acquisition.json`, and the output contains no camera-transform or sparse-geometry file. Logs are retained in `data/acquisition/dozer-unposed-120.log`; settings and the selected order are in the dataset's acquisition and selection reports. This is acquisition evidence only.

Both acquisition modes now finalize all output images, metadata, point references, and license files before hashing. The schema-version-2 report is written last and excludes itself. In particular, a posed dataset's `ply_file_path` is written before `transforms.json` is hashed. This fixes future acquisition bookkeeping; the original historical report discrepancy described in [the reconstruction audit](RECONSTRUCTION_PROOF.md) is preserved rather than rewritten.

The upstream archive contains image sequences at four resolutions and COLMAP metadata, but no original video. Its image filenames do not provide capture timestamps or a frame rate. A photo slideshow assembled from these images must be labeled as such; it is not an original-video M2 validation.

## Mapillary consecutive 360 experiment (2026-11-05)

The first street-panorama sample is **9 consecutive photographs by Cicero101**,
captured in a Beijing residential courtyard on 2025-05-27 from 05:11:05 through
05:11:13 (the source title does not specify a timezone). They belong to Mapillary
sequence `m4ks1Y6pR3fcIjBz9wXxWt` and are publicly redistributed in a
[Wikimedia Commons sequence category](https://commons.wikimedia.org/wiki/Category:Photographs_of_Beijing_from_Mapillary_(m4ks1Y6pR3fcIjBz9wXxWt)).
This avoids needing a Mapillary API token or creating an account.

```sh
python3 scripts/fetch-mapillary-sample.py
```

The [pinned source manifest](../scripts/samples/mapillary-beijing.json) records
each original filename, Mapillary image ID, source and Commons URLs, author,
license, timestamps, GPS metadata, byte count, SHA-1 and SHA-256. The command
saves unchanged 7680 × 3840 equirectangular JPEGs to
`data/samples/mapillary-beijing/images/`, with `provenance.json`,
`ATTRIBUTION.txt` and `acquisition.json`. It checks every cached or downloaded
source against the pinned hashes and preserves failures in its report.
No source photographs are committed or included in the static viewer release.

**Acquisition PASS:** 9 originals, 34,937,629 bytes; all hashes reverified from
the local cache. An initial 12-image attempt stopped after 9 because Wikimedia
returned HTTP 429. Its failure is retained in
`data/research/acquisition-planned12-failure.json`; no alternate host or
credential was used to bypass that limit. A fresh acquisition can encounter
upstream throttling and should be retried later; it is not guaranteed by the
successful cached validation.

These images are **CC-BY-SA-4.0**, credited to **Cicero101 / Mapillary**, with
Wikimedia Commons as the redistribution source. Individual file descriptions
confirm this license; [Mapillary's official license guidance](https://help.mapillary.com/hc/en-us/articles/115001770409-CC-BY-SA-license-for-open-data)
also requires photographer attribution. Keep the source links, credit, license
link and modification notice with any derivative, and preserve applicable
[ShareAlike terms](https://creativecommons.org/licenses/by-sa/4.0/).

The first 24 category records were inspected for acquisition candidates, with
one-second timestamp intervals and approximate GPS spacing of 1.36–1.45 m
(median 1.447 m). **This is a bounded dense sample, not a claim to have found
Mapillary's globally densest region.** Source GPS coordinates are not measured
full camera poses and must not be substituted for reconstruction extrinsics.
No supplied camera poses or sparse geometry are included.

Inspected previews show quiet paths, building facades, parked bicycles/scooters
and trees. The yellow nadir band and camera operator obstruction must be
excluded from reconstruction views. Moving foliage, any people and panorama
stitching remain potential inconsistencies. Acquisition does not establish
camera-estimation, diffusion, Gaussian training or rendering success; report
those separately after actual execution.
