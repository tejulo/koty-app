import { Injectable, Optional } from '@nestjs/common';
import type { PrismaClient } from '@prisma/client';

import { PrismaService } from '../prisma/prisma.service';
import {
  HealthDatabaseDto,
  HealthResponseDto,
} from './dto/health-response.dto';

@Injectable()
export class HealthService {
  constructor(@Optional() private readonly prisma?: PrismaService) {}

  async check(): Promise<HealthResponseDto> {
    const database = await this.checkDatabase();

    return {
      status: database.status === 'down' ? 'degraded' : 'ok',
      timestamp: new Date().toISOString(),
      database,
    };
  }

  private async checkDatabase(): Promise<HealthDatabaseDto> {
    if (!this.prisma) {
      return { status: 'unknown' };
    }

    const client: PrismaClient = this.prisma;
    try {
      await client.$queryRaw`SELECT 1`;
      return { status: 'up', message: 'Prisma responded to SELECT 1' };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Prisma is not reachable';
      return { status: 'down', message };
    }
  }
}