import createTypeScriptConfig from '@koty-app/config/eslint';

export default createTypeScriptConfig({
  strict: true,
  tsconfigRootDir: import.meta.dirname,
  project: './tsconfig.json',
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/no-extraneous-class': 'off',
  },
});
