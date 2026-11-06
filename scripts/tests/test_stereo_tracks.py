"""Synthetic geometry fixtures; these tests do not validate real matches."""
from pathlib import Path
import sys
import unittest
import importlib.util
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stereo_tracks import camera_from_pose,triangulate_observed,angular_separation,spatial_holdout

try:
    import cv2
except ImportError:
    cv2=None


def camera(center):
    pose=np.eye(4);pose[:3,3]=center
    return camera_from_pose(pose,[512]*4)


def project(xyz,c):
    q=np.column_stack([xyz,np.ones(len(xyz))])@c['projection'].T
    return q[:,:2]/q[:,2,None]


class StereoTrackTests(unittest.TestCase):
    @unittest.skipIf(cv2 is None,'OpenCV required; executed in existing OpenCV environment')
    def test_known_large_disparity_requires_wider_search(self):
        spec=importlib.util.spec_from_file_location('warp',Path(__file__).resolve().parents[1]/'warp-panorama-gap.py')
        warp=importlib.util.module_from_spec(spec);spec.loader.exec_module(warp)
        rng=np.random.default_rng(17)
        left=cv2.GaussianBlur(rng.integers(0,256,(64,1280,3),dtype=np.uint8),(3,3),0)
        right=np.zeros_like(left);right[:,:960]=left[:,320:]
        narrow,_=warp.stereo_disparities(left,right,0,256,5)
        wide,reverse=warp.stereo_disparities(left,right,0,512,5)
        interior=(slice(10,54),slice(600,900))
        self.assertGreater(float(np.median(np.abs(narrow[interior]-320))),60)
        self.assertLess(float(np.median(np.abs(wide[interior]-320))),.2)
        mask=np.ones(wide.shape,bool)
        consistent=warp.valid_matches(wide,reverse,mask,mask,left,right,0,1,512,.5,15)
        self.assertGreater(float(np.mean(consistent[interior])),.9)

    def test_exact_fixed_pose_triangulation_and_parallax(self):
        a,b=camera([0,0,0]),camera([1,0,0])
        xyz=np.array([[0,0,10],[2,1,8],[-1,-2,6.]])
        result=triangulate_observed(project(xyz,a),project(xyz,b),a,b)
        np.testing.assert_allclose(result['xyz'],xyz,atol=1e-11)
        np.testing.assert_allclose(result['errors'],0,atol=1e-10)
        self.assertTrue(result['positive'].all())
        self.assertAlmostEqual(result['parallax'][0],np.degrees(np.arctan(.1)))

    def test_rotated_camera_uses_world_frame(self):
        a=camera([0,0,0]);pose=np.eye(4);theta=.2
        pose[:3,:3]=[[np.cos(theta),0,np.sin(theta)],[0,1,0],[-np.sin(theta),0,np.cos(theta)]]
        pose[:3,3]=[2,.3,0];b=camera_from_pose(pose,[500,510,512,512])
        xyz=np.array([[1.,2,10],[0,-1,6]])
        r=triangulate_observed(project(xyz,a),project(xyz,b),a,b)
        np.testing.assert_allclose(r['xyz'],xyz,atol=1e-11)

    def test_vertical_mismatch_reports_error_and_behind_camera_is_invalid(self):
        a,b=camera([0,0,0]),camera([1,0,0]);xyz=np.array([[0.,0,10]])
        right=project(xyz,b);right[:,1]+=30
        r=triangulate_observed(project(xyz,a),right,a,b)
        self.assertGreater(np.max(r['errors']),10)
        behind=np.array([[0.,0,-10]])
        self.assertFalse(triangulate_observed(project(behind,a),project(behind,b),a,b)['positive'].any())

    def test_half_pixel_conversion_changes_world_bearing(self):
        a,b=camera([0,0,0]),camera([1,0,0]);xyz=np.array([[0.,0,10]])
        index0,index1=project(xyz,a)-.5,project(xyz,b)-.5
        np.testing.assert_allclose(triangulate_observed(index0+.5,index1+.5,a,b)['xyz'],xyz,atol=1e-11)
        self.assertGreater(np.linalg.norm(triangulate_observed(index0,index1,a,b)['xyz']-xyz),.001)

    def test_degenerate_and_empty_observations(self):
        a=camera([0,0,0]);xy=np.array([[512.,512]])
        self.assertFalse(triangulate_observed(xy,xy,a,a)['positive'].any())
        r=triangulate_observed(np.empty((0,2)),np.empty((0,2)),a,a)
        self.assertEqual(r['xyz'].shape,(0,3))

    def test_rigid_camera_and_finite_observations_required(self):
        pose=np.eye(4);pose[0,0]=-1
        with self.assertRaises(ValueError):camera_from_pose(pose,[512]*4)
        with self.assertRaises(ValueError):camera_from_pose(np.eye(4),[0,512,512,512])
        a=camera([0,0,0])
        with self.assertRaises(ValueError):triangulate_observed([[np.nan,1]],[[1,1]],a,a)

    def test_spherical_duplicates_cross_seam(self):
        theta=np.deg2rad(.1)
        a=np.array([np.sin(theta),0,-np.cos(theta)]);b=np.array([-np.sin(theta),0,-np.cos(theta)])
        self.assertAlmostEqual(float(angular_separation(a,b)),.2,places=8)

    def test_spatial_holdout_keeps_entire_tile_and_validates_domain(self):
        uv=np.array([[.01,.01],[.04,.02],[.09,.01]])
        np.testing.assert_array_equal(spatial_holdout(uv),[True,True,False])
        for invalid in [[1,.5],[-.1,.5],[.5,np.nan]]:
            with self.assertRaises(ValueError):spatial_holdout(invalid)


if __name__=='__main__':unittest.main()
