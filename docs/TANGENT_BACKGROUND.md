# Twenty tangent views and presentation backgrounds

User-authorized2026-11-06 after the previously closed same-data campaign. This
is one bounded reopening, not permission for another model/parameter sweep.
Preserve every earlier source, pose, seed, world and observation. Work directory:
`data/jobs/street-tangent-background-20261106/`.

## Declared configuration

- Same nine licensed7680×3840 Mapillary/Wikimedia original ERP photographs and
  preserved all-nine fixed-rig SfM. Physical5 RGB stays withheld from training,
  calibration-image inference, point colors and presentation backgrounds.
- Twenty directions from the outward face normals of an icosahedron. Each is
  a true square pinhole reprojection,1024×1024,80° horizontal/vertical FOV, from
  original pixels. Analytically verify full-sphere coverage and overlap. All
  twenty directions at one sphere share exactly one real camera center.
- Pinned DAV2 Small, Apache-2.0, executed locally on MPS **after** reprojection.
  Request1036 neural input (multiple14); record the actual model tensor size,
  not merely the output image size. If that causes a concrete memory/platform
  failure, retain its evidence and permit one explicit518-input recovery before
  training. No silent checkpoint, device or resolution substitution.
- Fit relative inverse camera-Z against training SfM anchors with deterministic
  withheld track IDs. Jointly constrain overlapping crops using
  `inverseRadial = cosToCropForward * (scale * raw + offset)`; raw camera-Z-like
  predictions must not be directly equated across differently rotated cameras.
  Unanchored/unidentifiable regions remain unsupported. No arbitrary metres.
- One calibrated spherical range per ray; retain disagreement diagnostics and
  discard invalid/nonpositive/unsupported range. Geometry initialization uses
  ERP vertical band.25–.85 and each center's training-SfM P99 range cap; upper
  sky and known nadir artwork are not assigned fabricated finite distances.
  All20 RGB directions remain training inputs with the same nadir-only mask. Shared SfM anchors tie physical
  centers; compare neighboring-center agreement without claiming ground truth.
- One Brush0.3.0 Metal run:8,000 steps,1024 max resolution,800k cap,SH1,seed42.
  New initialization capped at180k dense points plus preserved non5 sparse seed.
  Same native budget as `street-final-hires`, no factorial attribution.

## Presentation completion is a separate treatment

Expose GS-only (default), original-panorama background, and background plus a
coarse depth-textured shell if practical. Use only the eight non5 sources. The
background panorama follows orientation without translation, with known near
object/parallax and source-switch artifacts. Mesh triangles use calibrated
estimated depth and reject invalid samples/depth discontinuities. They are
display surfaces, not measured floors, collision or recovered invisible sides.
Select by actual camera-center proximity. The known bottom15% camera artwork
is replaced in display textures by smoothed column-color extrapolation fading
to a uniform tone; these are explicitly nonobserved presentation pixels. They
do not enter depth, training RGB, point positions or collision. No diffusion.

World/background geometry is explicit right-handed viewer Y-up. Original ERP
local rays are `(+cos(lat)sin(lon), -sin(lat), +cos(lat)cos(lon))`, the existing
CV convention; panorama-to-world includes the actual world asset transform.
Mesh UV is `(u,1-v)` with ordinary vertically flipped image textures. Never
apply the asset transform twice or confuse camera-Z with radial distance.

## Evidence, deployment and stopping

Reuse the same75 evaluation cameras and source references as the last run.
Compare actual GS-only renders at512 output, plus1024 detail where practical.
Measure background completion separately; its colored pixels and source-photo
coverage cannot prove a Gaussian scene rendered or improve GS-only acceptance.
Inspect branches/railings, walls, road, far region, movement and background
source transitions. Physical5 poses/sparse geometry remain all-nine estimates;
this is appearance withholding, not independent geometry truth.

Publish plan/input/depth/scene evidence as soon as each is deployable, with
unexecuted stages NOT RUN. Continue local execution while a deployment agent
publishes. Reuse the existing checksum-pinned static archive/overlay mechanism.
Record native/model timings, bytes, memory, failures and test/browser scopes.
Finish with one actual exported candidate and honest comparison, or retain a
concrete blocker. No additional same-data training search after seeing the result.

Primary basis: [360MonoDepth](https://manurare.github.io/360monodepth/),
[official DAV2 model/interface/license](https://github.com/DepthAnything/Depth-Anything-V2),
[Three.js background API](https://threejs.org/docs/pages/Scene.html).
This implementation reuses DAV2 and our explicit calibration; it does not claim
to reproduce the complete360MonoDepth optimization or adopt its model.
