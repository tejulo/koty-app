# Create OpenSpec Before Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow a new Linear ticket to complete planning by having Architect create its OpenSpec artifacts before the supervisor reads `verification_profile`.

**Architecture:** Planning keeps Analyst and Architect as isolated invocations. Architect receives only known ticket and contract values, creates the active OpenSpec artifacts, then returns a manifest; the supervisor reads the selected profile and artifact hashes from those files and validates the manifest before advancing to implementation.

**Tech Stack:** Python 3.12, CrewAI 1.15.16, Pydantic 2, pytest, YAML, OpenSpec.

**Spec:** `docs/superpowers/specs/2026-09-02-token-efficient-crewai-core-design.md`

## Global Constraints

- Valid profiles remain exactly `standard`, `browser`, `operational`, and `browser_operational`.
- The Architect decides and records the profile in `design.md`; the supervisor validates it and never supplies a default.
- Every plan continues to require hashes for `proposal.md`, `design.md`, `tasks.md`, and at least one OpenSpec spec.
- Base gates remain `python`, `lint`, `test`, `build`, `integration`, and strict OpenSpec validation for every profile.
- Keep runtime state under `.agent/crew` and retained attempt contracts under the active OpenSpec change.

---

### Task 1: Capture Fresh-Change Planning Behavior

**Files:**
- Modify: `crewai/tests/test_main.py:209-274`
- Modify: `crewai/tests/test_crew.py:195-225`

**Interfaces:**
- Consumes: `run_planning(ticket_id, change_id, state)` and the existing `kickoff_role` test seam.
- Produces: regression coverage proving Architect runs when the active change has no artifacts and receives no profile or artifact hashes before it creates them.

- [x] **Step 1: Write the failing planning regression test**

Replace the pre-seeded artifact setup with a mocked Architect invocation that writes these files to the fresh active change:

```python
for name, content in {
    "proposal.md": "proposal",
    "design.md": "verification_profile: operational",
    "tasks.md": "tasks",
    "specs/crew-supervision/spec.md": "spec",
}.items():
    path = change / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
```

Return a `PlanManifest` built from the written hashes. Assert planning advances to `implementing`, Architect is called after Analyst, and its inputs are exactly `ticket_contract_path`, `plan_manifest_path`, `ticket_id`, `change_id`, `ticket_sha256`, `ticket_contract_sha256`, and `base_gates`.

- [x] **Step 2: Run the regression test to verify it fails**

Run: `uv run pytest tests/test_main.py::test_planning_creates_artifacts_before_reading_the_profile -q`

Expected: FAIL because the current supervisor calls `_selected_profile()` before the mocked Architect can create `design.md`.

- [x] **Step 3: Update the task-template contract test**

Change the expected architecture placeholders to:

```python
{
    "ticket_contract_path",
    "plan_manifest_path",
    "ticket_id",
    "change_id",
    "ticket_sha256",
    "ticket_contract_sha256",
    "base_gates",
}
```

- [x] **Step 4: Run the task-template test to verify it fails**

Run: `uv run pytest tests/test_crew.py::test_role_tasks_accept_their_phase_contract_paths_and_authoritative_hashes -q`

Expected: FAIL because the existing template still requires `verification_profile` and `openspec_artifact_hashes` before Architect runs.

### Task 2: Create Artifacts Before Validating the Manifest

**Files:**
- Modify: `crewai/src/crew/config/tasks.yaml:16-29`
- Modify: `crewai/src/crew/main.py:338-365`
- Test: `crewai/tests/test_main.py:209-274`
- Test: `crewai/tests/test_crew.py:195-225`

**Interfaces:**
- Consumes: a persisted `TicketContract`, an empty active OpenSpec change, and a `PlanManifest` produced by Architect.
- Produces: a validated `PlanManifest` and `ExecutionState` in `implementing`, or a blocked state if the created design lacks a valid profile or the manifest hashes do not match.

- [x] **Step 1: Change the Architect task instructions**

Require Architect to create or update `proposal.md`, `design.md`, `tasks.md`, and at least one file below `specs/`. Require `design.md` to contain one valid `verification_profile` and require the returned manifest to calculate hashes from the files it created. Keep the contract, ticket identity, and immutable base gates as supplied inputs.

- [x] **Step 2: Reorder `run_planning()`**

Invoke Architect with only known contract data, then read the profile and artifact hashes after it returns:

```python
architect = kickoff_role("architect", inputs={...})
_record_usage(state, "architect", architect)
manifest = _as_model(architect, PlanManifest)
profile = _selected_profile(change_id)
artifact_paths = {
    name: active_change(change_id) / name
    for name in manifest.artifacts
}
```

Pass `profile` and `artifact_paths` to `workflow.validate_plan_manifest()` unchanged. Do not add a default profile or relax any manifest, hash, or OpenSpec checks.

- [x] **Step 3: Run focused tests to verify the change**

Run: `uv run pytest tests/test_main.py tests/test_crew.py -q`

Expected: PASS, including the fresh-change regression and task-template contract tests.

- [ ] **Step 4: Commit the implementation**

```bash
git add crewai/src/crew/config/tasks.yaml crewai/src/crew/main.py crewai/tests/test_main.py crewai/tests/test_crew.py docs/superpowers/plans/2026-09-03-create-openspec-before-profile.md
git commit -m "fix(crewai): create OpenSpec before profile validation"
```

### Task 3: Validate Repository Gates and Integrate

**Files:**
- Verify: `openspec/changes/dev-40/`
- Verify: repository quality gates

**Interfaces:**
- Consumes: the committed planning fix.
- Produces: verified branch pushed to origin and merged into `main`.

- [ ] **Step 1: Validate the active OpenSpec change**

Run: `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive`

Expected: PASS.

- [ ] **Step 2: Run repository verification**

Run: `mise exec -- pnpm verify`

Expected: PASS for lint, typecheck, Vitest, shell tests, builds, and `crew:check`.

- [ ] **Step 3: Inspect the commit before publishing**

Run: `git status --short && git diff main...HEAD && git log --oneline -10`

Expected: only the planning fix, its regression tests, and this implementation plan are included; untracked third-party reports remain unstaged.

- [ ] **Step 4: Push and merge**

```bash
git push origin feat/dev-40-optimize-crewai-core
git switch main
git merge --no-ff feat/dev-40-optimize-crewai-core -m "merge: fix CrewAI OpenSpec planning"
git push origin main
```

Expected: `main` contains the fix and matches `origin/main`.
