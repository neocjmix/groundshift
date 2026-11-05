#!/usr/bin/env python3
"""Register generated views around fixed, image-estimated original cameras.

Reuses matching features, remaps the nine-image seed to database IDs, and resumes
CPU COLMAP mapping. Original poses are fixed; synthetic poses remain estimated.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time
import traceback

import numpy as np
import pycolmap


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('job',type=Path);args=parser.parse_args();job=args.job
    out=job/'poses';out.mkdir(exist_ok=False);started=time.monotonic()
    report=dict(status='RUNNING',startedAt=datetime.now(timezone.utc).isoformat(),method='Fixed original-image SfM seed; synthetic cameras registered from feature observations',fixedOriginalCameras=9)
    try:
        db=out/'database.db';shutil.copyfile(job/'poses-unanchored/database.db',db)
        seed=out/'seed';seed.mkdir();model=pycolmap.Reconstruction(job/'poses-real/dataset/sparse');model.write_text(seed)
        with pycolmap.Database.open(db) as database:
            by_name={im.name:im for im in database.read_all_images()}
            mapping={im.image_id:by_name[im.name].image_id for im in model.images.values()}
            for im in model.images.values():
                keypoints=database.read_keypoints(mapping[im.image_id])[:,:2]
                old=np.array([p.xy for p in im.points2D])
                if keypoints.shape!=old.shape or not np.allclose(keypoints,old,atol=1e-4):
                    raise RuntimeError('Original keypoint ordering changed; cannot reuse seed tracks')
        lines=(seed/'images.txt').read_text().splitlines();actual=0
        for i,line in enumerate(lines):
            if line.startswith('#'):continue
            if actual%2==0:
                parts=line.split();parts[0]=str(mapping[int(parts[0])]);lines[i]=' '.join(parts)
            actual+=1
        (seed/'images.txt').write_text('\n'.join(lines)+'\n')
        lines=(seed/'points3D.txt').read_text().splitlines()
        for i,line in enumerate(lines):
            if not line or line.startswith('#'):continue
            parts=line.split()
            for j in range(8,len(parts),2):parts[j]=str(mapping[int(parts[j])])
            lines[i]=' '.join(parts)
        (seed/'points3D.txt').write_text('\n'.join(lines)+'\n')
        lines=(seed/'frames.txt').read_text().splitlines()
        for i,line in enumerate(lines):
            if not line or line.startswith('#'):continue
            parts=line.split();parts[0]=str(mapping[int(parts[0])]);parts[-1]=str(mapping[int(parts[-1])]);lines[i]=' '.join(parts)
        (seed/'frames.txt').write_text('\n'.join(lines)+'\n')
        pycolmap.match_exhaustive(db,matching_options=pycolmap.FeatureMatchingOptions({'num_threads':4,'use_gpu':False,'guided_matching':True}),device=pycolmap.Device.cpu)
        options=pycolmap.IncrementalPipelineOptions({'num_threads':4,'random_seed':42,'multiple_models':False,'fix_existing_frames':True,'ba_refine_focal_length':False,'ba_refine_principal_point':False,'ba_refine_extra_params':False,'ba_refine_sensor_from_rig':False})
        options.mapper.abs_pose_refine_focal_length=False;options.mapper.abs_pose_refine_extra_params=False
        options.mapper.fix_existing_frames=True
        sparse=out/'sparse';sparse.mkdir()
        models=pycolmap.incremental_mapping(db,job/'augmented/images',sparse,options,input_path=seed)
        if not models:raise RuntimeError('No seeded reconstruction exported')
        model=max(models.values(),key=lambda m:m.num_reg_images())
        dataset=out/'dataset';(dataset/'images').mkdir(parents=True);(dataset/'sparse').mkdir()
        frames=[]
        for im in sorted(model.images.values(),key=lambda im:im.name):
            if not im.has_pose:continue
            cam=model.cameras[im.camera_id];K=cam.calibration_matrix();matrix=np.eye(4);matrix[:3]=im.cam_from_world().inverse().matrix();matrix=matrix@np.diag([1,-1,-1,1])
            frames.append(dict(file_path='images/'+im.name,w=cam.width,h=cam.height,fl_x=float(K[0,0]),fl_y=float(K[1,1]),cx=float(K[0,2]),cy=float(K[1,2]),transform_matrix=matrix.tolist()))
            shutil.copyfile(job/'augmented/images'/im.name,dataset/'images'/im.name)
        model.write(dataset/'sparse');model.export_PLY(dataset/'init.ply')
        (dataset/'transforms.json').write_text(json.dumps(dict(camera_model='PINHOLE',ply_file_path='init.ply',frames=frames),indent=2)+'\n')
        shutil.copyfile(job/'augmented/provenance.json',dataset/'provenance.json')
        report.update(status='PASS',registeredImages=[Path(f['file_path']).name for f in frames],unregisteredImages=sorted(set(by_name)-{Path(f['file_path']).name for f in frames}),points3D=model.num_points3D())
    except Exception as error:
        report.update(status='FAIL',error=f'{type(error).__name__}: {error}');traceback.print_exc();raise
    finally:
        report.update(elapsedSeconds=time.monotonic()-started,finishedAt=datetime.now(timezone.utc).isoformat());(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
