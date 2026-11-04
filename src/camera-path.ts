import { Matrix4, Quaternion, Vector3 } from 'three';
import { z } from 'zod';
import type { WorldManifest } from './world';

const number = z.number().finite();
const row = z.tuple([number, number, number, number]);
const nonBlank = z.string().trim().min(1);
const matrix = z.tuple([row, row, row, row]).superRefine((value, context) => {
  const rotation = new Matrix4().set(...value.flat() as Parameters<Matrix4['set']>);
  const columns = [0, 1, 2].map((index) => new Vector3().setFromMatrixColumn(rotation, index));
  const tolerance = 0.0001;
  const rigid = columns.every((column) => Math.abs(column.length() - 1) < tolerance)
    && Math.abs(columns[0].dot(columns[1])) < tolerance
    && Math.abs(columns[0].dot(columns[2])) < tolerance
    && Math.abs(columns[1].dot(columns[2])) < tolerance
    && Math.abs(rotation.determinant() - 1) < tolerance
    && value[3].every((entry, index) => Math.abs(entry - (index === 3 ? 1 : 0)) < tolerance);
  if (!rigid) context.addIssue({ code: 'custom', message: 'Camera matrix must be a right-handed rigid camera-to-world transform' });
});

const cameraFileSchema = z.object({
  schemaVersion: z.literal(1),
  cameraConvention: z.literal('OpenGL: +X right, +Y up, -Z forward'),
  worldConvention: z.enum(['right-handed Y-up, arbitrary units', 'right-handed Y-up, meters']),
  sequenceNotes: nonBlank.optional(),
  frames: z.array(z.object({
    image: nonBlank,
    cameraToWorld: matrix,
    continuousFromPrevious: z.boolean().optional(),
    componentId: nonBlank.optional(),
  }).strict()).min(1),
}).strict();

export interface PathPose {
  image: string;
  position: Vector3;
  quaternion: Quaternion;
  continuousFromPrevious?: boolean;
  componentId?: string;
}

export interface CameraPath {
  poses: PathPose[];
  sequenceNotes?: string;
}

/** Camera matrices already use world coordinates. Never apply assetToWorld twice. */
export function parseCameraPath(input: unknown, unit: WorldManifest['coordinates']['unit']): CameraPath {
  const file = cameraFileSchema.parse(input);
  const expected = unit === 'meters' ? 'right-handed Y-up, meters' : 'right-handed Y-up, arbitrary units';
  if (file.worldConvention !== expected) throw new Error('Camera units must match the world manifest');
  return {
    sequenceNotes: file.sequenceNotes,
    poses: file.frames.map((frame) => {
      const transform = new Matrix4().set(...frame.cameraToWorld.flat() as Parameters<Matrix4['set']>);
      return {
        image: frame.image,
        position: new Vector3().setFromMatrixPosition(transform),
        quaternion: new Quaternion().setFromRotationMatrix(transform).normalize(),
        continuousFromPrevious: frame.continuousFromPrevious,
        componentId: frame.componentId,
      };
    }),
  };
}

/** Gap before checkpoint `to`. An explicit marker is required to interpolate. */
export function cameraPathGap(path: CameraPath, to: number): string | null {
  const previous = path.poses[to - 1];
  const next = path.poses[to];
  if (!previous || !next) return 'End of camera sequence';
  if (previous.componentId && next.componentId && previous.componentId !== next.componentId) {
    return 'Different reconstruction components';
  }
  if (next.continuousFromPrevious !== true) return 'Continuity between these views is unverified';
  return null;
}

function clampCursor(path: CameraPath, cursor: number): number {
  if (!Number.isFinite(cursor)) throw new Error('Camera progress must be finite');
  return Math.max(0, Math.min(path.poses.length - 1, cursor));
}

/** Linear centers and shortest-arc orientation interpolation, only on marked edges. */
export function sampleCameraPath(path: CameraPath, cursor: number) {
  let value = clampCursor(path, cursor);
  const left = Math.floor(value);
  if (value !== left && cameraPathGap(path, left + 1)) value = left;
  const a = path.poses[Math.floor(value)];
  const b = path.poses[Math.min(Math.floor(value) + 1, path.poses.length - 1)];
  const fraction = value - Math.floor(value);
  return {
    cursor: value,
    position: new Vector3().lerpVectors(a.position, b.position, fraction),
    quaternion: new Quaternion().slerpQuaternions(a.quaternion, b.quaternion, fraction).normalize(),
    interpolated: fraction !== 0,
  };
}

/** Stop at the first unknown edge, even when one frame spans several checkpoints. */
export function advanceCameraPath(path: CameraPath, cursor: number, delta: number) {
  if (!Number.isFinite(delta)) throw new Error('Camera progress delta must be finite');
  let value = sampleCameraPath(path, cursor).cursor;
  const target = clampCursor(path, value + delta);
  const direction = Math.sign(delta);
  while (value !== target) {
    const next = direction > 0 ? Math.floor(value) + 1 : Math.ceil(value) - 1;
    const reason = cameraPathGap(path, direction > 0 ? next : next + 1);
    if (reason) return { cursor: value, stopped: true, reason };
    value = direction > 0 ? Math.min(next, target) : Math.max(next, target);
  }
  const stopped = direction > 0 ? value === path.poses.length - 1 : direction < 0 && value === 0;
  return { cursor: value, stopped, reason: stopped ? 'End of camera sequence' : null };
}
