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

export const auditInvalidFieldExample = {
  code: 'AUDIT_INVALID_FIELD',
  message: 'Field is not allowed by the entity allowlist',
  fieldErrors: [{ field: 'before.password', message: 'not allowed' }],
  correlationId: '550e8400-e29b-41d4-a716-446655440000',
};

export const auditTransitionConflictExample = {
  code: 'AUDIT_TRANSITION_CONFLICT',
  message:
    'Audit transition conflict: a record with the same (scope, transitionKey) ' +
    'exists for a different correlationId',
  fieldErrors: [],
  correlationId: '550e8400-e29b-41d4-a716-446655440000',
};

export const outboxSemanticConflictExample = {
  code: 'OUTBOX_SEMANTIC_CONFLICT',
  message:
    'Outbox semantic key reused with a different payload (DEV-32)',
  fieldErrors: [],
  correlationId: '550e8400-e29b-41d4-a716-446655440000',
};

export const outboxPayloadTooLargeExample = {
  code: 'OUTBOX_PAYLOAD_TOO_LARGE',
  message: 'Outbox payload exceeds the maximum allowed size (DEV-32)',
  fieldErrors: [
    {
      field: 'payload',
      message: 'payload must be at most 65536 bytes (got 70000)',
    },
  ],
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
        'AUDIT_TRANSITION_CONFLICT',
        'AUDIT_INVALID_FIELD',
        'OUTBOX_SEMANTIC_CONFLICT',
        'OUTBOX_PAYLOAD_TOO_LARGE',
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
    auditInvalidField: {
      summary: 'Campo no permitido en la allowlist de auditoría',
      value: auditInvalidFieldExample,
    },
    auditTransitionConflict: {
      summary: 'Conflicto de transición de auditoría (DEV-36)',
      value: auditTransitionConflictExample,
    },
    outboxSemanticConflict: {
      summary: 'Conflicto de clave semántica del outbox (DEV-32)',
      value: outboxSemanticConflictExample,
    },
    outboxPayloadTooLarge: {
      summary: 'Payload del outbox demasiado grande (DEV-32)',
      value: outboxPayloadTooLargeExample,
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

export const auditInvalidFieldSchema = {
  type: 'object',
  required: ['code', 'message', 'fieldErrors', 'correlationId'],
  description:
    'Respuesta de error cuando un campo registrado en before/after no está ' +
    'en la allowlist del entityType correspondiente',
  properties: errorResponseSchema.properties,
  example: auditInvalidFieldExample,
};

export const auditTransitionConflictSchema = {
  type: 'object',
  required: ['code', 'message', 'fieldErrors', 'correlationId'],
  description:
    'Respuesta de error cuando una transición de auditoría colisiona con ' +
    'un registro existente con un correlationId distinto',
  properties: errorResponseSchema.properties,
  example: auditTransitionConflictExample,
};

export const outboxSemanticConflictSchema = {
  type: 'object',
  required: ['code', 'message', 'fieldErrors', 'correlationId'],
  description:
    'Respuesta de error cuando una clave semántica del outbox se reutiliza ' +
    'con un payload distinto (DEV-32)',
  properties: errorResponseSchema.properties,
  example: outboxSemanticConflictExample,
};

export const outboxPayloadTooLargeSchema = {
  type: 'object',
  required: ['code', 'message', 'fieldErrors', 'correlationId'],
  description:
    'Respuesta de error cuando el payload del outbox excede el tamaño ' +
    'máximo permitido (DEV-32)',
  properties: errorResponseSchema.properties,
  example: outboxPayloadTooLargeExample,
};
