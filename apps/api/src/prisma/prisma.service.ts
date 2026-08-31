import {
  Inject,
  Injectable,
  OnModuleDestroy,
  OnModuleInit,
} from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

import { PRISMA_CLIENT, isIntegrationTestEnv } from './prisma.constants';

/**
 * NestJS-friendly wrapper around PrismaClient.
 *
 * The service delegates every Prisma method to the underlying client so consumers
 * can keep using the full Prisma API while benefiting from Nest lifecycle hooks.
 *
 * `$connect` is deferred when `INTEGRATION_TEST=true` so that the global setup of
 * the integration test suite has time to provision the isolated database before
 * any query is issued.
 */
@Injectable()
export class PrismaService
  extends PrismaClient
  implements OnModuleInit, OnModuleDestroy
{
  constructor(@Inject(PRISMA_CLIENT) client?: PrismaClient) {
    super();
    if (client) {
      Object.assign(this, client);
    }
  }

  async onModuleInit(): Promise<void> {
    if (isIntegrationTestEnv()) {
      return;
    }
    await this.$connect();
  }

  async onModuleDestroy(): Promise<void> {
    await this.$disconnect();
  }
}

/**
 * Public type alias used by consumers (e.g. `IdempotencyService`) that need
 * to call Prisma delegates typed against a fully generated `PrismaClient`.
 * The runtime instance is the same `PrismaService` injected by NestJS.
 */
export type PrismaServiceClient = PrismaClient;