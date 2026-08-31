import {
  BadRequestException,
  Body,
  Controller,
  Headers,
  HttpCode,
  HttpStatus,
  Logger,
  NotFoundException,
  Post,
  Req,
  Res,
  UnauthorizedException,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import type { Request, Response } from 'express';

import {
  IdempotencyService,
  type IdempotencyScope,
} from '../common/idempotency/idempotency.service';

interface EchoBody {
  organizationId?: string;
  actorId?: string;
  message?: string;
  forceFail?: boolean;
  forceReplay?: boolean;
}

const MAX_IDEMPOTENCY_KEY_LENGTH = 128;
const MIN_IDEMPOTENCY_KEY_LENGTH = 8;
const ECHO_COMMAND_TYPE = 'echo';
const FAIL_COMMAND_TYPE = 'fail';

const ECHO_HEADER = 'idempotency-key';
const CORRELATION_ID_HEADER = 'x-correlation-id';
const DEFAULT_ORGANIZATION_ID = 'default-organization';
const UNKNOWN_CORRELATION_ID = 'unknown';

interface RequestWithCorrelationId extends Request {
  headers: Record<string, string | string[] | undefined> & {
    [CORRELATION_ID_HEADER]?: string;
  };
}

function readCorrelationId(
  headers: Record<string, string | string[] | undefined>,
): string {
  const raw = headers[CORRELATION_ID_HEADER];
  if (typeof raw === 'string' && raw.length > 0) {
    return raw;
  }
  return UNKNOWN_CORRELATION_ID;
}

/**
 * Smoke controller used by integration tests to validate the idempotency
 * contract end-to-end without depending on the not-yet-implemented
 * organization / invitation services. It only mounts when the env flag
 * `ENABLE_IDEMPOTENCY_ECHO=true` is set; otherwise the controller is hidden
 * by the `AppModule` configuration.
 */
@ApiTags('idempotency')
@Controller('_idempotency')
export class IdempotencyEchoController {
  private readonly logger = new Logger(IdempotencyEchoController.name);

  constructor(private readonly idempotency: IdempotencyService) {}

  @Post('echo')
  @HttpCode(HttpStatus.OK)
  async echo(
    @Req() req: RequestWithCorrelationId,
    @Res({ passthrough: true }) res: Response,
    @Headers('idempotency-key') idempotencyKey: string | undefined,
    @Body() body: EchoBody,
  ): Promise<unknown> {
    if (!idempotencyKey) {
      // Endpoint requires the header so the contract is exercised on every
      // call. Without the header the request is treated as malformed.
      throw new BadRequestException({
        message: 'Idempotency-Key header is required',
        fieldErrors: [{ field: 'idempotencyKey', message: 'required' }],
      });
    }

    if (
      idempotencyKey.length < MIN_IDEMPOTENCY_KEY_LENGTH ||
      idempotencyKey.length > MAX_IDEMPOTENCY_KEY_LENGTH
    ) {
      const min = String(MIN_IDEMPOTENCY_KEY_LENGTH);
      const max = String(MAX_IDEMPOTENCY_KEY_LENGTH);
      throw new BadRequestException({
        message: 'Validation failed',
        fieldErrors: [
          {
            field: 'idempotencyKey',
            message: `Idempotency-Key must be between ${min} and ${max} characters`,
          },
        ],
      });
    }

    const actorId = body.actorId;
    if (!actorId || typeof actorId !== 'string') {
      throw new UnauthorizedException('Authenticated actor is required');
    }

    const organizationId = body.organizationId ?? DEFAULT_ORGANIZATION_ID;
    const commandType = body.forceFail ? FAIL_COMMAND_TYPE : ECHO_COMMAND_TYPE;
    const message = body.message ?? null;

    const scope: IdempotencyScope = {
      organizationId,
      actorId,
      commandType,
    };

    const forceFail = body.forceFail === true;

    const result = await this.idempotency.run({
      scope,
      key: idempotencyKey,
      request: body,
      execute: () => {
        if (forceFail) {
          return Promise.reject(
            new NotFoundException('Forced failure for idempotency test'),
          );
        }
        return Promise.resolve({
          status: HttpStatus.CREATED,
          body: {
            echoed: message,
          },
        });
      },
      onCommit: (echoed) => {
        this.logger.debug(
          `Idempotency committed for key ${idempotencyKey}: ${JSON.stringify(echoed)}`,
        );
      },
    });

    res.status(result.status);
    return {
      ...result.body,
      replayed: result.replayed,
      correlationId: readCorrelationId(req.headers),
    };
  }

  @Post('headers-check')
  @HttpCode(HttpStatus.OK)
  headersCheck(
    @Headers('idempotency-key') idempotencyKey: string | undefined,
  ): { key: string | undefined } {
    return { key: idempotencyKey };
  }

  static get headerName(): string {
    return ECHO_HEADER;
  }
}