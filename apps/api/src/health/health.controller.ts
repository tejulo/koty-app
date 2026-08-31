import { ApiResponse, ApiTags } from '@nestjs/swagger';
import { Controller, Get, HttpCode, HttpException, HttpStatus } from '@nestjs/common';

import { HealthService } from './health.service';
import { HealthResponseDto } from './dto/health-response.dto';
import { errorResponseSchema } from '../common/openapi/schemas/error.schema';

@ApiTags('health')
@Controller()
export class HealthController {
  constructor(private readonly healthService: HealthService) {}

  @Get()
  @HttpCode(HttpStatus.OK)
  @ApiResponse({
    status: 200,
    description: 'Health check response',
    type: HealthResponseDto,
  })
  @ApiResponse({
    status: 503,
    description: 'Health check degraded response',
    type: HealthResponseDto,
  })
  @ApiResponse({
    status: 500,
    description: 'Error response',
    schema: errorResponseSchema,
  })
  async check(): Promise<HealthResponseDto> {
    const result = await this.healthService.check();

    if (result.status === 'degraded') {
      throw new HttpException(result, HttpStatus.SERVICE_UNAVAILABLE);
    }

    return result;
  }
}