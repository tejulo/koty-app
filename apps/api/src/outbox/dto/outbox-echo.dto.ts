import { z } from 'zod';
import { createStrictZodDto } from '../../common/validation/create-zod-dto';
import {
  DEFAULT_AGGREGATE_TYPE,
  DEFAULT_EVENT_TYPE,
  MAX_SEMANTIC_KEY_LENGTH,
  MIN_SEMANTIC_KEY_LENGTH,
} from '../outbox.constants';

/**
 * DEV-32 — Input DTO for the smoke endpoint `POST /api/v1/_outbox/echo`.
 *
 * The endpoint exists to validate the outbox contract end-to-end
 * without depending on a real domain service. `forceRollback` lets
 * integration tests assert the atomicity guarantee (CA2): when set to
 * `true`, the handler raises an error **after** invoking
 * `OutboxService.record`, so the test can confirm that no row remains
 * in `OutboxEvent`.
 */
export const outboxEchoRequestSchema = z.object({
  organizationId: z.string().min(1),
  aggregateType: z
    .string()
    .min(1)
    .optional()
    .default(DEFAULT_AGGREGATE_TYPE),
  aggregateId: z.string().min(1).optional(),
  version: z
    .number()
    .int()
    .min(0)
    .optional()
    .default(1),
  semanticKey: z
    .string()
    .min(MIN_SEMANTIC_KEY_LENGTH)
    .max(MAX_SEMANTIC_KEY_LENGTH),
  eventType: z.string().min(1).optional().default(DEFAULT_EVENT_TYPE),
  causationId: z.string().min(1).optional(),
  payload: z.record(z.unknown()).optional().default({}),
  forceRollback: z.boolean().optional().default(false),
});

export class OutboxEchoRequestDto extends createStrictZodDto(
  outboxEchoRequestSchema,
) {}
