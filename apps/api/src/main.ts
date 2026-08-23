import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

const REQUIRED_ENV_VARS = ['DATABASE_URL'] as const;

function validateEnvironment(): void {
  const missing: string[] = [];

  for (const key of REQUIRED_ENV_VARS) {
    if (!process.env[key]) {
      missing.push(key);
    }
  }

  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variables: ${missing.join(', ')}. ` +
      `Please set these variables before starting the API. ` +
      `Copy .env.example to .env and configure the values.`,
    );
  }
}

async function bootstrap() {
  validateEnvironment();

  const app = await NestFactory.create(AppModule);
  const port = process.env.PORT ?? '3001';
  await app.listen(port);
  console.log(`API running on port ${port}`);
}
void bootstrap();
