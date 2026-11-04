import { describe, expect, it } from 'vitest';
import { Matrix4, Quaternion, Vector3 } from 'three';
import { advanceCameraPath, cameraPathGap, parseCameraPath, sampleCameraPath } from './camera-path';

// Synthetic mathematical cases only; these are not recovered scene poses.
function frame(x: number, yaw = 0, continuousFromPrevious?: boolean, componentId?: string) {
  const transform = new Matrix4().compose(new Vector3(x, 2, 3),
    new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), yaw), new Vector3(1, 1, 1));
  return {
    image: `synthetic-${x}.png`, continuousFromPrevious, componentId,
    cameraToWorld: [0, 1, 2, 3].map((row) => [0, 1, 2, 3].map((column) => transform.elements[column * 4 + row])),
  };
}

function file(frames = [frame(0), frame(2, Math.PI / 2, true), frame(4, Math.PI, true)]) {
  return {
    schemaVersion: 1,
    cameraConvention: 'OpenGL: +X right, +Y up, -Z forward',
    worldConvention: 'right-handed Y-up, arbitrary units',
    frames,
  };
}

describe('recorded camera metadata', () => {
  it('retains row-major world translation and OpenGL negative-Z forward', () => {
    const path = parseCameraPath(file(), 'arbitrary');
    expect(path.poses[1].position.toArray()).toEqual([2, 2, 3]);
    const forward = new Vector3(0, 0, -1).applyQuaternion(path.poses[1].quaternion);
    expect(forward.x).toBeCloseTo(-1, 12);
    expect(forward.y).toBeCloseTo(0, 12);
    expect(forward.z).toBeCloseTo(0, 12);
    expect(new Vector3(0, 1, 0).applyQuaternion(path.poses[1].quaternion).toArray()).toEqual([0, 1, 0]);
  });

  it('supports legacy camera files without asserting continuity', () => {
    const path = parseCameraPath(file([frame(0), frame(2)]), 'arbitrary');
    expect(cameraPathGap(path, 1)).toMatch(/unverified/);
    expect(sampleCameraPath(path, 0.5).cursor).toBe(0);
  });

  it('retains sequence evidence and permits a single checkpoint', () => {
    const path = parseCameraPath({ ...file([frame(0)]), sequenceNotes: 'Synthetic parser test' }, 'arbitrary');
    expect(path.sequenceNotes).toBe('Synthetic parser test');
    expect(advanceCameraPath(path, 0, 1)).toMatchObject({ cursor: 0, stopped: true });
  });

  it.each(['OpenCV: +Z forward', '', undefined])('rejects unconverted camera conventions: %s', (cameraConvention) => {
    expect(() => parseCameraPath({ ...file(), cameraConvention }, 'arbitrary')).toThrow();
  });

  it('requires matching explicit world units', () => {
    expect(() => parseCameraPath(file(), 'meters')).toThrow('units');
    expect(() => parseCameraPath({ ...file(), worldConvention: 'right-handed Y-up, meters' }, 'meters')).not.toThrow();
  });

  it.each([
    { name: 'scale', change: (rows: number[][]) => { rows[0][0] = 2; } },
    { name: 'shear', change: (rows: number[][]) => { rows[0][1] = 0.2; } },
    { name: 'reflection', change: (rows: number[][]) => { rows[0][0] = -1; } },
    { name: 'projective row', change: (rows: number[][]) => { rows[3][0] = 0.1; } },
    { name: 'nonfinite translation', change: (rows: number[][]) => { rows[0][3] = Infinity; } },
    { name: 'NaN rotation', change: (rows: number[][]) => { rows[0][0] = NaN; } },
  ])('rejects $name', ({ change }) => {
    const input = file();
    change(input.frames[0].cameraToWorld);
    expect(() => parseCameraPath(input, 'arbitrary')).toThrow();
  });

  it('rejects empty frames and unsupported metadata versions', () => {
    expect(() => parseCameraPath(file([]), 'arbitrary')).toThrow();
    expect(() => parseCameraPath({ ...file(), schemaVersion: 2 }, 'arbitrary')).toThrow();
  });
});

describe('bounded camera interpolation', () => {
  const path = parseCameraPath(file(), 'arbitrary');

  it('preserves both measured endpoints and clamps outside the sequence', () => {
    for (const [cursor, expected] of [[-5, 0], [0, 0], [2, 2], [99, 2]]) {
      const sample = sampleCameraPath(path, cursor);
      expect(sample.cursor).toBe(expected);
      expect(sample.position.toArray()).toEqual(path.poses[expected].position.toArray());
      expect(Math.abs(sample.quaternion.dot(path.poses[expected].quaternion))).toBeCloseTo(1, 12);
      expect(sample.interpolated).toBe(false);
    }
  });

  it('interpolates centers linearly and orientation as a normalized shortest arc', () => {
    const sample = sampleCameraPath(path, 0.5);
    expect(sample.position.toArray()).toEqual([1, 2, 3]);
    const forward = new Vector3(0, 0, -1).applyQuaternion(sample.quaternion);
    expect(forward.x).toBeCloseTo(-Math.SQRT1_2, 12);
    expect(forward.z).toBeCloseTo(-Math.SQRT1_2, 12);
    expect(sample.quaternion.length()).toBeCloseTo(1, 12);
    expect(sample.interpolated).toBe(true);
  });

  it('crosses the 180-degree seam without rotating through zero', () => {
    const seam = parseCameraPath(file([frame(0, Math.PI * 170 / 180), frame(2, -Math.PI * 170 / 180, true)]), 'arbitrary');
    const forward = new Vector3(0, 0, -1).applyQuaternion(sampleCameraPath(seam, 0.5).quaternion);
    expect(forward.z).toBeCloseTo(1, 12);
    expect(forward.x).toBeCloseTo(0, 12);
  });

  it('always blocks different explicit components, despite a continuity claim', () => {
    const disconnected = parseCameraPath(file([frame(0, 0, false, 'a'), frame(2, 0, true, 'b')]), 'arbitrary');
    expect(cameraPathGap(disconnected, 1)).toMatch(/Different reconstruction components/);
    expect(sampleCameraPath(disconnected, 0.5).cursor).toBe(0);
  });

  it.each([undefined, false])('stops before an unverified edge in either direction: %s', (continuity) => {
    const gapped = parseCameraPath(file([frame(0), frame(1, 0, true), frame(2, 0, continuity), frame(3, 0, true)]), 'arbitrary');
    expect(advanceCameraPath(gapped, 0.4, 100)).toMatchObject({ cursor: 1, stopped: true, reason: expect.stringMatching(/unverified/) });
    expect(advanceCameraPath(gapped, 2.7, -100)).toMatchObject({ cursor: 2, stopped: true });
    // Explicit checkpoint jumps remain possible; no interpolation is fabricated.
    expect(sampleCameraPath(gapped, 2).position.x).toBe(2);
  });

  it('advances in both directions and stops exactly at endpoints', () => {
    expect(advanceCameraPath(path, 0.3, 0.5)).toMatchObject({ cursor: 0.8, stopped: false });
    expect(advanceCameraPath(path, 1.5, -0.5)).toMatchObject({ cursor: 1, stopped: false });
    expect(advanceCameraPath(path, 1.5, 5)).toMatchObject({ cursor: 2, stopped: true });
    expect(advanceCameraPath(path, 0.3, -5)).toMatchObject({ cursor: 0, stopped: true });
  });

  it('rejects nonfinite playback input', () => {
    expect(() => sampleCameraPath(path, NaN)).toThrow();
    expect(() => advanceCameraPath(path, 0, Infinity)).toThrow();
  });
});
