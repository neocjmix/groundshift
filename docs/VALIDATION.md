# Validation — 2026-11-04

**M0 PASS. M1 PASS for the supplied-pose image dataset.** Both have actual GPU execution and visually inspected browser screenshots. Newly estimated poses have partial coverage; they are not substituted for the supplied-pose result.

## Environment

2022 MacBook Air (Mac14,2), Apple M2, 8 CPU / 10 GPU cores, 16 GB unified memory, macOS 26.6.2 (25G83), Metal 4. Node 25.6.1, npm 11.9.0, Chrome 156.0.8078.81. Web rendering reports `ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)`. Brush separately reports an Apple M2 integrated adapter with `backend: Metal`.

The original M0/M1 reconstruction and viewer validation below ran locally. Remote operations in that phase acquired open-source dependencies and licensed sample files. The later user-requested Railway deployment serves static files only; no hosted reconstruction or paid API was introduced.

## Subsequent static hosting verification

Railway deployment and public-origin browser rendering both passed on 2026-11-04. All 14 published files matched local hashes, both scenes visibly rendered, and orbit/zoom/reset/replacement worked. See [deployment identifiers, fresh measurements, screenshots and limitations](DEPLOYMENT.md). This separate result does not replace the original local hardware evidence below.

## Executed checks

| Check | Result | Evidence and scope |
| --- | --- | --- |
| TypeScript | PASS | `npm run typecheck` |
| ESLint | PASS | `npm run lint` |
| Schema and loader tests | PASS | `npm test`: 86 tests across two files |
| Native adapter and cancellation tests | PASS | `python3 -m unittest discover -s scripts/tests -v`: 15 tests; Python compilation also passed |
| Production build | PASS | `npm run build`; Spark/Three bundle is about 3.52 MB / 1.18 MB gzip and produces Vite's size advisory |
| Production browser suite | PASS | `npm run test:browser`: 3 headed Chrome tests, 30.5 s |
| Real sample pixels and visual inspection | PASS | Houseplant leaves and pot visible; source +Y mapping upright; [screenshot](evidence/m0-houseplant.png) |
| Orbit / zoom / reset / replacement | PASS | Drag changed actual camera position; immediate reset returned exactly after damping; wheel/buttons; local folder replacement; one live canvas |
| Loading and failure recovery | PASS | Missing/invalid manifests, HTTP 404 asset, corrupt PLY, delayed old scene replacement, forced WebGL context loss then successful retry |
| Narrow layout | PASS | Inspected 390 × 844 CSS viewport screenshot; no horizontal overflow; this is desktop Chrome resizing, not mobile hardware acceptance |
| Native Metal training/export | PASS | [Native execution, timings and memory](M1.md), preserved real backend logs |
| Reconstructed scene in same viewer | PASS | Non-background pixels, no page exceptions, actual inspected excavator/road/cones; [screenshot](evidence/m1-dozer.png) |
| New full-dataset CPU pose registration | FAIL | Largest model 16/40 images; [details](COLMAP.md) |
| Partial estimated-pose pipeline | PASS execution; FAIL useful visual quality | CPU poses → 1,500 Metal steps → 1,048-splat PLY → local-folder viewer; strong blur and stretching in the [inspected result](evidence/m1-estimated-partial.png) |
| Real CPU SfM cancellation | PASS | SIGTERM during native feature extraction produced CANCELLED report/stage, exit 143; 1.406 s signal-to-exit in one run |
| FFmpeg command availability | PASS | Actual version and filter help; frame extraction not implied |
| Original video, route-following, collision, other devices | NOT RUN | Outside M0/M1 validation |
| GPU-memory-only usage, held-out quality / PSNR | NOT RUN | No measurements claimed |

Native process cancellation/failure tests use explicitly labelled mock executables. They establish adapter behavior, not GPU training. Actual Metal success is supported by separate Brush execution, logs, exported artifacts and browser inspection.

## Browser measurements

These are one sequential headed production run, with no training in progress. Browser viewport 1440 × 1000, device scale 1, drawing buffer 1076 × 862. FPS is the app's rounded, one-second animation-loop rate, including browser scheduling; it is not GPU-only throughput. The display refresh rate limits these results. Load values include local transfer, decode and renderer preparation, not dependency installation or a cold browser benchmark.

| Scene | Gaussians | Exact file bytes | Load/decode | Five one-second FPS samples |
| --- | ---: | ---: | ---: | --- |
| Houseplant | 113,648 | 3,636,736 | 0.62 s | 60, 60, 60, 60, 60 |
| Local dozer, 1,500 steps | 194,789 | 17,921,240 | 1.37 s | 52, 60, 60, 60, 60 |

Raw browser readbacks: [M0](evidence/m0-browser.json), [M1](evidence/m1-browser.json). The JSON intentionally says that automated pixels require separate inspection; this document records that inspection. The central sample image contained 54,024 pixels above the test's background threshold. Pixel occupancy alone is not the visual quality check.

The Houseplant is recognizable and upright. The locally trained dozer shows the excavator, orange cones, lane markings, roadside and building. Background edges and some near geometry remain blurry or stretched. This is a short low-resolution reconstruction; free off-route viewing can expose missing information. No floor, gravity measurement, calibrated metric scale or unrestricted walking is claimed.

A separate 16-camera estimated-pose result was opened from its local folder in headed Chrome and inspected. It decoded 1,048 Gaussians and submitted frames on the same M2 renderer, but the image is heavily smeared and incomplete. That establishes a functioning raw-image processing path, **not acceptable reconstruction quality**. The 40-view supplied-pose result remains the main M1 acceptance artifact. [Partial-result readback](evidence/m1-estimated-browser.json) records the separate check; the native job files keep their original browser NOT RUN marker because browser verification is a subsequent operation.

Screenshot attribution: Houseplant by Marcel Padilla, CC-BY-4.0 ([source](SAMPLES.md)); dozer imagery by Nerfstudio team/contributors, Apache-2.0 under the selected dataset distribution ([source](M1.md)). UI overlays and display transforms are Groundshift additions.

## Evidence, reruns and known issues

- `test-results/` contains full screenshots and test measurements. It is ignored and replaced by reruns; selected evidence is copied here.
- `data/jobs/dozer-1500/` retains `job.json`, `training.log`, `resources.txt`, exact Brush help and the exported world. These local files and assets are deliberately not committed. Acquisition and execution commands in [M1.md](M1.md) reproduce them.
- `data/validation/colmap/` retains CPU SfM execution, omitted image names and the fixed-calibration retry. Low reprojection error on registered images does not imply full coverage.
- The first CSS build failed on an invalid empty import, then passed after removal. An initial browser failure assertion expected a 404 where Vite returned its HTML fallback; the viewer now reports HTML assets explicitly, and the suite tests a real 404 response separately. Earlier failures were not treated as passes.
- `npm audit --omit=dev`: zero vulnerabilities. Full `npm audit` reports 12 moderate dependency entries stemming from the same `minimatch <11.0.1` glob denial-of-service advisory in lint tooling. These packages are not shipped to the browser. No incompatible transitive major-version override was forced; revisit upstream tooling updates.
- Standalone COLMAP installation was blocked by the existing Xcode-license state. Official arm64 PyCOLMAP wheels provide the working CPU path; no system license or permission setting was changed.

Next: improve overlap/registration for the unposed-image route, evaluate longer training with the same small dataset if fidelity is needed, then begin M2 with an original steady 10–15 second walk. Preserve new measurements separately; this report is a dated single-machine result.
