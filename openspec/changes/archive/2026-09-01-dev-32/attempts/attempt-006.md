# Attempt 6

## Status

retryable_failure

## Failure

- Type: implementation
- Stage: integration

## Summary

Artefactos OpenSpec (proposal, spec, design, tasks) completos y validados en modo estricto. Tareas A y B marcadas [x]. Tests unitarios pasan (82/82). Lint, build y openspec validate pasan. Sin embargo, la verificación de integración falla con 14 tests fallidos de 19: los endpoints de eco de idempotency (DEV-31), audit (DEV-36) y outbox (DEV-32) devuelven HTTP 500 en lugar de los códigos esperados (201/200/404). Esto afecta 5 de los 6 escenarios de outbox.integration.spec.ts (persistencia básica, idempotencia por semanticKey, conflicto 409, bloqueo de UPDATE/DELETE por trigger SQL). Solo el escenario de rollback atómico pasa. El error 500 en el endpoint POST /api/v1/_outbox/echo indica un bug de implementación en el controlador o servicio (validación, registro de módulo, o excepción no manejada) que otra ejecución del Crew puede corregir. Browser E2E not_required (justificado en design.md: superficie 100% API + PostgreSQL). No se archiva OpenSpec ni se modifica Linear.

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
