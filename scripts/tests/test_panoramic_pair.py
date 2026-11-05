"""Analytic pair diagnostics, not evidence of learned-depth scene accuracy."""
from pathlib import Path
import sys
import unittest

try:
    import numpy as np
except ImportError:
    np = None

if np is not None:
    sys.path.insert(0, str(Path(__file__).parents[1]))
    import panoramic_pair as PAIR
    from spherical_depth import erp_pixel_rays, erp_unit_rays


@unittest.skipUnless(np is not None, "NumPy required; pair geometry NOT RUN")
class PanoramicPairTests(unittest.TestCase):
    def setUp(self):
        self.range = np.full((4, 8), 3.)
        self.rgb = np.arange(96, dtype=np.uint8).reshape(4, 8, 3)
        self.pose = np.eye(4)

    def compare(self, **changes):
        args = dict(source_range=self.range, target_range=self.range,
                    source_rgb=self.rgb, target_rgb=self.rgb,
                    source_pose=self.pose, target_pose=self.pose, stride=1)
        args.update(changes)
        return PAIR.compare_direction(**args)

    def test_identity_preserves_color_coordinates_and_all_candidate_denominators(self):
        result = self.compare()
        samples, summary = result["samples"], result["summary"]
        np.testing.assert_array_equal(samples["target_u"], samples["source_columns"])
        np.testing.assert_array_equal(samples["target_v"], samples["source_rows"])
        np.testing.assert_allclose(samples["signed_residual"], 0, atol=1e-14)
        np.testing.assert_array_equal(samples["rgb_mae"], 0)
        self.assertTrue(samples["candidate"].all())
        self.assertTrue(samples["source_nearest_in_target_pixel"].all())
        self.assertEqual(summary["selectedSourceSamples"], 32)
        self.assertEqual(summary["candidateFraction"], 1.)
        self.assertEqual(summary["classificationStatus"], "NOT RUN")
        self.assertIsNone(samples["agreement"])

    def test_known_translation_matches_specific_target_pixel_and_color(self):
        source_mask = np.zeros((4, 8), bool)
        source_mask[1, 3] = True
        source_ray = erp_pixel_rays(3, 1, 4, 8)
        target_ray = erp_pixel_rays(5, 2, 4, 8)
        target_pose = self.pose.copy()
        target_pose[:3, 3] = source_ray * 3 - target_ray * 2
        target_rgb = np.zeros_like(self.rgb)
        target_rgb[2, 5] = self.rgb[1, 3]
        result = self.compare(target_pose=target_pose, target_range=np.full((4, 8), 2.),
                              target_rgb=target_rgb, source_mask=source_mask, tolerance=1e-10)
        sample = result["samples"]
        np.testing.assert_allclose(sample["world_xyz"][0], source_ray * 3)
        np.testing.assert_allclose(sample["target_u"], [5], atol=1e-12)
        np.testing.assert_allclose(sample["target_v"], [2], atol=1e-12)
        np.testing.assert_allclose(sample["signed_residual"], 0, atol=1e-12)
        np.testing.assert_allclose(sample["rgb_mae"], 0, atol=1e-12)
        self.assertTrue(sample["agreement"][0])

    def test_rotated_target_axes_use_inverse_pose_rotation(self):
        target_pose = np.array([[0., 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1]])
        result = self.compare(target_pose=target_pose, target_rgb=np.roll(self.rgb, -2, axis=1))
        sample = result["samples"]
        np.testing.assert_allclose(np.mod(sample["target_u"], 8), (sample["source_columns"] - 2) % 8)
        np.testing.assert_allclose(sample["signed_residual"], 0, atol=1e-12)
        np.testing.assert_allclose(sample["rgb_mae"], 0)

    def test_translated_views_of_one_plane_have_small_discretization_residual(self):
        h, w = 128, 256
        rays = erp_unit_rays(h, w)
        mask = (rays[..., 2] > .75) & (np.abs(rays[..., 1]) < .3)
        target_mask = rays[..., 2] > .5
        radial = np.full((h, w), np.nan)
        np.divide(5., rays[..., 2], out=radial, where=rays[..., 2] > 0)
        target_pose = np.eye(4)
        target_pose[0, 3] = .5
        rgb = np.full((h, w, 3), 80, np.uint8)
        result = self.compare(source_range=radial, target_range=radial, source_rgb=rgb,
                              target_rgb=rgb, source_mask=mask, target_mask=target_mask,
                              target_pose=target_pose, stride=3, tolerance=.01)
        sample = result["samples"]
        np.testing.assert_allclose(sample["world_xyz"][:, 2], 5, atol=1e-12)
        self.assertTrue(sample["candidate"].all())
        self.assertLess(np.max(np.abs(sample["signed_residual"])), .003)
        self.assertTrue(sample["agreement"].all())
        np.testing.assert_allclose(sample["rgb_mae"], 0, atol=1e-12)

    def seam_case(self, **changes):
        angle = np.pi / 8
        c, s = np.cos(angle), np.sin(angle)
        pose = np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]])
        target_range = self.range.copy()
        target_range[:, -1], target_range[:, 0] = 2., 4.
        source_mask = np.zeros((4, 8), bool)
        source_mask[2, 0] = True
        target_rgb = np.zeros_like(self.rgb)
        target_rgb[:, 0] = 100
        args = dict(source_mask=source_mask, target_pose=pose, target_range=target_range,
                    source_rgb=np.full_like(self.rgb, 50), target_rgb=target_rgb)
        args.update(changes)
        return self.compare(**args)

    def test_depth_and_rgb_bilinear_interpolation_wrap_the_horizontal_seam(self):
        sample = self.seam_case()["samples"]
        self.assertTrue(sample["candidate"][0])
        np.testing.assert_allclose(sample["target_sampled_range"], 3)
        np.testing.assert_allclose(sample["signed_residual"], 0, atol=1e-12)
        np.testing.assert_allclose(sample["target_rgb"], [[50, 50, 50]])
        np.testing.assert_allclose(sample["rgb_mae"], 0, atol=1e-12)

    def test_nonzero_weight_invalid_neighbor_excludes_candidate_without_losing_denominator(self):
        mask = np.ones((4, 8), bool)
        mask[2, 0] = False
        result = self.seam_case(target_mask=mask)
        self.assertEqual(result["summary"]["selectedSourceSamples"], 1)
        self.assertEqual(result["summary"]["candidateSamples"], 0)
        self.assertEqual(result["summary"]["unsupportedTargetSamples"], 1)
        self.assertTrue(np.isnan(result["samples"]["signed_residual"][0]))

    def test_zero_weight_invalid_neighbors_do_not_poison_exact_pixel(self):
        mask = np.zeros((4, 8), bool)
        mask[2, 3] = True
        radial = np.full((4, 8), np.nan)
        radial[2, 3] = 3
        result = self.compare(source_mask=mask, target_range=radial, target_mask=mask)
        self.assertEqual(result["summary"]["candidateSamples"], 1)

    def test_front_behind_and_agreement_are_explicit_not_ground_truth_visibility(self):
        target = self.range.copy()
        target[:, :2], target[:, 2:4], target[:, 4:] = 1., 5., 3.
        result = self.compare(target_range=target, tolerance=.1)
        classification = result["summary"]["classification"]
        self.assertEqual(classification["behind"]["samples"], 8)
        self.assertEqual(classification["in_front"]["samples"], 8)
        self.assertEqual(classification["agreement"]["samples"], 16)
        self.assertEqual(classification["agreement"]["sourceFraction"], .5)
        self.assertEqual(classification["agreement"]["rgbMeanAbsoluteError255"]["mean"], 0.)
        self.assertTrue(np.all(result["samples"]["signed_residual"][:2] > 0))

    def test_tolerance_source_grid_and_sample_vectors_have_same_selection(self):
        mask = np.zeros((4, 8), bool)
        mask[2, 2:4] = True
        grid = np.full((4, 8), .1)
        grid[2, 3] = 2.
        a = self.compare(source_mask=mask, target_range=np.ones((4, 8)), tolerance=grid)
        b = self.compare(source_mask=mask, target_range=np.ones((4, 8)), tolerance=np.array([.1, 2.]))
        np.testing.assert_array_equal(a["samples"]["agreement"], [False, True])
        np.testing.assert_array_equal(a["samples"]["agreement"], b["samples"]["agreement"])

    def test_explicit_relative_tolerance_is_scaled_by_target_range_not_source_range(self):
        target = self.range.copy()
        target[:, :4], target[:, 4:] = 2., 4.
        result = self.compare(target_range=target, relative_tolerance=.3)
        sample = result["samples"]
        np.testing.assert_allclose(sample["tolerance"], sample["target_sampled_range"] * .3)
        np.testing.assert_array_equal(sample["agreement"], sample["source_columns"] >= 4)
        np.testing.assert_array_equal(sample["behind"], sample["source_columns"] < 4)

    def test_projected_source_zbuffer_keeps_ties_and_wraps_seam_without_filtering_candidates(self):
        keep = PAIR.nearest_in_target_pixels(np.array([-.4, 7.6, -.4, 2.]),
                                             np.array([1., 1., 1., 0.]), np.array([4., 2., 2., 5.]), 4, 8)
        np.testing.assert_array_equal(keep, [False, True, True, True])
        source = self.range.copy()
        source[0, 0] = 2.
        result = self.compare(source_range=source, target_range=np.full((2, 4), 3.),
                              target_rgb=np.zeros((2, 4, 3), np.uint8))
        self.assertEqual(result["summary"]["candidateSamples"], 32)
        self.assertLess(result["summary"]["nearestSourceInTargetPixel"]["samples"], 32)

    def test_discrete_source_zbuffer_clamps_poles_without_vertical_wrap(self):
        keep = PAIR.nearest_in_target_pixels(np.zeros(3), np.array([-.5, 3.5, 3.2]),
                                             np.array([1., 2., 3.]), 4, 8)
        np.testing.assert_array_equal(keep, [True, True, False])

    def test_target_center_coincidence_is_unsupported_not_a_fake_ray(self):
        mask = np.zeros((4, 8), bool)
        mask[1, 3] = True
        pose = self.pose.copy()
        pose[:3, 3] = erp_pixel_rays(3, 1, 4, 8) * 3
        result = self.compare(source_mask=mask, target_pose=pose)
        self.assertEqual(result["summary"]["candidateSamples"], 0)
        self.assertEqual(result["summary"]["selectedSourceSamples"], 1)
        self.assertTrue(np.isnan(result["samples"]["target_u"][0]))

    def test_no_supported_sources_returns_empty_json_safe_summary(self):
        import json
        result = self.compare(source_mask=np.zeros((4, 8), bool), tolerance=.1)
        self.assertEqual(result["summary"]["selectedSourceSamples"], 0)
        self.assertIsNone(result["summary"]["candidateFraction"])
        self.assertEqual(result["samples"]["world_xyz"].shape, (0, 3))
        json.dumps(result["summary"], allow_nan=False)

    def test_roi_summaries_keep_their_own_supported_and_source_denominators(self):
        target_mask = np.ones((4, 8), bool)
        target_mask[:, :2] = False
        result = self.compare(target_mask=target_mask, tolerance=.1)
        roi = result["samples"]["source_columns"] < 4
        summary = PAIR.summarize_samples(result["samples"], roi)
        self.assertEqual(summary["selectedSourceSamples"], 16)
        self.assertEqual(summary["candidateSamples"], 8)
        self.assertEqual(summary["classification"]["agreement"]["sourceFraction"], .5)

    def test_rejects_nonrigid_poses_bad_shapes_masks_and_unusable_tolerances(self):
        scaled = self.pose.copy()
        scaled[0, 0] = 2
        for changes in ({"target_pose": scaled}, {"source_pose": np.eye(3)},
                        {"target_rgb": self.rgb.astype(float)}, {"source_mask": np.ones((4, 8))},
                        {"target_mask": np.ones((2, 4), bool)}, {"target_range": np.ones((3, 8))},
                        {"stride": 0}, {"tolerance": -.1}, {"tolerance": np.nan},
                        {"tolerance": np.ones(5)}, {"relative_tolerance": np.nan},
                        {"relative_tolerance": -.1}, {"relative_tolerance": [.1, .2]},
                        {"relative_tolerance": .1, "tolerance": .1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.compare(**changes)


if __name__ == "__main__":
    unittest.main()
