# Vision

Groundshift turns pedestrian memories into places people can revisit. Someone walks through a location and records video; a reconstruction process makes it explorable later. In the long term, independent captures can connect and be shared, potentially within hours.

The product is not a precise digital twin. Accept approximations, incomplete unseen geometry and imperfect texture when the place still feels recognizable. Maintain the continuity of paths, turns, and landmarks.

## Prototype scope
The user redirected the next experiment to dense consecutive Mapillary 360°
imagery, followed by diffusion-assisted filling of missing viewpoints and
Gaussian reconstruction. Begin with a small, licensed, reproducibly acquired
sequence. Compare an observed-image baseline with the generated-view experiment;
do not assume that plausible generated pixels improve multi-view geometry.

The existing original-video workflow remains a validated input path. An iOS
capture app is deferred while the public-panorama experiment is evaluated.
Output remains a browser-viewable reconstructed scene with explicit coordinates,
source attribution, and an honest distinction between captured and generated
content. See [the current experiment](MAPILLARY_EXPERIMENT.md).

## Deferred
Free off-path walking, scene connections, shared worlds, automatic uploads,
accounts, mobile capture app, cloud compute, GIS alignment, real-time reconstruction.
Missing-view generation is now a bounded experiment, not an accepted capability.

## Priorities
1. Reproducible end-to-end operation.
2. Recognizable and spatially coherent walking experience.
3. Responsive rendering on the target laptop.
4. Reasonable time and memory use.
5. Fidelity only when it improves the experience.
