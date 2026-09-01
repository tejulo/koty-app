# Attempt 10

## Status

retryable_failure

## Failure

- Type: infrastructure
- Stage: integration

## Summary

Contrato OpenSpec de DEV-32 completo y validado (Change 'dev-32' is valid, exit 0). Implementación en código completa: modelo Prisma OutboxEvent con @@unique, migración 20260831022810_add_outbox_event con trigger BEFORE UPDATE OR DELETE + REVOKE UPDATE, DELETE, OutboxService con superficie mínima record (sin update/delete/patch/truncate, sin llamadas externas), OutboxEchoController gated por ENABLE_OUTBOX_ECHO, DTOs, códigos OUTBOX_SEMANTIC_CONFLICT/OUTBOX_PAYLOAD_TOO_LARGE, OpenAPI schema y tag outbox. Tests unitarios 82/82 passed (incluye outbox.service.spec.ts 10/10, outbox-canonical-fingerprint.spec.ts 10/10). python/lint/test/build pasados. El gate integration falla (exit 1) por la categoría compartida shared_test_harness documentada en attempt-009.integration-diagnosis.json: vitest compila con esbuild pero no implementa correctamente emitDecoratorMetadata, por lo que los 4 controllers (AuditController, AuditEchoController, IdempotencyEchoController, OutboxEchoController) se instancian con dependencias undefined y devuelven HTTP 500. El test decorator-metadata.integration.spec.ts falla explícitamente con NEST_DI_METADATA_MISSING listando los 4 controllers afectados. El escenario forceRollback=true del outbox pasa, confirmando que la transacción Prisma y OutboxService están correctamente cableados. El repairHint indica Configura Vitest con SWC y decoratorMetadata y repairScope está limitado a apps/api/vitest.config.integration.ts, apps/api/package.json y pnpm-lock.yaml (infraestructura compartida, no artefactos OpenSpec de DEV-32). El plan no declara fuera de alcance ningún criterio de aceptación. Como category es shared_test_harness y la corrección requiere cambios compartidos fuera del scope DEV-32 (instalar @swc/core/unplugin-swc, permitir @swc/core en pnpm-workspace.yaml, regenerar pnpm-lock.yaml, reescribir vitest.config.integration.ts para usar SWC en lugar de esbuild), el problema es corregible por otra ejecución del Crew dentro de repairScope sin debilitar specs ni saltear pruebas. Playwright skipped porque design.md declara Browser E2E: not_required (superficie 100% API HTTP + PostgreSQL).

## Verification

~~~json
{
  "python": "passed",
  "lint": "passed",
  "test": "passed",
  "build": "passed",
  "integration": "failed",
  "playwright": "skipped",
  "openspec": "passed"
}
~~~
