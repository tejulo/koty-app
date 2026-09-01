import { BadRequestException, HttpException, HttpStatus } from '@nestjs/common';

import { ErrorCode } from '../common/errors/error-code.enum';

/**
 * DEV-32 — Thrown when an `OutboxEvent` insertion collides with an existing
 * `(organizationId, aggregateType, aggregateId, semanticKey)` row whose
 * canonical fingerprint differs from the incoming one. Mapped to HTTP
 * `409 Conflict` with `code = OUTBOX_SEMANTIC_CONFLICT` by
 * `ApiExceptionFilter`.
 */
export class OutboxSemanticConflictException extends HttpException {
  constructor(
    message = 'Outbox semantic key reused with a different payload',
  ) {
    super(
      {
        message,
        code: ErrorCode.OUTBOX_SEMANTIC_CONFLICT,
      },
      HttpStatus.CONFLICT,
    );
  }
}

/**
 * DEV-32 — Thrown when the `payload` of a new `OutboxEvent` exceeds
 * `OUTBOX_MAX_PAYLOAD_BYTES`. Mapped to HTTP `400 Bad Request` with
 * `code = OUTBOX_PAYLOAD_TOO_LARGE` by `ApiExceptionFilter`.
 */
export class OutboxPayloadTooLargeException extends BadRequestException {
  constructor(
    fieldErrors: { field: string; message: string }[],
    message = 'Outbox payload exceeds the maximum allowed size',
  ) {
    super({
      message,
      code: ErrorCode.OUTBOX_PAYLOAD_TOO_LARGE,
      fieldErrors,
    });
  }
}
