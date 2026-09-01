import { Injectable } from '@nestjs/common';
import { randomUUID } from 'node:crypto';

import { canonicalStringify } from '../common/idempotency/canonical-fingerprint';
import {
  MAX_SEMANTIC_KEY_LENGTH,
  MIN_SEMANTIC_KEY_LENGTH,
  OUTBOX_MAX_PAYLOAD_BYTES,
} from './outbox.constants';
import {
  computeOutboxCanonicalFingerprint,
  type OutboxCanonicalFingerprintInput,
} from './outbox-canonical-fingerprint';
import {
  OutboxPayloadTooLargeException,
  OutboxSemanticConflictException,
} from './outbox.exceptions';

export interface OutboxEventInput {
  organizationId: string;
  aggregateType: string;
  aggregateId: string;
  version: number;
  semanticKey: string;
  eventType: string;
  correlationId?: string;
  causationId?: string | null;
  payload: Record<string, unknown>;
}

export interface OutboxEventRecord {
  id: string;
  organizationId: string;
  aggregateType: string;
  aggregateId: string;
  version: number;
  eventType: string;
  correlationId: string;
  causationId: string | null;
  payload: Record<string, unknown>;
  createdAt: Date;
  created: boolean;
}

interface OutboxEventRow {
  id: string;
  organizationId: string;
  aggregateType: string;
  aggregateId: string;
  version: number;
  eventType: string;
  correlationId: string;
  causationId: string | null;
  payload: Record<string, unknown>;
  createdAt: Date;
}

interface OutboxEventCreateInput {
  id?: string;
  organizationId: string;
  aggregateType: string;
  aggregateId: string;
  version: number;
  semanticKey: string;
  eventType: string;
  correlationId: string;
  causationId: string | null;
  payload: Record<string, unknown>;
}

/**
 * Structural type of the Prisma delegate of `OutboxEvent`. Mirrors the
 * shape produced by `prisma generate` so the service can compile against
 * a typed delegate without depending on the regenerated `PrismaClient`
 * type. Keep this in sync with `apps/api/prisma/schema.prisma`.
 *
 * `findUnique` is narrowed to return `Promise<OutboxEventRow>` (no
 * `| null`) on purpose: by the time the service invokes it from the
 * idempotency branch of `record`, a `P2002` error has just been
 * raised by `create`, which means the unique constraint
 * `(organizationId, aggregateType, aggregateId, semanticKey)` is
 * already violated and the colliding row must exist. The append-only
 * trigger installed by the `20260831022810_add_outbox_event` migration
 * prevents the row from being deleted between the `create` and the
 * `findUnique` calls, so the call MUST yield a non-null result. The
 * non-nullable return type makes that invariant explicit and lets the
 * TypeScript compiler / `@typescript-eslint/no-unnecessary-condition`
 * rule trust the lookup result without a defensive branch.
 */
export interface OutboxEventDelegate {
  findUnique(args: {
    where: {
      organizationId_aggregateType_aggregateId_semanticKey: {
        organizationId: string;
        aggregateType: string;
        aggregateId: string;
        semanticKey: string;
      };
    };
  }): Promise<OutboxEventRow>;
  createMany(args: {
    data: OutboxEventCreateInput;
    skipDuplicates: boolean;
  }): Promise<{ count: number }>;
}

@Injectable()
export class OutboxService {
  /**
   * Persist a new `OutboxEvent` row using the **caller-managed**
   * transaction. The service intentionally does not open its own
   * transaction: domain handlers wrap `prisma.$transaction([...])`
   * (or `prisma.$transaction(async (tx) => { ... })`) so the
   * outbox write is atomic with the rest of the command.
   *
   * The method enforces the payload size limit before reaching the
   * database, computes a canonical fingerprint for conflict detection
   * and treats a `P2002` unique violation as an idempotent replay when
   * the fingerprint matches.
   */
  async record(
    input: OutboxEventInput,
    outboxEvent: OutboxEventDelegate,
  ): Promise<OutboxEventRecord> {
    this.assertValidInput(input);
    this.assertPayloadFits(input.payload);

    const correlationId = input.correlationId ?? randomUUID();
    const causationId = input.causationId ?? null;

    const fingerprintInput: OutboxCanonicalFingerprintInput = {
      organizationId: input.organizationId,
      aggregateType: input.aggregateType,
      aggregateId: input.aggregateId,
      version: input.version,
      semanticKey: input.semanticKey,
      eventType: input.eventType,
      payload: input.payload,
    };
    const fingerprint = computeOutboxCanonicalFingerprint(fingerprintInput);

    const data: OutboxEventCreateInput = {
      organizationId: input.organizationId,
      aggregateType: input.aggregateType,
      aggregateId: input.aggregateId,
      version: input.version,
      semanticKey: input.semanticKey,
      eventType: input.eventType,
      correlationId,
      causationId,
      payload: input.payload,
    };

    const result = await outboxEvent.createMany({
      data,
      skipDuplicates: true,
    });
    const existing = await outboxEvent.findUnique({
      where: {
        organizationId_aggregateType_aggregateId_semanticKey: {
          organizationId: input.organizationId,
          aggregateType: input.aggregateType,
          aggregateId: input.aggregateId,
          semanticKey: input.semanticKey,
        },
      },
    });
    if (result.count === 1) {
      return this.toRecord(existing, true);
    }

    const existingFingerprint = computeOutboxCanonicalFingerprint({
      organizationId: existing.organizationId,
      aggregateType: existing.aggregateType,
      aggregateId: existing.aggregateId,
      version: existing.version,
      semanticKey: input.semanticKey,
      eventType: existing.eventType,
      payload: existing.payload,
    });
    if (existingFingerprint !== fingerprint) {
      throw new OutboxSemanticConflictException();
    }
    return this.toRecord(existing, false);
  }

  private assertValidInput(input: OutboxEventInput): void {
    if (!input.organizationId || input.organizationId.length === 0) {
      throw new OutboxPayloadTooLargeException([
        {
          field: 'organizationId',
          message: 'organizationId must be a non-empty string',
        },
      ]);
    }
    if (!input.aggregateType || input.aggregateType.length === 0) {
      throw new OutboxPayloadTooLargeException([
        {
          field: 'aggregateType',
          message: 'aggregateType must be a non-empty string',
        },
      ]);
    }
    if (!input.aggregateId || input.aggregateId.length === 0) {
      throw new OutboxPayloadTooLargeException([
        {
          field: 'aggregateId',
          message: 'aggregateId must be a non-empty string',
        },
      ]);
    }
    if (!Number.isInteger(input.version) || input.version < 0) {
      throw new OutboxPayloadTooLargeException([
        {
          field: 'version',
          message: 'version must be a non-negative integer',
        },
      ]);
    }
    if (
      !input.semanticKey ||
      input.semanticKey.length < MIN_SEMANTIC_KEY_LENGTH ||
      input.semanticKey.length > MAX_SEMANTIC_KEY_LENGTH
    ) {
      throw new OutboxPayloadTooLargeException([
        {
          field: 'semanticKey',
          message: `semanticKey must be between ${String(MIN_SEMANTIC_KEY_LENGTH)} and ${String(MAX_SEMANTIC_KEY_LENGTH)} characters`,
        },
      ]);
    }
    if (!input.eventType || input.eventType.length === 0) {
      throw new OutboxPayloadTooLargeException([
        {
          field: 'eventType',
          message: 'eventType must be a non-empty string',
        },
      ]);
    }
    if (typeof input.payload !== 'object' || Array.isArray(input.payload)) {
      throw new OutboxPayloadTooLargeException([
        {
          field: 'payload',
          message: 'payload must be a JSON object',
        },
      ]);
    }
  }

  private assertPayloadFits(payload: Record<string, unknown>): void {
    const serialized = canonicalStringify(payload);
    const size = Buffer.byteLength(serialized, 'utf8');
    if (size > OUTBOX_MAX_PAYLOAD_BYTES) {
      throw new OutboxPayloadTooLargeException([
        {
          field: 'payload',
          message: `payload must be at most ${String(OUTBOX_MAX_PAYLOAD_BYTES)} bytes (got ${String(size)})`,
        },
      ]);
    }
  }

  private toRecord(row: OutboxEventRow, created: boolean): OutboxEventRecord {
    return {
      id: row.id,
      organizationId: row.organizationId,
      aggregateType: row.aggregateType,
      aggregateId: row.aggregateId,
      version: row.version,
      eventType: row.eventType,
      correlationId: row.correlationId,
      causationId: row.causationId,
      payload: row.payload,
      createdAt: row.createdAt,
      created,
    };
  }

}
