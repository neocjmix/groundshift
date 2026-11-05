#!/usr/bin/env python3
"""Bounded scooter experiment: focused crops, whole-frame augmentation, depth fusion.

Run stages in the existing environment appropriate to each model. Large artifacts
and detailed reports stay in data/. Generated camera poses are estimated by SfM,
never assigned from interpolation time. No diffusion runs during depth fusion.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'segmind/tiny-sd'
REVISION = 'cad0bd7495fa6c4bcca01b19a723dc91627fe84f'


def load_module(filename):
    spec = importlib.util.spec_from_file_location(filename.replace('-', '_'), ROOT / 'scripts' / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def prepare(job, report):
    import numpy as np
    from PIL import Image, ImageDraw
    prep = load_module('prepare-panoramas.py')
    source = ROOT / 'data/jobs/mapillary-beijing-rig-poses-v2/dataset'
    poses = json.loads((source / 'transforms.json').read_text())['frames']
    panos = sorted((ROOT / 'data/samples/mapillary-beijing/images').glob('*.jpg'))
    centers, matrices = [], []
    for i in range(9):
        frame = next(f for f in poses if f['file_path'] == f'images/pano_{i+1:06d}_view_01.png')
        matrix = np.array(frame['transform_matrix']) @ np.diag([1, -1, -1, 1])
        matrices.append(matrix)
        centers.append(matrix[:3, 3])
    # Manually selected centers of the same scooter in two observed panoramas.
    rays = []
    for i, x, y in [(0, 731, 565), (8, 1343, 594)]:
        yaw, pitch = (x / 1920 - .5) * 2 * np.pi, (.5 - y / 960) * np.pi
        rays.append(matrices[i][:3, :3] @ np.array([np.sin(yaw)*np.cos(pitch), -np.sin(pitch), np.cos(yaw)*np.cos(pitch)]))
    distances = np.linalg.lstsq(np.column_stack([rays[0], -rays[1]]), centers[8]-centers[0], rcond=None)[0]
    estimates = [centers[0]+distances[0]*rays[0], centers[8]+distances[1]*rays[1]]
    target = np.mean(estimates, axis=0)
    folder = job / 'originals'
    (folder / 'images').mkdir(parents=True)
    frames, records = [], []
    contact = Image.new('RGB', (768, 3*282), '#141921')
    for i, (path, matrix) in enumerate(zip(panos, matrices)):
        ray = matrix[:3, :3].T @ (target-matrix[:3, 3]); ray /= np.linalg.norm(ray)
        yaw, pitch = np.degrees(np.arctan2(ray[0], ray[2])), np.degrees(-np.arcsin(ray[1]))
        pixels = np.asarray(Image.open(path).convert('RGB'))
        crop = prep.crop_panorama(pixels, 512, 45, yaw, pitch)
        name = f'frame_{i*8:04d}.png'
        Image.fromarray(crop).save(folder / 'images' / name)
        c2w = matrix.copy(); c2w[:3, :3] = matrix[:3, :3] @ prep.crop_rotation(yaw, pitch) @ np.diag([1,-1,-1])
        f = 256 / np.tan(np.radians(22.5))
        frames.append(dict(file_path=f'images/{name}', w=512, h=512, fl_x=float(f), fl_y=float(f), cx=256., cy=256., transform_matrix=c2w.tolist()))
        records.append(dict(file=name, kind='observed', source=path.name, panoramaIndex=i, yawDegrees=float(yaw), pitchDegrees=float(pitch)))
        thumb = Image.fromarray(crop).resize((256,256)); x,y=i%3*256,i//3*282
        contact.paste(thumb,(x,y+26)); ImageDraw.Draw(contact).text((x+8,y+7),f'Original {i+1} / frame {i*8}',fill='white')
    contact.save(job / 'originals-contact.jpg')
    provenance=json.loads((source/'provenance.json').read_text())
    provenance['notes'] += ' Object-focused perspective crops of one parked white scooter. Derived from real spherical images with analytic rotations; no new physical camera positions.'
    write(folder/'provenance.json',provenance)
    write(folder/'transforms.json',dict(camera_model='PINHOLE',ply_file_path='init.ply',frames=frames))
    shutil.copyfile(source/'init.ply',folder/'init.ply')
    write(job/'inputs.json',dict(targetWorld=target.tolist(),targetMeaning='Approximate focus triangulated from manually selected endpoint bearings and estimated source cameras',records=records,hfovDegrees=45,width=512,height=512))
    report.update(realImages=9, plannedTotalImages=65, endpointRayGap=float(np.linalg.norm(estimates[0]-estimates[1])), target=target.tolist())


def interpolate(job, report):
    import numpy as np
    from PIL import Image
    from rife_mlx.pipeline_mlx import interpolate_pair
    from rife_mlx.utils.weights import build_model
    model=build_model('4.25',weights_dir=str(ROOT/'data/tools/rife-model'))
    output=job/'interpolation'; output.mkdir()
    originals=sorted((job/'originals/images').glob('*.png'))
    for pair in range(8):
        images={0:np.asarray(Image.open(originals[pair])),8:np.asarray(Image.open(originals[pair+1]))}
        for stride in (8,4,2):
            for left in range(0,8,stride):
                mid=left+stride//2
                images[mid]=interpolate_pair(model,images[left],images[left+stride],.5,1.)
        for local,pixels in sorted(images.items()):
            Image.fromarray(pixels).save(output/f'frame_{pair*8+local:04d}.png')
        print(f'RIFE pair {pair+1}/8',flush=True)
    report.update(images=65, synthetic=56, model='Practical-RIFE 4.25',device='MLX/Metal', meaning='Optical-flow initial images for whole-frame diffusion, not measured intermediate cameras')


def diffuse(job, report):
    import torch
    from PIL import Image
    from diffusers import StableDiffusionImg2ImgPipeline
    if not torch.backends.mps.is_available():
        raise RuntimeError('Local MPS required')
    pipeline=StableDiffusionImg2ImgPipeline.from_pretrained(MODEL,revision=REVISION,cache_dir=ROOT/'data/tools/object-diffusion-models',local_files_only=True,torch_dtype=torch.float16).to('mps')
    pipeline.enable_attention_slicing()
    output=job/'augmented'; (output/'images').mkdir(parents=True)
    provenance=json.loads((job/'originals/provenance.json').read_text())
    provenance['notes'] += f' 9 real crops + 56 full-frame synthetic intermediate images: RIFE 4.25 followed by {MODEL}@{REVISION} image-to-image diffusion on MPS, CreativeML OpenRAIL-M. Synthetic images do not supply measured camera poses.'
    write(output/'provenance.json',provenance)
    report.update(model=MODEL,revision=REVISION,device='MPS',steps=30,strength=.2,guidance=3.,seed=41,license='CreativeML OpenRAIL-M',images=[])
    prompt='photograph of the same parked white electric scooter with a blue quilted handlebar cover, black seat, small wheels, on a grey paved apartment courtyard, green plants behind, natural daylight'
    for i,path in enumerate(sorted((job/'interpolation').glob('*.png'))):
        before=time.monotonic()
        if i%8==0:
            shutil.copyfile(job/'originals/images'/path.name,output/'images'/path.name)
            kind='observed'
        else:
            result=pipeline(prompt=prompt,negative_prompt='duplicate scooter, extra wheels, warped object, drawing, blurry',image=Image.open(path).convert('RGB'),num_inference_steps=30,strength=.2,guidance_scale=3.,generator=torch.Generator('cpu').manual_seed(41))
            if result.nsfw_content_detected and any(result.nsfw_content_detected):
                raise RuntimeError(f'Model flagged frame {i}; no output published')
            result.images[0].save(output/'images'/path.name)
            torch.mps.synchronize(); kind='synthetic'
        report['images'].append(dict(file=path.name,kind=kind,seconds=time.monotonic()-before))
        write(job/'diffuse.json',report)
        print(f'Image {i+1}/65 {kind}',flush=True)
    write(output/'sequence.json',dict(frames=[dict(file='images/'+item['file'],kind=item['kind']) for item in report['images']],notes='Ordered real and generated image inputs; camera poses must be estimated separately.'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','interpolate','diffuse'])
    parser.add_argument('job',type=Path)
    args=parser.parse_args(); args.job.mkdir(parents=True,exist_ok=True)
    path=args.job/f'{args.stage}.json'
    if path.exists():
        parser.error('Stage report already exists; preserve evidence and use a fresh job')
    report=dict(status='RUNNING',startedAt=datetime.now(timezone.utc).isoformat(),stage=args.stage)
    started=time.monotonic(); write(path,report)
    try:
        globals()[args.stage](args.job,report)
        report['status']='PASS'
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}')
        traceback.print_exc(); raise
    finally:
        report.update(finishedAt=datetime.now(timezone.utc).isoformat(),elapsedSeconds=time.monotonic()-started)
        write(path,report)


if __name__=='__main__':
    main()
