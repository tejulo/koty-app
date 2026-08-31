import { HttpException, HttpStatus } from '@nestjs/common';

import { ErrorCode } from '../errors/error-code.enum';

/**
 * Thrown when an `Idempotency-Key` is reused with a request payload that
 * produces a different canonical fingerprint than the original confirmed
 * request.
 *
 * Mapped to HTTP 409 Conflict / `IDEMPOTENCY_KEY_REUSED` by
 * `ApiExceptionFilter`.
 */
export class IdempotencyKeyReusedException extends HttpException {
  constructor(
    message = 'Idempotency key reused with a different request payload',
  ) {
    super(
      {
        message,
        code: ErrorCode.IDEMPOTENCY_KEY_REUSED,
      },
      HttpStatus.CONFLICT,
    );
  }
}