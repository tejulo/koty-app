export const fieldErrorSchema = {
  type: 'object',
  required: ['field', 'message'],
  properties: {
    field: { type: 'string', description: 'Nombre del campo que falló' },
    message: { type: 'string', description: 'Descripción del error' },
  },
};

export const idempotencyKeyReusedExample = {
  code: 'IDEMPOTENCY_KEY_REUSED',
  message: 'Idempotency key reused with a different request payload',
  fieldErrors: [],
  correlationId: '550e8400-e29b-41d4-a716-446655440000',
};

export const errorResponseSchema = {
  type: 'object',
  required: ['code', 'message', 'fieldErrors', 'correlationId'],
  properties: {
    code: {
      type: 'string',
      description: 'Código de error predefinido',
      example: 'VALIDATION_ERROR',
      enum: [
        'VALIDATION_ERROR',
        'NOT_FOUND',
        'INTERNAL_ERROR',
        'BAD_REQUEST',
        'UNAUTHORIZED',
        'IDEMPOTENCY_KEY_REUSED',
      ],
    },
    message: {
      type: 'string',
      description: 'Mensaje legible del error',
      example: 'Validation failed',
    },
    fieldErrors: {
      type: 'array',
      description: 'Lista de errores específicos de campo',
      items: { $ref: '#/components/schemas/FieldError' },
    },
    correlationId: {
      type: 'string',
      format: 'uuid',
      description: 'Identificador de correlación de la solicitud',
      example: '550e8400-e29b-41d4-a716-446655440000',
    },
  },
  examples: {
    idempotencyKeyReused: {
      summary: 'Conflicto por reutilización de clave de idempotencia',
      value: idempotencyKeyReusedExample,
    },
  },
};

export const idempotencyKeyReusedSchema = {
  type: 'object',
  required: ['code', 'message', 'fieldErrors', 'correlationId'],
  description:
    'Respuesta de error cuando una clave de idempotencia se reutiliza con un cuerpo distinto',
  properties: errorResponseSchema.properties,
  example: idempotencyKeyReusedExample,
};