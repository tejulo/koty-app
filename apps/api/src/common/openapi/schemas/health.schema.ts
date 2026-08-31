export const healthDatabaseSchema = {
  type: 'object',
  required: ['status'],
  properties: {
    status: {
      type: 'string',
      enum: ['up', 'down', 'unknown'],
      description: 'Estado de la conexion Prisma a PostgreSQL',
      example: 'up',
    },
    message: {
      type: 'string',
      description: 'Mensaje opcional con detalle del estado (sin credenciales)',
    },
  },
};

export const healthResponseSchema = {
  type: 'object',
  required: ['status', 'timestamp', 'database'],
  properties: {
    status: {
      type: 'string',
      enum: ['ok', 'degraded'],
      description: 'Estado del health check',
      example: 'ok',
    },
    timestamp: {
      type: 'string',
      format: 'date-time',
      description: 'Fecha y hora de la respuesta',
      example: '2024-01-15T10:30:00.000Z',
    },
    database: {
      ...healthDatabaseSchema,
      description: 'Estado de la conexion Prisma a PostgreSQL',
    },
  },
};