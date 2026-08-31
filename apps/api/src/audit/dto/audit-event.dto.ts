import { z } from 'zod';
import { createStrictZodDto } from '../../common/validation/create-zod-dto';

/**
 * DEV-36 — HTTP response DTO for a single `AuditEvent`.
 *
 * The schema intentionally **does not** include `transitionKey`. That field
 * is for internal idempotency arbitration only and is stripped before the
 * service returns the DTO to controllers and HTTP responses.
 */
export const auditScopeSchema = z.enum(['PLATFORM', 'ORGANIZATION']);
export const auditActorTypeSchema = z.enum([
  'USER',
  'SYSTEM',
  'API_KEY',
  'WORKER',
]);

const isoDateString = z
  .union([z.string(), z.date()])
  .transform((value) =>
    value instanceof Date ? value.toISOString() : value,
  );

export const auditEventResponseSchema = z.object({
  id: z.string().uuid(),
  scope: auditScopeSchema,
  organizationId: z.string().nullable(),
  actorType: auditActorTypeSchema,
  actorId: z.string().min(1),
  action: z.string().min(1),
  entityType: z.string().min(1),
  entityId: z.string().min(1),
  occurredAt: isoDateString,
  correlationId: z.string().min(1),
  before: z.record(z.unknown()).nullable(),
  after: z.record(z.unknown()).nullable(),
  createdAt: isoDateString,
});

export class AuditEventResponseDto extends createStrictZodDto(
  auditEventResponseSchema,
) {}
