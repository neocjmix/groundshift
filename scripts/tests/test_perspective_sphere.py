"""Analytic geometry controls, independent of learned model outputs."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from perspective_sphere import sample_plane, crop_ranges, stitch_ranges
from spherical_depth import erp_unit_rays, backproject_radial

spec=importlib.util.spec_from_file_location('crops',Path(__file__).resolve().parents[1]/'prepare-panoramas.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
FIT=dict(convention='inverse-camera-z',units='sfm-arbitrary',scale=1.,offset=0.)


class PerspectiveSphereTests(unittest.TestCase):
    def test_corner_origin_bilinear_and_no_perspective_wrap(self):
        array=np.array([[1.,3.],[5.,7.]])
        np.testing.assert_allclose(sample_plane(array,[[.5,.5],[1,1],[1.5,1.5]]),[1,4,7])
        self.assertTrue(np.isnan(sample_plane(array,[[0,.5],[2,.5],[np.nan,1]])).all())

    def test_nan_zero_weight_and_nonzero_weight(self):
        array=np.array([[1.,np.nan],[3.,4.]])
        self.assertEqual(float(sample_plane(array,[.5,.5])),1)
        self.assertTrue(np.isnan(sample_plane(array,[1,.5])))

    def test_camera_z_plane_reconstructs_constant_z(self):
        rays=erp_unit_rays(24,48)
        radial,_=crop_ranges(np.full((32,32),.2),FIT,np.eye(3),rays,[16,16,16,16])
        valid=np.isfinite(radial)
        self.assertGreater(valid.sum(),20)
        np.testing.assert_allclose((radial[...,None]*rays)[valid,2],5,atol=1e-12)
        self.assertTrue(np.isnan(radial[rays[...,2]<0]).all())

    def test_radial_not_z_for_oblique_ray(self):
        ray=np.array([[[.6,0,.8]]])
        radial,score=crop_ranges(np.full((32,32),.2),FIT,np.eye(3),ray,[8,8,16,16])
        self.assertAlmostEqual(radial.item(),6.25)
        self.assertAlmostEqual(score.item(),.8)

    def test_invalid_conventions_rotations_calibration(self):
        args=[np.ones((4,4)),FIT,np.eye(3),np.array([[[0,0,1.]]]),[2,2,2,2]]
        for changed in [dict(FIT,convention='inverse-ray-range'),dict(FIT,units='meters'),dict(FIT,scale=-1.)]:
            with self.assertRaises(ValueError):crop_ranges(args[0],changed,*args[2:])
        with self.assertRaises(ValueError):crop_ranges(args[0],FIT,np.diag([-1,1,1]),*args[3:])
        with self.assertRaises(ValueError):crop_ranges(*args[:3],np.array([[[0,0,2.]]]),args[4])
        radial,_=crop_ranges(np.ones((4,4)),dict(FIT,offset=-2),*args[2:])
        self.assertTrue(np.isnan(radial).all())

    def test_full_horizontal_coverage_seam_and_known_sphere(self):
        rays=erp_unit_rays(24,48);ranges=[];scores=[]
        # Analytic camera-Z for a sphere centered at the physical camera.
        yy,xx=np.mgrid[:64,:64];camera_rays=np.stack([(xx+.5-32)/32,(yy+.5-32)/32,np.ones_like(xx)],axis=-1)
        camera_rays/=np.linalg.norm(camera_rays,axis=-1,keepdims=True)
        prediction=1/(5*camera_rays[...,2])
        for yaw in range(0,360,60):
            radial,score=crop_ranges(prediction,FIT,C.crop_rotation(yaw,0),rays,[32,32,32,32])
            ranges.append(radial);scores.append(score)
        stitched=stitch_ranges(ranges,scores,.01)
        np.testing.assert_allclose(stitched['radial'][10:14],5,atol=.003)
        np.testing.assert_allclose(stitched['radial'][10:14,0],stitched['radial'][10:14,-1],atol=.003)
        # Six 90-degree crops overlap near their edges, not at every longitude.
        self.assertTrue((stitched['support'][10:14,[0,-1]]>=1).all())
        self.assertTrue(stitched['consensus'][10:14].any())

    def test_downward_rotation_adds_road_without_moving_center(self):
        ray=np.array([[[0,np.sin(np.deg2rad(55)),np.cos(np.deg2rad(55))]]])
        level,_=crop_ranges(np.ones((512,512)),FIT,np.eye(3),ray,[256]*4)
        down,_=crop_ranges(np.ones((512,512)),FIT,C.crop_rotation(0,-30),ray,[256]*4)
        self.assertTrue(np.isnan(level).all());self.assertTrue(np.isfinite(down).all())
        pose=np.eye(4);pose[:3,3]=[1,2,3]
        relative=np.eye(4);relative[:3,:3]=C.crop_rotation(60,-30)
        np.testing.assert_array_equal((pose@relative)[:3,3],pose[:3,3])

    def test_selection_is_centrality_not_nearest_depth_and_unsupported_retained(self):
        ranges=np.array([[[5.,5.,np.nan]],[[10.,np.nan,np.nan]]])
        scores=np.array([[[.8,.8,-np.inf]],[[.9,-np.inf,-np.inf]]])
        out=stitch_ranges(ranges,scores,.2)
        np.testing.assert_array_equal(out['support'],[[2,1,0]])
        np.testing.assert_array_equal(out['winner'],[[1,0,-1]])
        self.assertEqual(out['radial'][0,0],10)
        self.assertFalse(out['consensus'].any())
        self.assertAlmostEqual(out['log_spread'][0,0],np.log(2))
        self.assertTrue(np.isnan(out['radial'][0,2]))

    def test_world_backprojection_respects_pose_not_gravity_guess(self):
        rays=erp_unit_rays(4,8);rgb=np.zeros((4,8,3),np.uint8)
        pose=np.eye(4);pose[:3,:3]=C.crop_rotation(60,-30);pose[:3,3]=[3,4,5]
        xyz,_,rows,cols=backproject_radial(np.full((4,8),7.),rgb,pose,stride=1)
        np.testing.assert_allclose(xyz,(rays[rows,cols]*7)@pose[:3,:3].T+pose[:3,3],atol=1e-6)


if __name__=='__main__':unittest.main()
