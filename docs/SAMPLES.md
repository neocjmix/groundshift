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
