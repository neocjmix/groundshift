import { describe, expect, it } from 'vitest';
import { nearestBackground, panoramaRay, parseBackground, parseBackgroundMesh } from './background';

const identity = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]];
const fixture = () => ({ schemaVersion: 1, views: [{ id: 'synthetic', center: [0, 0, 0], panoramaToWorld: identity, imagePath: 'images/synthetic.jpg', meshPath: 'shell.json' }] });

describe('presentation-only background contract (synthetic fixtures)', () => {
  it('keeps CVERP directions and longitude seam explicit', () => {
    expect(panoramaRay(.5, .5)).toEqual([0, -0, 1]);
    expect(panoramaRay(.75, .5)[0]).toBeCloseTo(1);
    expect(panoramaRay(.5, 0)[1]).toBeCloseTo(-1);
    expect(panoramaRay(.5, 1)[1]).toBeCloseTo(1);
    panoramaRay(0, .37).forEach((x, i) => expect(x).toBeCloseTo(panoramaRay(1, .37)[i]));
  });
  it('accepts declared pose and rejects reflection, wrong center, duplicate IDs and unknown fields', () => {
    expect(parseBackground(fixture()).views).toHaveLength(1);
    const reflected = fixture(); reflected.views[0].panoramaToWorld = [[-1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];
    expect(() => parseBackground(reflected)).toThrow('right-handed');
    const wrong = fixture(); wrong.views[0].center = [1,0,0]; expect(() => parseBackground(wrong)).toThrow('center');
    expect(() => parseBackground({ ...fixture(), views: [...fixture().views, ...fixture().views] })).toThrow('Duplicate');
    expect(() => parseBackground({ ...fixture(), inferredFloor: true })).toThrow();
  });
  it.each(['../private.jpg', '/private.jpg', 'https://example.com/photo.jpg', 'a/%2e.jpg', 'a\\b.jpg', 'a//b.jpg'])(
    'rejects unsafe nested background reference %s', path => {
      const f = fixture(); f.views[0].imagePath = path; expect(() => parseBackground(f)).toThrow();
      f.views[0].imagePath = 'safe.jpg'; f.views[0].meshPath = path; expect(() => parseBackground(f)).toThrow();
    });
  it('requires matching UV counts and bounded triangle indices', () => {
    const m = { schemaVersion: 1, positions: [0,0,0, 1,0,0, 0,1,0], uvs: [0,0, 1,0, 0,1], indices: [0,1,2] };
    expect(parseBackgroundMesh(m)).toEqual(m);
    expect(() => parseBackgroundMesh({ ...m, indices: [0,1,3] })).toThrow('triangle');
    expect(() => parseBackgroundMesh({ ...m, uvs: [0,0,1,0] })).toThrow();
    expect(() => parseBackgroundMesh({ ...m, positions: [NaN,...m.positions.slice(1)] })).toThrow();
  });
  it('selects nearest deterministically and suppresses midpoint flicker', () => {
    const a = parseBackground(fixture()).views[0], b = { ...a, id: 'other', center: [10,0,0] as [number,number,number] };
    expect(nearestBackground([a,b], [5,0,0])).toBe(0);
    expect(nearestBackground([a,b], [5.1,0,0], 0)).toBe(0);
    expect(nearestBackground([a,b], [6,0,0], 0)).toBe(1);
    expect(nearestBackground([a,b], [4.9,0,0], 1)).toBe(1);
  });
});
