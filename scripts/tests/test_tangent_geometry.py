import unittest
from pathlib import Path
import sys
import importlib.util
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tangent_geometry import icosahedron_normals,view_angles,project_rays,fit_overlap_system,shell_mesh,fill_display_nadir
from spherical_depth import erp_unit_rays
spec=importlib.util.spec_from_file_location('crop',Path(__file__).resolve().parents[1]/'prepare-panoramas.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)


class TangentGeometryTests(unittest.TestCase):
    def test_twenty_face_normals_and_crop_forward_agree(self):
        normals=icosahedron_normals();self.assertEqual(normals.shape,(20,3))
        np.testing.assert_allclose(np.linalg.norm(normals,axis=1),1)
        for n in normals:
            rotation=C.crop_rotation(*view_angles(n));np.testing.assert_allclose(rotation[:,2],n,atol=1e-12)
            self.assertAlmostEqual(np.linalg.det(rotation),1)

    def test_full_sphere_poles_and_seam_are_covered(self):
        rays=erp_unit_rays(90,180).reshape(-1,3);rays=np.r_[rays,[[0,-1,0],[0,1,0],[1e-10,0,-1],[-1e-10,0,-1]]]
        intr=C.intrinsics(1024,80);params=[intr[k] for k in ['fx','fy','cx','cy']];count=np.zeros(len(rays),int)
        for n in icosahedron_normals():count+=project_rays(rays,C.crop_rotation(*view_angles(n)),params,1024)[2]
        self.assertGreaterEqual(int(count.min()),1);self.assertGreater(float(count.mean()),2)

    def test_inverse_camera_z_must_convert_before_overlap_comparison(self):
        ray=np.array([[.3,0,np.sqrt(1-.3**2)]]);radial=7.
        inv=[];zs=[]
        for yaw in [0,40]:
            _,cos,_=project_rays(ray,C.crop_rotation(yaw,0),[512]*4,1024)
            z=radial*cos[0];zs.append(z);inv.append(cos[0]/z)
        self.assertNotAlmostEqual(zs[0],zs[1]);np.testing.assert_allclose(inv,[1/radial]*2)

    def test_anchored_overlap_recovers_relative_affine_coefficients(self):
        true=np.array([.5,.1,.9,-.05]);anchor=[];overlap=[]
        for inverse in [.1,.2,.4,.5]:
            c0,c1=.6,.9;r0=(inverse/c0-true[1])/true[0];r1=(inverse/c1-true[3])/true[2]
            anchor.append(([c0*r0,c0,0,0],inverse));overlap.append([c0*r0,c0,-c1*r1,-c1])
        fit=fit_overlap_system(anchor,overlap,[.5,.1,.7,.02]);np.testing.assert_allclose(fit,true,atol=.001)

    def test_unanchored_and_unidentifiable_systems_are_not_metric_calibration(self):
        with self.assertRaises(ValueError):fit_overlap_system([],[[1,1,-1,-1]],[1,0,1,0])
        with self.assertRaises(ValueError):fit_overlap_system([([1,1,0,0],1)],[],[1,0,1,0])

    def test_mesh_does_not_bridge_holes_or_depth_discontinuities(self):
        depth=np.full((4,8),3.);depth[:,4:]=30.;depth[1,1]=np.nan
        mesh=shell_mesh(depth,np.eye(4));idx=np.array(mesh['indices']).reshape(-1,3);values=np.c_[depth,depth[:,:1]].ravel()
        self.assertTrue(np.isfinite(mesh['positions']).all());self.assertGreater(len(idx),0)
        self.assertTrue(np.isfinite(values[idx]).all());self.assertTrue(np.all(values[idx].max(axis=1)/values[idx].min(axis=1)<=1.25))

    def test_mesh_wrap_duplicates_same_position_with_continuous_u(self):
        mesh=shell_mesh(np.full((4,8),3.),np.eye(4));p=np.array(mesh['positions']).reshape(4,9,3);uv=np.array(mesh['uvs']).reshape(4,9,2)
        np.testing.assert_allclose(p[:,0],p[:,-1]);self.assertTrue(np.all(uv[:,-1,0]>1));self.assertTrue(np.all(uv[:,0,0]>0))

    def test_mesh_rejects_reflected_and_nonfinite_world_poses(self):
        for pose in [np.diag([-1,1,1,1]),np.array([[1,0,0,np.nan],[0,1,0,0],[0,0,1,0],[0,0,0,1]])]:
            with self.assertRaises(ValueError):shell_mesh(np.ones((4,8)),pose)

    def test_nadir_display_fill_preserves_observed_region_and_input_bytes(self):
        rgb=np.full((100,200,3),[100,110,120],np.uint8);rgb[85:]=[255,190,0];original=rgb.copy();filled=fill_display_nadir(rgb)
        np.testing.assert_array_equal(rgb,original);np.testing.assert_array_equal(filled[:85],rgb[:85]);np.testing.assert_array_equal(filled[85:],np.full((15,200,3),[100,110,120],np.uint8))

    def test_display_fill_cannot_create_depth_or_accept_ambiguous_color(self):
        with self.assertRaises(ValueError):fill_display_nadir(np.zeros((4,8,3),float))
        with self.assertRaises(ValueError):fill_display_nadir(np.zeros((4,8,3),np.uint8),start=1)


if __name__=='__main__':unittest.main()
