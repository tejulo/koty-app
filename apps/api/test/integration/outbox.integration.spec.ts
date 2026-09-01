import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { Test } from '@nestjs/testing';
import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { PrismaClient } from '@prisma/client';

import { AppModule } from '../../src/app.module';
import { ApiExceptionFilter } from '../../src/common/errors/api-exception.filter';

const ENABLE_OUTBOX_FLAG = 'ENABLE_OUTBOX_ECHO';

describe('Outbox transactional HTTP contract (integration)', () => {
  let app: INestApplication;
  let prisma: PrismaClient;
  let previousOutboxFlag: string | undefined;
  const runId = Date.now();
  const organizationId = `org-outbox-${runId}`;

  beforeAll(async () => {
    previousOutboxFlag = process.env[ENABLE_OUTBOX_FLAG];
    process.env[ENABLE_OUTBOX_FLAG] = 'true';
    if (!process.env['DATABASE_URL_TEST']) {
      throw new Error('DATABASE_URL_TEST must be set by global-setup');
    }

    prisma = new PrismaClient({
      datasourceUrl: process.env['DATABASE_URL_TEST'],
    });

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
    if (previousOutboxFlag === undefined) {
      delete process.env[ENABLE_OUTBOX_FLAG];
    } else {
      process.env[ENABLE_OUTBOX_FLAG] = previousOutboxFlag;
    }
  });

  const sendEcho = (
    body: Record<string, unknown>,
    headers: Record<string, string> = {},
  ) =>
    request(app.getHttpServer())
      .post('/api/v1/_outbox/echo')
      .set('Content-Type', 'application/json')
      .send(body)
      .set(headers);

  it('persists an OutboxEvent through the echo endpoint', async () => {
    const correlationId = '11111111-1111-4111-8111-111111111111';
    const semanticKey = `it-create-${runId}`;
    const response = await sendEcho(
      {
        organizationId,
        aggregateType: 'outbox-echo',
        aggregateId: `agg-${runId}-1`,
        version: 1,
        semanticKey,
        eventType: 'outbox-echo.create',
        payload: { message: 'first' },
      },
      { 'x-correlation-id': correlationId },
    );

    expect(response.status).toBe(201);
    expect(response.body).toMatchObject({
      organizationId,
      aggregateType: 'outbox-echo',
      aggregateId: `agg-${runId}-1`,
      version: 1,
      eventType: 'outbox-echo.create',
      correlationId,
      created: true,
    });
    expect(response.body.payload).toEqual({ message: 'first' });

    const records = await prisma.outboxEvent.findMany({
      where: { organizationId, semanticKey },
    });
    expect(records).toHaveLength(1);
  });

  it('collapses a retry with the same semanticKey and payload into one row', async () => {
    const semanticKey = `it-retry-${runId}`;
    const body = {
      organizationId,
      aggregateType: 'outbox-echo',
      aggregateId: `agg-${runId}-2`,
      version: 1,
      semanticKey,
      eventType: 'outbox-echo.create',
      payload: { message: 'same' },
    };

    const first = await sendEcho(body, {
      'x-correlation-id': '22222222-2222-4222-8222-222222222222',
    });
    expect(first.status).toBe(201);
    expect(first.body.created).toBe(true);

    const second = await sendEcho(body, {
      'x-correlation-id': '33333333-3333-4333-8333-333333333333',
    });
    expect(second.status).toBe(201);
    expect(second.body.created).toBe(false);
    expect(second.body.id).toBe(first.body.id);

    const records = await prisma.outboxEvent.findMany({
      where: { organizationId, semanticKey },
    });
    expect(records).toHaveLength(1);
  });

  it('returns 409 OUTBOX_SEMANTIC_CONFLICT when the payload differs', async () => {
    const semanticKey = `it-conflict-${runId}`;
    const aggregateId = `agg-${runId}-3`;

    const first = await sendEcho(
      {
        organizationId,
        aggregateType: 'outbox-echo',
        aggregateId,
        version: 1,
        semanticKey,
        eventType: 'outbox-echo.create',
        payload: { message: 'first' },
      },
      { 'x-correlation-id': '44444444-4444-4444-8444-444444444444' },
    );
    expect(first.status).toBe(201);

    const conflict = await sendEcho(
      {
        organizationId,
        aggregateType: 'outbox-echo',
        aggregateId,
        version: 1,
        semanticKey,
        eventType: 'outbox-echo.create',
        payload: { message: 'different' },
      },
      { 'x-correlation-id': '55555555-5555-4555-8555-555555555555' },
    );
    expect(conflict.status).toBe(409);
    expect(conflict.body).toMatchObject({
      code: 'OUTBOX_SEMANTIC_CONFLICT',
      fieldErrors: [],
    });
    expect(typeof conflict.body.correlationId).toBe('string');
  });

  it('blocks UPDATE attempts at the database level', async () => {
    const semanticKey = `it-blocked-update-${runId}`;
    const response = await sendEcho(
      {
        organizationId,
        aggregateType: 'outbox-echo',
        aggregateId: `agg-${runId}-4`,
        version: 1,
        semanticKey,
        eventType: 'outbox-echo.create',
        payload: { message: 'blocked-update' },
      },
      { 'x-correlation-id': '66666666-6666-4666-8666-666666666666' },
    );
    expect(response.status).toBe(201);

    const record = await prisma.outboxEvent.findFirstOrThrow({
      where: { organizationId, semanticKey },
    });

    await expect(
      prisma.$executeRawUnsafe(
        'UPDATE "OutboxEvent" SET "eventType" = $1 WHERE "id" = $2',
        'tampered',
        record.id,
      ),
    ).rejects.toThrow(/append-only/i);

    const untouched = await prisma.outboxEvent.findUniqueOrThrow({
      where: { id: record.id },
    });
    expect(untouched.eventType).toBe('outbox-echo.create');
  });

  it('blocks DELETE attempts at the database level', async () => {
    const semanticKey = `it-blocked-delete-${runId}`;
    const response = await sendEcho(
      {
        organizationId,
        aggregateType: 'outbox-echo',
        aggregateId: `agg-${runId}-5`,
        version: 1,
        semanticKey,
        eventType: 'outbox-echo.create',
        payload: { message: 'blocked-delete' },
      },
      { 'x-correlation-id': '77777777-7777-4777-8777-777777777777' },
    );
    expect(response.status).toBe(201);

    const record = await prisma.outboxEvent.findFirstOrThrow({
      where: { organizationId, semanticKey },
    });

    await expect(
      prisma.$executeRawUnsafe(
        'DELETE FROM "OutboxEvent" WHERE "id" = $1',
        record.id,
      ),
    ).rejects.toThrow(/append-only/i);

    const stillThere = await prisma.outboxEvent.findUnique({
      where: { id: record.id },
    });
    expect(stillThere).not.toBeNull();
  });

  it('rolls back the outbox write when the handler forces a failure', async () => {
    const semanticKey = `it-rollback-${runId}`;
    const response = await sendEcho(
      {
        organizationId,
        aggregateType: 'outbox-echo',
        aggregateId: `agg-${runId}-6`,
        version: 1,
        semanticKey,
        eventType: 'outbox-echo.create',
        payload: { message: 'should-not-persist' },
        forceRollback: true,
      },
      { 'x-correlation-id': '88888888-8888-4888-8888-888888888888' },
    );
    expect(response.status).toBeGreaterThanOrEqual(500);

    const records = await prisma.outboxEvent.findMany({
      where: { organizationId, semanticKey },
    });
    expect(records).toHaveLength(0);
  });
});
