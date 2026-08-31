import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { Test } from '@nestjs/testing';
import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { PrismaClient } from '@prisma/client';

import { AppModule } from '../../src/app.module';
import { ApiExceptionFilter } from '../../src/common/errors/api-exception.filter';
import { IDEMPOTENCY_KEY_HEADER } from '../../src/common/openapi/swagger.config';

const ENABLE_FLAG = 'ENABLE_IDEMPOTENCY_ECHO';

describe('Idempotency HTTP contract (integration)', () => {
  let app: INestApplication;
  let prisma: PrismaClient;
  let previousEchoFlag: string | undefined;

  beforeAll(async () => {
    previousEchoFlag = process.env[ENABLE_FLAG];
    process.env[ENABLE_FLAG] = 'true';
    if (!process.env['DATABASE_URL']) {
      throw new Error('DATABASE_URL must be set for integration tests');
    }
    if (!process.env['DATABASE_URL_TEST']) {
      // The global-setup guarantees this, but defensive fallback keeps the
      // contract clear for callers running specs outside the standard flow.
      process.env['DATABASE_URL'] = process.env['DATABASE_URL'];
    }

    prisma = new PrismaClient({ datasourceUrl: process.env['DATABASE_URL_TEST'] });

    const moduleRef = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleRef.createNestApplication({ logger: false });
    app.setGlobalPrefix('api/v1');
    app.useGlobalFilters(new ApiExceptionFilter());
    await app.init();
  });

  afterAll(async () => {
    if (app) {
      await app.close();
    }
    if (prisma) {
      await prisma.$disconnect();
    }
    if (previousEchoFlag === undefined) {
      delete process.env[ENABLE_FLAG];
    } else {
      process.env[ENABLE_FLAG] = previousEchoFlag;
    }
  });

  const sendEcho = (
    key: string,
    body: Record<string, unknown>,
    headers: Record<string, string> = {},
  ) =>
    request(app.getHttpServer())
      .post('/api/v1/_idempotency/echo')
      .set(IDEMPOTENCY_KEY_HEADER, key)
      .set('Content-Type', 'application/json')
      .send(body)
      .set(headers);

  it('returns the cached response when the same key and payload arrive twice', async () => {
    const key = `it-cache-${Date.now()}`;
    const body = {
      organizationId: 'org-it',
      actorId: 'actor-it',
      message: 'hello',
    };

    const first = await sendEcho(key, body);
    expect(first.status).toBe(201);
    expect(first.body.replayed).toBe(false);

    const second = await sendEcho(key, body);
    expect(second.status).toBe(201);
    expect(second.body.replayed).toBe(true);
    expect(second.body.echoed).toBe('hello');

    const records = await prisma.idempotencyRecord.findMany({
      where: {
        organizationId: 'org-it',
        actorId: 'actor-it',
        commandType: 'echo',
        idempotencyKey: key,
      },
    });
    expect(records).toHaveLength(1);
  });

  it('rejects with 409 IDEMPOTENCY_KEY_REUSED when the payload changes', async () => {
    const key = `it-conflict-${Date.now()}`;
    const firstBody = {
      organizationId: 'org-it',
      actorId: 'actor-it',
      message: 'hello',
    };
    const conflictBody = {
      organizationId: 'org-it',
      actorId: 'actor-it',
      message: 'different',
    };

    const first = await sendEcho(key, firstBody);
    expect(first.status).toBe(201);

    const conflict = await sendEcho(key, conflictBody);
    expect(conflict.status).toBe(409);
    expect(conflict.body).toMatchObject({
      code: 'IDEMPOTENCY_KEY_REUSED',
      fieldErrors: [],
    });
    expect(typeof conflict.body.correlationId).toBe('string');

    const records = await prisma.idempotencyRecord.findMany({
      where: {
        organizationId: 'org-it',
        actorId: 'actor-it',
        commandType: 'echo',
        idempotencyKey: key,
      },
    });
    expect(records).toHaveLength(1);
  });

  it('does not consume the key when the command fails before commit', async () => {
    const failingKey = `it-fail-${Date.now()}`;
    const successKey = `it-success-${Date.now()}`;
    const baseBody = {
      organizationId: 'org-it',
      actorId: 'actor-it',
      message: 'will fail',
      forceFail: true,
    };

    const failingResponse = await sendEcho(failingKey, baseBody);
    expect(failingResponse.status).toBe(404);

    const records = await prisma.idempotencyRecord.findMany({
      where: {
        organizationId: 'org-it',
        actorId: 'actor-it',
        idempotencyKey: failingKey,
      },
    });
    expect(records).toHaveLength(0);

    // A fresh key with valid content must succeed and persist a single record.
    const success = await sendEcho(successKey, {
      organizationId: 'org-it',
      actorId: 'actor-it',
      message: 'will succeed',
    });
    expect(success.status).toBe(201);
    expect(success.body.replayed).toBe(false);

    const successRecords = await prisma.idempotencyRecord.findMany({
      where: {
        organizationId: 'org-it',
        actorId: 'actor-it',
        commandType: 'echo',
        idempotencyKey: successKey,
      },
    });
    expect(successRecords).toHaveLength(1);
  });

  it('rejects the request when the Idempotency-Key header is missing', async () => {
    const response = await request(app.getHttpServer())
      .post('/api/v1/_idempotency/echo')
      .send({ organizationId: 'org-it', actorId: 'actor-it' });
    expect(response.status).toBe(400);
    expect(response.body).toMatchObject({
      code: 'VALIDATION_ERROR',
    });
  });

  it('rejects the request when the Idempotency-Key header is too long', async () => {
    const tooLong = 'a'.repeat(129);
    const response = await sendEcho(tooLong, {
      organizationId: 'org-it',
      actorId: 'actor-it',
    });
    expect(response.status).toBe(400);
    expect(response.body).toMatchObject({
      code: 'VALIDATION_ERROR',
    });
  });
});