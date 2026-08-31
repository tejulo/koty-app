import { Injectable } from '@nestjs/common';
import { randomUUID } from 'node:crypto';

import { PrismaService } from '../prisma/prisma.service';
import {
  getAuditChangeFields,
  isExcludedChangeField,
} from './audit.constants';
import {
  computeCanonicalTransitionKey,
  type AuditTransitionInput,
} from './canonical-transition-key';
import {
  AuditInvalidFieldException,
  AuditTransitionConflictException,
} from './audit.exceptions';
import type { FieldError } from '../common/errors/error-response.interface';

/**
 * DEV-36 — Allowed values for the actor type and scope. Mirrors the Prisma
 * enums so the service does not need to depend on the regenerated Prisma
 * client types.
 */
export type AuditActorType = 'USER' | 'SYSTEM' | 'API_KEY' | 'WORKER';
export type AuditScope = 'PLATFORM' | 'ORGANIZATION';

export interface AuditEventInput {
  scope: AuditScope;
  organizationId?: string | null;
  actorType: AuditActorType;
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  occurredAt?: Date;
  correlationId?: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
}

export interface AuditEventRecord {
  id: string;
  scope: AuditScope;
  organizationId: string | null;
  actorType: AuditActorType;
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  occurredAt: Date;
  correlationId: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  createdAt: Date;
  created: boolean;
}

export interface AuditSearchQuery {
  actorType?: AuditActorType;
  actorId?: string;
  action?: string;
  entityType?: string;
  entityId?: string;
  from?: Date;
  to?: Date;
  limit?: number;
  offset?: number;
  organizationId?: string;
}

export interface AuditSearchPage {
  items: AuditEventRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditEventRow {
  id: string;
  scope: AuditScope;
  organizationId: string | null;
  actorType: AuditActorType;
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  occurredAt: Date;
  correlationId: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  createdAt: Date;
}

/**
 * Shape of a row as it lives in the database. Mirrors the columns declared
 * by `apps/api/prisma/schema.prisma`. The `before`/`after` columns are
 * JSONB and may be persisted as `null` (when the allowlist filters every
 * field out) or as a JSON object.
 */
interface AuditEventRowRaw extends AuditEventRow {
  transitionKey: string;
}

interface AuditEventDelegate {
  findUnique(args: {
    where: { scope_transitionKey: { scope: string; transitionKey: string } };
  }): Promise<AuditEventRowRaw | null>;
  findMany(args: {
    where: AuditEventWhereInput;
    orderBy: AuditEventOrderBy;
    take: number;
    skip: number;
  }): Promise<AuditEventRowRaw[]>;
  count(args: { where: AuditEventWhereInput }): Promise<number>;
  create(args: {
    data: AuditEventCreateInput;
  }): Promise<AuditEventRowRaw>;
}

/**
 * Structural shape of `where` for `AuditEvent`. Defined locally so the
 * service can compile against a typed delegate without depending on the
 * regenerated `Prisma.AuditEventWhereInput` type (which only exists after
 * `prisma generate` has produced the client and TypeScript has re-resolved
 * the package). Mirrors `apps/api/prisma/schema.prisma`.
 */
export interface AuditEventWhereInput {
  scope?: AuditScope;
  organizationId?: string | null;
  actorType?: AuditActorType;
  actorId?: string;
  action?: string;
  entityType?: string;
  entityId?: string;
  correlationId?: string;
  occurredAt?: { gte?: Date; lte?: Date };
}

export type AuditEventOrderBy = { occurredAt: 'asc' | 'desc' };

export interface AuditEventCreateInput {
  id?: string;
  scope: AuditScope;
  organizationId: string | null;
  actorType: AuditActorType;
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  occurredAt?: Date;
  correlationId: string;
  transitionKey: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
}

const UNIQUE_VIOLATION_CODE = 'P2002';
const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 200;

/**
 * Shape of a Prisma unique-constraint error. Defined locally so the service
 * stays decoupled from the generated client at type level.
 */
class PrismaUniqueViolationError extends Error {
  constructor(public readonly code: string) {
    super('Prisma unique violation');
    this.name = 'PrismaUniqueViolationError';
  }
}

@Injectable()
export class AuditService {
  constructor(private readonly prismaService: PrismaService) {}

  /**
   * Register a new `AuditEvent`. The method enforces the `before`/`after`
   * allowlist, silently drops excluded secret fields, computes a canonical
   * `transitionKey` and lets the database `@@unique` arbitrate concurrent
   * inserts. A second call with the same transition returns the existing
   * record with `created: false` (idempotent).
   */
  async record(input: AuditEventInput): Promise<AuditEventRecord> {
    const allowlist = getAuditChangeFields(input.entityType);

    // Allowlist + exclusion are validated up front so that a `record` call
    // with disallowed / sensitive fields never reaches the database. A
    // single bad field is enough to throw before any other sanitization
    // step runs.
    this.validateChanges(input.before ?? null, allowlist, 'before');
    this.validateChanges(input.after ?? null, allowlist, 'after');

    const filteredBefore = this.sanitizeChanges(
      input.before ?? null,
      allowlist,
    );
    const filteredAfter = this.sanitizeChanges(
      input.after ?? null,
      allowlist,
    );

    const correlationId = input.correlationId ?? randomUUID();
    const occurredAt = input.occurredAt ?? new Date();

    const transitionInput: AuditTransitionInput = {
      scope: input.scope,
      action: input.action,
      entityType: input.entityType,
      entityId: input.entityId,
      correlationId,
    };
    const transitionKey = computeCanonicalTransitionKey(transitionInput);

    const data: AuditEventCreateInput = {
      scope: input.scope,
      organizationId:
        input.scope === 'ORGANIZATION'
          ? (input.organizationId ?? null)
          : null,
      actorType: input.actorType,
      actorId: input.actorId,
      action: input.action,
      entityType: input.entityType,
      entityId: input.entityId,
      occurredAt,
      correlationId,
      transitionKey,
      before: filteredBefore,
      after: filteredAfter,
    };

    try {
      const created = await this.getDelegate().create({ data });
      return this.toRecord(created, true);
    } catch (error: unknown) {
      if (isPrismaUniqueViolation(error)) {
        const existing = await this.getDelegate().findUnique({
          where: {
            scope_transitionKey: { scope: input.scope, transitionKey },
          },
        });
        if (!existing) {
          throw error;
        }
        if (existing.correlationId !== correlationId) {
          throw new AuditTransitionConflictException();
        }
        return this.toRecord(existing, false);
      }
      throw error;
    }
  }

  /**
   * Search the `AuditEvent` table with the supplied filters. The
   * `organizationId` argument is the scope the caller is allowed to see: it
   * is applied as a hard filter to avoid leaking events from other
   * organizations. To keep the smoke controller self-contained, the search
   * passes the filter through `where` without extra context resolution.
   */
  async search(query: AuditSearchQuery): Promise<AuditSearchPage> {
    const limit = clampLimit(query.limit ?? DEFAULT_LIMIT);
    const offset = clampOffset(query.offset ?? 0);
    const where = this.buildWhere(query);

    const [rows, total] = await Promise.all([
      this.getDelegate().findMany({
        where,
        orderBy: { occurredAt: 'desc' },
        take: limit,
        skip: offset,
      }),
      this.getDelegate().count({ where }),
    ]);

    return {
      items: rows.map((row) => this.toRecord(row, false)),
      total,
      limit,
      offset,
    };
  }

  private validateChanges(
    value: Record<string, unknown> | null,
    allowlist: readonly string[],
    fieldPrefix: 'before' | 'after',
  ): void {
    if (value === null) {
      return;
    }

    const fieldErrors: FieldError[] = [];

    for (const key of Object.keys(value)) {
      if (isExcludedChangeField(key)) {
        continue;
      }
      if (!allowlist.includes(key)) {
        fieldErrors.push({
          field: `${fieldPrefix}.${key}`,
          message: `Field "${key}" is not allowed for entity type`,
        });
      }
    }

    if (fieldErrors.length > 0) {
      throw new AuditInvalidFieldException(fieldErrors);
    }
  }

  private sanitizeChanges(
    value: Record<string, unknown> | null,
    allowlist: readonly string[],
  ): Record<string, unknown> | null {
    if (value === null) {
      return null;
    }

    const result: Record<string, unknown> = {};
    for (const [key, raw] of Object.entries(value)) {
      if (isExcludedChangeField(key)) {
        continue;
      }
      if (!allowlist.includes(key)) {
        continue;
      }
      result[key] = raw;
    }

    return Object.keys(result).length === 0 ? null : result;
  }

  private buildWhere(query: AuditSearchQuery): AuditEventWhereInput {
    const where: AuditEventWhereInput = {};
    if (query.actorType) {
      where.actorType = query.actorType;
    }
    if (query.actorId) {
      where.actorId = query.actorId;
    }
    if (query.action) {
      where.action = query.action;
    }
    if (query.entityType) {
      where.entityType = query.entityType;
    }
    if (query.entityId) {
      where.entityId = query.entityId;
    }
    if (query.organizationId) {
      where.organizationId = query.organizationId;
    }
    if (query.from !== undefined || query.to !== undefined) {
      const occurredAt: { gte?: Date; lte?: Date } = {};
      if (query.from !== undefined) occurredAt.gte = query.from;
      if (query.to !== undefined) occurredAt.lte = query.to;
      where.occurredAt = occurredAt;
    }
    return where;
  }

  private toRecord(
    row: AuditEventRowRaw,
    created: boolean,
  ): AuditEventRecord {
    return {
      id: row.id,
      scope: row.scope,
      organizationId: row.organizationId,
      actorType: row.actorType,
      actorId: row.actorId,
      action: row.action,
      entityType: row.entityType,
      entityId: row.entityId,
      occurredAt: row.occurredAt,
      correlationId: row.correlationId,
      before: row.before,
      after: row.after,
      createdAt: row.createdAt,
      created,
    };
  }

  private getDelegate(): AuditEventDelegate {
    const client = this.prismaService as unknown as {
      auditEvent: AuditEventDelegate;
    };
    return client.auditEvent;
  }
}

function isPrismaUniqueViolation(error: unknown): error is PrismaUniqueViolationError {
  if (typeof error !== 'object' || error === null) {
    return false;
  }
  const code = (error as { code?: unknown }).code;
  return code === UNIQUE_VIOLATION_CODE;
}

function clampLimit(value: number): number {
  if (!Number.isFinite(value) || value <= 0) return DEFAULT_LIMIT;
  if (value > MAX_LIMIT) return MAX_LIMIT;
  return Math.floor(value);
}

function clampOffset(value: number): number {
  if (!Number.isFinite(value) || value < 0) return 0;
  return Math.floor(value);
}
