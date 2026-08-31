import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { Test } from '@nestjs/testing';
import type { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { PrismaClient } from '@prisma/client';

import { AppModule } from '../../src/app.module';
import { ApiExceptionFilter } from '../../src/common/errors/api-exception.filter';

const ENABLE_AUDIT_FLAG = 'ENABLE_AUDIT_ECHO';

describe('Audit append-only HTTP contract (integration)', () => {
  let app: INestApplication;
  let prisma: PrismaClient;
  let previousAuditFlag: string | undefined;
  const runId = Date.now();
  const orgA = `org-a-${runId}`;
  const orgB = `org-b-${runId}`;

  beforeAll(async () => {
    previousAuditFlag = process.env[ENABLE_AUDIT_FLAG];
    process.env[ENABLE_AUDIT_FLAG] = 'true';
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
    if (previousAuditFlag === undefined) {
      delete process.env[ENABLE_AUDIT_FLAG];
    } else {
      process.env[ENABLE_AUDIT_FLAG] = previousAuditFlag;
    }
  });

  const sendEcho = (
    body: Record<string, unknown>,
    headers: Record<string, string> = {},
  ) =>
    request(app.getHttpServer())
      .post('/api/v1/_audit/echo')
      .set('Content-Type', 'application/json')
      .send(body)
      .set(headers);

  it('persists an AuditEvent through the echo endpoint and never returns transitionKey', async () => {
    const correlationId = '11111111-1111-4111-8111-aaaaaaaaaaaa';
    const response = await sendEcho(
      {
        organizationId: orgA,
        actorId: 'actor-echo-1',
        message: 'first-message',
      },
      { 'x-correlation-id': correlationId },
    );

    expect(response.status).toBe(201);
    expect(response.body).toMatchObject({
      scope: 'ORGANIZATION',
      organizationId: orgA,
      actorType: 'USER',
      action: 'audit-echo.create',
      entityType: 'audit-echo',
      actorId: 'actor-echo-1',
      correlationId,
      created: true,
    });
    expect(response.body).not.toHaveProperty('transitionKey');

    const records = await prisma.auditEvent.findMany({
      where: { entityType: 'audit-echo', actorId: 'actor-echo-1' },
    });
    expect(records).toHaveLength(1);
    expect(records[0]?.transitionKey).toMatch(/^[0-9a-f]{64}$/);
  });

  it('collapses a retry with the same correlationId into a single AuditEvent', async () => {
    const correlationId = '22222222-2222-4222-8222-bbbbbbbbbbbb';
    const body = {
      organizationId: orgA,
      actorId: 'actor-echo-retry',
      message: 'retry-message',
    };

    const first = await sendEcho(body, { 'x-correlation-id': correlationId });
    expect(first.status).toBe(201);
    expect(first.body.created).toBe(true);

    const second = await sendEcho(body, { 'x-correlation-id': correlationId });
    expect(second.status).toBe(201);
    expect(second.body.created).toBe(false);
    expect(second.body.id).toBe(first.body.id);

    const records = await prisma.auditEvent.findMany({
      where: { entityType: 'audit-echo', actorId: 'actor-echo-retry' },
    });
    expect(records).toHaveLength(1);
  });

  it('blocks UPDATE attempts at the database level', async () => {
    const correlationId = '33333333-3333-4333-8333-cccccccccccc';
    const response = await sendEcho(
      {
        organizationId: orgA,
        actorId: 'actor-echo-blocked',
        message: 'blocked-update',
      },
      { 'x-correlation-id': correlationId },
    );
    expect(response.status).toBe(201);

    const record = await prisma.auditEvent.findFirstOrThrow({
      where: { entityType: 'audit-echo', actorId: 'actor-echo-blocked' },
    });

    await expect(
      prisma.$executeRawUnsafe(
        'UPDATE "AuditEvent" SET "action" = $1 WHERE "id" = $2',
        'tampered',
        record.id,
      ),
    ).rejects.toThrow(/append-only/i);

    const untouched = await prisma.auditEvent.findUniqueOrThrow({
      where: { id: record.id },
    });
    expect(untouched.action).toBe('audit-echo.create');
  });

  it('blocks DELETE attempts at the database level', async () => {
    const correlationId = '44444444-4444-4444-8444-dddddddddddd';
    const response = await sendEcho(
      {
        organizationId: orgA,
        actorId: 'actor-echo-delete',
        message: 'blocked-delete',
      },
      { 'x-correlation-id': correlationId },
    );
    expect(response.status).toBe(201);

    const record = await prisma.auditEvent.findFirstOrThrow({
      where: { entityType: 'audit-echo', actorId: 'actor-echo-delete' },
    });

    await expect(
      prisma.$executeRawUnsafe(
        'DELETE FROM "AuditEvent" WHERE "id" = $1',
        record.id,
      ),
    ).rejects.toThrow(/append-only/i);

    const stillThere = await prisma.auditEvent.findUnique({
      where: { id: record.id },
    });
    expect(stillThere).not.toBeNull();
  });

  it('filters search results by actor, action, entity and date range', async () => {
    await sendEcho(
      { organizationId: orgA, actorId: 'actor-search-1', message: 'one' },
      { 'x-correlation-id': '55555555-5555-4555-8555-eeeeeeeeeeee' },
    );
    await sendEcho(
      { organizationId: orgA, actorId: 'actor-search-2', message: 'two' },
      { 'x-correlation-id': '66666666-6666-4666-8666-ffffffffffff' },
    );

    const response = await request(app.getHttpServer())
      .get('/api/v1/audit-events')
      .query({
        organizationId: orgA,
        actorId: 'actor-search-1',
        action: 'audit-echo.create',
        entityType: 'audit-echo',
        from: new Date(Date.now() - 60_000).toISOString(),
        to: new Date(Date.now() + 60_000).toISOString(),
      });

    expect(response.status).toBe(200);
    expect(response.body.total).toBeGreaterThanOrEqual(1);
    expect(response.body.items.every((item: { actorId: string }) => item.actorId === 'actor-search-1')).toBe(true);
    expect(response.body.items.every((item: { action: string }) => item.action === 'audit-echo.create')).toBe(true);
    expect(response.body.items.every((item: { entityType: string }) => item.entityType === 'audit-echo')).toBe(true);
    expect(response.body.items.every((item: Record<string, unknown>) => !('transitionKey' in item))).toBe(true);
  });

  it('isolates search results by organizationId', async () => {
    await sendEcho(
      { organizationId: orgA, actorId: 'actor-iso-1', message: 'a' },
      { 'x-correlation-id': '77777777-7777-4777-8777-aaaaaaaaaaaa' },
    );
    await sendEcho(
      { organizationId: orgB, actorId: 'actor-iso-2', message: 'b' },
      { 'x-correlation-id': '88888888-8888-4888-8888-bbbbbbbbbbbb' },
    );

    const response = await request(app.getHttpServer())
      .get('/api/v1/audit-events')
      .query({ organizationId: orgA });

    expect(response.status).toBe(200);
    expect(
      response.body.items.every(
        (item: { organizationId: string }) => item.organizationId === orgA,
      ),
    ).toBe(true);
    expect(
      response.body.items.every(
        (item: { organizationId: string }) => item.organizationId !== orgB,
      ),
    ).toBe(true);
  });
});
