"""Synthetic contracts for a resolution change; no GPU/quality acceptance claims."""
from pathlib import Path
import copy
import importlib.util
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('final_quality',Path(__file__).resolve().parents[1]/'prepare-final-quality.py')
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)


class FinalQualityContracts(unittest.TestCase):
    def setUp(self):
        self.old=[dict(file_path='images/p04-level-000.png',physicalPanorama=4,ring='level',yaw=0,pitch=0,
            w=512,h=512,fl_x=256,fl_y=256,cx=256,cy=256,transform_matrix=np.eye(4).tolist())]
        self.new=copy.deepcopy(self.old)
        for k in ['w','h','fl_x','fl_y','cx','cy']:self.new[0][k]*=2

    def test_pixel_scale_changes_without_moving_camera(self):
        F.verify_frames(self.old,self.new)

    def test_scaled_world_translation_is_rejected(self):
        self.new[0]['transform_matrix'][0][3]=.1
        with self.assertRaisesRegex(ValueError,'pose'):F.verify_frames(self.old,self.new)

    def test_intrinsics_cannot_stay_at_old_pixel_scale(self):
        self.new[0]['fl_x']=256
        with self.assertRaisesRegex(ValueError,'intrinsics'):F.verify_frames(self.old,self.new)

    def test_withheld_rgb_and_changed_view_selection_rejected(self):
        for key,value in [('physicalPanorama',5),('yaw',60),('pitch',-30)]:
            with self.subTest(key=key):
                frames=copy.deepcopy(self.new);frames[0][key]=value
                with self.assertRaises(ValueError):F.verify_frames(self.old,frames)

    def test_duplicate_frame_cannot_represent_extra_camera(self):
        with self.assertRaisesRegex(ValueError,'identities'):F.verify_frames(self.old,self.new*2)

    def test_invalid_resolution_rejected_before_output_mutation(self):
        for bad in [True,0,4097,1024.5]:
            with self.subTest(value=bad),self.assertRaises(ValueError):F.P.prepare_inputs(Path('must-not-be-created'),bad)


if __name__=='__main__':unittest.main()
