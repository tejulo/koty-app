# Attempt 1

## Status

retryable_failure

## Failure

- Type: implementation
- Stage: lint

## Summary

El contrato OpenSpec de dev-32 está validado (openspec validate --strict --no-interactive → exit 0, evidence 86af54acccb844f0bd6e02ffa87ab7df). El cambio cubre los 5 criterios de aceptación del ticket (CA1..CA5) con 9 Requirements en specs/transactional-outbox/spec.md y las tareas de tasks.md marcadas [x] en su totalidad (Fase A y Fase B). Las verificaciones python, test y build pasan: python compileall → exit 0 (d815f8e16f3441c5bd347dcd98c2e397), vitest 82/82 en 10 archivos incluyendo outbox.service.spec.ts y outbox-canonical-fingerprint.spec.ts (1e47e8b2333146fe85eb7a7355b5212a), pnpm -r build (nest build + next build + tsc) → exit 0 (d25dd04cc267454f87227022ccf842b7). Playwright skipped porque design.md declara 'Browser E2E: not_required' (superficie 100% API + PostgreSQL, validable por integración contra base aislada). El gate lint falla (exit 1, evidence cf4e3f5a55344d1197e2bfc85086c122) por un único error @typescript-eslint/no-unnecessary-condition en apps/api/src/outbox/outbox.service.ts:240:7 sobre la cláusula `input.payload === null ||` dentro de assertValidInput: el tipo `OutboxEventInput.payload: Record<string, unknown>` no es anulable, por lo que la condición es redundante. El fix es eliminar esa cláusula conservando `typeof input.payload !== 'object' || Array.isArray(input.payload)`. Es un defecto puramente de implementación (no de spec, no de infraestructura, no de configuración, no de requirements): otra ejecución del Crew puede corregirlo tocando exclusivamente apps/api/src/outbox/outbox.service.ts sin debilitar requisitos ni escenarios. Por tanto, retryable_failure.

## Verification

~~~json
{
  "python": "passed",
  "lint": "failed",
  "test": "passed",
  "build": "passed",
  "playwright": "skipped",
  "openspec": "passed"
}
~~~
