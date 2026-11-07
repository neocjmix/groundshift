import { defineConfig } from 'vitest/config';

// Ignored data/ contains archived reproduction checkouts, not current tests.
export default defineConfig({
  test: { include: ['src/**/*.test.ts', 'build/**/*.test.ts', 'scripts/tests/*.test.mjs'] },
});
