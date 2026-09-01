# Attempt 9

## Status

retryable_failure

## Failure

- Type: infrastructure
- Stage: integration

## Summary

DEV-32 OpenSpec artifacts (proposal, spec, design, tasks) are complete and internally consistent. `openspec validate dev-32 --strict --no-interactive` exits 0 with `Change 'dev-32' is valid`. All 9 Requirements are implemented in code, all tasks in tasks.md are marked [x], design is respected (single `## Verification Strategy - Browser E2E: not_required` section), and no acceptance criterion is declared out of scope. python/lint/test/build all pass (82/82 unit tests). However, the `integration` gate fails (14 failed / 5 passed) due to a vitest + esbuild + `emitDecoratorMetadata` infrastructure issue affecting the four controllers (AuditController, AuditEchoController, IdempotencyEchoController, OutboxEchoController). The decorator-metadata integration test fails explicitly with `NEST_DI_METADATA_MISSING`. The Crew's attempt-009 fix to `vitest.config.integration.ts` (adding `import 'reflect-metadata'` and `esbuild.tsconfigRaw` with decorator metadata flags) was correct in intent but did not actually enable parameter type metadata for the controllers. This is the same pattern as DEV-31/DEV-36 (not specific to DEV-32). Browser E2E is `not_required` per design.md, so Playwright is skipped. The Crew should try an alternative approach: modify `apps/api/tsconfig.json` to include test files (and ensure `exclude` rules still prevent spec files from the build), create a dedicated `tsconfig.test.json` referenced via `esbuild.tsconfigRaw`, or use a different mechanism. The fix must be applied within the shared test harness scope without skipping tests.

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
