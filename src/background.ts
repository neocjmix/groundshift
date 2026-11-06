import { Matrix4, Vector3 } from 'three';
import { z } from 'zod';
import { relativePathSchema } from './world.ts';

const n = z.number().finite();
const v3 = z.tuple([n, n, n]);
const row = z.tuple([n, n, n, n]);
const rigid = z.tuple([row, row, row, row]).superRefine((rows, context) => {
  const m = new Matrix4().set(...rows.flat() as Parameters<Matrix4['set']>);
  const cols = [0, 1, 2].map(i => new Vector3().setFromMatrixColumn(m, i));
  if (!cols.every(c => Math.abs(c.length() - 1) < 1e-4)
    || Math.abs(cols[0].dot(cols[1])) > 1e-4 || Math.abs(cols[0].dot(cols[2])) > 1e-4
    || Math.abs(cols[1].dot(cols[2])) > 1e-4 || Math.abs(m.determinant() - 1) > 1e-4
    || !rows[3].every((x, i) => Math.abs(x - (i === 3 ? 1 : 0)) < 1e-4)) {
    context.addIssue({ code: 'custom', message: 'Background pose must be a right-handed rigid panorama-to-world transform' });
  }
});
const view = z.object({
  id: z.string().trim().min(1), center: v3, panoramaToWorld: rigid,
  imagePath: relativePathSchema, meshPath: relativePathSchema.optional(),
}).strict().superRefine((v, context) => {
  if (v.center.some((x, i) => Math.abs(x - v.panoramaToWorld[i][3]) > 1e-4)) {
    context.addIssue({ code: 'custom', message: 'Background center must match pose translation' });
  }
});
const schema = z.object({
  schemaVersion: z.literal(1),
  views: z.array(view).min(1).max(64),
  notes: z.string().trim().min(1).optional(),
}).strict().superRefine((s, context) => {
  if (new Set(s.views.map(v => v.id)).size !== s.views.length) context.addIssue({ code: 'custom', message: 'Duplicate background view' });
});
export type BackgroundManifest = z.infer<typeof schema>;
export type BackgroundView = BackgroundManifest['views'][number];
export type LoadedBackgroundView = BackgroundView & { imageUrl: string; meshUrl?: string };
export type LoadedBackground = { views: LoadedBackgroundView[]; notes?: string };
export type BackgroundMode = 'gs' | 'panorama' | 'depth-shell';
export const parseBackground = (input: unknown): BackgroundManifest => schema.parse(input);

const mesh = z.object({
  schemaVersion: z.literal(1),
  positions: z.array(n).min(9).max(1200000),
  uvs: z.array(n.min(0).max(2)).min(6).max(800000),
  indices: z.array(z.number().int().nonnegative()).min(3).max(2400000),
}).strict().superRefine((m, context) => {
  const count = m.positions.length / 3;
  if (!Number.isInteger(count) || m.uvs.length !== count * 2 || m.indices.length % 3 || m.indices.some(i => i >= count) || m.uvs.some((v, i) => i % 2 === 1 && v > 1)) {
    context.addIssue({ code: 'custom', message: 'Background mesh needs matching finite positions/UVs and valid triangle indices' });
  }
});
export const parseBackgroundMesh = (input: unknown) => mesh.parse(input);

/** Existing CVERP convention: +X right, +Y down, +Z center; v grows down. */
export function panoramaRay(u: number, v: number): [number, number, number] {
  const lon = (u - .5) * 2 * Math.PI, lat = (.5 - v) * Math.PI;
  return [Math.cos(lat) * Math.sin(lon), -Math.sin(lat), Math.cos(lat) * Math.cos(lon)];
}

/** Retain a source until another is 15% nearer; deterministic tie/first selection. */
export function nearestBackground(views: BackgroundView[], position: readonly number[], current = -1): number {
  if (!views.length) throw new Error('Background has no views');
  const distance = (v: BackgroundView) => Math.hypot(...v.center.map((x, i) => x - position[i]));
  let best = 0;
  for (let i = 1; i < views.length; i++) if (distance(views[i]) < distance(views[best])) best = i;
  return current >= 0 && current < views.length && distance(views[best]) >= distance(views[current]) * .85 ? current : best;
}
