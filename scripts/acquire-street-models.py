#!/usr/bin/env python3
"""Acquire only selected pinned public research code/weights, with SHA checks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
GIT='/Library/Developer/CommandLineTools/usr/bin/git'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def acquire(model,research,manifest):
    if model.get('adoptionStatus')=='BLOCKED':raise ValueError(model['reason'])
    ident=model['id'];repo=ROOT/'data/tools'/ident;revision=model['codeRevision']
    if not repo.exists():
        subprocess.run([GIT,'clone','--no-checkout','--filter=blob:none',model['repository'],str(repo)],check=True)
        subprocess.run([GIT,'-C',str(repo),'checkout','--detach',revision],check=True)
    if subprocess.check_output([GIT,'-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=revision:
        raise ValueError('Existing code revision differs; preserve it and select a separate checkout')
    source=research/(ident+'-source.json')
    if not source.exists():source.write_text(json.dumps(dict(repository=model['repository'].removeprefix('https://github.com/'),revision=revision),indent=2)+'\n')
    checkpoint=model['checkpoint'];dest=ROOT/'data/tools'/(ident+'-checkpoint');dest.mkdir(exist_ok=True)
    path=dest/checkpoint['file'];started=time.monotonic()
    if not path.exists():
        url=f'https://huggingface.co/{checkpoint["model"]}/resolve/{checkpoint["revision"]}/{checkpoint["file"]}'
        temporary=path.with_suffix(path.suffix+'.partial')
        with urllib.request.urlopen(url,timeout=120) as source,temporary.open('xb') as target:
            while block:=source.read(1048576):target.write(block)
        if temporary.stat().st_size!=checkpoint['bytes'] or sha(temporary)!=checkpoint['sha256']:
            raise ValueError('Checkpoint mismatch; failed partial retained')
        temporary.rename(path)
    if path.stat().st_size!=checkpoint['bytes'] or sha(path)!=checkpoint['sha256']:raise ValueError('Existing checkpoint changed')
    verified=dest/'verified.json'
    if not verified.exists():verified.write_text(json.dumps({**checkpoint,'seconds':time.monotonic()-started},indent=2)+'\n')
    if ident=='depthmaster':
        adaptation=manifest['depthmasterMpsAdaptation'];p=ROOT/adaptation['file']
        if sha(p)==adaptation['beforeSha256']:
            text=p.read_text().replace('from flash_attn.flash_attn_interface import flash_attn_func','try:\n    from flash_attn.flash_attn_interface import flash_attn_func\nexcept ImportError:\n    flash_attn_func = None').replace('if q.dtype == torch.bfloat16 or q.dtype == torch.float16:','if flash_attn_func is not None and q.device.type == "cuda" and q.dtype in (torch.bfloat16, torch.float16):')
            if hashlib.sha256(text.encode()).hexdigest()!=adaptation['afterSha256']:raise ValueError('Adaptation mismatch')
            p.write_text(text)
        if sha(p)!=adaptation['afterSha256']:raise ValueError('Unrecognized local model edit')
        evidence=research/'depthmaster-adaptation.json'
        if not evidence.exists():evidence.write_text(json.dumps(adaptation,indent=2)+'\n')
    print(ident,'verified',checkpoint['bytes'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('models',nargs='+',choices=['panda','da3','moge','depthmaster']);p.add_argument('--research',type=Path,required=True);a=p.parse_args()
    manifest=json.loads((ROOT/'scripts/samples/street-models.json').read_text());a.research.mkdir(parents=True,exist_ok=True)
    for name in a.models:acquire(next(m for m in manifest['models'] if m['id']==name),a.research,manifest)
