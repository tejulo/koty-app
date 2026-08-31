import {
  BadRequestException,
  Body,
  Controller,
  Headers,
  HttpCode,
  HttpStatus,
  Post,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';

import { AuditService } from '../audit/audit.service';

const CORRELATION_ID_HEADER = 'x-correlation-id';

interface EchoBody {
  organizationId?: string;
  actorId?: string;
  message?: string;
}

const MAX_ACTOR_ID_LENGTH = 128;
const MAX_MESSAGE_LENGTH = 1024;

/**
 * DEV-36 — Smoke controller used by integration tests to validate the
 * audit append-only contract end-to-end without depending on a not-yet
 * implemented domain service. It only mounts when
 * `ENABLE_AUDIT_ECHO=true` is set; otherwise the controller is hidden by
 * the `AppModule` configuration.
 */
@ApiTags('audit')
@Controller('_audit')
export class AuditEchoController {
  constructor(private readonly audit: AuditService) {}

  @Post('echo')
  @HttpCode(HttpStatus.CREATED)
  async echo(
    @Headers(CORRELATION_ID_HEADER) correlationIdHeader: string | undefined,
    @Body() body: EchoBody,
  ): Promise<unknown> {
    const actorId = body.actorId;
    if (!actorId || typeof actorId !== 'string') {
      throw new BadRequestException({
        message: 'actorId is required',
        fieldErrors: [{ field: 'actorId', message: 'actorId is required' }],
      });
    }
    if (actorId.length > MAX_ACTOR_ID_LENGTH) {
      throw new BadRequestException({
        message: 'actorId is too long',
        fieldErrors: [
          {
            field: 'actorId',
            message: `actorId must be at most ${String(MAX_ACTOR_ID_LENGTH)} characters`,
          },
        ],
      });
    }

    const message = body.message;
    if (message !== undefined && (typeof message !== 'string' || message.length === 0)) {
      throw new BadRequestException({
        message: 'message must be a non-empty string when provided',
        fieldErrors: [{ field: 'message', message: 'must be a non-empty string' }],
      });
    }
    if (typeof message === 'string' && message.length > MAX_MESSAGE_LENGTH) {
      throw new BadRequestException({
        message: 'message is too long',
        fieldErrors: [
          {
            field: 'message',
            message: `message must be at most ${String(MAX_MESSAGE_LENGTH)} characters`,
          },
        ],
      });
    }

    const correlationId = correlationIdHeader && correlationIdHeader.length > 0
      ? correlationIdHeader
      : undefined;

    const organizationId = body.organizationId ?? 'default-organization';

    const record = await this.audit.record({
      scope: 'ORGANIZATION',
      organizationId,
      actorType: 'USER',
      actorId,
      action: 'audit-echo.create',
      entityType: 'audit-echo',
      entityId: actorId,
      correlationId,
      before: null,
      after: message ? { message } : null,
    });

    return {
      id: record.id,
      scope: record.scope,
      organizationId: record.organizationId,
      actorType: record.actorType,
      actorId: record.actorId,
      action: record.action,
      entityType: record.entityType,
      entityId: record.entityId,
      occurredAt: record.occurredAt.toISOString(),
      correlationId: record.correlationId,
      before: record.before,
      after: record.after,
      createdAt: record.createdAt.toISOString(),
      created: record.created,
    };
  }
}
