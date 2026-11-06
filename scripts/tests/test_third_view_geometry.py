"""Synthetic convention/coverage tests, not validation of real correspondences."""
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from third_view_geometry import (rectified_ray_pixel, sample_supported_disparity,
                                rectified_to_corner, third_view_residual)


class ThirdViewGeometryTests(unittest.TestCase):
    def setUp(self):
        self.k = np.array([[4., 0, 3.5], [0, 4., 3.5], [0, 0, 1]])

    def test_roundtrip_array_centers_to_corner_pixels(self):
        ray = np.array([.25, -.125, 1.]); ray /= np.linalg.norm(ray)
        xy, centrality = rectified_ray_pixel(ray, np.eye(3), np.eye(3), self.k, (8, 8))
        np.testing.assert_allclose(xy, [4.5, 3.])
        np.testing.assert_allclose(rectified_to_corner(xy, np.eye(3), self.k, [4, 4, 4, 4]), [5, 3.5])
        self.assertGreater(centrality, .9)

    def test_rotated_ray_roundtrip(self):
        r = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0.]])
        rect = np.array([[1, 0, 0], [0, np.cos(.1), -np.sin(.1)], [0, np.sin(.1), np.cos(.1)]])
        xy, _ = rectified_ray_pixel(np.array([1., 0, 0]), r, rect, self.k, (8, 8))
        np.testing.assert_allclose(rectified_to_corner(xy, rect, self.k, [4]*4), [4, 4], atol=1e-12)

    def test_behind_and_outside_rays_unsupported(self):
        for ray in [[0, 0, -1], [100, 0, 1]]:
            self.assertEqual(rectified_ray_pixel(ray, np.eye(3), np.eye(3), self.k, (8, 8)), (None, None))

    def test_subpixel_coherent_disparity(self):
        d = np.array([[10., 11], [11, 12]])
        value, status = sample_supported_disparity(d, np.ones((2, 2), bool), [.25, .5])
        self.assertEqual(status, 'supported'); self.assertAlmostEqual(value, 10.75)

    def test_invalid_neighbor_does_not_get_filled(self):
        valid = np.array([[True, False], [True, True]])
        self.assertEqual(sample_supported_disparity(np.ones((2, 2)), valid, [.1, .1])[1], 'lr-photo-unsupported')
        self.assertEqual(sample_supported_disparity(np.ones((2, 2)), valid, [0, 0]), (1., 'supported'))

    def test_depth_boundary_not_interpolated(self):
        self.assertEqual(sample_supported_disparity(np.array([[1., 10], [1, 10]]), np.ones((2, 2), bool), [.5, .5])[1], 'disparity-discontinuity')

    def test_outside_nan_and_shape_rejected(self):
        d = np.ones((2, 2)); v = d.astype(bool)
        for xy in [[-1, 0], [1, 1], [np.nan, 0]]:
            self.assertIsNone(sample_supported_disparity(d, v, xy)[0])
        with self.assertRaises(ValueError):sample_supported_disparity(d, v[:1], [0, 0])

    def test_exact_and_known_third_view_angle(self):
        result = third_view_residual([0, 0, 10], [0, 0, 10], [1, 0, 0], [0, 0, 0])
        self.assertEqual(result['angleDegrees'], 0); self.assertEqual(result['relativeRangeDifference'], 0)
        result = third_view_residual([0, 0, 10], [1, 0, 10], [0, 0, 0], [0, 0, 0])
        self.assertAlmostEqual(result['angleDegrees'], np.degrees(np.arctan(.1)))
        self.assertLess(result['relativeRangeDifference'], 0)

    def test_seam_and_arbitrary_scale(self):
        args = [np.array([.001, 0, -10]), np.array([-.001, 0, -10]), np.array([1, 0, 0]), np.zeros(3)]
        a = third_view_residual(*args); b = third_view_residual(*(p*7 for p in args))
        self.assertLess(a['angleDegrees'], .02)
        self.assertAlmostEqual(a['angleDegrees'], b['angleDegrees'])
        self.assertAlmostEqual(a['relativeRangeDifference'], b['relativeRangeDifference'])
        self.assertAlmostEqual(a['crossRangeSfm']*7, b['crossRangeSfm'])


if __name__ == '__main__':unittest.main()
