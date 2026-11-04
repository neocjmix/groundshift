"""Synthetic adapter fixtures only; no diffusion/GPU/geometry acceptance claims."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'augment-generated-view.py'
spec=importlib.util.spec_from_file_location('augment_generated_view',SCRIPT)
AUGMENT=importlib.util.module_from_spec(spec);spec.loader.exec_module(AUGMENT)
try:
    from PIL import Image
except ImportError:
    Image=None


@unittest.skipUnless(Image,'Pillow unavailable; augmentation pixel checks NOT RUN')
class AugmentationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.train=root/'train';self.pose=root/'poses';self.job=root/'job';self.out=root/'output'
        for folder in (self.train,self.pose,self.job):folder.mkdir()
        (self.train/'images').mkdir()
        self.frames=[]
        for index in range(3):
            self.frames.append({'file_path':f'images/frame{index}.png','w':512,'h':512,
                'fl_x':256.,'fl_y':256.,'cx':256.,'cy':256.,
                'transform_matrix':[[1,0,0,index],[0,1,0,0],[0,0,1,0],[0,0,0,1]]})
        self.write(self.train/'transforms.json',{'camera_model':'PINHOLE','ply_file_path':'init.ply','frames':self.frames[:2]})
        self.write(self.pose/'transforms.json',{'camera_model':'PINHOLE','frames':self.frames})
        self.write(self.train/'provenance.json',{'sourceType':'images','sourceUrl':'https://example.com/fixture',
            'license':'Synthetic test','licenseUrl':'https://example.com/license','attribution':'Synthetic fixture'})
        (self.train/'init.ply').write_bytes(b'unchanged synthetic initialization fixture')
        reference=Image.new('RGB',(512,512),(20,40,60))
        for frame in self.frames[:2]:reference.save(self.train/frame['file_path'])
        reference.save(self.job/'reference.png')
        mask=Image.new('L',(512,512),0);mask.paste(255,(0,0,64,64));mask.save(self.job/'mask.png')
        completed=reference.copy();completed.paste((200,10,30),(0,0,64,64));completed.save(self.job/'completed.png')
        self.report={'status':'PASS','gpuInference':'PASS','synthetic':True,
            'input':{'originalSize':[512,512],'workingSize':[512,512],'syntheticPixels':4096,'syntheticFraction':1/64,
                'workingReferenceSha256':self.hash(self.job/'reference.png'),'workingMaskSha256':self.hash(self.job/'mask.png')},
            'output':{'file':'completed.png','sha256':self.hash(self.job/'completed.png')},
            'model':{'repository':'synthetic-fixture','revision':'no-model-executed',
                     'license':'Synthetic fixture model license','licenseUrl':'https://example.com/model-license'},
            'settings':{'prompt':'fixture','seed':0}}
        self.write(self.job/'report.json',self.report)
        self.args=argparse.Namespace(dataset=self.train,poses=self.pose,target='images/frame2.png',inpaint=self.job,
            output=self.out,source_reference=None,source_mask=None)

    def write(self,path,value):path.write_text(json.dumps(value))
    def hash(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def run_failure(self,pattern):
        with self.assertRaisesRegex(ValueError,pattern):AUGMENT.augment(self.args)
        report=json.loads((self.out/'augmentation.json').read_text())
        self.assertEqual(report['status'],'FAIL')
        self.assertTrue((self.out/'execution.log').read_text())

    def test_exact_pose_and_bytes_retained_without_target_photograph(self):
        self.assertFalse((self.pose/'images').exists())
        report=AUGMENT.augment(self.args)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['trainingImages'],3)
        transformed=json.loads((self.out/'transforms.json').read_text())
        self.assertEqual(transformed['frames'][-1],self.frames[-1])
        self.assertEqual((self.out/'images/frame2.png').read_bytes(),(self.job/'completed.png').read_bytes())
        for name in ('init.ply','images/frame0.png','images/frame1.png'):
            self.assertEqual((self.out/name).read_bytes(),(self.train/name).read_bytes())
        synthetic=json.loads((self.out/'synthetic-views.json').read_text())
        self.assertTrue(synthetic['views'][0]['synthetic'])
        self.assertEqual(synthetic['views'][0]['maskFraction'],1/64)
        self.assertFalse(report['targetPhotographPixelsRead'])
        self.assertEqual(report['geometryValidation'],'NOT RUN')

    def test_portable_world_preserves_synthetic_model_and_image_provenance(self):
        AUGMENT.augment(self.args)
        transforms,provenance=AUGMENT.RECONSTRUCT.validate_dataset(self.out)
        world,_=AUGMENT.RECONSTRUCT.artifact(transforms,provenance,'Synthetic fixture','fixture')
        notes=world['provenance']['notes']
        for value in ('images/frame2.png','synthetic-fixture','no-model-executed',
                      'Synthetic fixture model license','https://example.com/model-license',
                      'seed: 0','diffusion mask fraction: 0.015625',self.report['output']['sha256']):
            with self.subTest(value=value):self.assertIn(value,notes)
        self.assertEqual(world['provenance']['license'],'Synthetic test')

    def test_corrupted_completed_is_rejected(self):
        (self.job/'completed.png').write_bytes(b'corrupt')
        self.run_failure('Completed output hash mismatch')

    def test_unmasked_pixel_change_is_rejected_even_with_updated_output_hash(self):
        image=Image.open(self.job/'completed.png').convert('RGB');image.putpixel((500,500),(1,2,3));image.save(self.job/'completed.png')
        self.report['output']['sha256']=self.hash(self.job/'completed.png');self.write(self.job/'report.json',self.report)
        self.run_failure('outside the diffusion mask')

    def test_coordinate_frame_mismatch_is_rejected(self):
        self.frames[0]['transform_matrix'][0][3]+=10
        self.write(self.pose/'transforms.json',{'camera_model':'PINHOLE','frames':self.frames})
        self.run_failure('identical camera coordinates')

    def test_inpaint_resize_is_rejected(self):
        self.report['input']['originalSize']=[1024,1024]
        self.write(self.job/'report.json',self.report)
        self.run_failure('resize would invalidate')

    def test_target_already_in_training_is_rejected(self):
        self.args.target='images/frame0.png'
        self.run_failure('Target already occurs')

    def test_reencoded_originals_can_be_verified_by_hash_and_pixels(self):
        source=self.train.parent/'source';source.mkdir()
        for name in ('reference','mask'):
            image=Image.open(self.job/f'{name}.png');image.save(source/f'{name}.png',compress_level=0)
            self.report['input'].pop('working'+name.title()+'Sha256')
            self.report['input'][name+'Sha256']=self.hash(source/f'{name}.png')
            setattr(self.args,'source_'+name,source/f'{name}.png')
        self.write(source/'report.json',{'status':'PASS','frame':self.args.target,'camera':self.frames[-1]})
        self.write(self.job/'report.json',self.report)
        self.assertEqual(AUGMENT.augment(self.args)['sourceTargetBinding']['status'],'PASS')

    def test_wrong_source_target_binding_is_rejected(self):
        self.args.source_reference=self.job/'reference.png'
        self.report['input']['referenceSha256']=self.hash(self.job/'reference.png')
        self.report['frame']='images/wrong-view.png'
        self.write(self.job/'report.json',self.report)
        self.run_failure('does not match selected target')

    def test_same_filename_with_wrong_source_camera_is_rejected(self):
        self.args.source_reference=self.job/'reference.png'
        self.report['input']['referenceSha256']=self.hash(self.job/'reference.png')
        self.report['frame']=self.args.target
        self.report['camera']=copy.deepcopy(self.frames[-1])
        self.report['camera']['transform_matrix'][0][3]+=0.01
        self.write(self.job/'report.json',self.report)
        self.run_failure('matrix or calibration differs')

    def test_existing_output_is_not_overwritten(self):
        self.out.mkdir();marker=self.out/'keep';marker.write_text('keep')
        with self.assertRaisesRegex(ValueError,'Output exists'):AUGMENT.augment(self.args)
        self.assertEqual(list(self.out.iterdir()),[marker])


if __name__=='__main__':unittest.main()
