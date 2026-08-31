import {
  Body,
  Controller,
  Get,
  HttpCode,
  HttpStatus,
  Post,
  Query,
} from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';

import {
  AuditService,
  type AuditEventRecord,
  type AuditSearchPage,
  type AuditSearchQuery,
} from './audit.service';
import { auditEventResponseSchema, type AuditEventResponseDto } from './dto/audit-event.dto';
import {
  AuditSearchQueryDto,
  AuditSearchResponseDto,
  auditSearchQuerySchema,
  auditSearchResponseSchema,
} from './dto/audit-search.dto';

interface ProjectedItem {
  id: string;
  scope: 'PLATFORM' | 'ORGANIZATION';
  organizationId: string | null;
  actorType: 'USER' | 'SYSTEM' | 'API_KEY' | 'WORKER';
  actorId: string;
  action: string;
  entityType: string;
  entityId: string;
  occurredAt: string;
  correlationId: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  createdAt: string;
}

interface ProjectedPage {
  items: ProjectedItem[];
  total: number;
  limit: number;
  offset: number;
}

const toProjectedItem = (item: AuditEventRecord): ProjectedItem => ({
  id: item.id,
  scope: item.scope,
  organizationId: item.organizationId,
  actorType: item.actorType,
  actorId: item.actorId,
  action: item.action,
  entityType: item.entityType,
  entityId: item.entityId,
  occurredAt: item.occurredAt.toISOString(),
  correlationId: item.correlationId,
  before: item.before,
  after: item.after,
  createdAt: item.createdAt.toISOString(),
});

const projectPage = (page: AuditSearchPage): AuditSearchResponseDto => {
  const items: ProjectedItem[] = page.items.map(toProjectedItem);
  // The response schema explicitly does NOT declare `transitionKey`, so
  // `auditSearchResponseSchema.parse` is the boundary that strips it from
  // the HTTP body before it leaves the controller.
  const projected: ProjectedPage = {
    items,
    total: page.total,
    limit: page.limit,
    offset: page.offset,
  };
  return auditSearchResponseSchema.parse(projected);
};

// Validate the raw query/body via the Zod schema so the controller receives
// a strongly-typed `AuditSearchQuery` instead of the untyped fields exposed
// by the DTO class. Validation errors are surfaced as ZodError, which the
// `ApiExceptionFilter` translates into `400 VALIDATION_ERROR`.
const buildQuery = (source: unknown): AuditSearchQuery => {
  const parsed = auditSearchQuerySchema.parse(source);
  return {
    actorType: parsed.actorType,
    actorId: parsed.actorId,
    action: parsed.action,
    entityType: parsed.entityType,
    entityId: parsed.entityId,
    from: parsed.from ? new Date(parsed.from) : undefined,
    to: parsed.to ? new Date(parsed.to) : undefined,
    limit: parsed.limit,
    offset: parsed.offset,
    organizationId: parsed.organizationId,
  };
};

// Re-export the schemas so consumers can import them from a single
// location. The schema intentionally does not declare `transitionKey`; that
// field is internal-only and must never reach an HTTP response.
export { auditEventResponseSchema };

@ApiTags('audit')
@Controller('audit-events')
export class AuditController {
  constructor(private readonly audit: AuditService) {}

  @Get()
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Search audit events' })
  async list(
    @Query() query: AuditSearchQueryDto,
  ): Promise<AuditSearchResponseDto> {
    const result = await this.audit.search(buildQuery(query));
    return projectPage(result);
  }

  @Post()
  @HttpCode(HttpStatus.OK)
  @ApiOperation({ summary: 'Search audit events (POST for complex filters)' })
  async search(
    @Body() body: AuditSearchQueryDto,
  ): Promise<AuditSearchResponseDto> {
    const result = await this.audit.search(buildQuery(body));
    return projectPage(result);
  }
}

// `auditEventResponseSchema` is intentionally not part of the controller's
// runtime exports but is re-exported for unit tests. The type
// `AuditEventResponseDto` is re-exported indirectly through
// `audit-search.dto.ts`.
export type { AuditEventResponseDto };