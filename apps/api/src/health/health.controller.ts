import { ApiResponse, ApiTags } from '@nestjs/swagger';
import { Controller, Get } from '@nestjs/common';
import { HealthService } from './health.service';
import { HealthResponseDto } from './dto/health-response.dto';
import { errorResponseSchema } from '../common/openapi/schemas/error.schema';

@ApiTags('health')
@Controller()
export class HealthController {
  constructor(private readonly healthService: HealthService) {}

  @Get()
  @ApiResponse({
    status: 200,
    description: 'Health check response',
    type: HealthResponseDto,
  })
  @ApiResponse({
    status: 500,
    description: 'Error response',
    schema: errorResponseSchema,
  })
  check(): HealthResponseDto {
    return this.healthService.check();
  }
}
