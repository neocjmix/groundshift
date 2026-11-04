"""Small real FFmpeg fixtures plus non-GPU subprocess lifecycle checks."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "prepare-video.py"
SPEC = importlib.util.spec_from_file_location("prepare_video", SCRIPT)
VIDEO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VIDEO)
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


class VideoInputTests(unittest.TestCase):
    def test_invalid_sampling_parameters_fail_before_output(self):
        for flag, value in (("--start", "-1"), ("--duration", "0"), ("--fps", "nan"),
                            ("--max-edge", "1"), ("--max-frames", "0")):
            with self.subTest(flag=flag):
                result = subprocess.run([sys.executable, str(SCRIPT), "unused", "unused", flag, value],
                                        capture_output=True)
                self.assertEqual(result.returncode, 2)

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video, output = root / "video.mp4", root / "output"
            video.write_bytes(b"not needed")
            output.mkdir()
            marker = output / "marker.txt"
            marker.write_text("keep")
            result = subprocess.run([sys.executable, str(SCRIPT), str(video), str(output)], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"Output already exists", result.stderr)
            self.assertEqual(marker.read_text(), "keep")
            self.assertEqual(list(output.iterdir()), [marker])

    def test_unknown_license_is_honest_and_explicit(self):
        provenance = VIDEO.provenance_for(Path("/tmp/source.mp4"), Path("/tmp/result"), None)
        self.assertEqual(provenance["license"], "unspecified")
        self.assertEqual(provenance["sourceUrl"], "file:///tmp/source.mp4")
        self.assertIn("No ownership or redistribution permission is inferred", provenance["notes"])

    def test_invalid_provenance_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "provenance.json"
            path.write_text(json.dumps({"sourceUrl": "https://user:password@example.com/video",
                                        "license": "test", "licenseUrl": "https://example.com/license",
                                        "attribution": "Fixture"}))
            with self.assertRaises(ValueError):
                VIDEO.provenance_for(Path("/tmp/source.mp4"), Path("/tmp/result"), path)

    def test_dangling_output_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video = root / "input.mp4"
            video.write_bytes(b"unused")
            output = root / "output"
            output.symlink_to(root / "missing")
            result = subprocess.run([sys.executable, str(SCRIPT), str(video), str(output)], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertTrue(output.is_symlink())
            self.assertFalse((root / "missing").exists())


@unittest.skipUnless(FFMPEG and FFPROBE, "FFmpeg/ffprobe not installed; real media checks NOT RUN")
class VideoExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source.mp4"
        # One second of tiny colored quadrants, with distinguishable orientation.
        self.run_ffmpeg(["-f", "lavfi", "-i", "color=red:size=160x96:rate=8:duration=1",
                         "-vf", "drawbox=x=80:y=0:w=80:h=48:color=green:t=fill,"
                                "drawbox=x=0:y=48:w=80:h=48:color=blue:t=fill,"
                                "drawbox=x=80:y=48:w=80:h=48:color=white:t=fill",
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(self.source)])

    def run_ffmpeg(self, args):
        result = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin", "-n", *args],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result

    def prepare(self, source=None, args=(), name="prepared", expected=0):
        output = self.root / name
        result = subprocess.run([sys.executable, str(SCRIPT), str(source or self.source), str(output),
                                 "--ffmpeg", FFMPEG, "--ffprobe", FFPROBE, *args], capture_output=True)
        self.assertEqual(result.returncode, expected, result.stderr.decode())
        return output, json.loads((output / "report.json").read_text())

    def test_default_no_upscale_hashes_and_nominal_chronology(self):
        output, report = self.prepare()
        self.assertEqual(report["status"], "PASS")
        self.assertFalse(report["gpuUsed"])
        sequence = json.loads((output / "sequence.json").read_text())
        self.assertEqual(len(sequence["frames"]), 4)
        self.assertEqual([f["nominalSourceTimeSeconds"] for f in sequence["frames"]], [0, .25, .5, .75])
        self.assertIn("not actual frame PTS or camera capture timestamps", sequence["sampling"]["timestampMeaning"])
        self.assertEqual(sequence["source"]["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        for index, frame in enumerate(sequence["frames"]):
            self.assertEqual((frame["width"], frame["height"]), (160, 96))
            self.assertEqual(frame["index"], index)
            self.assertEqual(frame["sha256"], hashlib.sha256((output / frame["file"]).read_bytes()).hexdigest())
        self.assertEqual(len(report["stages"]), 4)
        for stage in report["stages"]:
            self.assertTrue((output / stage["stdout"]).exists())
            self.assertTrue((output / stage["stderr"]).exists())
            self.assertEqual(stage["status"], "PASS")

    def test_start_duration_frame_cap_and_scale(self):
        output, report = self.prepare(args=("--start", ".25", "--duration", ".5", "--fps", "8",
                                            "--max-frames", "2", "--max-edge", "80"))
        sequence = json.loads((output / "sequence.json").read_text())
        self.assertEqual(report["result"]["frameCount"], 2)
        self.assertEqual([f["nominalSourceTimeSeconds"] for f in sequence["frames"]], [.25, .375])
        self.assertEqual([(f["width"], f["height"]) for f in sequence["frames"]], [(80, 48)] * 2)

    def test_real_sampling_keeps_source_color_order(self):
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
        for index, color in enumerate(colors):
            (self.root / f"color_{index:02d}.ppm").write_bytes(b"P6\n32 16\n255\n" + bytes(color) * 32 * 16)
        changing = self.root / "changing.mp4"
        self.run_ffmpeg(["-framerate", "4", "-start_number", "0", "-i", str(self.root / "color_%02d.ppm"),
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(changing)])
        output, report = self.prepare(source=changing)
        self.assertEqual(report["result"]["frameCount"], 4)
        decoded = self.run_ffmpeg(["-framerate", "4", "-i", str(output / "images/frame_%06d.jpg"),
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]).stdout
        for index, expected in enumerate(colors):
            offset = index * 32 * 16 * 3 + (8 * 32 + 16) * 3
            self.assertTrue(all(abs(actual - target) < 10 for actual, target in
                                zip(decoded[offset:offset + 3], expected)))

    def test_rotation_metadata_is_baked_into_pixels(self):
        rotated = self.root / "rotated.mp4"
        self.run_ffmpeg(["-display_rotation", "90", "-i", str(self.source), "-c", "copy", str(rotated)])
        output, report = self.prepare(source=rotated, args=("--max-frames", "1"))
        self.assertEqual(report["result"]["dimensions"], ["96x160"])
        self.assertEqual(report["input"]["sideData"][0]["rotation"], 90)
        image = output / "images/frame_000001.jpg"
        decoded = self.run_ffmpeg(["-i", str(image), "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]).stdout
        def pixel(x, y):
            return tuple(decoded[(y * 96 + x) * 3:(y * 96 + x) * 3 + 3])
        # rotate=90 displays counterclockwise: top-right green moves top-left.
        self.assertGreater(pixel(20, 20)[1], pixel(20, 20)[0] + 60)
        self.assertGreater(pixel(20, 130)[0], pixel(20, 130)[1] + 100)

    def test_non_square_pixels_preserve_display_aspect_without_upscale(self):
        anamorphic = self.root / "anamorphic.mp4"
        self.run_ffmpeg(["-i", str(self.source), "-vf", "setsar=2/1", "-c:v", "libx264", str(anamorphic)])
        output, report = self.prepare(source=anamorphic, args=("--max-frames", "1"))
        self.assertEqual(report["input"]["sampleAspectRatio"], "2:1")
        self.assertEqual(report["result"]["dimensions"], ["160x48"])
        probe = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-of", "json",
                                str(output / "images/frame_000001.jpg")], capture_output=True, check=True)
        self.assertEqual(json.loads(probe.stdout)["streams"][0]["sample_aspect_ratio"], "1:1")

    def test_invalid_media_preserves_failure_and_probe_logs(self):
        broken = self.root / "broken.mp4"
        broken.write_bytes(b"not a video")
        output, report = self.prepare(source=broken, expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["stages"][-1]["name"], "ffprobe")
        self.assertEqual(report["stages"][-1]["status"], "FAIL")
        self.assertTrue((output / "logs/ffprobe.stderr.log").read_text())
        self.assertFalse((output / "sequence.json").exists())

    def test_start_after_end_fails_without_extraction(self):
        _, report = self.prepare(args=("--start", "2"), expected=1)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("outside video duration", report["error"])
        self.assertEqual(len(report["stages"]), 3)


FAKE_TOOL = '''#!/usr/bin/env python3
import json, os
from pathlib import Path
import signal, subprocess, sys, time
if "-version" in sys.argv:
    print("Test double; no media decoding or GPU")
elif Path(sys.argv[0]).name == "ffprobe":
    print(json.dumps({"streams": [{"width": 10, "height": 10, "duration": "15"}]}))
else:
    output = Path(sys.argv[-1]).parent.parent
    child_code = """import os, signal, sys, time
from pathlib import Path
marker=Path(sys.argv[1])
def stop(signum, frame):
    marker.with_name('grandchild-signal').write_text(str(signum))
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
marker.write_text(str(os.getpid()))
time.sleep(60)
"""
    child = subprocess.Popen([sys.executable, "-c", child_code, str(output / "grandchild-ready")])
    def stop(signum, frame):
        (output / "child-signal").write_text(str(signum))
        child.wait(timeout=3)
        sys.exit(42)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print("FAKE_EXTRACTION_READY", flush=True)
    time.sleep(60)
'''


class VideoCancellationTests(unittest.TestCase):
    def check_signal(self, signum):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("ffmpeg", "ffprobe"):
                tool = root / name
                tool.write_text(FAKE_TOOL)
                tool.chmod(0o755)
            video = root / "input.mp4"
            video.write_bytes(b"fake media; no GPU")
            output = root / "prepared"
            process = subprocess.Popen([sys.executable, str(SCRIPT), str(video), str(output),
                                        "--ffmpeg", str(root / "ffmpeg"), "--ffprobe", str(root / "ffprobe")],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 10
                while not (output / "grandchild-ready").exists():
                    if time.monotonic() > deadline or process.poll() is not None:
                        self.fail(f"Fake extraction did not start: {process.poll()}")
                    time.sleep(.02)
                process.send_signal(signum)
                stdout, stderr = process.communicate(timeout=8)
                self.assertEqual(process.returncode, 128 + signum, (stdout, stderr))
                report = json.loads((output / "report.json").read_text())
                self.assertEqual(report["status"], "CANCELLED")
                self.assertEqual(report["cancellationSignal"], signal.Signals(signum).name)
                stage = report["stages"][-1]
                self.assertEqual(stage["status"], "CANCELLED")
                self.assertEqual(stage["exitCode"], 42)
                self.assertEqual((output / "child-signal").read_text(), str(signum))
                self.assertEqual((output / "grandchild-signal").read_text(), str(signum))
                self.assertIn("FAKE_EXTRACTION_READY", (output / stage["stdout"]).read_text())
                self.assertFalse((output / "sequence.json").exists())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
                report_path = output / "report.json"
                if report_path.exists():
                    for stage in json.loads(report_path.read_text())["stages"]:
                        if stage.get("status") == "RUNNING" and "pid" in stage:
                            try:
                                os.killpg(stage["pid"], signal.SIGKILL)
                            except ProcessLookupError:
                                pass

    def test_sigterm_reaches_child_and_grandchild(self):
        self.check_signal(signal.SIGTERM)

    def test_sigint_reaches_child_and_grandchild(self):
        self.check_signal(signal.SIGINT)


if __name__ == "__main__":
    unittest.main()
