import { ApiProperty } from '@nestjs/swagger';

export class HealthDatabaseDto {
  @ApiProperty({
    description: 'Estado de la conexion Prisma a la base de datos',
    example: 'up',
    enum: ['up', 'down', 'unknown'],
  })
  status!: 'up' | 'down' | 'unknown';

  @ApiProperty({
    description: 'Mensaje opcional con detalle del estado (sin credenciales)',
    example: 'Prisma responded to SELECT 1',
    required: false,
  })
  message?: string;
}

export class HealthResponseDto {
  @ApiProperty({
    description: 'Estado del health check',
    example: 'ok',
    enum: ['ok', 'degraded'],
  })
  status!: string;

  @ApiProperty({
    description: 'Fecha y hora de la respuesta',
    example: '2024-01-15T10:30:00.000Z',
  })
  timestamp!: string;

  @ApiProperty({
    description: 'Estado de la conexion Prisma a PostgreSQL',
    type: () => HealthDatabaseDto,
  })
  database!: HealthDatabaseDto;
}