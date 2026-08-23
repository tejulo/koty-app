import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { SwaggerModule } from '@nestjs/swagger';
import { swaggerConfig } from './common/openapi/swagger.config';
import { ApiExceptionFilter } from './common/errors/api-exception.filter';
import { errorResponseSchema, fieldErrorSchema } from './common/openapi/schemas/error.schema';

async function bootstrap() {
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
