#!/usr/bin/env python3
"""Bounded alternative-model inference; raw depth semantics stay explicit.

Use the existing Torch environment. No upstream CLI/export services are loaded.
All checkpoints and code revisions must match the local research manifests.
"""
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

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data/jobs/street-conclusion-20261106'
GIT = '/Library/Developer/CommandLineTools/usr/bin/git'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''): h.update(block)
    return h.hexdigest()


def read(path): return json.loads(path.read_text())
def write(path, value): path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
def now(): return datetime.now(timezone.utc).isoformat()


def run(args):
    import numpy as np
    from PIL import Image
    import torch
    import torch.nn.functional as F
    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    report = dict(status='RUNNING', startedAt=now(), model=args.model, wrapperSha256=sha(Path(__file__)), device='mps',
                  precision='float32', cpuOperatorFallback=False, groups=[], images=[],
                  withheldRgb='Panorama5 never read; all-nine estimated poses remain shared geometry.')
    save = lambda: write(output / 'report.json', report)
    save()
    try:
        if not torch.backends.mps.is_available(): raise RuntimeError('MPS unavailable')
        torch.manual_seed(42)
        torch.set_num_threads(4)
        repo = ROOT / 'data/tools' / args.model
        if args.model == 'da2':
            revision = 'd659838585f2bc9967c7e9367af573795271dbbb'
            checkpoint = ROOT / 'data/tools/da2-checkpoint/model.safetensors'
            expected = 'd8ea568fc3dfb7d7432e5b763de499dd03fb6dc1c2020d84639f35e2dfa4f78e'
        else:
            revision = read(args.research / (args.model + '-source.json'))['revision']
            verified = read(ROOT / 'data/tools' / (args.model + '-checkpoint/verified.json'))
            checkpoint = ROOT / 'data/tools' / (args.model + '-checkpoint') / verified['file']
            expected = verified['sha256']
            report['checkpoint'] = verified
        actual = subprocess.check_output([GIT, '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != revision or sha(checkpoint) != expected: raise ValueError('Unverified code/checkpoint')
        report.update(codeRevision=revision, checkpointSha256=expected, checkpointBytes=checkpoint.stat().st_size)
        frames = read(BASE / 'inputs/transforms.json')['frames']
        if any(f['physicalPanorama'] == 5 for f in frames): raise ValueError('Withheld RGB leakage')
        centers = [4, 6] if args.smoke else [1, 2, 3, 4, 6, 7, 8, 9]
        frames = [f for f in frames if f['physicalPanorama'] in centers]
        report['physicalCenters'] = centers
        load_start = time.monotonic()
        if args.model in ('panda', 'da2'):
            if args.model == 'panda':
                sys.path.insert(0, str(repo))
                from networks.panda import make_model
                model = make_model(midas_model_type='vits', fine_tune_type='inference',
                                   max_depth=1., lora=True, train_decoder=True, lora_rank=4)
                weights = torch.load(checkpoint, map_location='cpu', weights_only=True)
                # Upstream checkpoint contains one training metadata key.
                report['ignoredCheckpointMetadata']={'epoch':str(weights.pop('epoch'))} if 'epoch' in weights else {}
                model.load_state_dict({k.removeprefix('module.'): v for k, v in weights.items()}, strict=True)
                model = model.to('mps').eval()
                meaning, size = 'affine-radial', (1008, 504)
            else:
                sys.path.insert(0, str(repo / 'src/da2'))
                from model.spherevit import SphereViT
                config = read(repo / 'configs/infer.json')
                model = SphereViT.from_pretrained(str(checkpoint.parent), config=config).to('mps').eval()
                meaning, size = 'scale-radial', (1092, 546)
            report.update(convention=meaning, workingSize=list(size))
            torch.mps.synchronize(); report['modelLoadSeconds'] = time.monotonic() - load_start; save()
            sources = sorted((ROOT / 'data/samples/mapillary-beijing/images').glob('*.jpg'))
            provenance = read(ROOT / 'scripts/samples/mapillary-beijing.json')['images']
            for p in centers:
                path = sources[p - 1]
                if sha(path) != provenance[p - 1]['sha256']: raise ValueError('Panorama source changed')
                rgb = np.array(Image.open(path).convert('RGB').resize(size, Image.Resampling.LANCZOS))
                before = time.monotonic()
                with torch.inference_mode():
                    if args.model == 'panda': raw = model.infer_image(rgb[:, :, ::-1].copy(), input_size=504)
                    else:
                        tensor = torch.from_numpy(rgb.transpose(2, 0, 1).copy()).float()[None].to('mps') / 255
                        raw = model(tensor).squeeze().cpu().numpy()
                torch.mps.synchronize()
                record = dict(id=f'p{p:02d}', physical=p, sourceSha256=sha(path), seconds=time.monotonic()-before)
                store_prediction(output, record, raw)
                report['images'].append(record); save()
        elif args.model == 'moge':
            sys.path.insert(0, str(repo))
            from moge.model.v2 import MoGeModel
            model = MoGeModel.from_pretrained(str(checkpoint)).to('mps').eval()
            report.update(convention='scale-camera-z', networkTokens=1600,
                          meaning='Model metric camera-Z estimate, rescaled to arbitrary SfM; no measured meters claim.')
            torch.mps.synchronize(); report['modelLoadSeconds'] = time.monotonic()-load_start; save()
            for frame in frames:
                path = BASE / 'inputs' / frame['file_path']
                rgb = np.array(Image.open(path).convert('RGB'))
                tensor = torch.from_numpy(rgb.transpose(2, 0, 1).copy()).float().to('mps')/255
                before = time.monotonic()
                result = model.infer(tensor, fov_x=90., num_tokens=1600, use_fp16=False, apply_mask=False)
                torch.mps.synchronize()
                raw = result['depth'].cpu().numpy()
                record = dict(id=path.stem, physical=frame['physicalPanorama'], sourceSha256=sha(path), seconds=time.monotonic()-before)
                store_prediction(output, record, raw)
                if 'mask' in result: np.save(output/(record['id']+'-model-mask.npy'), result['mask'].cpu().numpy())
                report['images'].append(record); save()
        elif args.model == 'da3':
            sys.path.insert(0, str(repo / 'src'))
            from depth_anything_3.cfg import create_object, load_config
            from safetensors.torch import load_file
            model = create_object(load_config(str(repo / 'src/depth_anything_3/configs/da3-small.yaml')))
            weights = load_file(str(checkpoint))
            weights={k.removeprefix('model.'):v for k,v in weights.items()}
            # HF safetensors omits aliases of the same Parameter. The upstream
            # auxiliary heads share one LayerNorm object. Restore aliases from
            # actual object identity, never initialize missing learned weights.
            aliases={}
            for name,param in model.named_parameters(remove_duplicate=False):aliases.setdefault(id(param),[]).append(name)
            restored=[]
            for names in aliases.values():
                present=[name for name in names if name in weights]
                if present:
                    for name in names:
                        if name not in weights:weights[name]=weights[present[0]];restored.append([name,present[0]])
            report['restoredSharedParameterAliases']=restored
            model.load_state_dict(weights, strict=True)
            model = model.to('mps').eval()
            report.update(convention='scale-camera-z', workingSize=[504,504],
                          conditioning='All available non5 physical centers, same ring/yaw per batch; real OpenCV w2c/K. Upstream relative-pose normalization. No predicted pose replacement.',
                          adapter='Unchanged core forward FP32; bypass optional CUDA Gaussian/export imports and API autocast.')
            torch.mps.synchronize(); report['modelLoadSeconds'] = time.monotonic()-load_start; save()
            for ring in ('level','down'):
                for yaw in range(0,360,60):
                    group = [f for f in frames if f['ring']==ring and f['yaw']==yaw]
                    arrays = [np.array(Image.open(BASE/'inputs'/f['file_path']).convert('RGB').resize((504,504),Image.Resampling.BICUBIC)) for f in group]
                    tensor = torch.from_numpy(np.stack(arrays).transpose(0,3,1,2).copy()).float()[None].to('mps')/255
                    tensor = (tensor-torch.tensor([.485,.456,.406],device='mps')[None,None,:,None,None])/torch.tensor([.229,.224,.225],device='mps')[None,None,:,None,None]
                    poses = np.array([np.array(f['transform_matrix'])@np.diag([1,-1,-1,1]) for f in group])
                    exts = np.linalg.inv(poses); exts = exts@np.linalg.inv(exts[:1])
                    distance = np.linalg.norm(np.linalg.inv(exts)[:,:3,3],axis=-1)
                    # torch.median uses the lower middle order statistic.
                    scale = max(float(np.sort(distance)[(len(distance)-1)//2]), .1)
                    exts[:,:3,3] /= scale
                    ext = torch.tensor(exts,dtype=torch.float32,device='mps')[None]
                    k = torch.tensor([[252,0,252],[0,252,252],[0,0,1]],dtype=torch.float32,device='mps')[None,None].repeat(1,len(group),1,1)
                    before = time.monotonic()
                    with torch.inference_mode(): result=model(tensor,ext,k,ref_view_strategy='first')
                    torch.mps.synchronize()
                    raw = F.interpolate(result['depth'].float().reshape(-1,1,504,504),size=(512,512),mode='bilinear',align_corners=False).squeeze(1).cpu().numpy()
                    gid=f'{ring}-{yaw:03d}'; report['groups'].append(dict(id=gid,seconds=time.monotonic()-before,centers=centers,poseNormalizationScale=scale))
                    for i,frame in enumerate(group):
                        path=BASE/'inputs'/frame['file_path'];record=dict(id=path.stem,physical=frame['physicalPanorama'],sourceSha256=sha(path),group=gid)
                        store_prediction(output,record,raw[i]);report['images'].append(record)
                    save()
        elif args.model == 'depthmaster':
            import ast
            sys.path.insert(0,str(repo))
            adaptation=read(args.research/'depthmaster-adaptation.json')
            if sha(ROOT/adaptation['file'])!=adaptation['afterSha256']:raise ValueError('Unrecorded device adaptation')
            report['deviceAdaptation']=adaptation
            from depthmaster.model import DepthMasterModel
            weights=torch.load(checkpoint,map_location='cpu',weights_only=True)
            model=DepthMasterModel(**weights['model_config'])
            model.load_state_dict(weights['model'],strict=True)
            del weights
            model=model.to('mps').eval()
            # Load the official projection helpers without importing the optional
            # benchmark datasets/evaluator. Model and projection code unchanged.
            source=repo/'eval_panorama/eval.py';tree=ast.parse(source.read_text())
            tree.body=[node for node in tree.body if not (isinstance(node,ast.ImportFrom) and node.module=='eval.utils.infer')]
            ns={'__file__':str(source),'__name__':'groundshift_depthmaster_projection'}
            exec(compile(tree,str(source),'exec'),ns)
            report.update(convention='scale-radial',workingSize=[1092,546],cubemapFaceSize=518,cubemapFov=95.,
                          projectionHelperSha256=sha(source),meaning='Official six-face joint spherical prediction; metric estimate subsequently aligned to arbitrary SfM, not measured meters.')
            torch.mps.synchronize();report['modelLoadSeconds']=time.monotonic()-load_start;save()
            sources=sorted((ROOT/'data/samples/mapillary-beijing/images').glob('*.jpg'))
            provenance=read(ROOT/'scripts/samples/mapillary-beijing.json')['images']
            for p in centers:
                path=sources[p-1]
                if sha(path)!=provenance[p-1]['sha256']:raise ValueError('Panorama changed')
                rgb=np.array(Image.open(path).convert('RGB').resize((1092,546),Image.Resampling.LANCZOS))
                tensor=torch.from_numpy(rgb.transpose(2,0,1).copy()).float()[None].to('mps')/255
                before=time.monotonic()
                with torch.inference_mode():
                    faces=ns['erp_to_cubemap_gpu'](tensor,face_w=518,fov_deg=95.)
                    w2c,k=ns['_get_camera_params_cached'](95.,518,torch.device('mps'),torch.float32)
                    result=model(faces,num_tokens=0,camera_type='Panorama',W2C=w2c[None],intrinsics=k[None])
                    points=result['pts3d'].float()*result['metric_scale'].float()[:,None,None,None]
                    ranges=torch.linalg.vector_norm(points.squeeze(0),dim=-1)
                    raw=ns['cubemap_to_erp_gpu'](ranges,pano_h=546,pano_w=1092,fov_deg=95.).cpu().numpy()
                torch.mps.synchronize()
                record=dict(id=f'p{p:02d}',physical=p,sourceSha256=sha(path),seconds=time.monotonic()-before)
                store_prediction(output,record,raw);report['images'].append(record);save()
        else: raise ValueError('Unsupported adapter; no silent model substitution')
        report['status']='PASS'
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc()
    finally:
        report.update(finishedAt=now(),elapsedSeconds=time.monotonic()-start,
                      maxResidentSetBytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        if torch.backends.mps.is_available():
            report.update(mpsCurrentAllocatedBytes=torch.mps.current_allocated_memory(),mpsDriverAllocatedBytes=torch.mps.driver_allocated_memory())
        save()
    print(report['status'],args.model,report.get('error',''),flush=True)
    return 0 if report['status']=='PASS' else 1


def store_prediction(output,record,raw):
    import numpy as np
    from PIL import Image
    raw=np.asarray(raw,np.float32)
    if raw.ndim!=2 or not np.isfinite(raw).all() or np.ptp(raw)<=0: raise ValueError('Invalid raw depth map')
    path=output/(record['id']+'.npy');np.save(path,raw)
    lo,hi=np.quantile(raw,[.02,.98]);Image.fromarray((np.clip((raw-lo)/(hi-lo),0,1)*255).astype(np.uint8)).save(output/(record['id']+'.png'))
    record.update(rawSha256=sha(path),size=list(raw.shape[::-1]),minimum=float(raw.min()),maximum=float(raw.max()))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('model',choices=['panda','da2','moge','da3','depthmaster']);p.add_argument('output',type=Path);p.add_argument('--research',type=Path,default=ROOT/'data/jobs/model-selection-20261106/research');p.add_argument('--smoke',action='store_true')
    args=p.parse_args()
    if args.model=='depthmaster':
        p.error('DepthMaster adoption is blocked by the unresolved migrated WorldMirror license chain; prior actual inference evidence is retained locally. No new execution.')
    raise SystemExit(run(args))
