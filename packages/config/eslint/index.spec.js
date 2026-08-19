import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { ESLint } from 'eslint';
import { describe, expect, it } from 'vitest';

import createTypeScriptConfig from './index.js';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

async function readPackageJson(relativePath) {
  return JSON.parse(await readFile(path.join(repoRoot, relativePath), 'utf8'));
}

async function calculateConfig(file, options = {}) {
  const eslint = new ESLint({
    overrideConfigFile: true,
    overrideConfig: createTypeScriptConfig(options),
  });

  return eslint.calculateConfigForFile(path.join(repoRoot, file));
}

describe('shared ESLint configuration', () => {
  it('pins a patched Vitest release and centralizes typescript-eslint', async () => {
    const rootPackage = await readPackageJson('package.json');
    const configPackage = await readPackageJson('packages/config/package.json');
    const consumers = await Promise.all([
      readPackageJson('apps/api/package.json'),
      readPackageJson('apps/worker/package.json'),
      readPackageJson('packages/contracts/package.json'),
    ]);

    expect(rootPackage.devDependencies.vitest).toBe('3.2.6');
    expect(configPackage.dependencies['typescript-eslint']).toBe('8.67.0');
    expect(configPackage.scripts.lint).toBe('eslint .');
    expect(
      consumers.every(
        (packageJson) => packageJson.devDependencies?.['typescript-eslint'] === undefined,
      ),
    ).toBe(true);
  });

  it.each(['ts', 'tsx', 'mts', 'cts'])('applies typed strict rules to .%s files', async (extension) => {
    const config = await calculateConfig(`fixture.${extension}`, {
      strict: true,
      project: './tsconfig.json',
      tsconfigRootDir: repoRoot,
    });

    expect(config.rules['@typescript-eslint/no-floating-promises'][0]).toBe(2);
    expect(config.rules['@typescript-eslint/no-unsafe-assignment'][0]).toBe(2);
    expect(config.rules['@typescript-eslint/no-unused-vars'][0]).toBe(2);
    expect(config.rules['@typescript-eslint/no-explicit-any'][0]).toBe(2);
  });
});
