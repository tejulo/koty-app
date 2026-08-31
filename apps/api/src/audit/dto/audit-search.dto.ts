import { z } from 'zod';
import { createStrictZodDto } from '../../common/validation/create-zod-dto';
import { auditEventResponseSchema } from './audit-event.dto';

/**
 * DEV-36 — Search DTOs for `GET /api/v1/audit-events` and
 * `POST /api/v1/audit-events`. The query schema is shared by both endpoints
 * to keep filters consistent.
 */
export const auditSearchQuerySchema = z.object({
  actorType: z.enum(['USER', 'SYSTEM', 'API_KEY', 'WORKER']).optional(),
  actorId: z.string().min(1).optional(),
  action: z.string().min(1).optional(),
  entityType: z.string().min(1).optional(),
  entityId: z.string().min(1).optional(),
  from: z
    .string()
    .datetime({ message: 'from must be an ISO 8601 timestamp' })
    .optional(),
  to: z
    .string()
    .datetime({ message: 'to must be an ISO 8601 timestamp' })
    .optional(),
  limit: z.coerce.number().int().min(1).max(200).default(50),
  offset: z.coerce.number().int().min(0).default(0),
  // Caller-supplied organizationId scope. The service is responsible for
  // verifying that the caller is allowed to read events for this scope.
  organizationId: z.string().min(1).optional(),
});

export class AuditSearchQueryDto extends createStrictZodDto(
  auditSearchQuerySchema,
) {}

export const auditSearchResponseSchema = z.object({
  items: z.array(auditEventResponseSchema),
  total: z.number().int().min(0),
  limit: z.number().int().min(1),
  offset: z.number().int().min(0),
});

export class AuditSearchResponseDto extends createStrictZodDto(
  auditSearchResponseSchema,
) {}
