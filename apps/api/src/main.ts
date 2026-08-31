import { NestFactory } from '@nestjs/core';
import { PrismaClient } from '@prisma/client';
import { AppModule } from './app.module';
import { SwaggerModule } from '@nestjs/swagger';
import {
  idempotencyKeyParameter,
  swaggerConfig,
} from './common/openapi/swagger.config';
import { ApiExceptionFilter } from './common/errors/api-exception.filter';
import {
  auditInvalidFieldSchema,
  auditTransitionConflictSchema,
  errorResponseSchema,
  fieldErrorSchema,
  idempotencyKeyReusedSchema,
} from './common/openapi/schemas/error.schema';
import { healthResponseSchema } from './common/openapi/schemas/health.schema';

async function bootstrap() {
  // Validate DATABASE_URL before touching the Nest container: a missing or
  // unparseable connection string should never let the API half-start.
  const databaseUrl = process.env['DATABASE_URL'];
  if (!databaseUrl) {
    console.error(
      'Missing required environment variable: DATABASE_URL. ' +
        'Copy .env.example to .env and configure the values.',
    );
    process.exit(1);
  }

  try {
    const probe = new PrismaClient({ datasourceUrl: databaseUrl });
    await probe.$disconnect();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`DATABASE_URL is not parseable by Prisma: ${message}`);
    process.exit(1);
  }

  const app = await NestFactory.create(AppModule);

  const globalPrefix = process.env.API_VERSION_PREFIX || 'api/v1';
  app.setGlobalPrefix(globalPrefix, {
    exclude: ['api/docs', 'api/docs-json'],
  });

  app.useGlobalFilters(new ApiExceptionFilter());

  const document = SwaggerModule.createDocument(app, swaggerConfig, {
    extraModels: [],
  });

  // Add schemas to the document
  document.components = document.components || {};
  document.components.schemas = {
    ErrorResponse: errorResponseSchema,
    FieldError: fieldErrorSchema,
    HealthResponse: healthResponseSchema,
    IdempotencyKeyReusedError: idempotencyKeyReusedSchema,
    AuditInvalidFieldError: auditInvalidFieldSchema,
    AuditTransitionConflictError: auditTransitionConflictSchema,
  };

  document.components.parameters = {
    ...(document.components.parameters || {}),
    IdempotencyKeyHeader: idempotencyKeyParameter,
  };

  SwaggerModule.setup('api/docs', app, document);

  // Setup JSON docs endpoint
  const httpAdapter = app.getHttpAdapter();
  httpAdapter.get('/api/docs-json', (_req: unknown, res: { json: (doc: unknown) => void }) => {
    res.json(document);
  });

  const port = process.env.PORT ?? '3001';
  await app.listen(port);
  console.log(`API running on port ${port}`);
}
void bootstrap();
