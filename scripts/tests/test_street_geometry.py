from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from street_geometry import project_world,depth_support,voxel_reduce,held_id,validate_stereo_report


class StreetGeometryTests(unittest.TestCase):
    def test_failed_stereo_requires_explicit_narrow_exception(self):
        horizon='ValueError: Stereo optical rays are too close to the rectification horizon'
        report=dict(status='FAIL',groups=[dict(status='PASS'),dict(status='FAIL',error=horizon)])
        with self.assertRaises(ValueError):validate_stereo_report(report)
        self.assertTrue(validate_stereo_report(report,True))
        report['groups'][1]['error']='missing image'
        with self.assertRaises(ValueError):validate_stereo_report(report,True)

    def test_success_label_cannot_hide_failed_stereo_group(self):
        with self.assertRaises(ValueError):validate_stereo_report(dict(status='PASS',groups=[dict(status='FAIL',error='missing image')]),True)

    def test_corner_origin_and_translated_pose(self):
        pose=np.eye(4);pose[:3,3]=[1,0,0]
        xy,z=project_world(np.array([[1,0,4],[2,1,2]]),pose,[4,4,4,4])
        np.testing.assert_allclose(xy,[[4,4],[6,6]]);np.testing.assert_allclose(z,[4,2])

    def test_depth_conflict_not_treated_as_occlusion_truth(self):
        points=np.array([[0,0,4],[0,0,6],[0,0,-4.]])
        rgb=np.full((8,8,3),100,np.uint8);depth=np.full((8,8),4.)
        agree,supported,residual,_=depth_support(points,np.full((3,3),100),depth,rgb,np.eye(4),[4]*4)
        np.testing.assert_array_equal(agree,[True,False,False]);np.testing.assert_array_equal(supported,[True,True,False]);self.assertEqual(residual[1],.5)

    def test_invalid_target_does_not_gain_support(self):
        depth=np.full((8,8),np.nan);rgb=np.zeros((8,8,3),np.uint8)
        agree,supported,_,_=depth_support(np.array([[0,0,4.]]),np.zeros((1,3)),depth,rgb,np.eye(4),[4]*4)
        self.assertFalse(agree.any());self.assertFalse(supported.any())

    def test_matching_depth_with_wrong_color_is_rejected(self):
        agree,supported,_,_=depth_support(np.array([[0,0,4.]]),np.zeros((1,3)),np.full((8,8),4.),np.full((8,8,3),255,np.uint8),np.eye(4),[4]*4)
        self.assertTrue(supported[0]);self.assertFalse(agree[0])

    def test_voxel_mean_and_negative_coordinates(self):
        p,c=voxel_reduce(np.array([[.1,.1,.1],[.3,.3,.3],[-.1,0,0]]),np.array([[0,0,0],[100,200,50],[50,50,50]]),1)
        self.assertEqual(len(p),2);index=np.argmax(p[:,0]);np.testing.assert_allclose(p[index],[.2]*3);np.testing.assert_array_equal(c[index],[50,100,25])

    def test_voxel_scale_invariance(self):
        p=np.array([[.1,0,0],[.3,0,0],[2,0,0]]);c=np.ones((3,3))*10
        a,_=voxel_reduce(p,c,1);b,_=voxel_reduce(p*7,c,7);np.testing.assert_allclose(a*7,b)

    def test_nonrigid_and_invalid_spacing_rejected(self):
        pose=np.eye(4);pose[0,0]=2
        with self.assertRaises(ValueError):project_world(np.ones((1,3)),pose,[4]*4)
        with self.assertRaises(ValueError):voxel_reduce(np.ones((1,3)),np.zeros((1,3)),0)

    def test_split_is_stable_and_both_sides_present(self):
        self.assertEqual(held_id('road-01'),held_id('road-01'))
        held=sum(held_id(i) for i in range(1000));self.assertGreater(held,150);self.assertLess(held,250)


if __name__=='__main__':unittest.main()
