import { defineConfig, globalIgnores } from 'eslint/config';
import tseslint from 'typescript-eslint';

export default function createTypeScriptConfig({
  strict = false,
  project,
  tsconfigRootDir,
  rules = {},
} = {}) {
  const parserOptions = project ? { project, tsconfigRootDir } : {};
  const baseConfig = project
    ? strict
      ? tseslint.configs.strictTypeChecked
      : tseslint.configs.recommendedTypeChecked
    : strict
      ? tseslint.configs.strict
      : tseslint.configs.recommended;

  return defineConfig([
    globalIgnores(['**/dist/**', '**/node_modules/**', '**/.next/**']),
    ...baseConfig,
    {
      files: ['**/*.{ts,tsx,mts,cts}'],
      languageOptions: { parserOptions },
      rules,
    },
  ]);
}
