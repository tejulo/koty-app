import { Client } from 'pg';

export async function teardown(): Promise<void> {
  const testDbName = process.env['TEST_DB_NAME'];
  if (!testDbName) {
    return;
  }

  const adminUrl =
    process.env['DATABASE_URL_ADMIN'] ??
    process.env['DATABASE_URL_TEST_ADMIN'] ??
    process.env['DATABASE_URL'];

  if (!adminUrl) {
    // eslint-disable-next-line no-console
    console.warn('Skipping teardown: no admin DATABASE_URL available.');
    return;
  }

  const admin = new Client({ connectionString: adminUrl });
  await admin.connect();
  try {
    await admin.query(
      `SELECT pg_terminate_backend(pid)
       FROM pg_stat_activity
       WHERE datname = $1 AND pid <> pg_backend_pid()`,
      [testDbName],
    );
    await admin.query(`DROP DATABASE IF EXISTS "${testDbName}"`);
  } finally {
    await admin.end();
  }
}
