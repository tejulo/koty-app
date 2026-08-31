import { DocumentBuilder } from '@nestjs/swagger';

export const IDEMPOTENCY_KEY_HEADER = 'Idempotency-Key';

export const idempotencyKeyParameter = {
  name: IDEMPOTENCY_KEY_HEADER,
  in: 'header' as const,
  required: false,
  description:
    'Clave opaca generada por el cliente para deduplicar comandos sensibles. ' +
    'Limitada a (organizationId, actorId, commandType). ' +
    'Longitud entre 8 y 128 caracteres.',
  schema: {
    type: 'string',
    minLength: 8,
    maxLength: 128,
    example: '01HMZ9XK3Q5V7R8T6Y4W2N0JDP',
  },
};

export const swaggerConfig = new DocumentBuilder()
  .setTitle('Koty API')
  .setDescription('API para la aplicación Koty - Contrato Base v1')
  .setVersion('1.0')
  .addTag('health', 'Health check endpoint')
  .addTag('audit', 'Consulta y registro de auditoría append-only')
  .build();
