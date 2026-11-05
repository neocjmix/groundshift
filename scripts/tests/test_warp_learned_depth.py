"""Small geometry/fit checks; real M2 job and held-out RGB are validated separately."""
import importlib.util
from pathlib import Path
import unittest

try:
    import numpy as np
except ImportError:
    np = None


SPEC = importlib.util.spec_from_file_location('warp_learned_depth', Path(__file__).resolve().parents[1] / 'warp-learned-depth.py')
WARP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WARP)


@unittest.skipUnless(np is not None, 'NumPy required; learned-depth fit NOT RUN')
class LearnedDepthWarpTests(unittest.TestCase):
    def test_bilinear_uses_colmap_corner_origin_after_conversion(self):
        array = np.array([[1, 3], [5, 7]], dtype=float)
        self.assertEqual(WARP.bilinear(array, 0.5, 0.5), 4)
        self.assertEqual(WARP.bilinear(array, 0, 0), 1)
        self.assertIsNone(WARP.bilinear(array, -0.01, 0))

    def test_affine_inverse_depth_rejects_one_sparse_outlier(self):
        x = np.linspace(0, 3, 101)
        y = 0.06 * x + 0.02
        y[50] = 2.0
        beta = WARP.robust_affine(x, y)
        np.testing.assert_allclose(beta, [0.06, 0.02], atol=0.001)
        depth = WARP.calibrated_depth(np.array([[0, 1, 2]], dtype=np.float32), beta)
        np.testing.assert_allclose(depth[0, 0], 50, rtol=0.02)
        self.assertGreater(depth[0, 0], depth[0, 2])

    def test_backprojection_obeys_camera_translation_and_pixel_centers(self):
        helpers = WARP.stereo_helpers()
        source = {'w': 2, 'h': 2, 'fl_x': 2, 'fl_y': 2, 'cx': 1, 'cy': 1,
                  'transform_matrix': np.eye(4).tolist()}
        target = {**source, 'transform_matrix': np.array([[1, 0, 0, 1],
                                                          [0, 1, 0, 0],
                                                          [0, 0, 1, 0],
                                                          [0, 0, 0, 1]], dtype=float).tolist()}
        depth = np.zeros((2, 2), dtype=np.float32)
        depth[1, 1] = 2
        points, y, x = WARP.backproject_to_target(depth, source, target, helpers)
        self.assertEqual((y.tolist(), x.tolist()), ([1], [1]))
        np.testing.assert_allclose(points[0], [-0.5, 0.5, 2], atol=1e-10)


if __name__ == '__main__':
    unittest.main()
