import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const repositoryRoot = resolve(import.meta.dirname, '../../..');

describe('monorepo development configuration', () => {
  it('uses distinct default ports for the web application and API', async () => {
    const apiMain = await readFile(
      resolve(repositoryRoot, 'apps/api/src/main.ts'),
      'utf8',
    );

    expect(apiMain).toContain("process.env.PORT ?? '3001'");
  });

  it('declares the shadcn/ui project configuration', async () => {
    const componentsConfig = JSON.parse(
      await readFile(resolve(repositoryRoot, 'apps/web/components.json'), 'utf8'),
    ) as { aliases: { utils: string }; tailwind: { config: string } };

    expect(componentsConfig).toMatchObject({
      aliases: { utils: '@/lib/utils' },
      tailwind: { config: 'tailwind.config.ts' },
    });
  });
});
