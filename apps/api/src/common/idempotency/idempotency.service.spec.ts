import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Prisma } from '@prisma/client';

import {
  IdempotencyAlreadyCommittedError,
  IdempotencyService,
} from './idempotency.service';
import { IdempotencyKeyReusedException } from './idempotency.exceptions';

interface FakeRecord {
  organizationId: string;
  actorId: string;
  commandType: string;
  idempotencyKey: string;
  requestFingerprint: string;
  responseStatus: number;
  responseBody: unknown;
}

type CreateArgs = {
  data: {
    organizationId: string;
    actorId: string;
    commandType: string;
    idempotencyKey: string;
    requestFingerprint: string;
    responseStatus: number;
    responseBody: unknown;
  };
};

const buildPrisma = (records: FakeRecord[]) => {
  const findUnique = vi.fn(
    async (args: {
      where: {
        organizationId_actorId_commandType_idempotencyKey: {
          organizationId: string;
          actorId: string;
          commandType: string;
          idempotencyKey: string;
        };
      };
    }) => {
      const where = args.where.organizationId_actorId_commandType_idempotencyKey;
      const found = records.find(
        (r) =>
          r.organizationId === where.organizationId &&
          r.actorId === where.actorId &&
          r.commandType === where.commandType &&
          r.idempotencyKey === where.idempotencyKey,
      );
      if (!found) {
        return null;
      }
      return {
        requestFingerprint: found.requestFingerprint,
        responseStatus: found.responseStatus,
        responseBody: found.responseBody,
      };
    },
  );
  const create = vi.fn(async (args: CreateArgs) => {
    const duplicate = records.some(
      (r) =>
        r.organizationId === args.data.organizationId &&
        r.actorId === args.data.actorId &&
        r.commandType === args.data.commandType &&
        r.idempotencyKey === args.data.idempotencyKey,
    );
    if (duplicate) {
      throw new Prisma.PrismaClientKnownRequestError(
        'Unique constraint failed',
        {
          code: 'P2002',
          clientVersion: 'test',
        },
      );
    }
    records.push(args.data);
    return args.data;
  });

  const prisma = {
    idempotencyRecord: { findUnique, create },
  };

  return { prisma, findUnique, create };
};

const buildService = (
  prisma: { idempotencyRecord: { findUnique: unknown; create: unknown } },
): IdempotencyService =>
  new IdempotencyService(
    prisma as unknown as ConstructorParameters<typeof IdempotencyService>[0],
  );

describe('IdempotencyService', () => {
  let records: FakeRecord[];

  beforeEach(() => {
    records = [];
  });

  describe('run', () => {
    it('reuses the cached response when the same key and fingerprint arrive', async () => {
      const fingerprint = 'fp-1';
      records.push({
        organizationId: 'org-1',
        actorId: 'actor-1',
        commandType: 'create-organization',
        idempotencyKey: 'k1',
        requestFingerprint: fingerprint,
        responseStatus: 201,
        responseBody: { id: 'x' },
      });
      const { prisma } = buildPrisma(records);
      const service = buildService(prisma);

      const execute = vi.fn(async () => {
        throw new Error('execute should not be called on a cache hit');
      });

      const result = await service.run({
        scope: {
          organizationId: 'org-1',
          actorId: 'actor-1',
          commandType: 'create-organization',
        },
        key: 'k1',
        request: { name: 'Acme' },
        execute,
      });

      expect(execute).not.toHaveBeenCalled();
      expect(result).toEqual({
        status: 201,
        body: { id: 'x' },
        replayed: true,
      });
    });

    it('throws IdempotencyKeyReusedException when the fingerprint differs', async () => {
      records.push({
        organizationId: 'org-1',
        actorId: 'actor-1',
        commandType: 'create-organization',
        idempotencyKey: 'k1',
        requestFingerprint: 'fp-original',
        responseStatus: 201,
        responseBody: { id: 'x' },
      });
      const { prisma } = buildPrisma(records);
      const service = buildService(prisma);

      const execute = vi.fn(async () => {
        throw new Error('execute should not be called on fingerprint conflict');
      });

      await expect(
        service.run({
          scope: {
            organizationId: 'org-1',
            actorId: 'actor-1',
            commandType: 'create-organization',
          },
          key: 'k1',
          request: { name: 'Beta' },
          execute,
        }),
      ).rejects.toBeInstanceOf(IdempotencyKeyReusedException);
      expect(execute).not.toHaveBeenCalled();
    });

    it('persists a new IdempotencyRecord when execute() resolves', async () => {
      const { prisma, create } = buildPrisma(records);
      const service = buildService(prisma);

      const onCommit = vi.fn();
      const result = await service.run({
        scope: {
          organizationId: 'org-1',
          actorId: 'actor-1',
          commandType: 'create-organization',
        },
        key: 'k1',
        request: { name: 'Acme' },
        execute: async () => ({ status: 201, body: { id: 'created' } }),
        onCommit,
      });

      expect(create).toHaveBeenCalledTimes(1);
      expect(result.replayed).toBe(false);
      expect(result.status).toBe(201);
      expect(result.body).toEqual({ id: 'created' });
      expect(onCommit).toHaveBeenCalledWith({ id: 'created' });
    });

    it('does not persist an IdempotencyRecord when execute() throws before commit', async () => {
      const { prisma, create } = buildPrisma(records);
      const service = buildService(prisma);

      await expect(
        service.run({
          scope: {
            organizationId: 'org-1',
            actorId: 'actor-1',
            commandType: 'create-organization',
          },
          key: 'k1',
          request: { name: 'Acme' },
          execute: async () => {
            throw new Error('domain validation failed');
          },
        }),
      ).rejects.toThrow('domain validation failed');

      expect(create).not.toHaveBeenCalled();
      expect(records).toHaveLength(0);
    });

    it('treats a concurrent commit with the same fingerprint as idempotent', async () => {
      records.push({
        organizationId: 'org-1',
        actorId: 'actor-1',
        commandType: 'create-organization',
        idempotencyKey: 'k1',
        requestFingerprint: 'fp-1',
        responseStatus: 201,
        responseBody: { id: 'x' },
      });

      const { prisma } = buildPrisma(records);
      const service = buildService(prisma);

      const execute = vi.fn(async () => {
        throw new Error('execute should not be called on a cache hit');
      });

      const result = await service.run({
        scope: {
          organizationId: 'org-1',
          actorId: 'actor-1',
          commandType: 'create-organization',
        },
        key: 'k1',
        request: { name: 'Acme' },
        execute,
      });

      expect(execute).not.toHaveBeenCalled();
      expect(result.replayed).toBe(true);
    });
  });

  describe('IdempotencyAlreadyCommittedError', () => {
    it('is a class with a descriptive message', () => {
      const error = new IdempotencyAlreadyCommittedError();
      expect(error).toBeInstanceOf(Error);
      expect(error.message).toMatch(/Cannot commit/);
    });
  });
});