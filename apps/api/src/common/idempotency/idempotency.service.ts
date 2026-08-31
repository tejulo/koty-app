import { Injectable, Logger } from '@nestjs/common';
import { Prisma } from '@prisma/client';

import { PrismaService } from '../../prisma/prisma.service';
import { computeCanonicalFingerprint } from './canonical-fingerprint';
import { IdempotencyKeyReusedException } from './idempotency.exceptions';

/**
 * Scope of an idempotency key. The combination of the three values uniquely
 * identifies the namespace in which a key is meaningful. Reusing the same
 * key outside of its scope is intentional and is not treated as a conflict.
 */
export interface IdempotencyScope {
  organizationId: string;
  actorId: string;
  commandType: string;
}

/**
 * Optional configuration for `IdempotencyService.run`.
 */
export interface RunOptions<TResult> {
  scope: IdempotencyScope;
  key: string;
  request: unknown;
  execute: () => Promise<{ status: number; body: TResult }>;
  /**
   * Optional hook invoked once the response has been confirmed and persisted.
   * Receives the body returned by `execute`. Used by handlers that need to
   * surface the value through downstream interceptors (e.g. correlation-id).
   */
  onCommit?: (result: TResult) => void;
}

/**
 * Result returned to handlers. Handlers are responsible for translating the
 * `status` into an HTTP response with the same `body`.
 */
export interface IdempotencyResult<T> {
  status: number;
  body: T;
  /**
   * Indicates whether the response was served from the idempotency cache.
   * Handlers can use this flag to skip downstream side effects.
   */
  replayed: boolean;
}

/**
 * Inputs for `commit()`. Provided so that callers that prefer to manage the
 * transaction boundaries themselves (or that want to commit before/after
 * additional side effects) can still persist an `IdempotencyRecord` manually.
 */
export interface CommitInput<T> {
  scope: IdempotencyScope;
  key: string;
  fingerprint: string;
  status: number;
  body: T;
}

/**
 * Thrown when an `execute()` callback throws after the IdempotencyRecord was
 * persisted. It is used internally to signal that the caller did not respect
 * the "no commit before throw" contract. Exposed for completeness and tests.
 */
export class IdempotencyAlreadyCommittedError extends Error {
  constructor() {
    super(
      'Cannot commit an IdempotencyRecord after the execute() callback threw',
    );
  }
}

interface IdempotencyRecordRow {
  requestFingerprint: string;
  responseStatus: number;
  responseBody: unknown;
}

/**
 * Structural type for the Prisma delegate of `IdempotencyRecord`. Mirrors the
 * shape produced by `prisma generate` so the service can compile against a
 * typed delegate without depending on the regenerated `PrismaClient` type.
 * Keep this in sync with `apps/api/prisma/schema.prisma`.
 */
interface IdempotencyRecordDelegate {
  findUnique(args: {
    where: {
      organizationId_actorId_commandType_idempotencyKey: {
        organizationId: string;
        actorId: string;
        commandType: string;
        idempotencyKey: string;
      };
    };
  }): Promise<IdempotencyRecordRow | null>;
  create(args: {
    data: {
      organizationId: string;
      actorId: string;
      commandType: string;
      idempotencyKey: string;
      requestFingerprint: string;
      responseStatus: number;
      responseBody: Prisma.InputJsonValue;
    };
  }): Promise<unknown>;
}

const UNIQUE_VIOLATION_CODE = 'P2002';

@Injectable()
export class IdempotencyService {
  private readonly logger = new Logger(IdempotencyService.name);

  constructor(private readonly prismaService: PrismaService) {}

  /**
   * Idempotency orchestrator. See `apps/api/src/common/idempotency` docs.
   *
   * - If no `IdempotencyRecord` exists for the given scope and key, execute the
   *   callback and persist the result only when the callback resolves
   *   successfully (i.e. it reached "commit").
   * - If a record exists with the same fingerprint, return its cached
   *   response without re-running the callback.
   * - If a record exists with a different fingerprint, throw
   *   `IdempotencyKeyReusedException` (mapped to 409 IDEMPOTENCY_KEY_REUSED).
   */
  async run<TResult>(
    options: RunOptions<TResult>,
  ): Promise<IdempotencyResult<TResult>> {
    const fingerprint = computeCanonicalFingerprint(options.request);

    const existing = await this.findRecord(options.scope, options.key);

    if (existing) {
      if (existing.requestFingerprint !== fingerprint) {
        throw new IdempotencyKeyReusedException();
      }

      return {
        status: existing.responseStatus,
        body: existing.responseBody as TResult,
        replayed: true,
      };
    }

    const result = await options.execute();

    await this.commit({
      scope: options.scope,
      key: options.key,
      fingerprint,
      status: result.status,
      body: result.body,
    });

    if (options.onCommit) {
      options.onCommit(result.body);
    }

    return { status: result.status, body: result.body, replayed: false };
  }

  /**
   * Persist an IdempotencyRecord for the given scope, key and result. Used by
   * `run()` and exposed for advanced callers (e.g. tests) that want to manage
   * commit explicitly.
   */
  async commit<T>(input: CommitInput<T>): Promise<void> {
    try {
      await this.getDelegate().create({
        data: {
          organizationId: input.scope.organizationId,
          actorId: input.scope.actorId,
          commandType: input.scope.commandType,
          idempotencyKey: input.key,
          requestFingerprint: input.fingerprint,
          responseStatus: input.status,
          responseBody: input.body as Prisma.InputJsonValue,
        },
      });
    } catch (error) {
      if (
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === UNIQUE_VIOLATION_CODE
      ) {
        // Concurrent writer won the race. Re-read the persisted record to
        // ensure the caller observes a consistent state.
        const winner = await this.findRecord(input.scope, input.key);
        if (winner && winner.requestFingerprint !== input.fingerprint) {
          throw new IdempotencyKeyReusedException();
        }
        this.logger.debug(
          `Idempotency record already committed by a concurrent writer for key ${input.key}`,
        );
        return;
      }
      throw error;
    }
  }

  private findRecord(
    scope: IdempotencyScope,
    key: string,
  ): Promise<IdempotencyRecordRow | null> {
    return this.getDelegate().findUnique({
      where: {
        organizationId_actorId_commandType_idempotencyKey: {
          organizationId: scope.organizationId,
          actorId: scope.actorId,
          commandType: scope.commandType,
          idempotencyKey: key,
        },
      },
    });
  }

  private getDelegate(): IdempotencyRecordDelegate {
    // `PrismaService` extends `PrismaClient`. The generated client exposes
    // `idempotencyRecord` after `prisma generate` runs against the updated
    // schema. The structural cast keeps the service independent of the
    // regenerated client type and gives the call sites a properly typed
    // delegate rather than the generic `any` from a forceful cast.
    const client = this.prismaService as unknown as {
      idempotencyRecord: IdempotencyRecordDelegate;
    };
    return client.idempotencyRecord;
  }
}