import { defineConfig } from '@playwright/test';
// Pure TypeScript unit tests; no browser or application fixture is started.
export default defineConfig({ testDir: './unit', workers: 1, retries: 0, reporter: 'list' });
