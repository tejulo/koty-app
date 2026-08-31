-- CreateEnum
CREATE TYPE "AuditScope" AS ENUM ('PLATFORM', 'ORGANIZATION');

-- CreateEnum
CREATE TYPE "AuditActorType" AS ENUM ('USER', 'SYSTEM', 'API_KEY', 'WORKER');

-- CreateTable
CREATE TABLE "AuditEvent" (
    "id" TEXT NOT NULL,
    "scope" "AuditScope" NOT NULL,
    "organizationId" TEXT,
    "actorType" "AuditActorType" NOT NULL,
    "actorId" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "occurredAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "correlationId" TEXT NOT NULL,
    "transitionKey" TEXT NOT NULL,
    "before" JSONB,
    "after" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "AuditEvent_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "AuditEvent_scope_transitionKey_key" ON "AuditEvent"("scope", "transitionKey");

-- CreateIndex
CREATE INDEX "AuditEvent_scope_organizationId_occurredAt_idx" ON "AuditEvent"("scope", "organizationId", "occurredAt");

-- CreateIndex
CREATE INDEX "AuditEvent_actorType_actorId_occurredAt_idx" ON "AuditEvent"("actorType", "actorId", "occurredAt");

-- CreateIndex
CREATE INDEX "AuditEvent_action_occurredAt_idx" ON "AuditEvent"("action", "occurredAt");

-- CreateIndex
CREATE INDEX "AuditEvent_entityType_entityId_occurredAt_idx" ON "AuditEvent"("entityType", "entityId", "occurredAt");

-- Append-only enforcement: any UPDATE or DELETE on the AuditEvent table
-- raises an exception. The migration also revokes the default UPDATE/DELETE
-- privileges for PUBLIC so that the only allowed write path is INSERT.
CREATE OR REPLACE FUNCTION audit_event_block_mutations()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'AuditEvent is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER "audit_event_append_only"
BEFORE UPDATE OR DELETE ON "AuditEvent"
FOR EACH ROW EXECUTE FUNCTION audit_event_block_mutations();

REVOKE UPDATE, DELETE ON TABLE "AuditEvent" FROM PUBLIC;
