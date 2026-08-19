import { defineConfig } from 'eslint/config';
import createTypeScriptConfig from '@koty-app/config/eslint';

export default defineConfig([
  ...createTypeScriptConfig({
    strict: true,
    tsconfigRootDir: import.meta.dirname,
    project: './tsconfig.eslint.json',
  }),
  {
    files: ['src/**/*.spec.ts'],
    rules: {
      // Vitest spies intentionally reference mocked object methods without their receiver.
      '@typescript-eslint/unbound-method': 'off',
    },
  },
]);
