import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { PrismaClient } from '@prisma/client';

import { isIntegrationTestEnv } from './prisma.constants';

/**
 * NestJS-friendly wrapper around PrismaClient.
 *
 * The service extends `PrismaClient` directly so that every model
 * delegate (`outboxEvent`, `idempotencyRecord`, `auditEvent`, etc.) is
 * installed by the parent constructor on the same instance that NestJS
 * injects into the rest of the application. An earlier iteration of
 * this service tried to delegate the model delegates via
 * `Object.assign(this, injectedClient)`, but the Prisma engine installs
 * some delegates as non-enumerable properties, so `Object.assign` left
 * `prismaService.outboxEvent` undefined and every smoke controller
 * returned HTTP 500 (see `openspec/changes/dev-32/attempts/attempt-007.md`).
 * The current design avoids that pitfall by having Nest instantiate a
 * single `PrismaService` whose parent constructor configures every
 * delegate on `this`.
 *
 * The `datasourceUrl` is resolved from `DATABASE_URL_TEST` (set by the
 * integration test global setup to point at the isolated PostgreSQL)
 * when available, falling back to `DATABASE_URL` for production / local
 * development runs. `$connect` is deferred when `INTEGRATION_TEST=true`
 * so the global setup has time to provision the isolated database
 * before any query is issued.
 */
@Injectable()
export class PrismaService
  extends PrismaClient
  implements OnModuleInit, OnModuleDestroy
{
  constructor() {
    const datasourceUrl =
      process.env['DATABASE_URL_TEST'] ?? process.env['DATABASE_URL'];
    if (!datasourceUrl) {
      throw new Error(
        'PrismaService: DATABASE_URL (or DATABASE_URL_TEST) must be defined.',
      );
    }
    super({ datasourceUrl });
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
