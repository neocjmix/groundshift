# World artifact v1

A world is a directory with `world.json`, one Gaussian Splatting asset, and optionally original camera metadata. Serve this directory over local HTTP alongside the viewer. Asset URLs resolve relative to the manifest URL, so replacing a scene does not require changing viewer code.

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

`camerasPath` is optional and refers to preserved camera metadata. It does not enable path navigation or make that data interchangeable across reconstruction engines. The file should retain its own original coordinate conventions and calibration details. A future trajectory contract can be defined when path navigation is implemented; v1 does not invent one.

## Asset and provenance constraints

- Exactly one `gaussian-splat` asset is supported. Declared formats are `ply`, `spz`, `splat`, `ksplat`, and `sog`; a format label does not prove that a particular file is decodable. PLY must contain splat attributes, not merely an arbitrary point cloud or mesh.
- Paths must be plain, nonempty relative paths. No absolute paths, empty/dot/traversal segments, backslashes, percent escapes, URL schemes, query strings, fragments, or control characters are accepted. Plain spaces inside filenames are allowed and URL-encoded by the resolver. Asset and camera paths follow the same rule.
- The manifest base URL must be absolute HTTP(S) without embedded credentials. Use a local static server for local files; browsers do not load the artifact through `file:` URLs.
- `sourceType` is `images`, `video`, or `sample`. `sourceUrl` and `licenseUrl` must be absolute HTTP(S) or `file:` URLs without credentials. A local original dataset can use its `file:` URL and a local license document, but absolute paths may expose local directory names when sharing artifacts.
- `license`, `attribution`, and `backend` are required nonblank strings. Record the source license, required credit, and actual producing tool/version. The scene license is independent of the renderer and trainer software licenses. `notes` is optional.

The parser uses [Zod's strict object validation and refinements](https://zod.dev/api). Parser tests use synthetic metadata only and do not count as browser, GPU, reconstruction, or dataset-license validation.
