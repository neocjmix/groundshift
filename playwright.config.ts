import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  testMatch: '**/*.pw.mjs',
  workers: 1,
  timeout: process.env.GS_BASE_URL ? 180_000 : 60_000,
  use: {
    channel: 'chrome',
    headless: process.env.HEADLESS === '1',
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
    baseURL: process.env.GS_BASE_URL || 'http://127.0.0.1:4318',
    trace: 'retain-on-failure',
  },
  webServer: process.env.GS_BASE_URL ? undefined : {
    command: 'npm run preview -- --port 4318',
    url: 'http://127.0.0.1:4318',
    reuseExistingServer: false,
  },
});
