import { BadRequestException, HttpException, HttpStatus } from '@nestjs/common';

import { ErrorCode } from '../common/errors/error-code.enum';
import type { FieldError } from '../common/errors/error-response.interface';

/**
 * DEV-36 — Thrown when a `before`/`after` field is not part of the
 * `AUDIT_CHANGE_FIELDS` allowlist for the entity type. Mapped to HTTP 400
 * with `code = AUDIT_INVALID_FIELD` by `ApiExceptionFilter`.
 */
export class AuditInvalidFieldException extends BadRequestException {
  constructor(fieldErrors: FieldError[], message = 'Audit field is not allowed') {
    super({
      message,
      code: ErrorCode.AUDIT_INVALID_FIELD,
      fieldErrors,
    });
  }
}

/**
 * DEV-36 — Thrown when an `AuditEvent` insertion collides with an existing
 * `(scope, transitionKey)` pair whose persisted `correlationId` differs from
 * the incoming one. Mapped to HTTP 409 with
 * `code = AUDIT_TRANSITION_CONFLICT` by `ApiExceptionFilter`.
 */
export class AuditTransitionConflictException extends HttpException {
  constructor(
    message = 'Audit transition conflict for a different correlationId',
  ) {
    super(
      {
        message,
        code: ErrorCode.AUDIT_TRANSITION_CONFLICT,
      },
      HttpStatus.CONFLICT,
    );
  }
}
