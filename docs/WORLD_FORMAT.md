# World artifact v1

A world is a directory with `world.json`, one Gaussian Splatting asset, and optionally camera metadata. Serve this directory over HTTP alongside the viewer or select it with **Open world folder**. Asset and camera URLs resolve relative to the manifest URL, so replacing a scene does not require changing viewer code.

`src/world.ts` is the executable contract. The parser rejects missing required fields, unknown fields, unsupported versions, nonfinite numbers, invalid camera bases, and unsafe relative paths. Validation checks metadata structure; it does not establish the accuracy of camera poses, the asset's license, or successful rendering.

## Manifest

The following is a **synthetic format example**, not a measured scene, recovered camera pose, or recommended spawn:

```json
{
  "schemaVersion": 1,
  "id": "format-example",
  "title": "Synthetic format example",
  "assets": [{
    "kind": "gaussian-splat",
    "format": "ply",
    "path": "scene.ply"
  }],
  "coordinates": {
    "handedness": "right",
    "upAxis": "y",
    "unit": "arbitrary",
    "assetToWorld": {
      "position": [0, 0, 0],
      "quaternion": [0, 0, 0, 1],
      "scale": 1
    }
  },
  "navigation": {
    "mode": "orbit",
    "camera": {
      "position": [2, 1, 3],
      "target": [0, 0, 0],
      "up": [0, 1, 0],
      "fov": 60,
      "near": 0.01,
      "far": 1000
    },
    "camerasPath": "cameras.json"
  },
  "provenance": {
    "sourceType": "sample",
    "sourceUrl": "https://example.com/replace-with-real-source",
    "license": "Replace with verified dataset license",
    "licenseUrl": "https://example.com/replace-with-real-license",
    "attribution": "Replace with required source attribution",
    "backend": "Replace with producing engine and version",
    "notes": "Document coordinate evidence, camera choice, and limitations here."
  }
}
```

## Coordinate semantics

The viewer world is right handed, with positive Y up. This defines the **world** convention; it does not assert that a source asset is already Y-up. Explicitly describe the source-to-world conversion in provenance. An identity conversion is still an explicit choice that requires source evidence or an honest declaration that orientation is unverified.

For asset-space point `p`, the viewer applies `worldPoint = position + rotate(quaternion, scale * p)`. The quaternion is `[x, y, z, w]`, its length must be within `0.00001` of one, and the uniform scale must be finite and positive. No automatic recentering, unit conversion, axis swap, or floor inference is part of the contract. `unit` is either `arbitrary` or `meters`; reconstruction scale is arbitrary unless known reference measurements establish meters.

The navigation camera `position`, `target`, and `up` are in world coordinates, **after** the asset transform. Three.js cameras look along their local negative Z axis toward `target`; local positive Y is the image-up direction. `up` must be nonzero and nonparallel to the viewing direction. `fov` is vertical field of view in degrees, strictly between 0 and 180. The clipping planes use world units and must satisfy `0 < near < far`. Choose a view from a verified source camera or a visually checked orbit view; an orbit camera is not a claim of a safe walking spawn.

`navigation.mode` accepts `orbit` or `camera-path`. The latter requires `camerasPath` and starts at its first actual camera pose. The authored `navigation.camera` remains required as the orbit fallback and supplies the viewer's vertical FOV and clipping planes in either mode. Path playback does not infer per-frame focal lengths. An orbit world with valid camera metadata also offers a **Camera path** switch. Missing or invalid camera metadata produces a visible warning and leaves the scene usable in orbit; cancellation still cancels the whole load.

## Optional camera sequence v1

`src/camera-path.ts` validates `camerasPath`. Existing native `cameras.json` files remain compatible. Its required fields are:

- `schemaVersion: 1`.
- `cameraConvention: "OpenGL: +X right, +Y up, -Z forward"`.
- `worldConvention: "right-handed Y-up, arbitrary units"`, or `"right-handed Y-up, meters"` when the manifest uses meters.
- A nonempty `frames` array, each with `image` (the source image identifier) and `cameraToWorld` (a row-major 4×4 rigid transform). The upper-left 3×3 rotation must be orthonormal and right handed; translation is the last column, and the last row is `[0, 0, 0, 1]`. Validation allows `0.0001` floating-point tolerance, rejects nonfinite values, and never derives a pose from an image filename.

Camera matrices are already in **world coordinates**, after the source-to-world conversion. The viewer does **not** apply `assetToWorld` to these matrices again. The native exporter transforms camera rotation columns and centers into the same frame as the displayed asset. Another backend must explicitly export this convention; unconverted OpenCV matrices are rejected. Preserve source calibration and the derivation in the reconstruction logs/provenance; this small viewing contract is not a full calibration archive.

Optional continuity fields are backward compatible:

```json
{
  "sequenceNotes": "Describe actual capture ordering, component evidence, omissions and limitations.",
  "frames": [
    { "image": "first-image.png", "componentId": "reconstruction-component-0", "continuousFromPrevious": false, "cameraToWorld": "4x4 numeric matrix required here" },
    { "image": "second-image.png", "componentId": "reconstruction-component-0", "continuousFromPrevious": true, "cameraToWorld": "4x4 numeric matrix required here" }
  ]
}
```

This is an **illustrative field excerpt**, not valid camera JSON or measured data. `sequenceNotes` is optional nonblank text. Per-frame `componentId` is an optional nonblank identifier; `continuousFromPrevious` is an optional boolean describing the edge from the preceding array entry. Its first entry has no incoming edge. Different explicit component IDs always prevent interpolation, even if a continuity flag is true. A missing or false flag also prevents interpolation. Legacy files without these flags therefore provide checkpoints only. Do not label disconnected SfM components as one component: their separate coordinate frames require explicit registration before a shared-world export.

An exporter may mark an edge only when the two poses belong to the same aligned reconstruction component and follow a verified acquisition/extraction sequence without omitted selected views between them. The flag authorizes a straight interpolation for viewing; it does not prove that the camera physically traveled along that segment or that the space is traversable. Never infer continuity merely from sorted filenames or proximity. Record the supporting evidence and uncertainty in `sequenceNotes`.

The viewer linearly interpolates camera centers and uses shortest-arc quaternion interpolation for orientation between marked adjacent poses. **Play path** can run forward or backward, pauses at every unknown/disconnected edge and at endpoints, and pauses when the browser tab becomes hidden. **Previous**, **Next**, and the labeled checkpoint slider explicitly jump between actual camera poses, including across a flagged gap. They do not synthesize the missing path. Speed is measured in camera intervals (views) per second, because capture timestamps and metric scale may be unavailable; it is not walking speed or original video timing.

Drag on the scene, or focus it and use arrow keys, to look around while the position remains on the chosen camera sequence. **Reset view** returns to the first pose and clears free look. Zoom buttons change the viewing field of view in path mode. Switching back to **Orbit** restores the authored orbit camera. No floor, collision, unseen geometry, or free walking is introduced.

Tests of interpolation and camera loading use explicitly synthetic fixtures. The browser control test renders the actual reconstructed asset and actual exported poses, but adds **test-only continuity markers** to intercepted JSON to exercise gap handling. Passing that test proves the controls operate; actual capture-sequence and route-quality acceptance must be recorded separately.

## Asset and provenance constraints

- Exactly one `gaussian-splat` asset is supported. Declared formats are `ply`, `spz`, `splat`, `ksplat`, and `sog`; a format label does not prove that a particular file is decodable. PLY must contain splat attributes, not merely an arbitrary point cloud or mesh.
- Paths must be plain, nonempty relative paths. No absolute paths, empty/dot/traversal segments, backslashes, percent escapes, URL schemes, query strings, fragments, or control characters are accepted. Plain spaces inside filenames are allowed and URL-encoded by the resolver. Asset and camera paths follow the same rule.
- The manifest base URL must be absolute HTTP(S) without embedded credentials. Use a local static server for local files; browsers do not load the artifact through `file:` URLs.
- `sourceType` is `images`, `video`, or `sample`. `sourceUrl` and `licenseUrl` must be absolute HTTP(S) or `file:` URLs without credentials. A local original dataset can use its `file:` URL and a local license document, but absolute paths may expose local directory names when sharing artifacts.
- `license`, `attribution`, and `backend` are required nonblank strings. Record the source license, required credit, and actual producing tool/version. The scene license is independent of the renderer and trainer software licenses. `notes` is optional.

The parser uses [Zod's strict object validation and refinements](https://zod.dev/api). Parser tests use synthetic metadata only and do not count as browser, GPU, reconstruction, or dataset-license validation.
