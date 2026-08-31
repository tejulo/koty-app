import { defineConfig } from 'vitest/config';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  root: fileURLToPath(new URL('./', import.meta.url)),
  test: {
    environment: 'node',
    include: ['test/integration/**/*.integration.spec.ts'],
    globalSetup: [
      'test/setup/global-setup.ts',
      'test/setup/global-teardown.ts',
    ],
    testTimeout: 60_000,
    hookTimeout: 120_000,
    env: {
      INTEGRATION_TEST: 'true',
    },
  },
});
