"""Synthetic projection/stereo tests; real scene quality needs separate inspection."""
import argparse
import importlib.util
import io
import json
from contextlib import redirect_stderr
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("warp_gap", Path(__file__).parents[1] / "warp-panorama-gap.py")
WARP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WARP)
try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


@unittest.skipUnless(cv2 is not None, "NumPy/OpenCV required; projection/stereo NOT RUN")
class StereoProjectionTests(unittest.TestCase):
    def frame(self, position=(0, 0, 0), name="a.png", width=192, height=96):
        gl = np.diag([1., -1., -1., 1.])
        gl[:3, 3] = position
        return {"file_path": f"images/{name}", "w": width, "h": height,
                "fl_x": 100., "fl_y": 100., "cx": width / 2, "cy": height / 2,
                "transform_matrix": gl.tolist()}

    def test_opengl_camera_conversion_and_relative_translation(self):
        left = self.frame()
        right = self.frame((1, 0, 0))
        np.testing.assert_allclose(WARP.camera(left), np.eye(4))
        np.testing.assert_allclose(WARP.relative_camera(left, right)[:3, 3], [-1, 0, 0])
        bad = self.frame()
        bad["transform_matrix"][0][0] = 2
        with self.assertRaisesRegex(ValueError, "orthonormal"):
            WARP.camera(bad)

    def test_corner_origin_intrinsics_project_to_opencv_integer_pixel_centers(self):
        frame = self.frame()
        k = WARP.intrinsics(frame)
        self.assertEqual(k[0, 2], frame["cx"] - 0.5)
        self.assertEqual(k[1, 2], frame["cy"] - 0.5)
        # Ray construction matches prepare-panoramas.py: original COLMAP
        # coordinates of a pixel are (column + 0.5, row + 0.5).
        for column, row in ((0, 0), (31, 22), (191, 95)):
            point = np.array([(column + 0.5 - frame["cx"]) / frame["fl_x"],
                              (row + 0.5 - frame["cy"]) / frame["fl_y"], 1.])
            projected = k @ point
            np.testing.assert_allclose(projected[:2] / projected[2], [column, row], atol=1e-12)

    def test_disparity_sign_swap_and_vertical_matching_rotation(self):
        left, right = self.frame(), self.frame((1, 0, 0))
        result = WARP.rectification(left, right)
        self.assertEqual(result[6], 0)
        self.assertAlmostEqual(result[7], 1)
        self.assertFalse(result[8])
        reversed_result = WARP.rectification(right, left)
        self.assertTrue(reversed_result[8])
        vertical = WARP.rectification(left, self.frame((0, 1, 0)))
        self.assertEqual(vertical[6], 1)
        matrix = np.arange(24).reshape(4, 6).astype(np.float32)
        np.testing.assert_array_equal(WARP.matching_orientation(WARP.matching_orientation(matrix, 1), 1, inverse=True), matrix)
        with self.assertRaisesRegex(ValueError, "nonzero"):
            WARP.rectification(left, left)

    def test_depth_unprojection_and_halfway_target_projection(self):
        k = np.array([[100., 0, 50], [0, 100, 50], [0, 0, 1]])
        disparity = np.zeros((101, 101), dtype=np.float32)
        disparity[50, 50] = 20
        valid = disparity > 0
        points, y, x = WARP.depth_points(disparity, valid, k, 1, 0, 1)
        np.testing.assert_allclose(points, [[0, 0, 5]])
        target_points = WARP.to_target(points, self.frame(), np.eye(3), self.frame((0.5, 0, 0)))
        np.testing.assert_allclose(target_points, [[-0.5, 0, 5]])
        image, depth = WARP.forward_splat(target_points, np.array([[7, 11, 19]], dtype=np.uint8), k, 101, 101, 1)
        self.assertEqual(np.count_nonzero(depth), 1)
        self.assertEqual(depth[50, 40], 5)
        np.testing.assert_array_equal(image[50, 40], [7, 11, 19])
        reverse_points, _, _ = WARP.depth_points(-disparity, valid, k, 1, 0, -1)
        np.testing.assert_allclose(reverse_points, points)

    def test_zbuffer_keeps_nearest_and_rejects_points_behind_camera(self):
        k = np.array([[10., 0, 4], [0, 10, 4], [0, 0, 1]])
        points = np.array([[0., 0, 10], [0, 0, 2], [0, 0, -1]])
        colors = np.array([[1, 2, 3], [4, 5, 6], [200, 201, 202]], dtype=np.uint8)
        image, depth = WARP.forward_splat(points, colors, k, 9, 9, 1)
        np.testing.assert_array_equal(image[4, 4], [4, 5, 6])
        self.assertEqual(depth[4, 4], 2)
        self.assertEqual(np.count_nonzero(depth), 1)

    def test_actual_sgbm_known_shift_and_target_pixels_are_not_required(self):
        rng = np.random.default_rng(72)
        texture = rng.integers(30, 220, (96, 192), dtype=np.uint8)
        left_image = np.repeat(texture[:, :, None], 3, axis=2)
        right_image = np.zeros_like(left_image)
        right_image[:, :-8] = left_image[:, 8:]
        dl, dr = WARP.stereo_disparities(left_image, right_image, 0, 64, 5)
        self.assertAlmostEqual(float(np.median(dl[10:-10, 80:150])), 8, delta=0.25)
        self.assertAlmostEqual(float(np.median(dr[10:-10, 20:110])), -8, delta=0.25)
        # This dataset deliberately has no target image at all. A real run must
        # succeed using only its camera record, proving no target-pixel reads.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "dataset"
            (source / "images").mkdir(parents=True)
            cv2.imwrite(str(source / "images/a.png"), left_image)
            cv2.imwrite(str(source / "images/c.png"), right_image)
            frames = [self.frame(name="a.png"), self.frame((1, 0, 0), "c.png"), self.frame((0.5, 0, 0), "missing-target.png")]
            (source / "transforms.json").write_text(json.dumps({"camera_model": "PINHOLE", "frames": frames}))
            args = argparse.Namespace(dataset=source, output=root / "result", left="a.png", right="c.png",
                                      target="missing-target.png", max_disparity=64, rectified_scale=2,
                                      lr_tolerance=1.5, photo_tolerance=32, footprint=2)
            report = WARP.run(args)
            self.assertEqual(report["status"], "PASS")
            self.assertFalse(report["targetImagePixelsRead"])
            self.assertGreater(report["coverage"]["observedWarpPixels"], 96 * 192 * 0.5)
            self.assertNotIn("missing-target.png", report["inputs"])
            mask = cv2.imread(str(args.output / "mask.png"), cv2.IMREAD_UNCHANGED)
            self.assertEqual(mask.ndim, 2)
            self.assertTrue(set(np.unique(mask)).issubset({0, 255}))

    def test_keyboard_interrupt_retains_cancelled_report_and_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(dataset=root / "dataset", output=root / "result",
                                      max_disparity=64, rectified_scale=2, lr_tolerance=1.5,
                                      photo_tolerance=32, footprint=2)
            with patch.object(Path, "read_bytes", side_effect=KeyboardInterrupt("test cancellation")):
                with self.assertRaises(KeyboardInterrupt):
                    WARP.run(args)
            report = json.loads((args.output / "report.json").read_text())
            self.assertEqual(report["status"], "CANCELLED")
            self.assertIn("KeyboardInterrupt", report["traceback"])

    def test_cli_sigterm_handler_marks_cancelled_and_restores_previous_handler(self):
        previous = signal.getsignal(signal.SIGTERM)
        def interrupt_read(*_args):
            handler = signal.getsignal(signal.SIGTERM)
            self.assertTrue(callable(handler))
            self.assertIsNot(handler, previous)
            handler(signal.SIGTERM, None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "result"
            with (patch.object(sys, "argv", [str(Path(__file__).parents[1] / "warp-panorama-gap.py"),
                                             str(root / "dataset"), str(output)]),
                  patch.object(Path, "read_bytes", side_effect=interrupt_read),
                  redirect_stderr(io.StringIO())):
                self.assertEqual(WARP.main(), 130)
            self.assertIs(signal.getsignal(signal.SIGTERM), previous)
            report = json.loads((output / "report.json").read_text())
            self.assertEqual(report["status"], "CANCELLED")
            self.assertIn("SIGTERM", report["error"])


if __name__ == "__main__":
    unittest.main()
