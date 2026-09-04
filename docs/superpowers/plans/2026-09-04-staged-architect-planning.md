# Staged Architect Planning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent Architect output-length failures by generating a compact outline and bounded artifact units with durable supervisor-owned retries.

**Architecture:** Analyst still produces `TicketContract`. Architect first returns a `PlanOutline`, then one `PlanArtifactUnit` for proposal, design, tasks, and each spec; the supervisor assembles the existing `PlanDraft` and keeps the current atomic promotion, `PlanManifest`, gates, and downstream phases unchanged.

**Tech Stack:** Python 3.12, CrewAI 1.15.16, OpenAI SDK 2.54.0, Pydantic, pytest, OpenSpec.

**Spec:** `openspec/changes/dev-40/design.md`

## Global Constraints

- Work only in `.worktrees/feat-dev-40-optimize-crewai-core` on `feat/dev-40-optimize-crewai-core`.
- Preserve the existing phases, four verification profiles, six base gates, Ralph ownership, and downstream contracts.
- Keep `PlanDraft`, `PlanManifest`, and `write_plan_draft()` as the final promotion boundary.
- Do not write active OpenSpec files until all staged units validate.
- Architect has no tools, delegation, manager, or Flow; every invocation is a one-task Crew.
- Set Architect `max_retry_limit=0`; the supervisor owns retries and persists every attempt.
- Unit retries do not increment `ExecutionState.last_attempt`.
- Preserve untracked `task-5-report.md` and `task-6-report.md` and never stage them.
- Do not upgrade CrewAI in this change.

---

### Task 1: Specify Staged Planning

**Files:**
- Modify: `openspec/changes/dev-40/proposal.md`
- Modify: `openspec/changes/dev-40/design.md`
- Modify: `openspec/changes/dev-40/tasks.md`
- Modify: `openspec/changes/dev-40/specs/crew-supervision/spec.md`

**Interfaces:**
- Consumes: current DEV-40 contract.
- Produces: requirements for staged Architect calls, bounded context, durable checkpoints, and supervisor-owned length retries.

- [ ] Add requirements and scenarios for staged artifact generation, bounded context, checkpoint resume, and direct/wrapped `LengthFinishReasonError` handling.
- [ ] Preserve the existing final `PlanDraft`/`PlanManifest` contract and promotion semantics in the design.
- [ ] Add implementation and verification tasks with acceptance-criterion mappings.
- [ ] Run `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive`; expect success.

### Task 2: Add Planning Contracts and Bounded Context

**Files:**
- Create: `crewai/src/crew/planning.py`
- Create: `crewai/tests/test_planning.py`
- Modify: `crewai/src/crew/models.py`

**Interfaces:**
- Produces: `ProjectContextSection`, `ProjectContextCatalog`, `PlanUnitOutline`, `PlanOutline`, `PlanArtifactUnit`, `PlanningCheckpoint`.
- Produces: `build_context_catalog(path)`, `render_context_index(catalog)`, `render_context_bundle(catalog, refs, max_refs, max_chars)`, `validate_plan_outline(outline, contract, catalog, max_refs, max_chars)`, `assemble_plan_draft(outline, units)`.

- [ ] Write failing tests proving the index omits section bodies, bundles include only selected refs, unknown/oversized selections fail, outline structure is strict, and assembly returns the existing `PlanDraft` shape.
- [ ] Run `mise exec -- uv run --project crewai pytest crewai/tests/test_planning.py -q`; expect RED because the API is missing.
- [ ] Implement deterministic `##`/`###` section parsing, compact indexes, bounded bundles, strict outline/unit validators, and the `PlanDraft` assembler.
- [ ] Run the same command; expect GREEN.

### Task 3: Split Architect Crews and Budgets

**Files:**
- Modify: `crewai/src/crew/crew.py`
- Modify: `crewai/src/crew/config/agents.yaml`
- Modify: `crewai/src/crew/config/tasks.yaml`
- Modify: `crewai/.env.example`
- Modify: `crewai/tests/test_crew.py`

**Interfaces:**
- Produces: `architect_outline_crew()` with `PlanOutline` output.
- Produces: `architect_artifact_crew()` with `PlanArtifactUnit` output.
- Uses defaults: outline `4000`, artifact `8000`, retry `16000`, reasoning effort `low`, one length retry, 12 context refs, 48000 context characters.

- [ ] Change tests first to require both isolated one-task crews, exact structured outputs/placeholders, no tools, no delegation, `max_retry_limit=0`, independent token budgets, and documented environment defaults.
- [ ] Run `mise exec -- uv run --project crewai pytest crewai/tests/test_crew.py -q`; expect RED.
- [ ] Replace the monolithic Architect task with outline and artifact tasks and configure explicit reasoning effort and budgets.
- [ ] Remove unused composite crew factories after confirming no production references.
- [ ] Run the same command; expect GREEN.

### Task 4: Persist and Resume Unit Generation

**Files:**
- Modify: `crewai/src/crew/main.py`
- Modify: `crewai/src/crew/workflow.py`
- Modify: `crewai/src/crew/models.py`
- Modify: `crewai/tests/test_main.py`
- Modify: `crewai/tests/test_workflow.py`

**Interfaces:**
- Produces: attempt-scoped `context-catalog.json` and `planning-checkpoint.json`.
- Produces: structural error-chain detection for `LengthFinishReasonError`.
- Produces: unique Architect usage files by unit and invocation.
- Consumes and assembles Task 2 contracts; invokes Task 3 crews.

- [ ] Write failing tests for attempt paths, atomic checkpoint reload, exact call order, direct/wrapped length failures, failed usage, retry exhaustion, restart reuse, unchanged active files before assembly, and stable `last_attempt`.
- [ ] Run focused workflow/main tests; expect RED.
- [ ] Add checkpoint/catalog paths and `ExecutionState.planning_checkpoint_path`, clearing it only during replan.
- [ ] Extend usage recording with stage, unit, invocation, status, effective limit, error type, and failed-call usage while preserving latest-reference aliases.
- [ ] Replace monolithic `run_planning()` with load-or-create contract/catalog/checkpoint, outline generation, missing-unit generation, assembly, and the unchanged final promotion sequence.
- [ ] Disable hidden CrewAI retries and retry only the failed unit once with the retry token budget.
- [ ] Persist execution state after the checkpoint, outline, every success, and every handled failure.
- [ ] Run `mise exec -- uv run --project crewai pytest crewai/tests/test_workflow.py crewai/tests/test_main.py -q`; expect GREEN.

### Task 5: Document and Verify

**Files:**
- Modify: `crewai/README.md`
- Modify: `docs/superpowers/plans/2026-09-04-staged-architect-planning.md`

**Interfaces:**
- Verifies all prior tasks and downstream compatibility.

- [x] Update README flow, limits, retry ownership, checkpoint paths, and remove stale Architect `12/1200` documentation.
- [x] Run `mise exec -- uv run --project crewai pytest crewai/tests -q`; expect zero failures.
- [x] Run `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive`; expect success.
- [ ] Run `mise exec -- pnpm test:integration`; expect success.
- [x] Run `mise exec -- pnpm verify`; expect success.
- [x] Run `git diff --check`, inspect `git status --short`, and confirm the two pre-existing report files remain untracked and untouched.
