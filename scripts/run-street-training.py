#!/usr/bin/env python3
"""Run matched local Metal trials sequentially, preserving each failure/export."""
import argparse
from pathlib import Path
import subprocess
import time
import json
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('variants',nargs='+',choices=['sparse','dense','filtered','stereo','sphere']);p.add_argument('--steps',type=int,default=8000);p.add_argument('--suffix',default='');p.add_argument('--series-name',default='');a=p.parse_args()
    job=a.job.resolve();series=job/('training-series'+a.suffix+a.series_name+'.json')
    if series.exists():raise ValueError('Never overwrite a training series')
    report=dict(status='RUNNING',startedAt=datetime.now(timezone.utc).isoformat(),trials=[])
    def save():series.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        for variant in a.variants:
            name=variant+a.suffix;output=job/('training-'+name);command=[str(ROOT/'data/tools/venv/bin/python'),str(ROOT/'scripts/reconstruct.py'),str(job/'datasets'/variant),str(output),'--steps',str(a.steps),'--resolution','512','--max-splats','400000','--title','Street '+name,'--id','street-'+name]
            row=dict(variant=variant,id=name,status='RUNNING',command=command);report['trials'].append(row);save();before=time.monotonic();print('Starting',name,flush=True)
            with (job/('training-'+name+'.log')).open('x') as log:r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            row.update(status='PASS' if r.returncode==0 else 'FAIL',exitCode=r.returncode,elapsedSeconds=time.monotonic()-before);save();print(row['status'],name,flush=True)
        report['status']='PASS' if all(r['status']=='PASS' for r in report['trials']) else 'FAIL'
    finally:report['finishedAt']=datetime.now(timezone.utc).isoformat();save()
    if report['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
