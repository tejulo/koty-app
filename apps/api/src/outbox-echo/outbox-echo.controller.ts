import {
  Body,
  Controller,
  Headers,
  HttpCode,
  HttpStatus,
  Logger,
  Post,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { Prisma } from '@prisma/client';

import {
  OutboxService,
  type OutboxEventDelegate,
} from '../outbox/outbox.service';
import { PrismaService } from '../prisma/prisma.service';
import { outboxEchoRequestSchema } from '../outbox/dto/outbox-echo.dto';

const CORRELATION_ID_HEADER = 'x-correlation-id';

interface EchoRequest {
  organizationId: string;
  aggregateType?: string;
  aggregateId?: string;
  version?: number;
  semanticKey: string;
  eventType?: string;
  causationId?: string;
  payload?: Record<string, unknown>;
  forceRollback?: boolean;
}

/**
 * Structural type of the Prisma transaction client used by the smoke
 * controller. The integration test boots the app with a freshly
 * generated Prisma client, so we narrow the surface we use to the
 * delegate `outboxEvent` to keep the controller free of `any` casts
 * that ESLint would reject.
 */
type OutboxTransactionDelegate = Prisma.TransactionClient & {
  outboxEvent: OutboxEventDelegate;
};

/**
 * DEV-32 — Smoke controller used by integration tests to validate the
 * transactional outbox contract end-to-end without depending on a
 * not-yet implemented domain service. It only mounts when
 * `ENABLE_OUTBOX_ECHO=true` is set; otherwise the controller is hidden
 * by the `AppModule` configuration.
 *
 * The controller wraps the `OutboxService.record` call inside an
 * explicit `prisma.$transaction` so the test can force a rollback with
 * `forceRollback: true` and assert that no row is persisted (CA2).
 */
@ApiTags('outbox')
@Controller('_outbox')
export class OutboxEchoController {
  private readonly logger = new Logger(OutboxEchoController.name);

  constructor(
    private readonly outbox: OutboxService,
    private readonly prisma: PrismaService,
  ) {}

  @Post('echo')
  @HttpCode(HttpStatus.CREATED)
  async echo(
    @Headers(CORRELATION_ID_HEADER) correlationIdHeader: string | undefined,
    @Body() body: EchoRequest,
  ): Promise<unknown> {
    const parsed = outboxEchoRequestSchema.parse(body);
    const organizationId = parsed.organizationId;
    const aggregateType = parsed.aggregateType;
    const aggregateId = parsed.aggregateId ?? parsed.semanticKey;
    const version = parsed.version;
    const eventType = parsed.eventType;
    const payload = parsed.payload;
    const forceRollback = parsed.forceRollback;
    const correlationId =
      correlationIdHeader && correlationIdHeader.length > 0
        ? correlationIdHeader
        : undefined;

    const record = await this.prisma.$transaction(async (txParam) => {
      const tx = txParam as OutboxTransactionDelegate;
      const created = await this.outbox.record({
        organizationId,
        aggregateType,
        aggregateId,
        version,
        semanticKey: parsed.semanticKey,
        eventType,
        correlationId,
        causationId: parsed.causationId ?? null,
        payload,
      }, tx.outboxEvent);
      // Touch the transaction client so the `$transaction` call is
      // observable by the smoke test and so future domain handlers
      // can chain additional writes through `tx` without re-plumbing
      // the service. The call is a no-op read and does not write to
      // the database.
      await tx.outboxEvent.findUnique({
        where: {
          organizationId_aggregateType_aggregateId_semanticKey: {
            organizationId,
            aggregateType,
            aggregateId,
            semanticKey: parsed.semanticKey,
          },
        },
      });
      if (forceRollback) {
        this.logger.debug(
          `OutboxEchoController: forced rollback after record (semanticKey=${parsed.semanticKey})`,
        );
        throw new Error(
          'OutboxEchoController: forced rollback after record',
        );
      }
      return created;
    });

    return {
      id: record.id,
      organizationId: record.organizationId,
      aggregateType: record.aggregateType,
      aggregateId: record.aggregateId,
      version: record.version,
      eventType: record.eventType,
      correlationId: record.correlationId,
      causationId: record.causationId,
      payload: record.payload,
      createdAt: record.createdAt.toISOString(),
      created: record.created,
    };
  }
}
