#!/usr/bin/env python3
"""Estimate panorama world poses with fixed analytic pinhole-camera rigs on CPU.

Consumes prepare-panoramas.py output. Rig rotations/zero baseline describe crop
projection, not measured world poses. Upstream: https://colmap.github.io/rigs.html
and installed PyCOLMAP 4.2.1 panorama.py/create_pano_rig_config.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import shutil
import signal
import sys
import time
import traceback


def module(filename):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(filename.replace('-', '_'), path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


BASE = module('estimate-poses.py')
PREPARE = module('prepare-panoramas.py')


def validate_crops(manifest):
    import numpy as np
    if manifest.get('schemaVersion') != 1 or manifest.get('kind') != 'panorama-pinhole-crops':
        raise ValueError('Require a version 1 panorama-pinhole-crops manifest')
    intrinsic = manifest['intrinsics']
    if intrinsic.get('cameraModel') != 'PINHOLE':
        raise ValueError('Require PINHOLE crops')
    for key in ('width', 'height', 'fx', 'fy', 'cx', 'cy'):
        value = intrinsic.get(key)
        if not isinstance(value, (float, int)) or not np.isfinite(value) or value <= 0:
            raise ValueError(f'Invalid intrinsic {key}')
    if any(int(intrinsic[k]) != intrinsic[k] for k in ('width', 'height')):
        raise ValueError('Image dimensions must be integers')
    groups, names = {}, set()
    for crop in manifest['crops']:
        relative = Path(crop['file'])
        if relative.is_absolute() or len(relative.parts) != 2 or relative.parts[0] != 'images':
            raise ValueError('Crop path must be images/FILENAME')
        if crop['file'] in names:
            raise ValueError('Duplicate crop file')
        names.add(crop['file'])
        rotation = np.asarray(crop['relativeCameraToPanoramaRotation'], dtype=float)
        if rotation.shape != (3, 3) or not np.isfinite(rotation).all() or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-10):
            raise ValueError('Crop rotation must be finite orthonormal 3x3')
        if abs(np.linalg.det(rotation) - 1) > 1e-10:
            raise ValueError('Crop rotation must be right-handed')
        expected = PREPARE.crop_rotation(crop['yawDegrees'], crop['pitchDegrees'])
        if not np.allclose(rotation, expected, atol=1e-10):
            raise ValueError('Crop rotation contradicts declared yaw/pitch')
        groups.setdefault(crop['sourceId'], []).append(crop)
    if len(groups) < 3:
        raise ValueError('Require at least three physical panoramas')
    first = next(iter(groups.values()))
    if len(first) < 2:
        raise ValueError('Require at least two virtual cameras per panorama')
    keys = [(c['yawDegrees'], c['pitchDegrees']) for c in first]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate virtual camera orientation')
    ordered = []
    for source_id, crops in groups.items():
        by_view = {(c['yawDegrees'], c['pitchDegrees']): c for c in crops}
        if len(by_view) != len(crops) or set(by_view) != set(keys):
            raise ValueError('All panoramas must have the same complete virtual camera set')
        ordered.append((source_id, [by_view[key] for key in keys]))
    return intrinsic, ordered


def rig_config(pycolmap, rotations):
    import numpy as np
    reference = np.asarray(rotations[0])
    sensors = []
    for index, rotation in enumerate(rotations):
        cam_from_rig = None if index == 0 else pycolmap.Rigid3d(
            pycolmap.Rotation3d(np.asarray(rotation).T @ reference), np.zeros(3))
        sensors.append(pycolmap.RigConfigCamera(ref_sensor=index == 0,
                       image_prefix=f'view_{index:02d}/', cam_from_rig=cam_from_rig))
    return pycolmap.RigConfig(cameras=sensors)


def rig_checks(model, mapping, intrinsic):
    import numpy as np
    groups = {}
    intrinsics_error = 0.0
    for image in model.images.values():
        if not image.has_pose:
            continue
        entry = mapping[image.name]
        world_from_camera = image.cam_from_world().inverse().matrix()
        groups.setdefault(entry['sourceId'], []).append((entry, world_from_camera))
        actual = model.cameras[image.camera_id].calibration_matrix()
        expected = np.array([[intrinsic['fx'], 0, intrinsic['cx']], [0, intrinsic['fy'], intrinsic['cy']], [0, 0, 1]])
        intrinsics_error = max(intrinsics_error, float(np.max(np.abs(actual - expected))))
    center_error, rotation_error = 0.0, 0.0
    by_panorama = {}
    for source_id, views in groups.items():
        first_entry, first_pose = views[0]
        deviation = 0.0
        for entry, pose in views:
            deviation = max(deviation, float(np.linalg.norm(pose[:, 3] - first_pose[:, 3])))
            expected = np.asarray(entry['relativeCameraToPanoramaRotation']).T @ np.asarray(first_entry['relativeCameraToPanoramaRotation'])
            actual = pose[:, :3].T @ first_pose[:, :3]
            rotation_error = max(rotation_error, float(np.max(np.abs(actual - expected))))
        center_error = max(center_error, deviation)
        by_panorama[source_id] = {'registeredCrops': len(views), 'maxCenterDeviation': deviation,
                                 'estimatedCenter': first_pose[:, 3].tolist()}
    passed = bool(groups) and max(center_error, rotation_error, intrinsics_error) < 1e-7
    return {'status': 'PASS' if passed else 'FAIL', 'maxCenterDeviation': center_error,
            'maxRelativeRotationElementError': rotation_error, 'maxIntrinsicElementError': intrinsics_error,
            'units': 'arbitrary reconstruction scale; co-location is a mathematical rig constraint',
            'panoramas': by_panorama}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prepared', type=Path, help='prepare-panoramas.py output containing crops.json/images/')
    parser.add_argument('output', type=Path, help='New job directory')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--max-features', type=int, default=8192)
    args = parser.parse_args(argv)
    if args.threads < 1 or args.max_features < 128:
        parser.error('Require positive threads and at least 128 features')
    if args.output.exists() or args.output.is_symlink():
        parser.error('Output exists; prior evidence is never overwritten')
    args.prepared = args.prepared.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {'schemaVersion': 1, 'status': 'RUNNING', 'operation': 'CPU panorama rig SfM',
              'startedAt': datetime.now(timezone.utc).isoformat(), 'device': 'cpu',
              'providedWorldCameraPosesUsed': False, 'providedSparseGeometryUsed': False,
              'fixedAnalyticCropRig': True, 'fixedIntrinsics': True, 'stages': [],
              'rigConstraintCheck': {'status': 'NOT RUN'}, 'fullRegistration': 'NOT RUN',
              'source': str(args.prepared), 'browserRendering': 'NOT RUN'}
    code = 1
    def save():
        PREPARE.write_json(output / 'report.json', report)
    def stage(name, operation):
        record = {'name': name, 'status': 'RUNNING'}
        report['stages'].append(record)
        began = time.monotonic()
        save()
        try:
            result = operation()
            record['status'] = 'PASS'
            return result
        except BaseException as error:
            record.update(status='CANCELLED' if BASE.cancelled(error) else 'FAIL', error=str(error))
            raise
        finally:
            record['elapsedSeconds'] = time.monotonic() - began
            save()
    print(f'Panorama rig SfM; log: {output / "execution.log"}', flush=True)
    with BASE.native_log(output / 'execution.log'), BASE.cancellation_signals():
        try:
            save()
            import numpy as np
            import pycolmap
            report['pycolmapVersion'] = pycolmap.__version__
            manifest_bytes = (args.prepared / 'crops.json').read_bytes()
            report['sourceManifestSha256'] = hashlib.sha256(manifest_bytes).hexdigest()
            manifest = json.loads(manifest_bytes)
            intrinsic, groups = validate_crops(manifest)
            provenance = json.loads((args.prepared / 'provenance.json').read_text())
            PREPARE.validate_provenance(provenance)
            images = output / 'rig-images'
            images.mkdir()
            mapping = {}
            for pano_index, (source_id, crops) in enumerate(groups):
                for view_index, crop in enumerate(crops):
                    source = args.prepared / crop['file']
                    if source.is_symlink() or not source.is_file():
                        raise ValueError(f'Missing or symlink crop: {crop["file"]}')
                    data = source.read_bytes()
                    if hashlib.sha256(data).hexdigest() != crop['sha256']:
                        raise ValueError(f'Crop hash mismatch: {crop["file"]}')
                    name = f'view_{view_index:02d}/pano_{pano_index:06d}{source.suffix}'
                    (images / name).parent.mkdir(exist_ok=True)
                    (images / name).write_bytes(data)
                    mapping[name] = crop
            report.update(inputImages=[c['file'][7:] for c in manifest['crops']], inputPanoramas=len(groups),
                          virtualCamerasPerPanorama=len(groups[0][1]), intrinsic=intrinsic)
            PREPARE.write_json(output / 'rig-image-mapping.json', mapping)
            database, sparse = output / 'database.db', output / 'sparse'
            sparse.mkdir()
            params = ','.join(str(intrinsic[key]) for key in ('fx', 'fy', 'cx', 'cy'))
            stage('feature-extraction', lambda: pycolmap.extract_features(database, images,
                camera_mode=pycolmap.CameraMode.PER_FOLDER,
                reader_options=pycolmap.ImageReaderOptions(camera_model='PINHOLE', camera_params=params),
                extraction_options=pycolmap.FeatureExtractionOptions(use_gpu=False, num_threads=args.threads,
                    max_image_size=max(intrinsic['width'], intrinsic['height']),
                    sift={'max_num_features': args.max_features}), device=pycolmap.Device.cpu))
            config = rig_config(pycolmap, [crop['relativeCameraToPanoramaRotation'] for crop in groups[0][1]])
            def configure():
                with pycolmap.Database.open(database) as db:
                    pycolmap.apply_rig_config([config], db)
                    report['databaseRigs'] = db.num_rigs()
                    report['databaseFrames'] = db.num_frames()
            stage('configure-fixed-projection-rig', configure)
            stage('exhaustive-rig-matching', lambda: pycolmap.match_exhaustive(database,
                matching_options=pycolmap.FeatureMatchingOptions(use_gpu=False, num_threads=args.threads,
                    rig_verification=True, skip_image_pairs_in_same_frame=True), device=pycolmap.Device.cpu))
            report['matchingDiagnostics'] = BASE.database_diagnostics(database)
            options = pycolmap.IncrementalPipelineOptions(num_threads=args.threads, random_seed=0,
                ba_use_gpu=False, ba_refine_sensor_from_rig=False, ba_refine_focal_length=False,
                ba_refine_principal_point=False, ba_refine_extra_params=False, min_model_size=3)
            options.mapper.num_threads = args.threads
            options.mapper.abs_pose_refine_focal_length = False
            options.mapper.abs_pose_refine_extra_params = False
            models = stage('incremental-rig-mapping', lambda: pycolmap.incremental_mapping(database, images, sparse, options))
            if not models:
                report['fullRegistration'] = 'FAIL'
                raise RuntimeError('COLMAP produced no panorama rig reconstruction; no world poses exported')
            model_id, model = max(models.items(), key=lambda item: item[1].num_reg_images())
            report['rigConstraintCheck'] = rig_checks(model, mapping, intrinsic)
            if report['rigConstraintCheck']['status'] != 'PASS':
                raise RuntimeError('Reconstructed cameras violate fixed panorama rig constraints')
            registered = [image for image in model.images.values() if image.has_pose]
            names = sorted(mapping[image.name]['file'][7:] for image in registered)
            report.update(selectedModel=model_id, registeredImages=names,
                unregisteredImages=sorted(set(report['inputImages']) - set(names)),
                registrationCoverage=len(names)/len(mapping), fullRegistration='PASS' if len(names)==len(mapping) else 'FAIL',
                points3D=model.num_points3D(), meanReprojectionErrorPixels=model.compute_mean_reprojection_error(),
                models=[{'id': k, 'images': v.num_reg_images(), 'points3D': v.num_points3D()} for k,v in models.items()])
            dataset = output / 'dataset'
            (dataset / 'images').mkdir(parents=True)
            (dataset / 'sparse').mkdir()
            frames = []
            for image in sorted(registered, key=lambda im: im.name):
                crop = mapping[image.name]
                relative = crop['file']
                shutil.copyfile(args.prepared / relative, dataset / relative)
                camera = model.cameras[image.camera_id]
                matrix = np.eye(4)
                matrix[:3] = image.cam_from_world().inverse().matrix()
                matrix = matrix @ np.diag([1,-1,-1,1])
                k = camera.calibration_matrix()
                frames.append({'file_path': relative, 'w': camera.width, 'h': camera.height,
                    'fl_x': float(k[0,0]), 'fl_y': float(k[1,1]), 'cx': float(k[0,2]), 'cy': float(k[1,2]),
                    'transform_matrix': matrix.tolist()})
                image.name = relative[7:]
            model.write(dataset / 'sparse')
            model.export_PLY(dataset / 'init.ply')
            PREPARE.write_json(dataset / 'transforms.json', {'camera_model': 'PINHOLE', 'ply_file_path': 'init.ply', 'frames': frames})
            provenance['backend'] = f'PyCOLMAP {pycolmap.__version__} CPU fixed panorama-rig SfM'
            provenance['notes'] = provenance.get('notes','') + ' World poses and sparse geometry newly estimated from images. Crop camera orientations and co-location are constrained by analytic spherical projection; all world locations are estimated, gravity and metric scale unknown.'
            PREPARE.write_json(dataset / 'provenance.json', provenance)
            report.update(status='PASS', datasetPath=str(dataset))
            if len(names) != len(mapping):
                report['warning'] = 'Only largest registered component exported; partial coverage is not full reconstruction'
            code = 0
        except BaseException as error:
            report.update(status='CANCELLED' if BASE.cancelled(error) else 'FAIL', error=f'{type(error).__name__}: {error}')
            traceback.print_exc()
            if BASE.cancelled(error):
                code = 128 + getattr(error, 'signum', signal.SIGINT)
        finally:
            report['elapsedSeconds'] = time.monotonic() - started
            report['finishedAt'] = datetime.now(timezone.utc).isoformat()
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report['peakProcessRssBytes'] = int(rss if sys.platform == 'darwin' else rss * 1024)
            report['exitCode'] = code
            save()
    print(f'{report["status"]}: {output / "report.json"}')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
