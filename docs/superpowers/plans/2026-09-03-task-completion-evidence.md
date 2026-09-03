# Task Completion Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require hash-backed evidence for every PlanManifest acceptance criterion before standard or browser work can be reviewed or finalized.

**Architecture:** Extend the supervisor-produced `TaskCompletion` artifact with one evidence reference per `acceptance_map` criterion. Validation compares the evidence keys with the manifest, rejects empty mappings, and verifies each referenced file hash; ReviewPack and finalizer reuse that validation for every verification profile.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, CrewAI 1.15.16.

**Spec:** `openspec/changes/dev-40/design.md`

## Global Constraints

- Keep `openspec/changes/dev-40/tasks.md` unchanged and hash-stable.
- Keep the six immutable base gates and closed verification-profile enum unchanged.
- Preserve stale hash rejection for plans, tasks, TaskCompletion, and ReviewPack evidence.
- Do not stage or commit changes.

---

### Task 1: Prove Incomplete Completion Evidence Cannot Approve

**Files:**
- Modify: `crewai/tests/test_workflow.py`
- Modify: `crewai/tests/test_finalizer.py`

**Interfaces:**
- Consumes: `TaskCompletion`, `PlanManifest.acceptance_map`, `workflow.build_review_pack()`, and `finalizer._check_review_pack()`.
- Produces: failing regressions for standard and browser profiles whose completion artifact omits or empties an acceptance criterion's evidence.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("profile", ["standard", "browser"])
def test_review_pack_rejects_completion_without_evidence_for_every_criterion(...):
    completion = workflow.build_task_completion(...)
    completion.acceptance_evidence = {"AC-001": {}}
    write_model(completion_path, completion)

    with pytest.raises(ValueError, match="TaskCompletion evidence is incomplete"):
        workflow.build_review_pack(...)
```

```python
def test_finalizer_rejects_standard_review_pack_with_empty_completion_evidence(...):
    _write_current_review_artifacts(..., persisted_profile="standard")
    completion = workflow.load_model(completion_path, TaskCompletion)
    completion.acceptance_evidence = {"AC-001": {}}
    workflow.save_model(completion_path, completion)

    with pytest.raises(RuntimeError, match="TaskCompletion evidence"):
        finalizer._check_review_pack("DEV-40", "dev-40")
```

- [ ] **Step 2: Run the targeted tests and confirm they fail because the artifact has no criterion evidence**

Run: `mise exec -- uv run pytest tests/test_workflow.py tests/test_finalizer.py -k "completion and evidence" -v`

Expected: FAIL because current TaskCompletion only contains plan and tasks hashes.

### Task 2: Persist and Validate Criterion Evidence

**Files:**
- Modify: `crewai/src/crew/models.py`
- Modify: `crewai/src/crew/workflow.py`
- Modify: `crewai/src/crew/main.py`

**Interfaces:**
- Consumes: `PlanManifest.acceptance_map`, changed source/test/document paths, and `TaskCompletion` hashes.
- Produces: `TaskCompletion.acceptance_evidence: dict[str, dict[str, str]]`, with every key mapped once to at least one hash-backed project file.

- [ ] **Step 1: Add evidence to the persisted model**

```python
class TaskCompletion(BaseModel):
    ...
    acceptance_evidence: dict[str, dict[str, str]]
```

- [ ] **Step 2: Build evidence from changed project files and persist it after Programmer completes**

```python
def build_task_completion(
    manifest: PlanManifest,
    plan_path: Path,
    tasks_path: Path,
    acceptance_evidence: Mapping[str, list[Path]],
) -> TaskCompletion: ...
```

`run_programmer()` supplies the changed paths for every manifest criterion while excluding files beneath the active OpenSpec change. The build function rejects missing criterion keys, unknown criterion keys, empty evidence, external paths, and stale hashes.

- [ ] **Step 3: Reuse TaskCompletion validation before review and finalization**

`build_review_pack()` and `validate_review_pack()` continue to load and validate TaskCompletion. `run_verification()` already calls the same validation. `finalizer._check_review_pack()` reaches it through `validate_review_pack()` for every profile.

- [ ] **Step 4: Run the targeted tests and confirm they pass**

Run: `mise exec -- uv run pytest tests/test_workflow.py tests/test_finalizer.py -k "completion and evidence" -v`

Expected: PASS for valid standard/browser evidence, and rejection for missing, empty, unknown, or stale evidence.

### Task 3: Verify the Regression and Record the Result

**Files:**
- Modify: `.superpowers/sdd/2026-09-02-token-efficient-crewai-core/task-completion-fix-report.md`
- Test: `crewai/tests/test_main.py`
- Test: `crewai/tests/test_workflow.py`
- Test: `crewai/tests/test_finalizer.py`

**Interfaces:**
- Consumes: the complete phase-machine and finalizer test suites.
- Produces: verification evidence and an appended P1 report without changing the checklist artifact.

- [ ] **Step 1: Run the focused CrewAI suites**

Run: `mise exec -- uv run pytest tests/test_main.py tests/test_workflow.py tests/test_finalizer.py -v`

Expected: PASS.

- [ ] **Step 2: Run repository verification and OpenSpec validation**

Run: `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive && mise exec -- pnpm verify`

Expected: PASS.

- [ ] **Step 3: Append the implementation, rejected cases, and command results to the P1 report**

Record the unchanged `tasks.md` invariant, test coverage, and exact verification results. Do not stage or commit.

## Self-Review

- Spec coverage: preserves the phase contract and hash-validation requirements in `openspec/changes/dev-40/design.md`; adds proof for criterion-level completed work across all profiles.
- Placeholder scan: no deferred implementation or unspecified validation remains.
- Type consistency: `TaskCompletion.acceptance_evidence` is constructed by `build_task_completion()` and checked by `validate_task_completion()` before ReviewPack and finalizer consumption.
