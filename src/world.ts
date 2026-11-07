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
const similarity = z.object({position:vector3,quaternion,scale:finiteNumber.positive()}).strict();
const pagingBudget = {maxPagedSplats:z.number().int().min(65536).max(2097152).refine(n=>n%65536===0),lodSplatCount:z.number().int().positive()};

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
  paging: z.object({path:relativePathSchema,maxPagedSplats:z.number().int().min(65536).max(2097152).refine(n=>n%65536===0),lodSplatCount:z.number().int().positive()}).strict().optional(),
  route:z.object({path:relativePathSchema,...pagingBudget}).strict().optional(),
  provenance: z.object({
    sourceType: z.enum(['images', 'video', 'sample']),
    sourceUrl: provenanceUrl,
    license: nonBlank,
    licenseUrl: provenanceUrl,
    attribution: nonBlank,
    backend: nonBlank,
    notes: nonBlank.optional(),
  }).strict(),
}).strict().superRefine((value,context)=>{
  if(value.route&&(value.paging||value.streaming))context.addIssue({code:'custom',path:['route'],message:'Route delivery cannot also use single-world paging or partition streaming'});
  const budget=value.route??value.paging;
  if(budget&&budget.lodSplatCount>budget.maxPagedSplats)context.addIssue({code:'custom',message:'Selection budget must fit the page pool'});
});

const point=z.tuple([z.number().finite(),z.number().finite(),z.number().finite()]);
const positive=z.number().int().positive();
const chunk=z.object({id:z.string().min(1),path:relativePathSchema,bytes:positive,splats:positive,sha256:z.string().regex(/^[a-f0-9]{64}$/),anchors:z.array(point).min(1)}).strict();
const schema=z.object({schemaVersion:z.literal(1),coordinateSpace:z.literal('viewer-world'),totalSplats:positive,maxResidentChunks:positive.max(8),chunks:z.array(chunk).min(1).max(256)}).strict().superRefine((v,c)=>{
  if(new Set(v.chunks.map(x=>x.id)).size!==v.chunks.length||new Set(v.chunks.map(x=>x.path)).size!==v.chunks.length||v.chunks.reduce((n,x)=>n+x.splats,0)!==v.totalSplats)
    c.addIssue({code:'custom',message:'Chunk identities must be unique and counts must partition the source'});
});
export type StreamIndex=z.infer<typeof schema>;
export const parseStreamIndex=(input:unknown):StreamIndex=>schema.parse(input);
const pagedIndex=z.object({schemaVersion:z.literal(1),kind:z.literal('spark-rad'),root:relativePathSchema,sourceSplats:positive,files:z.array(z.object({path:relativePathSchema,bytes:positive,sha256:z.string().regex(/^[a-f0-9]{64}$/)}).strict()).min(1).max(2048)}).strict().superRefine((v,c)=>{if(new Set(v.files.map(f=>f.path)).size!==v.files.length||!v.files.some(f=>f.path===v.root))c.addIssue({code:'custom',message:'RAD files must be unique and include the root'});});
export type PagedIndex=z.infer<typeof pagedIndex>;
export const parsePagedIndex=(input:unknown):PagedIndex=>pagedIndex.parse(input);

// Independently reconstructed worlds, not unique-ownership partitions of one GS.
const routeIndex=z.object({schemaVersion:z.literal(1),coordinateSpace:z.literal('viewer-world'),
  segments:z.array(z.object({id:nonBlank,world:relativePathSchema,transform:similarity,anchors:z.array(vector3).min(1).max(2048)}).strict()).min(1).max(128),
}).strict().superRefine((value,context)=>{
  if(new Set(value.segments.map(s=>s.id)).size!==value.segments.length||new Set(value.segments.map(s=>s.world)).size!==value.segments.length)
    context.addIssue({code:'custom',message:'Route segment identities and world paths must be unique'});
});
export type RouteIndex=z.infer<typeof routeIndex>;
export type RouteSegment=RouteIndex['segments'][number];
export const parseRouteIndex=(input:unknown):RouteIndex=>routeIndex.parse(input);

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
