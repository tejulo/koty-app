# Ralph Reliability Plan

## Constraints

- Work on the current branch.
- Preserve existing DEV-32 implementation changes.
- Do not modify `apps/api`, OpenSpec DEV-32 requirements, or Prisma.
- Keep the orchestration code compact and cover new behavior with tests.
- Do not commit, push, archive OpenSpec, or close Linear during this work.

## Task 1: Runner-owned attempt and accounting

- Make the runner assign the attempt after parsing reviewer output.
- Do not consume budgets for blocked results.
- Keep ticket and infrastructure budgets independent.
- Store finalizer diagnostics outside attempt artifacts.

## Task 2: Required integration gate

- Add an `integration` verification gate and evidence requirement.
- Start PostgreSQL with `pnpm db:start` before each integration run.
- Make `pnpm db:start` wait for the Compose healthcheck.
- Require integration in the finalizer before archiving.

## Task 3: Single-flight and safe finalization

- Prevent concurrent ticket workers from starting together.
- Publish worker output atomically and preserve prior results.
- Do not relaunch after terminal blocked results.
- Make automatic commits reject unrelated files and omit runtime artifacts.

## Task 4: Verification

- Run focused CrewAI and shell tests while implementing.
- Run the complete repository verification suite after the changes.
- Run a final code review without committing or pushing.
