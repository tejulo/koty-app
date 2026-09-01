-- CreateTable
CREATE TABLE "OutboxEvent" (
    "id" TEXT NOT NULL,
    "organizationId" TEXT NOT NULL,
    "aggregateType" TEXT NOT NULL,
    "aggregateId" TEXT NOT NULL,
    "version" INTEGER NOT NULL,
    "semanticKey" TEXT NOT NULL,
    "eventType" TEXT NOT NULL,
    "correlationId" TEXT NOT NULL,
    "causationId" TEXT,
    "payload" JSONB NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "OutboxEvent_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "OutboxEvent_organizationId_aggregateType_aggregateId_sema_key" ON "OutboxEvent"("organizationId", "aggregateType", "aggregateId", "semanticKey");

-- CreateIndex
CREATE INDEX "OutboxEvent_organizationId_createdAt_idx" ON "OutboxEvent"("organizationId", "createdAt");

-- CreateIndex
CREATE INDEX "OutboxEvent_aggregateType_aggregateId_version_idx" ON "OutboxEvent"("aggregateType", "aggregateId", "version");

-- Append-only enforcement: any UPDATE or DELETE on the OutboxEvent table
-- raises an exception. The migration also revokes the default UPDATE/DELETE
-- privileges for PUBLIC so that the only allowed write path is INSERT.
CREATE OR REPLACE FUNCTION outbox_event_block_mutations()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'OutboxEvent is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER "outbox_event_append_only"
BEFORE UPDATE OR DELETE ON "OutboxEvent"
FOR EACH ROW EXECUTE FUNCTION outbox_event_block_mutations();

REVOKE UPDATE, DELETE ON TABLE "OutboxEvent" FROM PUBLIC;
