import { z } from 'zod';

const finiteNumber = z.number().finite();
const vector3 = z.tuple([finiteNumber, finiteNumber, finiteNumber]);
const nonBlank = z.string().refine((value) => value.trim().length > 0, 'Must not be blank');

// Plain filesystem-relative paths only. URL encoding is performed by URL(),
// rather than accepted here where it could conceal dot segments or separators.
export const relativePathSchema = nonBlank.refine((path) => (
  path === path.trim()
  && !/[\\?#%:]/u.test(path)
  && !Array.from(path).some((character) => {
    const code = character.charCodeAt(0);
    return code < 32 || code === 127;
  })
  && path.split('/').every((segment) => segment !== '' && segment !== '.' && segment !== '..')
), 'Use a plain relative file path without traversal, URL syntax, or control characters');

const provenanceUrl = nonBlank.refine((value) => {
  try {
    const url = new URL(value);
    return ['http:', 'https:', 'file:'].includes(url.protocol)
      && url.username === '' && url.password === '';
  } catch {
    return false;
  }
}, 'Use an absolute HTTP(S) or file URL without credentials');

const quaternion = z.tuple([finiteNumber, finiteNumber, finiteNumber, finiteNumber])
  .refine((value) => Math.abs(Math.hypot(...value) - 1) <= 0.00001,
    'Quaternion must be normalized (length within 0.00001 of 1)');

const cameraSchema = z.object({
  position: vector3,
  target: vector3,
  up: vector3,
  fov: finiteNumber.gt(0).lt(180),
  near: finiteNumber.positive(),
  far: finiteNumber.positive(),
}).strict().superRefine((camera, context) => {
  if (camera.far <= camera.near) {
    context.addIssue({ code: 'custom', path: ['far'], message: 'Far plane must exceed near plane' });
  }

  const direction = camera.target.map((value, index) => value - camera.position[index]!);
  const directionLength = Math.hypot(...direction);
  const upLength = Math.hypot(...camera.up);
  if (directionLength === 0 || !Number.isFinite(directionLength)) {
    context.addIssue({
      code: 'custom', path: ['target'], message: 'Camera position and target must define a finite nonzero direction',
    });
  }
  if (upLength === 0 || !Number.isFinite(upLength)) {
    context.addIssue({ code: 'custom', path: ['up'], message: 'Camera up must be a finite nonzero vector' });
  }
  if (directionLength > 0 && Number.isFinite(directionLength) && upLength > 0 && Number.isFinite(upLength)) {
    const [dx, dy, dz] = direction.map((value) => value / directionLength) as [number, number, number];
    const [ux, uy, uz] = camera.up.map((value) => value / upLength) as [number, number, number];
    const crossLength = Math.hypot(dy * uz - dz * uy, dz * ux - dx * uz, dx * uy - dy * ux);
    if (crossLength < 0.00000001) {
      context.addIssue({ code: 'custom', path: ['up'], message: 'Camera up must not be parallel to its viewing direction' });
    }
  }
});

const worldManifestSchema = z.object({
  schemaVersion: z.literal(1),
  id: nonBlank,
  title: nonBlank,
  assets: z.array(z.object({
    kind: z.literal('gaussian-splat'),
    format: z.enum(['ply', 'spz', 'splat', 'ksplat', 'sog']),
    path: relativePathSchema,
  }).strict()).length(1),
  coordinates: z.object({
    handedness: z.literal('right'),
    upAxis: z.literal('y'),
    unit: z.enum(['arbitrary', 'meters']),
    assetToWorld: z.object({
      position: vector3,
      quaternion,
      scale: finiteNumber.positive(),
    }).strict(),
  }).strict(),
  navigation: z.object({
    mode: z.enum(['orbit', 'camera-path']),
    camera: cameraSchema,
    camerasPath: relativePathSchema.optional(),
  }).strict().superRefine((navigation, context) => {
    if (navigation.mode === 'camera-path' && !navigation.camerasPath) {
      context.addIssue({ code: 'custom', path: ['camerasPath'], message: 'Camera-path mode requires camerasPath' });
    }
  }),
  // Archived field accepted for compatibility; no longer loaded or rendered.
  background: z.object({ path: relativePathSchema }).strict().optional(),
  streaming: z.object({ path: relativePathSchema }).strict().optional(),
  provenance: z.object({
    sourceType: z.enum(['images', 'video', 'sample']),
    sourceUrl: provenanceUrl,
    license: nonBlank,
    licenseUrl: provenanceUrl,
    attribution: nonBlank,
    backend: nonBlank,
    notes: nonBlank.optional(),
  }).strict(),
}).strict();

const point=z.tuple([z.number().finite(),z.number().finite(),z.number().finite()]);
const positive=z.number().int().positive();
const chunk=z.object({id:z.string().min(1),path:relativePathSchema,bytes:positive,splats:positive,sha256:z.string().regex(/^[a-f0-9]{64}$/),anchors:z.array(point).min(1)}).strict();
const schema=z.object({schemaVersion:z.literal(1),coordinateSpace:z.literal('viewer-world'),totalSplats:positive,maxResidentChunks:positive.max(8),chunks:z.array(chunk).min(1).max(256)}).strict().superRefine((v,c)=>{
  if(new Set(v.chunks.map(x=>x.id)).size!==v.chunks.length||new Set(v.chunks.map(x=>x.path)).size!==v.chunks.length||v.chunks.reduce((n,x)=>n+x.splats,0)!==v.totalSplats)
    c.addIssue({code:'custom',message:'Chunk identities must be unique and counts must partition the source'});
});
export type StreamIndex=z.infer<typeof schema>;
export const parseStreamIndex=(input:unknown):StreamIndex=>schema.parse(input);

export type WorldManifest = z.infer<typeof worldManifestSchema>;

/** Validate without guessing axes, poses, units, transforms, or missing fields. */
export function parseWorldManifest(input: unknown): WorldManifest {
  return worldManifestSchema.parse(input);
}

/** Resolve files beside their manifest, independent of the viewer's own URL. */
export function resolveAssetUrl(manifestUrl: string, path: string): string {
  const safePath = relativePathSchema.parse(path);
  const base = new URL(manifestUrl);
  if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password) {
    throw new Error('Manifest URL must use HTTP(S) without credentials');
  }
  return new URL(safePath, base).href;
}
