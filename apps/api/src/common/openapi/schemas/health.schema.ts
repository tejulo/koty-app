export const healthResponseSchema = {
  type: 'object',
  required: ['status', 'timestamp'],
  properties: {
    status: {
      type: 'string',
      description: 'Estado del health check',
      example: 'ok',
    },
    timestamp: {
      type: 'string',
      format: 'date-time',
      description: 'Fecha y hora de la respuesta',
      example: '2024-01-15T10:30:00.000Z',
    },
  },
};
