import createTypeScriptConfig from '@koty-app/config/eslint';

export default [
  ...createTypeScriptConfig({
    strict: true,
    project: './tsconfig.json',
    tsconfigRootDir: import.meta.dirname,
  }),
  {
    ignores: [
      '**/*.spec.ts',
      '**/*.test.ts',
      'test/**',
      '**/dist/**',
      '**/node_modules/**',
      '**/.next/**',
    ],
  },
];
