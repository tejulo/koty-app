export const PRISMA_CLIENT = Symbol('PRISMA_CLIENT');

/**
 * Integration tests set `process.env.INTEGRATION_TEST = 'true'` from globalSetup.
 * When this flag is set, PrismaService defers `$connect` so the global setup can
 * create the isolated database first.
 */
export const isIntegrationTestEnv = (): boolean =>
  process.env['INTEGRATION_TEST'] === 'true';