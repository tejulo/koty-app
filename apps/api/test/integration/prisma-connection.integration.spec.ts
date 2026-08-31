import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { PrismaClient } from '@prisma/client';

describe('Prisma integration smoke', () => {
  const connectionString = process.env['DATABASE_URL_TEST'];
  let client: PrismaClient;

  beforeAll(() => {
    if (!connectionString) {
      throw new Error(
        'DATABASE_URL_TEST must be set by global-setup before running integration tests.',
      );
    }
    client = new PrismaClient({ datasourceUrl: connectionString });
  });

  beforeAll(async () => {
    await client.$connect();
  });

  afterAll(async () => {
    await client.$disconnect();
  });

  it('connects to the isolated PostgreSQL database', async () => {
    const result = await client.$queryRaw<Array<{ value: number }>>`SELECT 1 AS value`;
    expect(result[0]).toEqual({ value: 1 });
  });

  it('exposes the Prisma migrations metadata table', async () => {
    const result = await client.$queryRaw<Array<{ exists: boolean }>>`
      SELECT EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_name = '_prisma_migrations'
      ) AS exists
    `;
    expect(result[0]?.exists).toBe(true);
  });
});
