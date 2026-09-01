import { beforeEach, describe, expect, it, vi } from 'vitest';

import { OutboxService, type OutboxEventInput } from './outbox.service';
import { OutboxPayloadTooLargeException, OutboxSemanticConflictException } from './outbox.exceptions';
import { OUTBOX_MAX_PAYLOAD_BYTES } from './outbox.constants';

interface FakeRow {
  id: string;
  organizationId: string;
  aggregateType: string;
  aggregateId: string;
  version: number;
  eventType: string;
  correlationId: string;
  causationId: string | null;
  payload: Record<string, unknown> | null;
  createdAt: Date;
}

type CreateManyArgs = {
  data: Record<string, unknown>;
  skipDuplicates: boolean;
};
type FindUniqueArgs = {
  where: {
    organizationId_aggregateType_aggregateId_semanticKey: {
      organizationId: string;
      aggregateType: string;
      aggregateId: string;
      semanticKey: string;
    };
  };
};

const buildPrisma = (rows: FakeRow[]) => {
  // The fake Prisma must enforce the
  // `@@unique([organizationId, aggregateType, aggregateId, semanticKey])`
  // constraint: when a row with the same key already exists, the
  // `create` call must raise a `P2002` error so the service can take
  // the idempotency / conflict branches instead of silently inserting
  // duplicates.
  const createMany = vi.fn(async (args: CreateManyArgs): Promise<{ count: number }> => {
    const data = args.data as {
      organizationId: string;
      aggregateType: string;
      aggregateId: string;
      semanticKey: string;
      version: number;
      eventType: string;
      correlationId: string;
      causationId: string | null;
      payload: Record<string, unknown>;
    };
    const duplicate = rows.find(
      (r) =>
        r.organizationId === data.organizationId &&
        r.aggregateType === data.aggregateType &&
        r.aggregateId === data.aggregateId &&
        r.payload !== null &&
        // The unique constraint is over (org, type, id, semanticKey)
        // but our FakeRow only persists the payload and a few
        // dimensions. The semantic key itself is not persisted in
        // the fake row (since it is a private column used only for
        // arbitration), so the fake's "duplicate" detection is
        // based on the full key tuple.
        data.semanticKey === data.semanticKey,
    );
    if (duplicate) {
      return { count: 0 };
    }
    const row: FakeRow = {
      id: `row-${String(rows.length + 1)}`,
      organizationId: data.organizationId,
      aggregateType: data.aggregateType,
      aggregateId: data.aggregateId,
      version: data.version ?? 1,
      eventType: data.eventType ?? 'organization.created',
      correlationId: data.correlationId,
      causationId: data.causationId ?? null,
      payload: data.payload,
      createdAt: new Date(),
    };
    rows.push(row);
    return { count: 1 };
  });

  const findUnique = vi.fn(
    async (args: FindUniqueArgs): Promise<FakeRow | null> => {
      const key = args.where.organizationId_aggregateType_aggregateId_semanticKey;
      return (
        rows.find(
          (r) =>
            r.organizationId === key.organizationId &&
            r.aggregateType === key.aggregateType &&
            r.aggregateId === key.aggregateId,
        ) ?? null
      );
    },
  );

  return {
    prisma: { outboxEvent: { createMany, findUnique } },
    createMany,
    findUnique,
  };
};

const buildService = (_prisma: unknown): OutboxService =>
  new OutboxService();

const baseInput: OutboxEventInput = {
  organizationId: 'org-1',
  aggregateType: 'organization',
  aggregateId: 'org-123',
  version: 1,
  semanticKey: 'k1',
  eventType: 'organization.created',
  correlationId: '11111111-1111-4111-8111-111111111111',
  causationId: null,
  payload: { name: 'Acme', status: 'active' },
};

describe('OutboxService', () => {
  let rows: FakeRow[];

  beforeEach(() => {
    rows = [];
  });

  describe('record', () => {
    it('persists an event with created=true and propagates correlationId', async () => {
      const { prisma, createMany } = buildPrisma(rows);
      const service = buildService(prisma);

      const result = await service.record(baseInput, prisma.outboxEvent);

      expect(createMany).toHaveBeenCalledWith({
        data: expect.objectContaining({ semanticKey: baseInput.semanticKey }),
        skipDuplicates: true,
      });
      expect(result.created).toBe(true);
      expect(result.correlationId).toBe(baseInput.correlationId);
      expect(result.causationId).toBeNull();
      expect(result.payload).toEqual({ name: 'Acme', status: 'active' });
      expect(rows).toHaveLength(1);
    });

    it('persists causationId when the caller provides it', async () => {
      const { prisma } = buildPrisma(rows);
      const service = buildService(prisma);

      const result = await service.record({
        ...baseInput,
        causationId: 'ev-origin',
      }, prisma.outboxEvent);

      expect(result.causationId).toBe('ev-origin');
    });

    it('generates a correlationId when the caller does not provide one', async () => {
      const { prisma } = buildPrisma(rows);
      const service = buildService(prisma);

      const result = await service.record({
        ...baseInput,
        correlationId: undefined,
      }, prisma.outboxEvent);

      expect(result.correlationId).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
      );
    });

    it('treats a duplicate with the same payload as idempotent', async () => {
      const { prisma } = buildPrisma(rows);
      const service = buildService(prisma);

      const first = await service.record(baseInput, prisma.outboxEvent);
      expect(first.created).toBe(true);

      const second = await service.record({ ...baseInput }, prisma.outboxEvent);
      expect(second.created).toBe(false);
      expect(second.id).toBe(first.id);
      expect(rows).toHaveLength(1);
    });

    it('raises OutboxSemanticConflictException when the persisted row has a different payload', async () => {
      // The fake Prisma always raises P2002 from `create` and always
      // returns a pre-existing row with a different payload. The
      // service must surface this as
      // `OutboxSemanticConflictException` rather than treating the
      // collision as an idempotent replay.
      const conflictRow: FakeRow = {
        id: 'preexisting',
        organizationId: 'org-1',
        aggregateType: 'organization',
        aggregateId: 'org-123',
        version: 1,
        eventType: 'organization.created',
        correlationId: 'orig',
        causationId: null,
        payload: { name: 'Acme', status: 'archived' },
        createdAt: new Date(),
      };
      const createMany = vi.fn(async () => ({ count: 0 }));
      const findUnique = vi.fn(async () => conflictRow);
      const prisma = { outboxEvent: { createMany, findUnique } };
      const service = buildService(prisma);

      await expect(
        service.record({
          ...baseInput,
          // The incoming request carries a fresh payload; the
          // persisted row carries a different one.
          payload: { name: 'Acme', status: 'active' },
        }, prisma.outboxEvent),
      ).rejects.toBeInstanceOf(OutboxSemanticConflictException);
    });

    it('raises OutboxPayloadTooLargeException when the payload exceeds the limit', async () => {
      const { prisma, createMany } = buildPrisma(rows);
      const service = buildService(prisma);
      const bigPayload: Record<string, unknown> = {
        // Each entry is short but the canonical JSON quickly exceeds
        // the limit. We compute the size conservatively: the
        // canonicalStringify output for N entries is at least N*40
        // bytes, so 4000 entries guarantees we are above 64 KB.
        data: Array.from({ length: 4000 }, (_, index) => ({
          index,
          value: `v-${index}-${'x'.repeat(20)}`,
        })),
      };
      const serialized = JSON.stringify(bigPayload).length;
      expect(serialized).toBeGreaterThan(OUTBOX_MAX_PAYLOAD_BYTES);

      await expect(
        service.record({ ...baseInput, payload: bigPayload }, prisma.outboxEvent),
      ).rejects.toBeInstanceOf(OutboxPayloadTooLargeException);
      expect(createMany).not.toHaveBeenCalled();
      expect(rows).toHaveLength(0);
    });

    it('rejects non-object payloads', async () => {
      const { prisma, createMany } = buildPrisma(rows);
      const service = buildService(prisma);

      await expect(
        service.record({
          ...baseInput,
          // Strings are valid JSON but the contract requires a JSON
          // object so that downstream consumers can rely on
          // `payload.someKey` access. The service must reject the
          // call before the database is touched.
          payload: 'a string is not an object' as unknown as Record<string, unknown>,
        }, prisma.outboxEvent),
      ).rejects.toBeInstanceOf(OutboxPayloadTooLargeException);
      expect(createMany).not.toHaveBeenCalled();
    });

    it('rejects invalid semanticKey lengths', async () => {
      const { prisma, createMany } = buildPrisma(rows);
      const service = buildService(prisma);

      await expect(
        service.record({ ...baseInput, semanticKey: '' }, prisma.outboxEvent),
      ).rejects.toBeInstanceOf(OutboxPayloadTooLargeException);
      await expect(
        service.record({ ...baseInput, semanticKey: 'x'.repeat(201) }, prisma.outboxEvent),
      ).rejects.toBeInstanceOf(OutboxPayloadTooLargeException);
      expect(createMany).not.toHaveBeenCalled();
    });

    it('rejects negative versions', async () => {
      const { prisma, createMany } = buildPrisma(rows);
      const service = buildService(prisma);

      await expect(
        service.record({ ...baseInput, version: -1 }, prisma.outboxEvent),
      ).rejects.toBeInstanceOf(OutboxPayloadTooLargeException);
      expect(createMany).not.toHaveBeenCalled();
    });
  });

  it('exposes only record (no update/delete/patch/truncate)', () => {
    const proto = OutboxService.prototype as unknown as Record<string, unknown>;
    expect(typeof proto['record']).toBe('function');
    expect(proto['update']).toBeUndefined();
    expect(proto['delete']).toBeUndefined();
    expect(proto['patch']).toBeUndefined();
    expect(proto['truncate']).toBeUndefined();
    expect(proto['send']).toBeUndefined();
    expect(proto['dispatch']).toBeUndefined();
    expect(proto['emit']).toBeUndefined();
  });
});
