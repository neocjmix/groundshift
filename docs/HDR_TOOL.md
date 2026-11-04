# Pinned local FFmpeg for HDR preparation

The Apple Silicon wheel from **imageio-ffmpeg 0.8.1** contains a standalone **FFmpeg 9.0** executable with `zscale` and `tonemap`. This provides explicit CPU color conversion without compiling FFmpeg or installing the Python wrapper. Use it locally alongside the existing `ffprobe`; the wheel does **not** contain ffprobe. [Official PyPI release metadata](https://pypi.org/pypi/imageio-ffmpeg/0.8.1/json), [imageio binary source pins](https://github.com/imageio/imageio-ffmpeg/blob/v0.8.1/tools/ffmpeg-sources.json).

Verified on the M2 Mac, 2026-11-05:

| Item | Value |
| --- | --- |
| Wheel | `imageio_ffmpeg-0.8.1-py3-none-macosx_12_0_arm64.whl` |
| Wheel bytes | 22,625,474 |
| Wheel SHA-256 | `5636d691e36e5274b13fe38182b1f627b2e35dcecc63944012c2470f9484fc45` |
| Archive member | `imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v9.0` |
| Executable bytes | 52,070,376 |
| Executable SHA-256 | `591260c945d0eef150e3bf82b0ef988bd36a9cecc18ff05d6679617159f0a95e` |
| Executable architecture/version | Mach-O arm64; `ffmpeg version 9.0` |

The local wheel hash matches PyPI, and the extracted executable matches both the wheel member and imageio's published executable pin. The official imageio wheel bundles an **osxexperts.net build**; it is not a binary published by the FFmpeg project. Imageio's source manifest records no independently published verification for that original archive. These pins establish repeatable package/payload identity, not a reproducible-build or independent authenticity audit.

## Install or verify

Run from the repository root on Apple Silicon macOS 12+ with Python 3.10+. This downloads the exact PyPI-hosted wheel only when absent, verifies both hashes, and extracts only the named executable and wrapper license. Existing files with different contents cause an error; existing matching files are reused. Nothing changes system FFmpeg or Python packages.

```sh
python3 - <<'PY'
import hashlib
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

directory = Path("data/tools/hdr-ffmpeg")
directory.mkdir(parents=True, exist_ok=True)
filename = "imageio_ffmpeg-0.8.1-py3-none-macosx_12_0_arm64.whl"
url = ("https://files.pythonhosted.org/packages/2b/47/"
       "9f9b654f853598bae0850fa22bba168103e45d31b5a2a893ed474f28d54a/" + filename)
wheel_hash = "5636d691e36e5274b13fe38182b1f627b2e35dcecc63944012c2470f9484fc45"
binary_hash = "591260c945d0eef150e3bf82b0ef988bd36a9cecc18ff05d6679617159f0a95e"
wheel = directory / filename

if wheel.exists():
    data = wheel.read_bytes()
else:
    with urlopen(url, timeout=60) as response:
        data = response.read()
if hashlib.sha256(data).hexdigest() != wheel_hash:
    raise SystemExit("Wheel checksum mismatch")
if not wheel.exists():
    with wheel.open("xb") as output:
        output.write(data)

with ZipFile(wheel) as archive:
    binary = archive.read("imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v9.0")
    license_text = archive.read("imageio_ffmpeg-0.8.1.dist-info/licenses/LICENSE")
if hashlib.sha256(binary).hexdigest() != binary_hash:
    raise SystemExit("Executable checksum mismatch")
executable = directory / "ffmpeg-macos-aarch64-v9.0"
for path, content in ((executable, binary), (directory / "imageio-LICENSE.txt", license_text)):
    if path.exists():
        if path.read_bytes() != content:
            raise SystemExit(f"Existing file differs: {path}")
    else:
        with path.open("xb") as output:
            output.write(content)
executable.chmod(0o755)
print(executable.resolve())
PY

data/tools/hdr-ffmpeg/ffmpeg-macos-aarch64-v9.0 -version
data/tools/hdr-ffmpeg/ffmpeg-macos-aarch64-v9.0 -L
data/tools/hdr-ffmpeg/ffmpeg-macos-aarch64-v9.0 -hide_banner -h filter=zscale
data/tools/hdr-ffmpeg/ffmpeg-macos-aarch64-v9.0 -hide_banner -h filter=tonemap
```

The existing development installation also has `data/tools/hdr-ffmpeg/ffmpeg` as a symlink to that executable. The instructions above do not require the symlink. All downloaded files remain in ignored `data/`.

Select the executable explicitly when following [video preparation](VIDEO.md):

```sh
python3 scripts/prepare-video.py /absolute/path/input.mov data/datasets/prepared-video \
  --duration 15 --fps 4 --max-edge 960 --max-frames 120 \
  --ffmpeg data/tools/hdr-ffmpeg/ffmpeg-macos-aarch64-v9.0 \
  --ffprobe /opt/homebrew/bin/ffprobe \
  --provenance /absolute/path/provenance.json
```

## Licenses and validation boundary

The wheel's Python wrapper and included wrapper `LICENSE` are **BSD-2-Clause**. The bundled executable is separate: its `-L` output declares **GPL-2.0-or-later**, and its configuration includes `--enable-gpl` and `--enable-libzimg`. Do not apply the wrapper's BSD license to FFmpeg. Linked components retain their terms. Groundshift keeps this tool local and does not redistribute the executable. [Wrapper license](https://github.com/imageio/imageio-ffmpeg/blob/v0.8.1/LICENSE), [FFmpeg licensing](https://github.com/FFmpeg/FFmpeg/blob/n9.0/LICENSE.md).

Local hash comparison, executable startup, and the availability of `zscale`, `tonemap`, `format`, `fps` and `scale` are **PASS**. Those checks establish tool capability, not conversion accuracy. The installed `tonemap` exposes named algorithms and `param`, `desat`, and `peak` controls; the selected conversion must record its transfer/gamut conversion, tone curve, reference luminance/peak assumptions and output encoding. See the current policy and execution evidence in [VIDEO.md](VIDEO.md).

Output BT.709/sRGB tags, a successful process exit, or merely brighter-looking images do not prove HDR conversion. Test actual decoded pixels using a known HDR ramp against an identity/retagged baseline, inspect monotonicity and clipping, then inspect representative converted images. Retain the exact filter command and measurements. A fixed tone policy is an explicit rendering choice; it is not a recovered camera exposure, measured scene luminance, or full Dolby Vision creative grading. This installation guide itself performs no media conversion, reconstruction or GPU validation.
