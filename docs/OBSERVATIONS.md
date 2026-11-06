# Railway observation surface

Railway displays every distinct exported Groundshift scene, including low-quality
and superseded trials. A successful deployment means that the files and viewer
work; it does not change a reconstruction's quality result.

The current observation release preserves29 distinct Gaussian scenes and43
chronological lab entries(29 scenes,14 reports). The latest
[street comparison](https://groundshift-viewer-production.up.railway.app/experiments/street/)
contains7 newly trained real-image street worlds, recommended3D, synchronized
motion, matched source/GS images, depth/initial clouds, measured runtime/memory
and failed stages. [Actual conclusion and reproduction](STREET_CONCLUSION.md):
a recognizable short route is feasible on M2; doubling training or adding
consistency filters does not improve the best observed mean. Geometry and
unrestricted walking remain limited. Existing scooter/desk/panorama outputs
remain unchanged.

The preceding [third-view road diagnostic](https://groundshift-viewer-production.up.railway.app/experiments/road-third-view/)
retains44/291 supported road tracks and frozen calibration evidence.
[Deployment evidence](DEPLOYMENT.md) separates publication from quality. The
supplied-pose dozer's camera-path re-export shares its unchanged PLY with the
existing scene; lineage remains visible instead of duplicating the binary.

The home catalog offers **Experiments**, category filters and text search. The
[comparison report](https://groundshift-viewer-production.up.railway.app/experiments/mapillary/index.html)
shows actual target crops, geometric warp/GS inputs, generation masks and local
diffusion results. Both cases have a real/generated opacity control, gray-fill
controls, measured errors, original source credits and model terms. The separate
[65-frame panorama report](https://groundshift-viewer-production.up.railway.app/experiments/video-4to6/)
shows the actual 2048×1024 MP4, selected generated frames, the held-out real
photo, an exploratory failed-quality bicycle repair and links to both matched
Gaussian worlds. The local M2 run used RIFE optical-flow interpolation, not
video diffusion; this distinction is visible in the report. The history also
records unsuccessful and cancelled stages. No outcome is hidden because of
poor visual quality.

The [relative-depth diagnostic](https://groundshift-viewer-production.up.railway.app/experiments/depth-v2/)
shows three licensed real crops and M2/MPS Depth Anything V2 Small predictions.
It records agreement with existing sparse depth ordering while labeling GS
improvement and novel-view synthesis **NOT RUN**. [Local evidence](DEPTH_EXPERIMENT.md).

## Rebuild from existing local evidence

For the complete current surface, first [restore the pinned observation
archive](DEPLOYMENT.md#restore-scene-assets-in-a-fresh-checkout). This does not
repeat camera estimation, training or diffusion. Later experiments use their
own append-only publishers, including `publish-street.py`; see the linked run
instructions. New jobs must be explicitly added to the publication list.

```sh
npm ci
npm run dev

# In another terminal, package the already restored/curated assets.
npm run package:viewer -- --include-reconstruction --include-independent --include-desk --include-experiments
```

The legacy `scripts/prepare-observations.py` rebuilds the original Mapillary
report; it is not a global regenerator of the later29-scene publication list.
Do not use it to reset the current allowlist. It preserves scene binary hashes and camera/asset
transforms, writes display-safe metadata, captures actual canvas previews, and
builds the comparison page from an embedded template. A narrowly selected set
of status/measurement fields becomes the public history; raw job reports are
not copied. Licensed public image crops remain separately attributed. The
helper emits `scripts/observation-worlds.json`, an explicit file allowlist used
by the static packager. Generated assets stay outside Git and are distributed
in checksum-pinned release attachments.

Do not upload `data/`, an entire repository, or unfiltered `dist/`. Private desk
footage/frames, private URLs, local paths, raw logs and model weights are outside
the observation package. The creator's display authorization for derived desk
trials does not grant an open reuse license.

## Verify local and public behavior

```sh
npm run typecheck
npm run lint
npm test
npm run test:browser

# After deployment: run the same catalog/render/report checks on the public origin.
GS_BASE_URL=https://groundshift-viewer-production.up.railway.app \
  npx playwright test tests/browser/gallery.pw.mjs tests/browser/observations.pw.mjs tests/browser/video-report.pw.mjs
```

These browser checks use headed Chrome, actual scene assets and image controls.
Pixel assertions are supplemented by visual screenshot inspection. A regression
check reuses existing scene exports and is not evidence of a new GPU training
run. [DEPLOYMENT.md](DEPLOYMENT.md) records the exact archive, checksums, deployment
ID and current public verification result. [MAPILLARY_EXPERIMENT.md](MAPILLARY_EXPERIMENT.md)
and [PANORAMA_VIDEO_EXPERIMENT.md](PANORAMA_VIDEO_EXPERIMENT.md) retain the
detailed reconstruction measurements and quality limits.
