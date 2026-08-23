import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: [
      'apps/{api,web,worker}/src/**/*.spec.ts',
      'packages/config/eslint/**/*.spec.js',
    ],
  },
});
