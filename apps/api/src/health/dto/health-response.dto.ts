import { ApiProperty } from '@nestjs/swagger';

export class HealthResponseDto {
  @ApiProperty({
    description: 'Estado del health check',
    example: 'ok',
  })
  status!: string;

  @ApiProperty({
    description: 'Fecha y hora de la respuesta',
    example: '2024-01-15T10:30:00.000Z',
  })
  timestamp!: string;
}
