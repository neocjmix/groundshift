"""Adapter tests only. These do not claim GPU or browser validation."""
import importlib.util
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "reconstruct.py"
spec = importlib.util.spec_from_file_location("reconstruct", SCRIPT)
reconstruct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconstruct)


def dataset_at(root):
    dataset = root / "dataset"
    dataset.mkdir()
    (dataset / "image.jpg").write_bytes(b"test fixture; never passed to a real trainer")
    frames = []
    for x in (0, 2):
        frames.append({"file_path": "image.jpg", "transform_matrix":
                       [[1, 0, 0, x], [0, 1, 0, 0], [0, 0, 1, 3], [0, 0, 0, 1]]})
    transforms = {"w": 512, "h": 512, "fl_x": 400, "fl_y": 400,
                  "camera_model": "OPENCV", "frames": frames}
    provenance = {"sourceType": "images", "sourceUrl": dataset.as_uri(),
                  "license": "test fixture", "licenseUrl": dataset.as_uri(),
                  "attribution": "Groundshift adapter test"}
    reconstruct.write_json(dataset / "transforms.json", transforms)
    reconstruct.write_json(dataset / "provenance.json", provenance)
    return dataset, transforms, provenance


class ReconstructionTests(unittest.TestCase):
    def test_mock_hardware_late_publish_cancellation_never_reports_pass(self):
        """No GPU executes: mock the backend/export and cancel during file copy."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset, _, _ = dataset_at(root)
            output, publish = root / "job", root / "published"
            brush = root / "mock-brush"
            brush.write_text("test only; never executed")
            handlers = {}
            original_copy = reconstruct.shutil.copytree

            class MockProcess:
                def __init__(self, _command, **kwargs):
                    kwargs["stdout"].write("TEST ONLY mocked training\n")

                def poll(self):
                    return 0

                def wait(self):
                    (output / "resources.txt").write_text("TEST ONLY mocked resource report\n")
                    (output / "world/scene.ply").write_text("TEST ONLY; not a Gaussian scene")
                    return 0

            def mock_tool(command, **_kwargs):
                return subprocess.CompletedProcess(command, 0,
                    stdout="brush-cli 0.3.0\n" if "--version" in command else "TEST ONLY mocked CLI help\n")

            def cancel_during_copy(src, dst):
                handlers[signal.SIGTERM](signal.SIGTERM, None)
                return original_copy(src, dst)

            with (patch.object(sys, "argv", [str(SCRIPT), str(dataset), str(output),
                                             "--brush", str(brush), "--publish", str(publish)]),
                  patch.object(reconstruct.subprocess, "run", side_effect=mock_tool),
                  patch.object(reconstruct.subprocess, "Popen", MockProcess),
                  patch.object(reconstruct, "ply_info", return_value={"testOnly": True}),
                  patch.object(reconstruct.signal, "signal", side_effect=lambda signum, handler: handlers.update({signum: handler})),
                  patch.object(reconstruct.shutil, "copytree", side_effect=cancel_during_copy),
                  redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
                code = reconstruct.main()
            report = json.loads((output / "job.json").read_text())
            self.assertNotEqual(code, 0)
            self.assertEqual(report["status"], "CANCELLED")
            self.assertEqual(report["browserRendering"], "NOT RUN")
            self.assertTrue((publish / "world.json").is_file(), "Completed copy is preserved after cancellation")
            self.assertIn("TEST ONLY mocked training", (output / "training.log").read_text())

    def test_route_orders_real_cameras_and_stops_at_missing_source_views(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, transforms, provenance = dataset_at(Path(temporary))
            first, last = transforms["frames"]
            first["file_path"], last["file_path"] = "images/a.jpg", "images/c.jpg"
            transforms["frames"] = [last, first]
            sequence = {"frames": [{"file": f"images/{name}.jpg"} for name in "abc"]}
            world, cameras = reconstruct.artifact(transforms, provenance, "test", "test", sequence, "colmap-0")
            self.assertEqual(world["navigation"]["camera"]["position"], [0, 0, 3])
            self.assertEqual([frame["image"] for frame in cameras["frames"]], ["images/a.jpg", "images/c.jpg"])
            self.assertFalse(cameras["frames"][1]["continuousFromPrevious"])
            self.assertEqual(cameras["frames"][1]["componentId"], "colmap-0")
            sequence["frames"].pop(1)
            _, cameras = reconstruct.artifact(transforms, provenance, "test", "test", sequence, "colmap-0")
            self.assertTrue(cameras["frames"][1]["continuousFromPrevious"])

    def test_ambiguous_or_unmapped_sequence_is_rejected(self):
        frames = [{"file_path": "images/a.jpg"}]
        for sequence in ({"frames": [{"file": "images/a.jpg"}] * 2}, {"frames": [{"file": "images/other.jpg"}]}):
            with self.assertRaises(ValueError):
                reconstruct.ordered_frames(frames, sequence, "colmap-0")
        with self.assertRaisesRegex(ValueError, "component ID"):
            reconstruct.ordered_frames(frames, {"frames": [{"file": "images/a.jpg"}]}, None)

    def test_sample_acquisition_refuses_any_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "images").mkdir()
            original = root / "images/original.jpg"
            original.write_bytes(b"preserve user input")
            fetch = SCRIPT.parent / "fetch-reconstruction-sample.py"
            result = subprocess.run([sys.executable, str(fetch), "--output", str(root)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"Output already exists", result.stderr)
            self.assertEqual(original.read_bytes(), b"preserve user input")

    def test_distortion_rejected_before_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, transforms, _ = dataset_at(Path(temporary))
            transforms["k1"] = .03
            reconstruct.write_json(dataset / "transforms.json", transforms)
            with self.assertRaisesRegex(ValueError, "ignores distortion"):
                reconstruct.validate_dataset(dataset)

    def test_camera_pose_and_forward_are_preserved_in_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, transforms, provenance = dataset_at(Path(temporary))
            world, cameras = reconstruct.artifact(transforms, provenance, "test", "test")
            camera = world["navigation"]["camera"]
            self.assertEqual(camera["position"], [0, 0, 3])
            self.assertEqual(camera["target"], [0, 0, 1])
            self.assertEqual(cameras["frames"][1]["cameraToWorld"][0][3], 2)
            self.assertEqual(world["coordinates"]["assetToWorld"]["quaternion"], [0, 0, 0, 1])

    def test_reflected_camera_is_not_accepted_as_rotation(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, transforms, _ = dataset_at(Path(temporary))
            transforms["frames"][0]["transform_matrix"][0][0] = -1
            reconstruct.write_json(dataset / "transforms.json", transforms)
            with self.assertRaisesRegex(ValueError, "right-handed"):
                reconstruct.validate_dataset(dataset)

    def test_missing_source_type_is_rejected_before_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, _, provenance = dataset_at(Path(temporary))
            del provenance["sourceType"]
            reconstruct.write_json(dataset / "provenance.json", provenance)
            with self.assertRaisesRegex(ValueError, "sourceType"):
                reconstruct.validate_dataset(dataset)

    def test_invalid_or_credential_urls_are_rejected(self):
        for value in ("relative/path", "javascript:alert(1)", "https://user:secret@example.org/data", "https://"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temporary:
                dataset, _, provenance = dataset_at(Path(temporary))
                provenance["licenseUrl"] = value
                reconstruct.write_json(dataset / "provenance.json", provenance)
                with self.assertRaisesRegex(ValueError, "absolute HTTP"):
                    reconstruct.validate_dataset(dataset)

    def test_extra_source_metadata_is_not_copied_into_strict_world_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, transforms, provenance = dataset_at(Path(temporary))
            provenance["captureNotes"] = {"arbitrary": "dataset metadata"}
            world, _ = reconstruct.artifact(transforms, provenance, "test", "test")
            self.assertEqual(set(world["provenance"]),
                             {"sourceType", "sourceUrl", "license", "licenseUrl", "attribution", "backend", "notes"})

    def test_blank_world_identity_is_rejected_before_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, transforms, provenance = dataset_at(Path(temporary))
            for title, identifier in ((" ", "test"), ("test", "")):
                with self.assertRaisesRegex(ValueError, "must not be blank"):
                    reconstruct.artifact(transforms, provenance, title, identifier)

    def test_invalid_calibration_rejected_before_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset, transforms, _ = dataset_at(Path(temporary))
            transforms["fl_y"] = 0
            reconstruct.write_json(dataset / "transforms.json", transforms)
            with self.assertRaisesRegex(ValueError, "fl_y"):
                reconstruct.validate_dataset(dataset)

    def test_z_up_to_y_up_keeps_right_handed_coordinates(self):
        q = reconstruct.align_up([0, 0, 1])
        for actual, expected in zip(reconstruct.rotate([0, 0, 1], q), [0, 1, 0]):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(reconstruct.rotate([0, 1, 0], q), [0, 0, -1]):
            self.assertAlmostEqual(actual, expected)

    def test_missing_input_records_failure_without_claiming_render(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = subprocess.run([sys.executable, str(SCRIPT), str(root / "missing"),
                                     str(root / "job")], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads((root / "job/job.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertNotIn("artifact", report)

    def test_failed_backend_preserves_exit_code_and_logs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset, _, _ = dataset_at(root)
            executable = root / "fake-brush"
            executable.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo "brush-cli 0.3.0"; exit 0; fi\n'
                                  'if [ "$1" = "--help" ]; then exit 0; fi\necho "synthetic backend failure"\nexit 7\n')
            executable.chmod(0o755)
            result = subprocess.run([sys.executable, str(SCRIPT), str(dataset), str(root / "job"),
                                     "--brush", str(executable)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            report = json.loads((root / "job/job.json").read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["exitCode"], 7)
            self.assertIn("synthetic backend failure", (root / "job/training.log").read_text())
            self.assertFalse((root / "job/world/world.json").exists())

    def test_cancellation_terminates_process_and_records_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dataset, _, _ = dataset_at(root)
            executable = root / "fake-brush"
            executable.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo "brush-cli 0.3.0"; exit 0; fi\n'
                                  'if [ "$1" = "--help" ]; then exit 0; fi\necho "synthetic backend started"\nsleep 30\n')
            executable.chmod(0o755)
            process = subprocess.Popen([sys.executable, str(SCRIPT), str(dataset), str(root / "job"),
                                        "--brush", str(executable)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                for _ in range(100):
                    log = root / "job/training.log"
                    if log.exists() and "synthetic backend started" in log.read_text():
                        break
                    time.sleep(.03)
                else:
                    self.fail("Synthetic backend did not start")
                process.send_signal(signal.SIGTERM)
                process.communicate(timeout=5)
                report = json.loads((root / "job/job.json").read_text())
                self.assertEqual(report["status"], "CANCELLED")
                self.assertNotEqual(process.returncode, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()


if __name__ == "__main__":
    unittest.main()
