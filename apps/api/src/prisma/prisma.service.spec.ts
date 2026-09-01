import {
  afterAll,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest';

import { PrismaService } from './prisma.service';

const DUMMY_DATABASE_URL = 'postgresql://test:test@localhost:5432/test';

const buildService = (): {
  service: PrismaService;
  connect: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
} => {
  const connect = vi.fn().mockResolvedValue(undefined);
  const disconnect = vi.fn().mockResolvedValue(undefined);
  const service = new PrismaService();
  service.$connect = connect as unknown as PrismaService['$connect'];
  service.$disconnect = disconnect as unknown as PrismaService['$disconnect'];
  return { service, connect, disconnect };
};

describe('PrismaService', () => {
  const originalIntegrationFlag = process.env['INTEGRATION_TEST'];
  const originalDatabaseUrl = process.env['DATABASE_URL'];
  const originalDatabaseUrlTest = process.env['DATABASE_URL_TEST'];

  beforeAll(() => {
    // The PrismaService constructor reads `DATABASE_URL` to instantiate
    // the underlying engine. The unit tests do not need a real database
    // (they mock `$connect` / `$disconnect`), so a syntactically valid
    // PostgreSQL URL is enough to let the parent constructor succeed.
    process.env['DATABASE_URL'] = DUMMY_DATABASE_URL;
  });

  afterAll(() => {
    if (originalDatabaseUrl === undefined) {
      delete process.env['DATABASE_URL'];
    } else {
      process.env['DATABASE_URL'] = originalDatabaseUrl;
    }
    if (originalDatabaseUrlTest === undefined) {
      delete process.env['DATABASE_URL_TEST'];
    } else {
      process.env['DATABASE_URL_TEST'] = originalDatabaseUrlTest;
    }
    if (originalIntegrationFlag === undefined) {
      delete process.env['INTEGRATION_TEST'];
    } else {
      process.env['INTEGRATION_TEST'] = originalIntegrationFlag;
    }
  });

  beforeEach(() => {
    delete process.env['INTEGRATION_TEST'];
  });

  it('connects on module init when not running integration tests', async () => {
    const { service, connect } = buildService();

    await service.onModuleInit();

    expect(connect).toHaveBeenCalledTimes(1);
  });

  it('skips $connect during integration tests', async () => {
    process.env['INTEGRATION_TEST'] = 'true';
    const { service, connect } = buildService();

    await service.onModuleInit();

    expect(connect).not.toHaveBeenCalled();

    if (originalIntegrationFlag === undefined) {
      delete process.env['INTEGRATION_TEST'];
    } else {
      process.env['INTEGRATION_TEST'] = originalIntegrationFlag;
    }
  });

  it('disconnects on module destroy', async () => {
    const { service, disconnect } = buildService();

    await service.onModuleDestroy();

    expect(disconnect).toHaveBeenCalledTimes(1);
  });
});
