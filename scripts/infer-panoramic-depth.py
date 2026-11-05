#!/usr/bin/env python3
"""One real ERP -> pinned MPS depth prediction, without implicit distance calibration."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

DA2_REVISION = 'd659838585f2bc9967c7e9367af573795271dbbb'
DA2_WEIGHTS = 'd8ea568fc3dfb7d7432e5b763de499dd03fb6dc1c2020d84639f35e2dfa4f78e'
DAV2_REVISION = '5426e4f0f36572d16453bbda7a8389317b1bef99'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--model', choices=['da2', 'dav2'], required=True)
    p.add_argument('--repo', type=Path, default=Path('data/tools/da2'))
    p.add_argument('--checkpoint', type=Path, default=Path('data/tools/da2-checkpoint'))
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = dict(status='RUNNING', startedAt=datetime.now(timezone.utc).isoformat(), model=args.model,
                  source=str(args.image.resolve()), sourceSha256=sha(args.image), device='mps',
                  calibration='NOT RUN: raw output only; no meter or range conversion')
    def save(): (args.output/'inference.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    save()
    try:
        import numpy as np
        from PIL import Image
        import torch
        if not torch.backends.mps.is_available(): raise RuntimeError('MPS is unavailable; no silent CPU substitution')
        torch.manual_seed(42)
        with Image.open(args.image) as im:
            report['originalSize'] = list(im.size)
            if im.width != im.height*2: raise ValueError('Require full 2:1 ERP')
            rgb = im.convert('RGB').resize((1092,546),Image.Resampling.LANCZOS)
        rgb.save(args.output/'source.png')
        report.update(workingSize=list(rgb.size), torchVersion=torch.__version__, pythonVersion=sys.version,
                      resize='Pillow Lanczos, full ERP; no crop', precision='float32', cpuFallback=False)
        loading = time.monotonic()
        if args.model == 'da2':
            revision = subprocess.check_output(['/Library/Developer/CommandLineTools/usr/bin/git','-C',str(args.repo),'rev-parse','HEAD'],text=True).strip()
            if revision != DA2_REVISION: raise ValueError('DA2 checkout is not the audited revision')
            weights = args.checkpoint/'model.safetensors'
            if sha(weights) != DA2_WEIGHTS: raise ValueError('DA2 checkpoint checksum mismatch')
            # Import only the unchanged inference model, avoiding upstream app/PLY/CLI dependencies.
            sys.path.insert(0,str(args.repo.resolve()/'src/da2'))
            from model.spherevit import SphereViT
            config = json.loads((args.repo/'configs/infer.json').read_text())
            if (config['spherevit']['sphere']['width'],config['spherevit']['sphere']['height']) != rgb.size:
                raise ValueError('Input shape must match upstream sphere angular embedding configuration')
            model = SphereViT.from_pretrained(str(args.checkpoint.resolve()),config=config).to('mps').eval()
            report.update(repository='https://github.com/EnVision-Research/DA-2', codeRevision=revision,
                          modelId='haodongli/DA-2', checkpointRevision='0d55ccb5e46b8ed4715fae3a4c04fc897f1689f3',
                          checkpointSha256=DA2_WEIGHTS, checkpointBytes=weights.stat().st_size,
                          outputMeaning='Scale-invariant radial ray range, normalized by prediction 98th percentile; dimensionless, not metric',
                          convention='relative-ray-range', config=config)
            tensor=torch.from_numpy(np.array(rgb).transpose(2,0,1).copy()).float().unsqueeze(0).to('mps')/255
            report['networkInputSize']=list(rgb.size)
            infer=lambda: model(tensor)
        else:
            from transformers import pipeline
            model = pipeline('depth-estimation',model='depth-anything/Depth-Anything-V2-Small-hf',revision=DAV2_REVISION,device='mps')
            shape=model.image_processor(images=rgb,return_tensors='pt')['pixel_values'].shape
            report.update(modelId='depth-anything/Depth-Anything-V2-Small-hf',checkpointRevision=DAV2_REVISION,
                          outputMeaning='Relative inverse-depth-like prediction. Direct ERP input is out of distribution; inverse radial calibration is a tested hypothesis, not native camera-Z or metric depth',
                          convention='relative-inverse-depth-like',networkInputSize=[int(shape[-1]),int(shape[-2])])
            infer=lambda: model(rgb)['predicted_depth']
        torch.mps.synchronize()
        report['modelLoadSeconds']=time.monotonic()-loading; save()
        start=time.monotonic()
        with torch.inference_mode(): output=infer()
        torch.mps.synchronize()
        report['inferenceSeconds']=time.monotonic()-start
        depth=output.squeeze().detach().cpu().numpy().astype(np.float32)
        if depth.shape != (rgb.height,rgb.width) or not np.isfinite(depth).all() or np.ptp(depth)<=0:
            raise ValueError(f'Invalid prediction {depth.shape}')
        np.save(args.output/'raw.npy',depth)
        low,high=np.quantile(depth,[.02,.98]); visual=np.clip((depth-low)/(high-low),0,1)
        Image.fromarray((visual*255).astype(np.uint8)).save(args.output/'depth.png')
        report.update(status='PASS',predictionMin=float(depth.min()),predictionMax=float(depth.max()),
                      rawSha256=sha(args.output/'raw.npy'),visualPercentiles=[float(low),float(high)],
                      mpsCurrentAllocatedBytes=torch.mps.current_allocated_memory(),
                      mpsDriverAllocatedBytes=torch.mps.driver_allocated_memory())
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}'); traceback.print_exc(); raise
    finally:
        report.update(finishedAt=datetime.now(timezone.utc).isoformat(),elapsedSeconds=time.monotonic()-started,
                      maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        save()

if __name__ == '__main__': main()
