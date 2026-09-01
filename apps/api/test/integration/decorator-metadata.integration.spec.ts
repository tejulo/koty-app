import 'reflect-metadata';
import { describe, expect, it } from 'vitest';

import { AuditController } from '../../src/audit/audit.controller';
import { AuditEchoController } from '../../src/audit-echo/audit-echo.controller';
import { IdempotencyEchoController } from '../../src/idempotency-echo/idempotency-echo.controller';
import { OutboxEchoController } from '../../src/outbox-echo/outbox-echo.controller';

describe('Nest integration transform', () => {
  it('emits dependency metadata for HTTP controllers', () => {
    const missing = [
      AuditController,
      AuditEchoController,
      IdempotencyEchoController,
      OutboxEchoController,
    ]
      .filter((controller) => !Reflect.getMetadata('design:paramtypes', controller))
      .map((controller) => controller.name);

    expect(
      missing,
      `NEST_DI_METADATA_MISSING: ${missing.join(', ')}`,
    ).toEqual([]);
  });
});
