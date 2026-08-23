import { DocumentBuilder } from '@nestjs/swagger';

export const swaggerConfig = new DocumentBuilder()
  .setTitle('Koty API')
  .setDescription('API para la aplicación Koty - Contrato Base v1')
  .setVersion('1.0')
  .addTag('health', 'Health check endpoint')
  .build();
