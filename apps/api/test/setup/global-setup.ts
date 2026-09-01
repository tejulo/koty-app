import { randomUUID } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { Client } from 'pg';

const RUN_ID = process.env['VITEST_RUN_ID'] ?? randomUUID();
const BASE_DB_NAME = process.env['TEST_DB_BASE_NAME'] ?? 'plandepo_test';
const ISOLATED_DB_NAME = `${BASE_DB_NAME}_${RUN_ID.replace(/-/g, '').slice(0, 12)}`;

function buildIsolatedUrl(template: string, dbName: string): string {
  const url = new URL(template);
  url.pathname = `/${dbName}`;
  return url.toString();
}

function readAdminUrl(): string {
  const adminUrl =
    process.env['DATABASE_URL_ADMIN'] ??
    process.env['DATABASE_URL_TEST_ADMIN'] ??
    process.env['DATABASE_URL'];

  if (!adminUrl) {
    throw new Error(
      'DATABASE_URL (or DATABASE_URL_TEST_ADMIN) must be defined for integration tests.',
    );
  }

  return adminUrl;
}

export async function setup(): Promise<void> {
  const baseUrl = process.env['DATABASE_URL_TEST'] ?? process.env['DATABASE_URL'];

  if (!baseUrl) {
    throw new Error(
      'DATABASE_URL must be defined for integration tests (use a local PostgreSQL).',
    );
  }

  const adminUrl = readAdminUrl();
  const isolatedUrl = buildIsolatedUrl(adminUrl, ISOLATED_DB_NAME);

  const admin = new Client({ connectionString: adminUrl });
  await admin.connect();
  await admin.query(`CREATE DATABASE "${ISOLATED_DB_NAME}"`);
  await admin.end();

  process.env['DATABASE_URL_TEST'] = isolatedUrl;
  process.env['TEST_DB_NAME'] = ISOLATED_DB_NAME;
  process.env['INTEGRATION_TEST'] = 'true';
  process.env['ENABLE_IDEMPOTENCY_ECHO'] = 'true';
  // DEV-36: enable the audit smoke controller for integration tests.
  process.env['ENABLE_AUDIT_ECHO'] = 'true';
  // DEV-32: enable the outbox smoke controller for integration tests.
  process.env['ENABLE_OUTBOX_ECHO'] = 'true';

  const apply = spawnSync(
    'pnpm',
    ['--filter', '@koty-app/api', 'exec', 'prisma', 'migrate', 'deploy'],
    {
      env: { ...process.env, DATABASE_URL: isolatedUrl },
      stdio: 'inherit',
    },
  );

  if (apply.status !== 0) {
    throw new Error(`prisma migrate deploy failed with code ${apply.status}`);
  }

  // eslint-disable-next-line no-console
  console.log(`Integration test database ready: ${ISOLATED_DB_NAME}`);
}
