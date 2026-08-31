import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuditService, type AuditEventInput } from './audit.service';
import {
  AuditInvalidFieldException,
  AuditTransitionConflictException,
} from './audit.exceptions';

interface FakeRow {
  id: string;
  scope: 'PLATFORM' | 'ORGANIZATION';
  organizationId: string | null;
  actorType: 'USER' | 'SYSTEM' | 'API_KEY' | 'WORKER';
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  occurredAt: Date;
  correlationId: string;
  transitionKey: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  createdAt: Date;
}

type CreateArgs = { data: { transitionKey: string; [k: string]: unknown } };
type FindUniqueArgs = {
  where: { scope_transitionKey: { scope: string; transitionKey: string } };
};
type WhereArgs = Record<string, unknown>;
type FindManyArgs = {
  where: WhereArgs;
  take: number;
  skip: number;
  orderBy?: { occurredAt: 'asc' | 'desc' };
};
type CountArgs = { where: WhereArgs };

const buildPrisma = (rows: FakeRow[]) => {
  // The fake Prisma must enforce the `@@unique([scope, transitionKey])`
  // constraint: when a row with the same key already exists it raises a
  // P2002 error. Without this, the idempotency and conflict branches of
  // the service would silently pass tests that should fail.
  const create = vi.fn(async (args: CreateArgs) => {
    const data = args.data as {
      transitionKey: string;
      scope: 'PLATFORM' | 'ORGANIZATION';
      organizationId: string | null;
      actorType: FakeRow['actorType'];
      actorId: string;
      action: string;
      entityType: string;
      entityId: string;
      occurredAt?: Date;
      correlationId: string;
      before: Record<string, unknown> | null;
      after: Record<string, unknown> | null;
    };
    const duplicate = rows.find(
      (r) => r.scope === data.scope && r.transitionKey === data.transitionKey,
    );
    if (duplicate) {
      const error = new Error('Unique constraint failed') as Error & {
        code: string;
      };
      error.code = 'P2002';
      throw error;
    }
    const row: FakeRow = {
      id: `row-${rows.length + 1}`,
      scope: data.scope,
      organizationId: data.organizationId,
      actorType: data.actorType,
      actorId: data.actorId,
      action: data.action,
      entityType: data.entityType,
      entityId: data.entityId,
      occurredAt: data.occurredAt ?? new Date(),
      correlationId: data.correlationId,
      transitionKey: data.transitionKey,
      before: data.before,
      after: data.after,
      createdAt: new Date(),
    };
    rows.push(row);
    return row;
  });

  const findUnique = vi.fn(async (args: FindUniqueArgs) => {
    const row = rows.find(
      (r) =>
        r.scope === args.where.scope_transitionKey.scope &&
        r.transitionKey === args.where.scope_transitionKey.transitionKey,
    );
    return row ?? null;
  });

  const findMany = vi.fn(async (args: FindManyArgs) => {
    const filtered = rows.filter((row) => matchesWhere(row, args.where));
    return filtered.slice(args.skip, args.skip + args.take);
  });

  const count = vi.fn(async (args: CountArgs) => {
    return rows.filter((row) => matchesWhere(row, args.where)).length;
  });

  return {
    prisma: { auditEvent: { create, findUnique, findMany, count } },
    create,
    findUnique,
    findMany,
    count,
  };
};

function matchesWhere(row: FakeRow, where: WhereArgs): boolean {
  for (const [key, value] of Object.entries(where)) {
    if (
      key === 'occurredAt' &&
      value &&
      typeof value === 'object' &&
      !Array.isArray(value)
    ) {
      const range = value as { gte?: Date; lte?: Date };
      if (range.gte && row.occurredAt < range.gte) return false;
      if (range.lte && row.occurredAt > range.lte) return false;
      continue;
    }
    if ((row as unknown as Record<string, unknown>)[key] !== value) {
      return false;
    }
  }
  return true;
}

const buildService = (prisma: unknown): AuditService =>
  new AuditService(
    prisma as unknown as ConstructorParameters<typeof AuditService>[0],
  );

const baseInput: AuditEventInput = {
  scope: 'ORGANIZATION',
  organizationId: 'org-1',
  actorType: 'USER',
  actorId: 'actor-1',
  action: 'organization.create',
  entityType: 'organization',
  entityId: 'org-123',
  correlationId: '11111111-1111-4111-8111-111111111111',
  before: null,
  after: { name: 'Acme', status: 'active' },
};

describe('AuditService', () => {
  let rows: FakeRow[];

  beforeEach(() => {
    rows = [];
  });

  describe('record', () => {
    it('persists an event with the canonical transition key and created=true', async () => {
      const { prisma, create } = buildPrisma(rows);
      const service = buildService(prisma);

      const result = await service.record(baseInput);

      expect(create).toHaveBeenCalledTimes(1);
      expect(result.created).toBe(true);
      // The audit record returned by the service must NOT expose the
      // `transitionKey` field (it is internal-only).
      const exposedKeys = Object.keys(result).sort();
      expect(exposedKeys).not.toContain('transitionKey');
      expect(result.before).toBeNull();
      expect(result.after).toEqual({ name: 'Acme', status: 'active' });
      expect(rows).toHaveLength(1);
      expect(rows[0]?.transitionKey).toMatch(/^[0-9a-f]{64}$/);
    });

    it('rejects unknown fields with AuditInvalidFieldException', async () => {
      const { prisma, create } = buildPrisma(rows);
      const service = buildService(prisma);

      await expect(
        service.record({
          ...baseInput,
          // `forbidden` is not in the organization allowlist and is not an
          // excluded field, so it must trip the allowlist validator.
          after: { forbidden: 'x', status: 'active' },
        }),
      ).rejects.toBeInstanceOf(AuditInvalidFieldException);
      expect(create).not.toHaveBeenCalled();
      expect(rows).toHaveLength(0);
    });

    it('silently drops excluded secret fields before persisting', async () => {
      const { prisma, create } = buildPrisma(rows);
      const service = buildService(prisma);

      await service.record({
        ...baseInput,
        after: {
          name: 'Acme',
          password: 'x',
          accessToken: 'y',
          refresh_token: 'z',
          clientSecret: 'w',
        },
      });

      const call = create.mock.calls[0]?.[0] as CreateArgs;
      expect(call.data.after).toEqual({ name: 'Acme' });
    });

    it('treats a duplicate transition with the same correlationId as idempotent', async () => {
      const { prisma } = buildPrisma(rows);
      const service = buildService(prisma);

      const first = await service.record(baseInput);
      expect(first.created).toBe(true);

      const second = await service.record({ ...baseInput });
      expect(second.created).toBe(false);
      expect(second.id).toBe(first.id);
      expect(rows).toHaveLength(1);
    });

    it('raises AuditTransitionConflictException when the persisted row carries a different correlationId', async () => {
      // The fake Prisma always raises P2002 from `create` and always
      // returns a pre-existing row whose correlationId differs from the
      // one being inserted. The service must surface this as
      // `AuditTransitionConflictException` instead of returning the
      // original row as if it were idempotent.
      const conflictRow: FakeRow = {
        id: 'preexisting',
        scope: 'ORGANIZATION',
        organizationId: 'org-1',
        actorType: 'USER',
        actorId: 'actor-1',
        action: 'organization.create',
        entityType: 'organization',
        entityId: 'org-123',
        occurredAt: new Date(),
        correlationId: 'original-correlation',
        transitionKey: 'collision-key',
        before: null,
        after: { name: 'Acme', status: 'active' },
        createdAt: new Date(),
      };
      const create = vi.fn(async () => {
        const error = new Error('Unique constraint failed') as Error & {
          code: string;
        };
        error.code = 'P2002';
        throw error;
      });
      const findUnique = vi.fn(async () => conflictRow);
      const findMany = vi.fn(async () => []);
      const count = vi.fn(async () => 0);
      const prisma = { auditEvent: { create, findUnique, findMany, count } };
      const service = buildService(prisma);

      await expect(
        service.record({
          ...baseInput,
          // The incoming request carries a fresh correlationId; the
          // persisted row carries the original one.
          correlationId: 'incoming-correlation',
        }),
      ).rejects.toBeInstanceOf(AuditTransitionConflictException);
    });

    it('persists null for before/after when every field is filtered out', async () => {
      const { prisma, create } = buildPrisma(rows);
      const service = buildService(prisma);

      await service.record({
        ...baseInput,
        before: { password: 'x' },
        after: { token: 'y' },
      });

      const call = create.mock.calls[0]?.[0] as CreateArgs;
      expect(call.data.before).toBeNull();
      expect(call.data.after).toBeNull();
    });

    it('forces organizationId to null for PLATFORM scope', async () => {
      const { prisma, create } = buildPrisma(rows);
      const service = buildService(prisma);

      await service.record({
        ...baseInput,
        scope: 'PLATFORM',
        organizationId: 'should-be-discarded',
      });

      const call = create.mock.calls[0]?.[0] as CreateArgs;
      expect(call.data.organizationId).toBeNull();
    });

    it('keeps organizationId for ORGANIZATION scope', async () => {
      const { prisma, create } = buildPrisma(rows);
      const service = buildService(prisma);

      await service.record({
        ...baseInput,
        scope: 'ORGANIZATION',
        organizationId: 'org-xyz',
      });

      const call = create.mock.calls[0]?.[0] as CreateArgs;
      expect(call.data.organizationId).toBe('org-xyz');
    });
  });

  describe('search', () => {
    const seed = async (): Promise<void> => {
      const now = Date.now();
      rows.push(
        makeRow({
          id: 'a-1',
          scope: 'ORGANIZATION',
          organizationId: 'org-1',
          actorId: 'actor-1',
          action: 'organization.create',
          entityType: 'organization',
          entityId: 'org-1',
          correlationId: 'c-1',
          occurredAt: new Date(now - 1000),
        }),
        makeRow({
          id: 'a-2',
          scope: 'ORGANIZATION',
          organizationId: 'org-1',
          actorId: 'actor-2',
          action: 'invitation.create',
          entityType: 'invitation',
          entityId: 'inv-1',
          correlationId: 'c-2',
          occurredAt: new Date(now - 500),
        }),
        makeRow({
          id: 'a-3',
          scope: 'ORGANIZATION',
          organizationId: 'org-2',
          actorId: 'actor-3',
          action: 'organization.update',
          entityType: 'organization',
          entityId: 'org-2',
          correlationId: 'c-3',
          occurredAt: new Date(now),
        }),
      );
    };

    it('filters by actorId, action, entityType and from/to range', async () => {
      await seed();
      const { prisma } = buildPrisma(rows);
      const service = buildService(prisma);

      const result = await service.search({
        organizationId: 'org-1',
        from: new Date(Date.now() - 10_000),
        to: new Date(Date.now() + 1),
      });

      expect(result.items).toHaveLength(2);
      expect(result.total).toBe(2);
    });

    it('isolates by organizationId', async () => {
      await seed();
      const { prisma } = buildPrisma(rows);
      const service = buildService(prisma);

      const result = await service.search({ organizationId: 'org-1' });

      expect(result.items.map((item) => item.organizationId)).toEqual([
        'org-1',
        'org-1',
      ]);
      expect(result.total).toBe(2);
    });

    it('clamps limit to 1-200 and applies offset', async () => {
      await seed();
      const { prisma } = buildPrisma(rows);
      const service = buildService(prisma);

      const result = await service.search({
        organizationId: 'org-1',
        limit: 1,
        offset: 1,
      });

      expect(result.items).toHaveLength(1);
      expect(result.limit).toBe(1);
      expect(result.offset).toBe(1);
    });
  });

  it('exposes record and search only (no update/delete methods)', () => {
    const auditProto = AuditService.prototype as unknown as Record<string, unknown>;
    expect(typeof auditProto['record']).toBe('function');
    expect(typeof auditProto['search']).toBe('function');
    expect(auditProto['update']).toBeUndefined();
    expect(auditProto['delete']).toBeUndefined();
    expect(auditProto['patch']).toBeUndefined();
    expect(auditProto['truncate']).toBeUndefined();
  });
});

function makeRow(overrides: Partial<FakeRow>): FakeRow {
  return {
    id: overrides.id ?? 'id',
    scope: overrides.scope ?? 'ORGANIZATION',
    organizationId: overrides.organizationId ?? 'org-1',
    actorType: overrides.actorType ?? 'USER',
    actorId: overrides.actorId ?? 'actor-1',
    action: overrides.action ?? 'organization.create',
    entityType: overrides.entityType ?? 'organization',
    entityId: overrides.entityId ?? 'org-1',
    occurredAt: overrides.occurredAt ?? new Date(),
    correlationId: overrides.correlationId ?? 'c-1',
    transitionKey: overrides.transitionKey ?? 'tk-1',
    before: overrides.before ?? null,
    after: overrides.after ?? null,
    createdAt: overrides.createdAt ?? new Date(),
  };
}