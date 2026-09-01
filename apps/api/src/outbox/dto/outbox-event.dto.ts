import { z } from 'zod';
import { createStrictZodDto } from '../../common/validation/create-zod-dto';

/**
 * DEV-32 — HTTP response DTO for a single `OutboxEvent`.
 *
 * The DTO intentionally **does not** expose any internal-only field
 * (no `semanticKey` is returned in the response because it is already
 * part of the unique constraint and would only confuse callers; the
 * endpoint of smoke returns the relevant identity, version, and
 * payload that the caller just submitted, plus the persisted
 * `correlationId`/`causationId` for traceability).
 */
const isoDateString = z
  .union([z.string(), z.date()])
  .transform((value) =>
    value instanceof Date ? value.toISOString() : value,
  );

export const outboxEventResponseSchema = z.object({
  id: z.string().uuid(),
  organizationId: z.string().min(1),
  aggregateType: z.string().min(1),
  aggregateId: z.string().min(1),
  version: z.number().int().min(0),
  eventType: z.string().min(1),
  correlationId: z.string().min(1),
  causationId: z.string().nullable(),
  payload: z.record(z.unknown()),
  createdAt: isoDateString,
  created: z.boolean(),
});

export class OutboxEventResponseDto extends createStrictZodDto(
  outboxEventResponseSchema,
) {}
