# World artifact v1

Storage-only derivatives can change the Gaussian asset from PLY to SPZ while
retaining all coordinate and navigation fields. Keep a separate world ID and
the original native output; never apply the manifest transform twice. A
matching point count/SH degree does not mean float values are lossless:
SPZ quantizes positions and attributes. [Actual SPZ v3 example and checks](COMPRESSION.md).

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

## Optional spatial SPZ delivery v1

The Paris serving prototype adds an optional`streaming: { "path": "chunks/index.json" }`
reference. The original single Gaussian asset remains the complete whole-scene
control. Without this field every older world loads as before. With it the
viewer loads the index and nearby chunks, and offers an explicit whole-scene
comparison mode. A missing/invalid index fails visibly rather than silently
downloading the entire scene. Local folders resolve all declared chunk files
and release their object URLs together on world disposal.

`parseStreamIndex` in`src/world.ts` validates schemaVersion1,
coordinateSpace`viewer-world`,totalSplats,maxResidentChunks(1..8),and1..256
unique ordered chunk records. Each requires a plain relative SPZ path, byte
length, Gaussian count, SHA256 and nonempty finite3Dcamera anchors. Counts must
sum to totalSplats. Chunk paths resolve beside the final redirected index URL.
Their Gaussian coordinates remain in **raw asset space** and receive the same
assetToWorld transform as the complete asset; only the index anchors are already
in viewer-world coordinates. Applying the transform to anchors again is wrong.

The bounded implementation chooses the nearest recorded anchor's region and
adjacent regions, at most maxResidentChunks, with one fetch/decode owner.
It verifies actual byte length/hash/decoded count, aborts obsolete fetches,
disposes obsolete late decode results and evicts distant meshes. Encoded file
sums are not GPU-memory measurements. Unique ownership prevents deliberate
double opacity; it does not guarantee visibility of distant objects whose
owner is unloaded. [Experiment, actual checks and limits](PARIS_STREAMING.md).

## Optional native RAD/LoD delivery v1

A world may instead declare:

```json
"paging": {"path":"rad/index.json","maxPagedSplats":524288,"lodSplatCount":350000}
```

The complete Gaussian SPZ asset remains mandatory as the whole-scene control.
`streaming` and `paging` together are rejected. `maxPagedSplats` must be a
multiple of65536 in65536..2097152;the actual Paris configuration is8pages.
The native target selected count can be lower for a particular view.

`parsePagedIndex` strictly validates schemaVersion1,kind`spark-rad`,root,
sourceSplats and declared files with unique relativepaths,positive bytes and
SHA256. The declared root must exist in that list. No arbitrary filename,
absolute path or traversal is accepted. Final redirected index URL determines
the file base. Root/radc files retain the raw asset-space convention and one
assetToWorld transform; these are not new camera/world solutions.

The HTTP loader fetches metadata only. The pinned-byte adapter feeds Spark's
native `PagedSplats` ranges and declared chunk filenames,verifying whole-file
length/SHA before use. Native paging owns hierarchical selection and eviction;
the adapter tracks actual requests/body bytes/pending/errors. It does not create
a complete decoded JS cache. On disposal,owned native resources and in-flight
requests are released/cancelled. Incomplete/erroring requests stay visible.
WholeSPZ comparison explicitly changes modes and uses the ordinary loader.

Local-folder RAD loading is **not implemented** and fails with an explicit
message; use local HTTP serving or wholeSPZ. Missing/invalid paging does not
silently download the entire scene. The explicit static packager includes only
pinned declared files and verifies byte/hash integrity. Conversion adds coarse
parent GS,so offline RAD can be larger than SPZ; it is not a lossless
compression claim. [Actual fidelity and residency evidence](PARIS_STREAMING.md).

## Retired source-photo background v1 (archival compatibility)

**Withdrawn by the user on 2026-11-07.** Translation misalignment worsens the
experience. Current live worlds omit `background`; the manifest schema still
accepts a safe historical reference so old artifacts open as GS-only worlds.
The current loader never fetches/reads background metadata, photos or meshes,
creates no background object URLs, and the viewer provides no backdrop controls
or render pass. Missing or malformed retired background files do not affect
GS loading. Ordinary cancellation and camera-path behavior remain supported.

The description below records the former experiment's artifact contract and
behavior, retained for interpreting historical evidence and rollback archives;
it does not describe an enabled current viewer feature.

A world may declare `"background": { "path": "background/background.json" }`.
Existing worlds and their bytes remain valid without it. Background completion
is **off by default**: the viewer starts in **GS only**, and background imagery
must never be included when accepting actual Gaussian rendering or geometry.
The optional metadata has strict fields `schemaVersion: 1`, nonempty `views`,
and optional nonblank `notes`. Each view has:

- `id`: unique nonblank source identifier.
- `center`: three finite numbers in viewer-world coordinates.
- `panoramaToWorld`: row-major4×4 right-handed rigid matrix, with translation
  equal to `center`. The rotation maps **CVERP** local rays to viewer-world:
  `lon=(u-.5)*2*pi`, `lat=(.5-v)*pi`,
  `ray=[cos(lat)*sin(lon), -sin(lat), cos(lat)*cos(lon)]`.
  Local+Y points down and local+Z faces the ERP center. This is **not** the
  OpenGL perspective-camera convention; do not apply an extra axis flip.
- `imagePath`: plain relative path to an explicitly licensed ERP background.
- optional `meshPath`: plain relative path to its estimated coarse-depth mesh.

All referenced paths resolve beside the background metadata file. HTTP
redirects determine the final base. Local-folder selection resolves exact
nested filenames and releases all temporary blob URLs on scene disposal.
Invalid optional metadata shows a warning while GS remains usable. Cancellation
continues to cancel the whole load. Textures/meshes are fetched lazily only after
choosing a background mode; interrupted/stale loads cannot replace a later one.
Only the active source texture and mesh are retained.

Mesh JSON has strict fields `schemaVersion: 1`, flat `positions` (XYZ), flat
`uvs` (UV), and triangle `indices`. Positions are **already transformed into
viewer-world units**, including any asset transform; the viewer does not
transform them again. Finite coordinates, matching vertex/UV counts and valid
triangle indices are required. UV uses `[u,1-v]` with the normal Three.js image
texture flipY setting. V must lie in[0,1]. U may lie in[0,2] for duplicated
longitude-seam vertices just past1; RepeatWrapping joins the source ERP seam.
The exporter, rather than the viewer, excludes invalid depths and triangles
crossing declared depth discontinuities. Do not fill omitted geometry by
inventing a surface.

**Panorama backdrop** displays an infinite-distance sphere that follows camera
translation. **Estimated depth shell** draws the declared world-space coarse
mesh over that sphere, retaining the panorama as a hole fallback. Both are
rendered in a separate backdrop pass, then depth is cleared before GS. Thus
they fill display gaps without being treated as physical occluders, measured
surfaces, collision geometry, or Gaussian evidence. Near objects may double and
parallax may disagree. Background source selection uses the nearest declared
center with15% distance hysteresis and deterministic ties. It swaps only after
the replacement loads; this is not view synthesis or continuous appearance
blending. Original source positions, training exclusions, licensing and all
remaining geometric uncertainty belong in the experiment provenance.

The static packager validates the background contract, includes only explicitly
referenced image/mesh files, rejects symlinks/private metadata and validates
mesh indices. It never walks the source dataset. Synthetic contract tests prove
these boundaries; actual public browser screenshots are required separately.

In the tangent-background experiment, the lower15% of its derived display ERP
textures replaces existing orange camera artwork with per-column boundary-tone
extrapolation blended toward a global mean. `background.notes` records this
modified region. This is generated display color only; source originals,
training RGB, depth inference and point clouds remain unchanged. It is not a
reconstructed floor, a new photograph, or diffusion training augmentation.

This fixed display fill does not remove artwork above its lower 15% boundary;
the executed experiment retains orange artwork in some views. Because backdrop
depth is cleared before GS, it also cannot erase an opaque artifact already
drawn by the Gaussians. Actual route and up/down comparisons show limited,
view-dependent completion rather than uniform dark-pixel or quality improvement.
