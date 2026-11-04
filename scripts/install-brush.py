#!/usr/bin/env python3
"""Install the pinned upstream Apple Silicon release into ignored data/tools/."""
import hashlib
from pathlib import Path
import platform
import subprocess
import tarfile
import urllib.request

VERSION = "0.3.0"
SHA256 = "65b2631398c839be3c1d4d7160fe2326389dec87830aac0710985e6690a1048c"
URL = f"https://github.com/ArthurBrussee/brush/releases/download/v{VERSION}/brush-app-aarch64-apple-darwin.tar.xz"


def main():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("This installer is for native Apple Silicon macOS only")
    destination = Path(__file__).resolve().parents[1] / f"data/tools/brush-{VERSION}"
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "brush.tar.xz"
    if not archive.exists():
        temporary = archive.with_suffix(".partial")
        with urllib.request.urlopen(URL, timeout=120) as response, temporary.open("wb") as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
        temporary.rename(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise SystemExit(f"Brush checksum mismatch; inspect/remove {archive} before retrying")
    with tarfile.open(archive) as bundle:
        bundle.extractall(destination, filter="data")
    executable = destination / "brush-app-aarch64-apple-darwin/brush_app"
    subprocess.run([str(executable), "--version"], check=True)
    print(executable)


if __name__ == "__main__":
    main()
