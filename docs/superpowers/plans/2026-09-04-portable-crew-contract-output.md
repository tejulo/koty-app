# Portable Crew Contract Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Accept validated contract JSON from OpenCode Go and Ollama without using provider-native structured output.

**Architecture:** Structured roles return plain text containing exactly one JSON object. The supervisor extracts an optional JSON code fence, validates it with the existing Pydantic contract, and owns one durable retry for invalid output so every provider call remains observable.

**Tech Stack:** Python 3.12, CrewAI 1.15.16, Pydantic 2, pytest, OpenSpec.

**Spec:** `openspec/changes/dev-40/design.md`

## Global Constraints

- Work only in `.worktrees/feat-dev-40-optimize-crewai-core` on `feat/dev-40-optimize-crewai-core`.
- Preserve phases, profiles, base gates, persisted contracts, and `write_plan_draft()` promotion.
- Do not set `output_pydantic`, `output_json`, or CrewAI guardrails on structured tasks.
- Validate every structured role locally with the existing Pydantic model.
- Persist a retry as `pending` before changing it to `consumed` before dispatch; never redispatch a consumed retry after restart.
- Keep Architect one-task, tool-free, without delegation or hidden retries.
- Preserve untracked `task-5-report.md` and `task-6-report.md`.

---

### Task 1: Specify Portable Contract Transport

**Files:**
- Modify: `openspec/changes/dev-40/proposal.md`
- Modify: `openspec/changes/dev-40/design.md`
- Modify: `openspec/changes/dev-40/tasks.md`
- Modify: `openspec/changes/dev-40/specs/crew-supervision/spec.md`

**Interfaces:**
- Produces: OpenSpec requirements for raw JSON transport, local validation, and supervisor-owned invalid-output retries.

- [ ] Add requirements and scenarios that every structured role returns JSON as text, local Pydantic validation is authoritative, and one invalid-output retry is persisted and auditable.
- [ ] Retain the existing semantic validation, stage boundaries, and Architect retry guarantees.
- [ ] Run `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive`.

### Task 2: Parse and Validate Raw Contracts

**Files:**
- Modify: `crewai/src/crew/main.py`
- Test: `crewai/tests/test_main.py`

**Interfaces:**
- Produces: `_as_model(output: object, model_type: type[ModelT]) -> ModelT` parsing `output.raw` as JSON after removing one optional `json` fence.

- [ ] Write failing tests for plain JSON, a fenced JSON object, malformed JSON, and a JSON object rejected by the Pydantic model.
- [ ] Run `mise exec -- uv run --project crewai pytest crewai/tests/test_main.py -q`; confirm the new tests fail because raw output is not parsed.
- [ ] Implement the smallest parser that strips whitespace, unwraps exactly one `json` fence, and calls `model_validate_json`.
- [ ] Run the focused test file and confirm green.

### Task 3: Move Structured Tasks to Raw Output

**Files:**
- Modify: `crewai/src/crew/crew.py`
- Modify: `crewai/src/crew/config/tasks.yaml`
- Test: `crewai/tests/test_crew.py`

**Interfaces:**
- Consumes: raw parser from Task 2.
- Produces: raw outputs for Analyst, both Architect tasks, Tester, and Reviewer.

- [ ] Write failing tests requiring those tasks to have no `output_pydantic` or `output_json`.
- [ ] Run `mise exec -- uv run --project crewai pytest crewai/tests/test_crew.py -q`; confirm the structural-output assertions fail.
- [ ] Remove the output declarations and state in each task prompt that its response is one JSON object matching its named contract, without fences or prose.
- [ ] Run the focused crew tests and confirm green.

### Task 4: Persist Invalid-Output Retries

**Files:**
- Modify: `crewai/src/crew/models.py`
- Modify: `crewai/src/crew/main.py`
- Test: `crewai/tests/test_main.py`
- Test: `crewai/tests/test_workflow.py`

**Interfaces:**
- Produces: one target-keyed contract-output retry state in `ExecutionState` and a common supervisor dispatch helper for structured roles.

- [ ] Write failing tests showing an invalid raw contract produces failed usage, retries once, records the second invocation separately, persists consumption before dispatch, and blocks without redispatch after restart.
- [ ] Run `mise exec -- uv run --project crewai pytest crewai/tests/test_main.py crewai/tests/test_workflow.py -q`; confirm red.
- [ ] Add the minimal `ExecutionState` fields and validation for an available, pending, or consumed target-keyed retry.
- [ ] Route Analyst, Architect outline/artifact, Tester, and Reviewer through one helper that records usage before retry/block handling and calls the raw parser.
- [ ] Preserve all existing semantic checks after parsing and retain the independent Architect length retry.
- [ ] Run the focused workflow/main tests and confirm green.

### Task 5: Verify the Change

**Files:**
- Modify: `docs/superpowers/plans/2026-09-04-portable-crew-contract-output.md`

- [x] Run `mise exec -- uv run --project crewai pytest crewai/tests -q`.
- [x] Run `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive`.
- [x] Run `mise exec -- pnpm verify`.
- [x] Run `git diff --check` and inspect `git status --short`; confirm the two pre-existing report files remain untracked and untouched.
