import { dirname } from 'path';
import { fileURLToPath } from 'url';
import createTypeScriptConfig from '@koty-app/config/eslint';

const __dirname = dirname(fileURLToPath(import.meta.url));

export default [
  ...createTypeScriptConfig({
    strict: true,
    project: './tsconfig.json',
    tsconfigRootDir: __dirname,
  }),
  {
    ignores: ['**/*.spec.ts', '**/*.test.ts', '**/dist/**', '**/node_modules/**', '**/.next/**'],
  },
];
