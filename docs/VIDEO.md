# Local video preparation

`scripts/prepare-video.py` extracts a bounded image sequence from a local video with native FFmpeg. It records the input hash, ordered frame hashes, sampling choices, source attribution, tool versions, exact commands, logs and completion status. It does not estimate cameras or train a scene.

The command uses Python 3 standard library modules and installed `ffmpeg`/`ffprobe` executables. The verified machine is the M2 MacBook Air, macOS Tahoe, with native arm64 FFmpeg **8.0.1** at `/opt/homebrew/bin/ffmpeg` and `/opt/homebrew/bin/ffprobe`. SDR extraction needs no new service or GPU dependency. HDR extraction additionally requires a zimg-enabled FFmpeg; the tested local arm64 FFmpeg 9.0 installation and licenses are recorded in [HDR_TOOL.md](HDR_TOOL.md). The installed Homebrew build reports GPL-3.0-or-later (`ffmpeg -L`); FFmpeg's licensing depends on its build options. See the [upstream license](https://github.com/FFmpeg/FFmpeg/blob/n8.0.1/LICENSE.md). The tested filter options are present in 8.0.1; older builds are not claimed compatible.

```sh
python3 scripts/prepare-video.py /absolute/path/walk.mov data/datasets/walk-frames \
  --start 0 --duration 15 --fps 4 --max-edge 960 --max-frames 120 \
  --provenance /absolute/path/walk-provenance.json
```

Both positional paths are required. The output must be new; existing directories, files and symlinks are refused. `--start 0`, `--duration 15`, `--fps 4`, `--max-edge 960` and `--max-frames 120` are defaults. Thus a complete 15-second clip normally yields 60 frames, and the frame cap can shorten the requested interval. End-of-file may produce fewer frames. Override tool paths with `--ffmpeg /path/ffmpeg --ffprobe /path/ffprobe`. If they are not installed, install a free FFmpeg build for your Mac first; no Python packages are needed.

## Image and timing behavior

The command chooses the first actual video stream, excluding attached cover art, seeks to the requested input-relative offset, and limits extraction duration and frame count. It uses CPU decoding (`-hwaccel none`), two decoder/encoder threads, and two filter threads. Audio and subtitles are omitted.

FFmpeg applies display-matrix autorotation before the image filters. Scaling fits within both the rotated source pixel dimensions and the requested maximum edge, preserves display aspect ratio, and makes square pixels. Small sources are not enlarged; nonsquare pixel inputs may shrink one dimension to preserve their displayed shape. JPEG output uses quality 2 with 4:4:4 chroma. Frames are derived images, not byte-identical copies of video frames. Metadata is stripped from JPEGs; the full probe result remains in the logs.

`sequence.json` is the explicit chronology supplied to later reconstruction/export. Its frame array is ordered, zero-based `index` values identify samples, and `file` paths are relative to the prepared directory. `nominalSourceTimeSeconds` is `start + index / fps`; `nominalClipTimeSeconds` is `index / fps`. These are **nominal sampling offsets, not actual decoded frame PTS, capture timestamps, or evidence of camera motion**. The `fps` filter can drop or duplicate source frames. Variable-rate or low-rate sources therefore do not imply one distinct captured image per sample. No camera calibration or poses are generated here.

The implementation was checked against the official versioned [FFmpeg CLI documentation](https://github.com/FFmpeg/FFmpeg/blob/n8.0.1/doc/ffmpeg.texi), [fps/scale filter documentation](https://github.com/FFmpeg/FFmpeg/blob/n8.0.1/doc/filters.texi), and [ffprobe JSON documentation](https://github.com/FFmpeg/FFmpeg/blob/n8.0.1/doc/ffprobe.texi), as well as the installed `-h full`, `-h filter=scale`, and `-h filter=fps` output. `-autorotate` is a boolean switch; it does not take a trailing `1` in this CLI. Rotation test fixtures use `-display_rotation 90`, which actually writes a display matrix in 8.0.1.

## HDR color preparation

Tagged BT.2020 HLG (`arib-std-b67`) and PQ (`smpte2084`) sources now use an explicit CPU conversion before JPEG encoding. HDR input requires both `zscale` and `tonemap`; the script checks the selected executable and fails before extraction if either is absent. The default Homebrew FFmpeg 8.0.1 on the verified machine lacks `zscale`. Use the pinned free executable from [HDR_TOOL.md](HDR_TOOL.md) with `--ffmpeg data/tools/hdr-ffmpeg/ffmpeg-macos-aarch64-v9.0`; `build-world.py` forwards this flag and `--ffprobe` unchanged.

The filter first samples frames, linearizes the tagged transfer function and converts BT.2020 primaries to BT.709 using zimg. Float32 RGB then passes through FFmpeg's documented Mobius operator with transition `0.3`, followed by sRGB encoding and full-range BT.601 JPEG matrix conversion. JPEGs use 4:4:4 chroma and standard sRGB interpretation without an embedded ICC profile. Scaling and display-matrix autorotation retain the existing behavior. No input transfer function is guessed or relabeled as SDR.

The policy sets a **100-nit reference white**, with **1000-nit HLG** or **10000-nit PQ** reference peak (`peak=10` or `100`). These are explicit rendering assumptions, not measured exposure, scene brightness, or camera calibration. Highlight desaturation is disabled (`desat=0`): on the tested FFmpeg 9.0 binary, `desat=2` produced neutral float highlight values above 1 in the ramp experiment, while the chosen setting kept all tested gray levels distinct. Colors outside the SDR gamut can still clip. This is a practical fixed global tone map, not a colorimetric-reference or display-calibration claim.

Dolby Vision compatibility IDs 1 and 4 can use their tagged HDR10/PQ or HLG base layer. Other/missing compatible HDR metadata is rejected. The pipeline does not apply Dolby Vision dynamic RPU grading or reproduce Apple's display-dependent rendering. Old HDR side data is removed after pixel conversion; source metadata remains in the private probe logs. `report.json` and `sequence.json` record the full source color tags, conversion method, output encoding and luminance assumptions in `sampling.colorConversion`. Exact arguments and a filter-capability stage are retained in the logs. HDR processing still reports `gpuUsed: false`.

The implementation follows the versioned [zscale and tonemap documentation](https://github.com/FFmpeg/FFmpeg/blob/n9.0/doc/filters.texi), [tonemap source](https://github.com/FFmpeg/FFmpeg/blob/n9.0/libavfilter/vf_tonemap.c), and the installed FFmpeg 9.0 filter help. Default peak inference is not relied upon after conversion to linear RGB.

## Provenance

An optional `--provenance` JSON must contain nonempty `sourceUrl`, `license`, `licenseUrl` and `attribution` strings. URLs must be absolute HTTP(S) or file URLs without credentials. Optional `notes` are retained. The supplied JSON is copied verbatim to `source-provenance.json`; normalized output provenance identifies video input and FFmpeg extraction. Passing metadata records the caller's assertions; it does not independently establish ownership or validate a license grant.

Without `--provenance`, the output uses the local input file URL, `license: "unspecified"`, and `attribution: "Creator and ownership not specified"`. Its `licenseUrl` points to its own local provenance record, which expressly makes no ownership or redistribution assertion. This default permits local preparation without guessing rights. It is not a public sample license.

## Output and failures

```text
prepared/
  images/frame_000001.jpg ...
  sequence.json
  provenance.json
  source-provenance.json       # when supplied
  report.json
  logs/ffmpeg-version.{stdout,stderr}.log
  logs/ffprobe-version.{stdout,stderr}.log
  logs/ffprobe.{stdout,stderr}.log
  logs/ffmpeg-extract.{stdout,stderr}.log
```

Each report stage stores its exact argument array, child exit code, elapsed time, stdout/stderr paths and status. `sequence.json` stores source SHA-256 and each image's path, dimensions, size, SHA-256 and nominal times. The final report also hashes sequence/provenance files. `peakChildRssBytes` is the maximum individual child RSS reported by the OS, not the combined Python/process-group footprint. The source file's size and modification time are checked for change during extraction.

Exit 0 and report `PASS` mean frame preparation succeeded. An execution failure returns 1 with report `FAIL`; argument/preflight rejection returns 2 before creating a job. SIGINT/SIGTERM propagate to the active child process group, retain partial images/logs, and produce `CANCELLED` with exit 130/143. A child that does not exit within three seconds is killed. No success sequence is written on extraction failure/cancellation. Retry with a new directory; partial output is never resumed or overwritten. Uncatchable SIGKILL, power loss or filesystem failure can leave `RUNNING`; that is not success.

## Earlier SDR fixture validation — 2026-11-04

The existing `data/previews/dozer-source/dozer-source-photos.mp4` is a **photo-slideshow fixture**, assembled from 40 licensed source photographs at an arbitrary preview speed. It is not an original walking recording. Its 20-second, 752×500 H.264 stream and source SHA-256 `f392ee631350bf870d9bb19ba8506f8840fcda544f2e48d3aeca39e6085e5378` were measured with ffprobe and hashing. The dataset provides no original video or capture timestamps. [Dataset provenance](SAMPLES.md).

The local fixture provenance passed below records Apache-2.0 source photographs, the pinned upstream license, and an explicit photo-slideshow-only note:

```sh
python3 scripts/prepare-video.py \
  data/previews/dozer-source/dozer-source-photos.mp4 \
  data/validation/video/dozer-slideshow \
  --provenance data/validation/video/dozer-slideshow-provenance.json

python3 -m unittest discover -s scripts/tests -p test_prepare_video.py -v
```

| Check | Result | Measured evidence |
| --- | --- | --- |
| Actual native extraction of photo-slideshow fixture | PASS | 60 JPEGs, 752×500, 3,078,529 image bytes; 1.042305 s total; maximum child RSS 47,333,376 bytes |
| Independent input, all 60 image, sequence and provenance hash readback | PASS | Compared on-disk bytes against stored hashes |
| Focused tests | PASS | 14 tests in 8.795 s; `data/validation/video/unit-tests.log` |
| Actual synthetic video orientation/aspect/order | PASS | 90° display matrix becomes 96×160 pixels with checked color quadrants; SAR 2:1 becomes square-pixel 160×48; four temporal colors remain ordered; clip/cap/no-upscale checks |
| Actual native FFmpeg SIGTERM | PASS | Parent exit 143, child exit 255, stage/job `CANCELLED`; completed 0.372605 s after signal; `data/validation/video/cancellation-check.json` |
| Child and grandchild SIGTERM/SIGINT forwarding | PASS | Real process-group signals against test-double tools; not a media/GPU test |
| Invalid media, out-of-range start, invalid provenance and existing output protection | PASS | Failure logs/report and no-overwrite checks |
| Original walking-video camera recovery, training and useful scene quality in this earlier fixture run | NOT RUN | These checks used a photo slideshow; later private original-video results are recorded separately below |

The canonical report and exact logs are in `data/validation/video/dozer-slideshow/`. The first development attempt with invalid `-autorotate 1` is preserved separately as `FAIL` in `data/validation/video/dozer-slideshow-local-only/`; the corrected standalone run is `.../dozer-slideshow-local-only-v2/`. All media, logs and generated outputs stay in ignored `data/`. The tests generate tiny synthetic media in temporary directories and never claim M2 acceptance or GPU execution.

## HDR validation — 2026-11-05

The focused video suite passes **20 tests in 5.732 seconds**, including real HLG and PQ native pixel conversion, HDR portrait rotation, missing-filter failure, and the previous SDR/process lifecycle checks. Run with an explicitly selected zimg executable; without one, the three HDR integration tests report skipped / **NOT RUN**, rather than success:

```sh
GROUNDSHIFT_HDR_FFMPEG=data/tools/hdr-ffmpeg/ffmpeg-macos-aarch64-v9.0 \
  python3 -m unittest discover -s scripts/tests -p test_prepare_video.py -v
```

The lossless 10-bit neutral ramp uses limited-range input levels `[64, 192, 320, 448, 576, 704, 832, 940]`. The tests verify decoded HLG/PQ and BT.2020 tags before testing conversion. The HLG output gray values are `[0, 45, 104, 162, 202, 231, 248, 255]`, versus `[0, 37, 75, 112, 149, 186, 224, 255]` for direct conversion without tone mapping. The values change and remain strictly ordered through the highlights. A separate synthetic -90° display matrix becomes 96×160 pixels with the gray ramp in the expected direction. These checks establish actual pixel processing and orientation, not full gamut/color-reference accuracy.

An early VideoToolbox experiment was replaced. Its original FFV1 ramp fixtures did not retain the intended primaries/transfer tags, so their identical outputs are **invalid evidence of HDR conversion efficacy**. Those failed/inconclusive experiments remain preserved locally; no claim that VideoToolbox inherently cannot convert HDR follows from them. The final implementation uses explicit, tested zscale/Mobius processing and has no VideoToolbox fallback.

A private original HLG/Dolby Vision base-layer recording was also processed locally. One representative frame from the exact source produced a correctly oriented 540×960 JPEG in **0.658735 seconds**, with maximum individual child RSS **160,382,976 bytes**. Decoded RGB differs from the same-time direct-conversion control by a mean **20.4845 levels per 8-bit channel**, confirming actual pixel changes. The converted frame was visually inspected. This isolated preparation check does not prove reconstructed scene quality; see [original-video validation](ORIGINAL_VIDEO.md) for the separate end-to-end run.

Pixel evidence, source/output/report hashes, exact filter graph, implementation hashes, executable hash/version, and explicit limitations are preserved in ignored `data/captures/desk-20261104/hdr-color-validation.json`. The focused test log is `data/validation/video/hdr-tests.log`. Original footage, screenshots, frame images, full probe metadata and derived private artifacts remain local and untracked. Calibrated color accuracy and Dolby Vision dynamic-RPU reproduction are **NOT RUN**.
