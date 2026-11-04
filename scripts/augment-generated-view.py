#!/usr/bin/env python3
"""Add one explicitly synthetic view to a local posed dataset without resizing.

This proves input integration only. It does not establish factual reconstruction,
novel-view quality, or independent geometry: supplied poses use all-image SfM.
Requires Pillow. Original target photograph pixels are never opened.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
import traceback

SPEC = importlib.util.spec_from_file_location('reconstruct', Path(__file__).with_name('reconstruct.py'))
RECONSTRUCT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECONSTRUCT)
LIMITS = ('Experimental generated-view augmentation; no geometry or multi-view quality validation. '
          'Camera poses and initialization use all-image SfM, so this is not independent held-out geometry. '
          'The added image is synthetic/reprojected supervision; the diffusion mask fraction is not an observed-pixel fraction. '
          'Do not evaluate generalization at the generated target view added to training.')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def image_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or path.parts[:1] != ('images',) or '..' in path.parts:
        raise ValueError('Images must use dataset-relative images/ paths')
    result = root / path
    if result.is_symlink() or not result.resolve().is_relative_to(root.resolve()):
        raise ValueError('Image path escapes dataset or is a symlink')
    return result


def load_png(path, size, mask=False):
    from PIL import Image
    with Image.open(path) as source:
        if source.size != tuple(size):
            raise ValueError(f'Image dimensions do not match unchanged target calibration: {path.name}')
        if mask:
            if source.mode not in ('1','L'):
                raise ValueError('Mask must be binary grayscale')
            value = source.convert('L')
            histogram = value.histogram()
            if any(histogram[1:255]) or not histogram[0] or not histogram[255]:
                raise ValueError('Mask must contain both 0 and 255 and no other values')
        else:
            if source.mode not in ('RGB','RGBA'):
                raise ValueError('Require an 8-bit RGB or opaque RGBA image')
            if source.mode == 'RGBA' and source.getextrema()[3] != (255,255):
                raise ValueError('Reference/completed image must be opaque')
            value = source.convert('RGB')
    return value


def verify_working(name, job, job_report, size, original=None):
    path = job / f'{name}.png'
    data = path.read_bytes()
    value = load_png(path,size,mask=name=='mask')
    inputs = job_report['input']
    working_key = 'working' + name.title() + 'Sha256'
    original_key = name + 'Sha256'
    result = {'workingSha256': sha(data)}
    if working_key in inputs:
        if sha(data) != inputs[working_key]:
            raise ValueError(f'Working {name} hash mismatch')
        result['verification'] = 'Recorded working-file hash'
    elif original is None:
        if original_key not in inputs or sha(data) != inputs[original_key]:
            raise ValueError(f'No recorded working {name} hash; provide --source-{name} to verify the original bytes and identical decoded pixels')
        result['verification'] = 'Cached file identical to recorded original bytes'
    if original is not None:
        original_bytes = original.read_bytes()
        if sha(original_bytes) != inputs.get(original_key):
            raise ValueError(f'Original {name} hash mismatch')
        original_image = load_png(original,size,mask=name=='mask')
        if original_image.tobytes() != value.tobytes():
            raise ValueError(f'Reencoded working {name} pixels differ from original input')
        result.update(originalSha256=sha(original_bytes),verification='Original byte hash and working decoded pixels verified')
    return value, result


def augment(args):
    from PIL import ImageChops
    src, posed, job = args.dataset.resolve(), args.poses.resolve(), args.inpaint.resolve()
    dst = args.output.resolve()
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Output exists; use a new directory')
    if any(dst.is_relative_to(parent) for parent in (src,posed,job)):
        raise ValueError('Output must be outside all input directories')
    dst.mkdir(parents=True,exist_ok=False)
    started = time.monotonic()
    report = {'schemaVersion':1,'status':'RUNNING','operation':'experimental-generated-view-augmentation',
              'startedAt':datetime.now(timezone.utc).isoformat(),'target':args.target,
              'targetPhotographPixelsRead':False,'limits':LIMITS,'gpuTraining':'NOT RUN',
              'geometryValidation':'NOT RUN','browserRendering':'NOT RUN'}
    with (dst/'execution.log').open('w') as log:
        try:
            transforms, provenance = RECONSTRUCT.validate_dataset(src)
            if any(frame['file_path']==args.target for frame in transforms['frames']):
                raise ValueError('Target already occurs in training dataset')
            if len({f['file_path'] for f in transforms['frames']}) != len(transforms['frames']):
                raise ValueError('Duplicate training image paths')
            target_path = image_path(dst,args.target)
            pose_bytes = (posed/'transforms.json').read_bytes()
            pose_document = json.loads(pose_bytes)
            selected = [f for f in pose_document['frames'] if f['file_path']==args.target]
            if len(selected)!=1:
                raise ValueError('Target must match exactly one supplied pose')
            target = selected[0]
            size = [target['w'],target['h']]
            if size != [512,512]:
                raise ValueError('This bounded experiment requires unchanged 512x512 calibration')
            calibration_keys = ('w','h','fl_x','fl_y','cx','cy')
            for key in calibration_keys:
                if key not in target:
                    raise ValueError(f'Explicit target calibration missing {key}')
            for frame in transforms['frames']:
                if any(frame.get(key,transforms.get(key)) != target[key] for key in calibration_keys):
                    raise ValueError('Training and generated target must share unchanged calibration')
                pose_matches = [f for f in pose_document['frames'] if f['file_path'] == frame['file_path']]
                if len(pose_matches) != 1 or pose_matches[0]['transform_matrix'] != frame['transform_matrix']:
                    raise ValueError('Training and target pose datasets do not share identical camera coordinates')
            job_bytes = (job/'report.json').read_bytes()
            result = json.loads(job_bytes)
            if result.get('status')!='PASS' or result.get('gpuInference')!='PASS' or not result.get('synthetic'):
                raise ValueError('Require a completed successful synthetic inpainting job with GPU inference PASS')
            if result['input'].get('originalSize') != size or result['input'].get('workingSize') != size:
                raise ValueError('Inpaint resize would invalidate unchanged calibration')
            if result['output'].get('file') != 'completed.png':
                raise ValueError('Expected completed.png output')
            completed_bytes = (job/'completed.png').read_bytes()
            if sha(completed_bytes) != result['output'].get('sha256'):
                raise ValueError('Completed output hash mismatch')
            completed = load_png(job/'completed.png',size)
            reference, reference_check = verify_working('reference',job,result,size,args.source_reference)
            mask, mask_check = verify_working('mask',job,result,size,args.source_mask)
            histogram = mask.histogram()
            fraction = histogram[255]/(size[0]*size[1])
            if histogram[255] != result['input'].get('syntheticPixels') or abs(fraction-result['input'].get('syntheticFraction',-1))>1e-12:
                raise ValueError('Mask population disagrees with inpainting report')
            difference = ImageChops.difference(completed,reference)
            if any(channel.getbbox() is not None for channel in ImageChops.multiply(difference,ImageChops.invert(mask).convert('RGB')).split()):
                raise ValueError('Completed image changed pixels outside the diffusion mask')
            source_binding = {'status':'NOT RUN','reason':'Source renderer/warp report not provided; explicit target choice remains caller responsibility'}
            if args.source_reference:
                source_report_path = args.source_reference.parent/'report.json'
                if source_report_path.is_file():
                    source_bytes = source_report_path.read_bytes()
                    source_report = json.loads(source_bytes)
                    source_target = source_report.get('frame') or source_report.get('cameras',{}).get('target',{}).get('file_path')
                    if source_report.get('status') != 'PASS' or source_target != args.target:
                        raise ValueError('Source renderer/warp report does not match selected target pose')
                    source_camera = source_report.get('camera') or source_report.get('cameras',{}).get('target',{})
                    if any(source_camera.get(key) != target[key] for key in (*calibration_keys,'transform_matrix')):
                        raise ValueError('Source renderer/warp target matrix or calibration differs from selected target pose')
                    source_binding = {'status':'PASS','sourceReportSha256':sha(source_bytes),'target':source_target,
                                      'verification':'Exact target filename, camera-to-world matrix and all six intrinsic fields'}
            for frame in transforms['frames']:
                original = image_path(src,frame['file_path'])
                load_png(original,size)
                destination = image_path(dst,frame['file_path'])
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(original,destination)
            init_relative = Path(transforms.get('ply_file_path','init.ply'))
            if init_relative.is_absolute() or '..' in init_relative.parts or not (src/init_relative).is_file():
                raise ValueError('Require a local initialization PLY')
            (dst/'init.ply').write_bytes((src/init_relative).read_bytes())
            target_path.parent.mkdir(parents=True,exist_ok=True)
            target_path.write_bytes(completed_bytes)
            transforms['frames'].append(target)
            transforms['ply_file_path'] = 'init.ply'
            RECONSTRUCT.write_json(dst/'transforms.json',transforms)
            (dst/'source-provenance.json').write_bytes((src/'provenance.json').read_bytes())
            provenance['notes'] = ('Source training dataset notes before augmentation: '+provenance.get('notes','')
                                   +' Current augmented dataset: '+LIMITS)
            RECONSTRUCT.write_json(dst/'provenance.json',provenance)
            for name in ('LICENSE','ATTRIBUTION.txt'):
                if (src/name).is_file(): shutil.copyfile(src/name,dst/name)
            synthetic = {'schemaVersion':1,'limits':LIMITS,'views':[{'file':args.target,'synthetic':True,
                'kind':'diffusion-completed-reprojected-view','sha256':sha(completed_bytes),'maskFraction':fraction,
                'model':result['model'],'settings':result['settings'],
                'sourceInpaintReportSha256':sha(job_bytes),'sourcePoseDocumentSha256':sha(pose_bytes),
                'sourceInputHashes':result['input'],'referenceVerification':reference_check,'maskVerification':mask_check,
                'sourceTargetBinding':source_binding,'pose':target,'poseMeaning':'Exact supplied all-image SfM pose; never inferred from generated pixels'}]}
            RECONSTRUCT.write_json(dst/'synthetic-views.json',synthetic)
            RECONSTRUCT.validate_dataset(dst)
            report.update(status='PASS',trainingImages=len(transforms['frames']),syntheticViews=1,
                completedSha256=sha(completed_bytes),initializationSha256=sha((dst/'init.ply').read_bytes()),
                sourceTargetBinding=source_binding)
            print(json.dumps(report,indent=2),file=log)
        except BaseException as error:
            report.update(status='FAIL',error=f'{type(error).__name__}: {error}')
            traceback.print_exc(file=log)
            raise
        finally:
            report['elapsedSeconds']=time.monotonic()-started
            RECONSTRUCT.write_json(dst/'augmentation.json',report)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dataset','poses','target','inpaint','output'):
        parser.add_argument(name,type=str if name=='target' else Path)
    parser.add_argument('--source-reference',type=Path,help='Original inpainting RGB input, for older reports without working-file hashes')
    parser.add_argument('--source-mask',type=Path,help='Original inpainting mask input, for older reports without working-file hashes')
    args=parser.parse_args(argv)
    try:
        report=augment(args)
        print(json.dumps(report,indent=2))
    except Exception as error:
        print(f'FAIL: {error}',file=sys.stderr)
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
