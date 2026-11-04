#!/usr/bin/env python3
"""Prepare a bounded, ordered local image sequence with FFmpeg (stdlib only)."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit


TIMESTAMP_MEANING = (
    "Nominal sampling offsets from the source video's input timeline start; "
    "not actual frame PTS or camera capture timestamps. FFmpeg fps may drop or "
    "duplicate source frames. Frame array order is source chronology."
)


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jpeg_size(path):
    """Read dimensions without a Pillow dependency or decoding/reencoding."""
    with path.open("rb") as stream:
        if stream.read(2) != b"\xff\xd8":
            raise ValueError(f"Not a JPEG: {path.name}")
        while True:
            marker = stream.read(1)
            if marker != b"\xff":
                raise ValueError(f"Invalid JPEG header: {path.name}")
            marker = stream.read(1)
            while marker == b"\xff":
                marker = stream.read(1)
            if not marker or marker in (b"\xda", b"\xd9"):
                raise ValueError(f"Missing JPEG dimensions: {path.name}")
            size_bytes = stream.read(2)
            if len(size_bytes) != 2:
                raise ValueError(f"Truncated JPEG: {path.name}")
            size = int.from_bytes(size_bytes, "big")
            if size < 2:
                raise ValueError(f"Invalid JPEG segment: {path.name}")
            if marker[0] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                             0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                data = stream.read(5)
                if len(data) != 5:
                    raise ValueError(f"Truncated JPEG dimensions: {path.name}")
                height, width = int.from_bytes(data[1:3], "big"), int.from_bytes(data[3:5], "big")
                if width < 1 or height < 1:
                    raise ValueError(f"Empty JPEG: {path.name}")
                return width, height
            stream.seek(size - 2, 1)


def provenance_for(video, output, supplied):
    if supplied is None:
        return {
            "sourceType": "video", "sourceUrl": video.as_uri(),
            "license": "unspecified", "licenseUrl": (output / "provenance.json").as_uri(),
            "attribution": "Creator and ownership not specified",
            "backend": "FFmpeg video frame extraction",
            "notes": "Local preparation only. No ownership or redistribution permission is inferred. "
                     + TIMESTAMP_MEANING,
        }
    value = json.loads(supplied.read_text())
    if not isinstance(value, dict):
        raise ValueError("Provenance must be a JSON object")
    for key in ("sourceUrl", "license", "licenseUrl", "attribution"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(f"Provenance requires a nonempty {key}")
    for key in ("sourceUrl", "licenseUrl"):
        url = value[key]
        parsed = urlsplit(url)
        valid = parsed.scheme in ("http", "https", "file")
        valid = valid and not parsed.username and not parsed.password
        valid = valid and (parsed.path.startswith("/") if parsed.scheme == "file" else bool(parsed.hostname))
        valid = valid and "\\" not in url and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in url)
        _ = parsed.port
        if not valid:
            raise ValueError(f"Provenance {key} requires an absolute HTTP(S) or file URL without credentials")
    if "notes" in value and not isinstance(value["notes"], str):
        raise ValueError("Provenance notes must be a string")
    return {**value, "sourceType": "video", "backend": "FFmpeg video frame extraction",
            "notes": (value.get("notes", "") + " " + TIMESTAMP_MEANING).strip()}


class Cancelled(KeyboardInterrupt):
    def __init__(self, signum):
        self.signum = signum
        super().__init__(f"Received {signal.Signals(signum).name}")


def run_tool(command, name, output, report):
    stage = {"name": name, "argv": command, "status": "RUNNING",
             "stdout": f"logs/{name}.stdout.log", "stderr": f"logs/{name}.stderr.log"}
    report["stages"].append(stage)
    write_json(output / "report.json", report)
    started = time.monotonic()
    process = None
    try:
        with (output / stage["stdout"]).open("wb") as stdout, (output / stage["stderr"]).open("wb") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                                       stdin=subprocess.DEVNULL, start_new_session=True)
            stage["pid"] = process.pid
            write_json(output / "report.json", report)
            code = process.wait()
            stage["exitCode"] = code
            if code != 0:
                raise RuntimeError(f"{name} exited {code}; see {stage['stderr']}")
            stage["status"] = "PASS"
    except KeyboardInterrupt as error:
        signum = getattr(error, "signum", signal.SIGINT)
        stage["status"], stage["error"] = "CANCELLED", str(error)
        if process is not None:
            try:
                os.killpg(process.pid, signum)
            except ProcessLookupError:
                pass
            try:
                stage["exitCode"] = process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stage["forcedKill"] = True
                stage["exitCode"] = process.wait()
        raise
    except Exception as error:
        stage["status"], stage["error"] = "FAIL", str(error)
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stage["exitCode"] = process.wait()
        raise
    finally:
        stage["elapsedSeconds"] = round(time.monotonic() - started, 6)
        write_json(output / "report.json", report)


def finite_positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be finite and greater than zero")
    return number


def finite_nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be finite and nonnegative")
    return number


def optional_number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Local video file (no upload)")
    parser.add_argument("output", type=Path, help="New directory; existing paths are never overwritten")
    parser.add_argument("--start", type=finite_nonnegative, default=0.0, help="Clip start offset in seconds (default: 0)")
    parser.add_argument("--duration", type=finite_positive, default=15.0, help="Maximum clip duration in seconds (default: 15)")
    parser.add_argument("--fps", type=finite_positive, default=4.0, help="Nominal sampling rate (default: 4)")
    parser.add_argument("--max-edge", type=int, default=960, help="Maximum output edge; never upscale (default: 960)")
    parser.add_argument("--max-frames", type=int, default=120, help="Maximum extracted images (default: 120)")
    parser.add_argument("--provenance", type=Path, help="Source/license/attribution JSON; otherwise license is unspecified")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable path or name")
    parser.add_argument("--ffprobe", default="ffprobe", help="ffprobe executable path or name")
    args = parser.parse_args(argv)
    if args.max_edge < 2 or args.max_frames < 1:
        parser.error("--max-edge must be at least 2 and --max-frames must be positive")
    video, output = args.video.expanduser().resolve(), args.output.expanduser().resolve()
    if not video.is_file():
        parser.error(f"Local input file does not exist: {video}")
    if output.exists() or args.output.expanduser().is_symlink():
        parser.error(f"Output already exists: {output}")
    try:
        provenance_path = args.provenance.expanduser().resolve() if args.provenance else None
        provenance = provenance_for(video, output, provenance_path)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    ffmpeg, ffprobe = shutil.which(args.ffmpeg), shutil.which(args.ffprobe)
    if not ffmpeg or not ffprobe:
        parser.error("FFmpeg and ffprobe must be installed or supplied with --ffmpeg/--ffprobe")
    # mkdir(exist_ok=False) is the reservation, including concurrent invocations.
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"Output already exists: {output}")
    started = time.monotonic()
    report = {"schemaVersion": 1, "status": "RUNNING", "startedAt": datetime.now(timezone.utc).isoformat(),
              "operation": "local-video-frame-preparation", "gpuUsed": False,
              "input": {"path": str(video)}, "output": str(output), "stages": []}
    received_signal = None

    def on_signal(signum, _frame):
        nonlocal received_signal
        if received_signal is None:
            received_signal = signum
            raise Cancelled(signum)

    previous = {signum: signal.signal(signum, on_signal) for signum in (signal.SIGINT, signal.SIGTERM)}
    exit_code = 1
    try:
        (output / "logs").mkdir()
        (output / "images").mkdir()
        write_json(output / "report.json", report)
        write_json(output / "provenance.json", provenance)
        if provenance_path:
            shutil.copyfile(provenance_path, output / "source-provenance.json")
            report["input"]["provenanceSha256"] = sha256(output / "source-provenance.json")
        initial = video.stat()
        report["input"].update({"bytes": initial.st_size, "sha256": sha256(video)})
        run_tool([ffmpeg, "-version"], "ffmpeg-version", output, report)
        run_tool([ffprobe, "-version"], "ffprobe-version", output, report)
        run_tool([ffprobe, "-v", "error", "-protocol_whitelist", "file,pipe", "-select_streams", "V:0",
                  "-show_streams", "-show_format", "-of", "json", str(video)], "ffprobe", output, report)
        probe = json.loads((output / "logs/ffprobe.stdout.log").read_text())
        streams = probe.get("streams", [])
        if not streams:
            raise ValueError("Input has no video stream (attached cover images are excluded)")
        stream = streams[0]
        width, height = stream.get("width", 0), stream.get("height", 0)
        if width < 1 or height < 1:
            raise ValueError("Input video has invalid dimensions")
        duration = optional_number(stream.get("duration"))
        if duration is None:
            duration = optional_number(probe.get("format", {}).get("duration"))
        if duration is not None and args.start >= duration:
            raise ValueError(f"Clip start {args.start} is outside video duration {duration}")
        effective_duration = min(args.duration, duration - args.start) if duration is not None else args.duration
        frame_limit = min(args.max_frames, max(1, math.ceil(effective_duration * args.fps - 1e-9)))
        sampling = {"startSeconds": args.start, "durationSeconds": args.duration,
                    "effectiveDurationSeconds": effective_duration, "fps": args.fps,
                    "maxFrames": args.max_frames, "effectiveFrameLimit": frame_limit,
                    "maxEdge": args.max_edge, "timestampMeaning": TIMESTAMP_MEANING,
                    "orientation": "FFmpeg autorotation applied before scaling; output pixels are display-oriented",
                    "scaling": "Fit within source pixel dimensions and maxEdge; square pixels, preserve display aspect ratio"}
        report["sampling"] = sampling
        report["input"].update({"durationSeconds": duration, "width": width, "height": height,
                                "sampleAspectRatio": stream.get("sample_aspect_ratio"),
                                "streamStartTimeSeconds": optional_number(stream.get("start_time")),
                                "sideData": stream.get("side_data_list", [])})
        filters = (f"fps=fps={args.fps}:start_time=0:round=near,"
                   f"scale=w='min({args.max_edge},iw)':h='min({args.max_edge},ih)':"
                   "force_original_aspect_ratio=decrease:reset_sar=1")
        command = [ffmpeg, "-hide_banner", "-nostdin", "-n", "-loglevel", "info",
                   "-filter_threads", "2", "-hwaccel", "none", "-threads", "2",
                   "-protocol_whitelist", "file,pipe", "-autorotate", "-ss", str(args.start),
                   "-i", str(video), "-map", "0:V:0", "-an", "-sn", "-dn", "-t", str(effective_duration),
                   "-vf", filters, "-fps_mode", "passthrough", "-frames:v", str(frame_limit),
                   "-c:v", "mjpeg", "-q:v", "2", "-pix_fmt", "yuvj444p", "-threads", "2",
                   "-map_metadata", "-1", "-start_number", "1", str(output / "images/frame_%06d.jpg")]
        run_tool(command, "ffmpeg-extract", output, report)
        frames = []
        for index, image in enumerate(sorted((output / "images").glob("frame_*.jpg"))):
            if image.name != f"frame_{index + 1:06d}.jpg":
                raise ValueError("Extracted image numbering is not contiguous")
            image_width, image_height = jpeg_size(image)
            if max(image_width, image_height) > args.max_edge:
                raise ValueError("Extracted frame exceeds --max-edge")
            frames.append({"index": index, "file": image.relative_to(output).as_posix(),
                           "nominalSourceTimeSeconds": args.start + index / args.fps,
                           "nominalClipTimeSeconds": index / args.fps,
                           "bytes": image.stat().st_size, "sha256": sha256(image),
                           "width": image_width, "height": image_height})
        if not frames or len(frames) > frame_limit:
            raise ValueError(f"Unexpected extracted frame count: {len(frames)} (limit {frame_limit})")
        final = video.stat()
        if (initial.st_size, initial.st_mtime_ns) != (final.st_size, final.st_mtime_ns):
            raise ValueError("Input video changed during preparation; output cannot be trusted")
        sequence = {"schemaVersion": 1, "kind": "video-samples", "source": report["input"],
                    "sampling": sampling, "frames": frames}
        write_json(output / "sequence.json", sequence)
        report["result"] = {"frameCount": len(frames), "imageBytes": sum(frame["bytes"] for frame in frames),
                            "dimensions": sorted({f"{frame['width']}x{frame['height']}" for frame in frames}),
                            "sequenceSha256": sha256(output / "sequence.json"),
                            "provenanceSha256": sha256(output / "provenance.json")}
        report["status"], exit_code = "PASS", 0
    except KeyboardInterrupt as error:
        signum = getattr(error, "signum", signal.SIGINT)
        report.update(status="CANCELLED", error=str(error), cancellationSignal=signal.Signals(signum).name)
        exit_code = 128 + signum
    except Exception as error:
        report.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    finally:
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        report["elapsedSeconds"] = round(time.monotonic() - started, 6)
        rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        report["peakChildRssBytes"] = int(rss if sys.platform == "darwin" else rss * 1024)
        report["memoryMeasurement"] = "Maximum individual child process RSS; not combined process-group memory"
        report["exitCode"] = exit_code
        write_json(output / "report.json", report)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    print(f"{report['status']}: {output / 'report.json'}")
    if report.get("error"):
        print(report["error"], file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
