import { z } from 'zod';

const label = z.string().trim().min(1);
const plainString = z.string().refine(value => value === value.trim(), 'Do not include surrounding whitespace');
const slug = plainString.regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/u, 'Use a lowercase scene identifier');
const manifestPath = plainString.regex(/^\/worlds\/[a-z0-9]+(?:-[a-z0-9]+)*\/world\.json$/u,
  'Use a same-origin /worlds/<folder>/world.json path');
const thumbnailPath = plainString.regex(/^\/worlds\/[a-z0-9]+(?:-[a-z0-9]+)*\/preview\.jpg$/u,
  'Use a same-origin /worlds/<folder>/preview.jpg path');

const sceneSchema = z.object({
  id: slug,
  title: label,
  description: label,
  category: z.enum(['capture', 'reconstruction', 'sample', 'experiment']),
  manifestPath,
  thumbnailPath,
  detail: label,
}).strict().superRefine((scene, context) => {
  if (scene.manifestPath.split('/')[2] !== scene.thumbnailPath.split('/')[2]) {
    context.addIssue({ code: 'custom', path: ['thumbnailPath'], message: 'Preview must belong to the same world as its manifest' });
  }
});

const catalogSchema = z.object({
  version: z.literal(1),
  scenes: z.array(sceneSchema).min(1),
}).strict().superRefine((catalog, context) => {
  for (const field of ['id', 'manifestPath', 'thumbnailPath'] as const) {
    const values = new Set<string>();
    catalog.scenes.forEach((scene, index) => {
      if (values.has(scene[field])) {
        context.addIssue({ code: 'custom', path: ['scenes', index, field], message: `Duplicate scene ${field}` });
      }
      values.add(scene[field]);
    });
  }
});

export type CatalogScene = z.infer<typeof sceneSchema>;
export type SceneCatalog = z.infer<typeof catalogSchema>;

/** Public discovery metadata only; scene coordinates and provenance stay in world.json. */
export function parseSceneCatalog(input: unknown): SceneCatalog {
  return catalogSchema.parse(input);
}
