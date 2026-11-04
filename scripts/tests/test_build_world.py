"""Pipeline safety tests; they do not stand in for native reconstruction."""
import importlib.util
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "build-world.py"
spec = importlib.util.spec_from_file_location("build_world", SCRIPT)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class PipelineTests(unittest.TestCase):
    def test_mock_hardware_late_publish_cancellation_never_reports_pass(self):
        """Mock CPU/GPU stages; exercise cancellation during a real file copy."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output, publish = root / "source", root / "job", root / "published"
            source.mkdir()
            provenance = source / "provenance.json"
            provenance.write_text("{}")
            handlers = {}
            original_copy = pipeline.shutil.copytree

            class MockProcess:
                def __init__(self, command, **_kwargs):
                    self.command = command

                def poll(self):
                    return 0

                def wait(self):
                    if any(str(arg).endswith("estimate-poses.py") for arg in self.command):
                        (output / "poses").mkdir()
                        pipeline.write_json(output / "poses/report.json", {
                            "status": "PASS", "inputImages": ["a", "b"],
                            "registeredImages": ["a", "b"], "selectedModel": 0,
                        })
                    else:
                        (output / "training/world").mkdir(parents=True)
                        (output / "training/world/world.json").write_text('{"testOnly":true}')
                        pipeline.write_json(output / "training/job.json", {
                            "status": "PASS", "artifact": {"testOnly": True},
                        })
                    return 0

            def cancel_during_copy(src, dst):
                handlers[signal.SIGTERM](signal.SIGTERM, None)
                return original_copy(src, dst)

            with (patch.object(sys, "argv", [str(SCRIPT), str(source), str(output),
                                             "--provenance", str(provenance), "--publish", str(publish)]),
                  patch.object(pipeline.subprocess, "Popen", MockProcess),
                  patch.object(pipeline.signal, "signal", side_effect=lambda signum, handler: handlers.update({signum: handler})),
                  patch.object(pipeline.shutil, "copytree", side_effect=cancel_during_copy),
                  redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
                code = pipeline.main()
            report = json.loads((output / "pipeline.json").read_text())
            self.assertNotEqual(code, 0)
            self.assertEqual(report["status"], "CANCELLED")
            self.assertEqual(report["browserRendering"], "NOT RUN")
            self.assertEqual(report["visualQuality"], "NOT RUN")
            self.assertTrue((publish / "world.json").is_file(), "Completed copy is preserved after cancellation")
            self.assertTrue((output / "reconstruct.log").is_file())

    def test_partial_sfm_does_not_silently_start_training(self):
        report = {"status": "PASS", "inputImages": ["a", "b", "c"],
                  "registeredImages": ["a", "b"], "selectedModel": 0}
        with self.assertRaisesRegex(ValueError, "Training was not started"):
            pipeline.coverage_gate(report, 1)
        gate = pipeline.coverage_gate(report, .6)
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["fullRegistration"], "FAIL")
        report["registeredImages"] = ["a", "unknown"]
        with self.assertRaisesRegex(ValueError, "do not match"):
            pipeline.coverage_gate(report, .6)

    def test_missing_source_failure_is_preserved_and_browser_unverified(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run([sys.executable, str(SCRIPT), str(root / "missing"), str(root / "job")], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads((root / "job/pipeline.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["browserRendering"], "NOT RUN")
            self.assertEqual(report["stages"], [])

    def test_existing_output_preserves_prior_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run([sys.executable, str(SCRIPT), str(root / "missing"), str(root)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"Output already exists", result.stderr)
            self.assertFalse((root / "pipeline.json").exists())


if __name__ == "__main__":
    unittest.main()
