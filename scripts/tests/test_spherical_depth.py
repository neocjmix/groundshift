"""Analytic geometry fixtures only; these do not certify learned depth accuracy."""
import importlib.util
import json
from pathlib import Path
import unittest

try:
    import numpy as np
except ImportError:
    np = None

if np is not None:
    def load(name, filename):
        spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    SPHERE = load("spherical_depth", "spherical_depth.py")
    CROPS = load("prepare_panoramas", "prepare-panoramas.py")


@unittest.skipUnless(np is not None, "NumPy required; spherical geometry NOT RUN")
class SphericalProjectionTests(unittest.TestCase):
    def test_cardinal_rays_and_poles_use_existing_right_handed_axes(self):
        # Fractional array indices reach exact cardinal directions between pixels.
        u = np.array([3.5, 5.5, 7.5, 1.5, 3.5, 3.5])
        v = np.array([1.5, 1.5, 1.5, 1.5, -.5, 3.5])
        expected = np.array([[0, 0, 1], [1, 0, 0], [0, 0, -1], [-1, 0, 0], [0, -1, 0], [0, 1, 0]])
        rays = SPHERE.erp_pixel_rays(u, v, 4, 8)
        np.testing.assert_allclose(rays, expected, atol=1e-14)
        np.testing.assert_allclose(np.cross(rays[1], rays[5]), rays[0], atol=1e-14)

    def test_pixel_centers_do_not_duplicate_seam_or_hit_poles(self):
        rays = SPHERE.erp_unit_rays(4, 8)
        np.testing.assert_allclose(np.linalg.norm(rays, axis=-1), 1, atol=1e-14)
        self.assertTrue(np.all(np.abs(rays[..., 1]) < 1))
        self.assertFalse(np.allclose(rays[:, 0], rays[:, -1]))
        # First pixel: longitude -157.5 degrees; latitude +67.5 degrees.
        expected = [np.cos(3 * np.pi / 8) * np.sin(-7 * np.pi / 8),
                    -np.sin(3 * np.pi / 8), np.cos(3 * np.pi / 8) * np.cos(-7 * np.pi / 8)]
        np.testing.assert_allclose(rays[0, 0], expected, atol=1e-14)

    def test_every_pixel_roundtrips_and_direction_length_does_not_matter(self):
        height, width = 64, 128
        rays = SPHERE.erp_unit_rays(height, width)
        u, v = SPHERE.directions_to_erp(rays * 17, height, width)
        yy, xx = np.indices((height, width))
        np.testing.assert_allclose(u, xx, atol=1e-10)
        np.testing.assert_allclose(v, yy, atol=1e-10)

    def test_analytic_crop_projection_matches_existing_preparation(self):
        for yaw, pitch in ((0, 0), (71, 24), (180, -40), (359, 87)):
            with self.subTest(yaw=yaw, pitch=pitch):
                u, v = CROPS.sampling_map(720, 360, 13, 94, yaw, pitch)
                rays = SPHERE.erp_pixel_rays(u, v, 360, 720)
                k = CROPS.intrinsics(13, 94)
                yy, xx = np.indices((13, 13))
                expected = np.stack(((xx + .5 - k["cx"]) / k["fx"],
                                     (yy + .5 - k["cy"]) / k["fy"], np.ones(xx.shape)), -1)
                expected = expected @ CROPS.crop_rotation(yaw, pitch).T
                expected /= np.linalg.norm(expected, axis=-1, keepdims=True)
                np.testing.assert_allclose(rays, expected, atol=4e-7)

    def test_horizontal_periodicity_and_vertical_domain(self):
        a = SPHERE.erp_pixel_rays(2.2, 1.1, 4, 8)
        np.testing.assert_allclose(a, SPHERE.erp_pixel_rays(2.2 + 24, 1.1, 4, 8), atol=1e-14)
        for u, v in ((0, -1), (0, 4), (np.nan, 1)):
            with self.subTest(u=u, v=v), self.assertRaises(ValueError):
                SPHERE.erp_pixel_rays(u, v, 4, 8)

    def test_rejects_wrong_projection_dimensions_and_zero_directions(self):
        for height, width in ((4, 7), (1, 2), (4., 8), (True, 2)):
            with self.subTest(height=height, width=width), self.assertRaises(ValueError):
                SPHERE.erp_unit_rays(height, width)
        for ray in ([0, 0, 0], [np.nan, 0, 1], [1, 2]):
            with self.subTest(ray=ray), self.assertRaises(ValueError):
                SPHERE.directions_to_erp(ray, 4, 8)


@unittest.skipUnless(np is not None, "NumPy required; depth conversion NOT RUN")
class DepthConventionTests(unittest.TestCase):
    def calibration(self, convention="inverse-ray-range", **changes):
        return dict(convention=convention, scale=2., offset=1., units="sfm-arbitrary",
                    source="Known analytic fixture", **changes)

    def test_inverse_radial_fit_has_explicit_arbitrary_units(self):
        radial, valid = SPHERE.calibrated_inverse_radial(np.array([0., 1., 2.]), self.calibration())
        np.testing.assert_allclose(radial, [1, 1 / 3, 1 / 5])
        np.testing.assert_array_equal(valid, [True, True, True])

    def test_direct_radial_is_not_inverse_depth(self):
        radial, valid = SPHERE.calibrated_radial([0, 1, 2], self.calibration("ray-range"))
        np.testing.assert_allclose(radial, [1, 3, 5])
        self.assertTrue(valid.all())
        with self.assertRaisesRegex(ValueError, "convention"):
            SPHERE.calibrated_inverse_radial([1], self.calibration("ray-range"))
        with self.assertRaisesRegex(ValueError, "convention"):
            SPHERE.calibrated_radial([1], self.calibration("inverse-ray-range"))

    def test_calibration_and_evidence_are_required_not_defaulted(self):
        for calibration in (None, {}, {"convention": "inverse-camera-Z"},
                            {**self.calibration(), "source": ""}, {**self.calibration(), "units": "unknown"},
                            {**self.calibration(), "scale": 0}, {**self.calibration(), "offset": np.inf}):
            with self.subTest(calibration=calibration), self.assertRaises(ValueError):
                SPHERE.calibrated_inverse_radial([1], calibration)
        for key in ("offset", "scale", "units", "source"):
            calibration = self.calibration()
            del calibration[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                SPHERE.calibrated_inverse_radial([1], calibration)
        with self.assertRaises(TypeError):
            SPHERE.calibrated_inverse_radial([1])

    def test_invalid_or_nonpositive_calibrated_values_are_excluded(self):
        values = [0, -.5, -1, np.nan, np.inf]
        for function, convention in ((SPHERE.calibrated_inverse_radial, "inverse-ray-range"),
                                     (SPHERE.calibrated_radial, "ray-range")):
            with self.subTest(convention=convention):
                radial, valid = function(values, self.calibration(convention))
                np.testing.assert_array_equal(valid, [True, False, False, False, False])
                self.assertTrue(np.isnan(radial[1:]).all())

    def test_camera_z_differs_from_radial_range_away_from_optical_axis(self):
        rays = np.array([[0., 0, 1], [3 / 5, 0, 4 / 5], [0, 1, 0], [0, 0, -1]])
        radial, valid = SPHERE.camera_z_to_radial(np.array([4., 4., 4., 4.]), rays)
        np.testing.assert_allclose(radial[:2], [4, 5])
        np.testing.assert_array_equal(valid, [True, True, False, False])
        self.assertTrue(np.isnan(radial[2:]).all())
        np.testing.assert_allclose((rays[:2] * radial[:2, None])[:, 2], [4, 4])

    def test_camera_z_rejects_bad_rays_and_invalid_depths(self):
        with self.assertRaisesRegex(ValueError, "unit"):
            SPHERE.camera_z_to_radial([4.], [[0., 0, 2.]])
        with self.assertRaisesRegex(ValueError, "matching"):
            SPHERE.camera_z_to_radial([4.], [0., 0, 1.])
        radial, valid = SPHERE.camera_z_to_radial([0, -1, np.nan, 2], [[0, 0, 1]] * 3 + [[np.nan, 0, 1]])
        self.assertFalse(valid.any())
        self.assertTrue(np.isnan(radial).all())


@unittest.skipUnless(np is not None, "NumPy required; spherical backprojection NOT RUN")
class BackprojectionTests(unittest.TestCase):
    def setUp(self):
        self.radial = np.arange(1, 33, dtype=float).reshape(4, 8)
        self.rgb = np.arange(96, dtype=np.uint8).reshape(4, 8, 3)

    def test_range_is_euclidean_radius_not_camera_z(self):
        xyz, colors, rows, columns = SPHERE.backproject_radial(self.radial, self.rgb, np.eye(4))
        np.testing.assert_allclose(np.linalg.norm(xyz, axis=1), self.radial.ravel())
        np.testing.assert_array_equal(colors, self.rgb.reshape(-1, 3))
        np.testing.assert_array_equal(self.radial[rows, columns], self.radial.ravel())
        self.assertTrue(np.any(xyz[:, 2] < 0), "Rear sphere is valid radial geometry")

    def test_known_rotation_translation_and_rgb_remain_correspondent(self):
        pose = np.array([[0., 0, 1, 10], [0, 1, 0, 20], [-1, 0, 0, 30], [0, 0, 0, 1]])
        mask = np.zeros((4, 8), dtype=bool)
        mask[1, 3] = True
        xyz, colors, rows, columns = SPHERE.backproject_radial(self.radial, self.rgb, pose, mask=mask)
        ray = SPHERE.erp_pixel_rays(3, 1, 4, 8) * self.radial[1, 3]
        np.testing.assert_allclose(xyz[0], [ray[2] + 10, ray[1] + 20, -ray[0] + 30])
        np.testing.assert_array_equal(colors, [self.rgb[1, 3]])
        np.testing.assert_array_equal(rows, [1])
        np.testing.assert_array_equal(columns, [3])

    def test_mask_stride_and_invalid_ranges_preserve_sample_indices(self):
        self.radial[0, 0] = 0
        self.radial[0, 2] = np.nan
        self.radial[0, 4] = -1
        self.radial[0, 6] = np.inf
        mask = np.ones((4, 8), dtype=bool)
        mask[2, 4] = False
        xyz, colors, rows, columns = SPHERE.backproject_radial(self.radial, self.rgb, np.eye(4), mask=mask, stride=2)
        np.testing.assert_array_equal(rows, [2, 2, 2])
        np.testing.assert_array_equal(columns, [0, 2, 6])
        np.testing.assert_array_equal(colors, self.rgb[rows, columns])
        self.assertTrue(np.isfinite(xyz).all())

    def test_empty_valid_region_is_an_empty_cloud(self):
        xyz, colors, rows, columns = SPHERE.backproject_radial(self.radial, self.rgb, np.eye(4), mask=np.zeros((4, 8), bool))
        self.assertEqual(xyz.shape, (0, 3))
        self.assertEqual(colors.shape, (0, 3))
        self.assertEqual(rows.size + columns.size, 0)

    def test_pose_must_be_explicit_finite_rigid_and_right_handed(self):
        for pose in (None, np.eye(3), np.diag([2., 1, 1, 1]), np.diag([-1., 1, 1, 1]),
                     np.diag([1., 1, 1, 2]), np.full((4, 4), np.nan)):
            with self.subTest(pose=pose), self.assertRaises(ValueError):
                SPHERE.backproject_radial(self.radial, self.rgb, pose)
        with self.assertRaises(TypeError):
            SPHERE.backproject_radial(self.radial, self.rgb)

    def test_rejects_ambiguous_masks_rgb_and_stride(self):
        for changes in ({"mask": np.ones((4, 8), np.uint8)}, {"mask": np.ones((4, 7), bool)},
                        {"stride": 0}, {"stride": 1.5}, {"stride": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                SPHERE.backproject_radial(self.radial, self.rgb, np.eye(4), **changes)
        with self.assertRaisesRegex(ValueError, "uint8"):
            SPHERE.backproject_radial(self.radial, self.rgb.astype(float), np.eye(4))


@unittest.skipUnless(np is not None, "NumPy required; seam checks NOT RUN")
class SeamTests(unittest.TestCase):
    def test_seam_blends_first_last_columns_and_is_periodic(self):
        values = np.zeros((4, 8))
        values[:, -1], values[:, 0] = 100, 200
        sampled = SPHERE.sample_erp_bilinear(values, [-.5, 7.5, 15.5, -8.5], 1.2)
        np.testing.assert_allclose(sampled, [150] * 4)

    def test_poles_clamp_vertically_and_never_wrap(self):
        values = np.zeros((4, 8, 3), dtype=np.uint8)
        values[0], values[-1] = [100, 30, 20], [40, 50, 60]
        sampled = SPHERE.sample_erp_bilinear(values, [1, 1], [-5, 50])
        np.testing.assert_allclose(sampled, [[100, 30, 20], [40, 50, 60]])

    def test_exact_pixel_values_ignore_zero_weight_nan_neighbor(self):
        values = np.full((4, 8), np.nan)
        values[1, 2] = 9
        self.assertEqual(SPHERE.sample_erp_bilinear(values, 2, 1), 9)
        self.assertTrue(np.isnan(SPHERE.sample_erp_bilinear(values, 2.1, 1)))

    def test_seam_diagnostic_detects_artificial_discontinuity_without_quality_claim(self):
        values = np.tile(np.arange(8), (4, 1))
        diagnostic = SPHERE.seam_diagnostics(values)
        self.assertEqual(diagnostic["seam"]["pairs"], 4)
        self.assertEqual(diagnostic["seam"]["medianAbs"], 7)
        self.assertEqual(diagnostic["interior"]["medianAbs"], 1)
        self.assertEqual(diagnostic["medianSeamToInteriorRatio"], 7)
        self.assertNotIn("status", diagnostic)

    def test_periodic_smooth_signal_has_no_extra_seam_jump(self):
        values = np.tile(np.sin((np.arange(128) + .5) / 128 * 2 * np.pi), (64, 1))
        diagnostic = SPHERE.seam_diagnostics(values)
        self.assertLess(diagnostic["seam"]["maxAbs"], 2 * np.pi / 128)

    def test_empty_diagnostics_remain_strict_json_and_masked_seam_is_not_counted(self):
        values = np.zeros((4, 8))
        mask = np.ones_like(values, bool)
        mask[:, 0] = False
        diagnostic = SPHERE.seam_diagnostics(values, mask)
        self.assertEqual(diagnostic["seam"]["pairs"], 0)
        self.assertIsNone(diagnostic["seam"]["medianAbs"])
        self.assertIsNone(diagnostic["medianSeamToInteriorRatio"])
        json.dumps(diagnostic, allow_nan=False)
        diagnostic = SPHERE.seam_diagnostics(np.full((4, 8), np.nan))
        self.assertEqual(diagnostic["interior"]["pairs"], 0)
        json.dumps(diagnostic, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
