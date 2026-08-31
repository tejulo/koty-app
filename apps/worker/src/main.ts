import { PrismaClient } from '@prisma/client';
import { Worker } from './index.js';

const REQUIRED_ENV_VARS = ['DATABASE_URL'] as const;

function validateEnvironment(): void {
  const missing: string[] = [];

  for (const key of REQUIRED_ENV_VARS) {
    if (!process.env[key]) {
      missing.push(key);
    }
  }

  if (missing.length > 0) {
    const error = new Error(
      `Missing required environment variables: ${missing.join(', ')}. ` +
      `Please set these variables before starting the Worker. ` +
      `Copy .env.example to .env and configure the values.`,
    );
    console.error(error.message);
    process.exit(1);
  }
}

async function validatePrismaClient(): Promise<void> {
  try {
    const probe = new PrismaClient({ datasourceUrl: process.env['DATABASE_URL'] });
    await probe.$disconnect();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`DATABASE_URL is not parseable by Prisma: ${message}`);
    process.exit(1);
  }
}

validateEnvironment();
await validatePrismaClient();

const worker = new Worker({
  name: 'koty-worker',
  port: 3001,
});

worker.start().catch((error: unknown) => {
  console.error('Failed to start worker:', error);
  process.exit(1);
});