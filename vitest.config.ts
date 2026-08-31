import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: [
      'apps/{api,web,worker}/src/**/*.spec.ts',
      'packages/config/eslint/**/*.spec.js',
    ],
    exclude: [
      'apps/api/src/common/**/*.spec.ts',
      'apps/api/src/health/**/*.spec.ts',
      'apps/api/src/**/*.integration.spec.ts',
      'apps/api/test/**',
      '**/node_modules/**',
      '**/dist/**',
    ],
  },
});