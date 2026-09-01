# Verified Crew Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Crew gate evidence durable and require the review verdict to match that evidence before Ralph retries or finalizes a ticket.

**Architecture:** The verification tool appends immutable gate runs to an attempt-local JSON document and stores raw output in adjacent logs. The reviewer cites those runs in its typed `CrewResult`; the runner and finalizer reject missing, mismatched, failed, or stale citations while preserving the reviewer as the author of the verdict.

**Tech Stack:** Python 3.12, Pydantic, CrewAI structured task output, pytest, pnpm gates.

**Spec:** `docs/superpowers/specs/2026-08-31-verified-crew-gates-design.md`

## Global Constraints

- Keep the fixed `MAX_TICKET_ATTEMPTS=3` policy unchanged.
- A verification-evidence contradiction must be `blocked`, never retried automatically.
- Use repository-relative evidence paths and existing allowlisted commands only.
- Keep the reviewer as the final-verdict author.
- Do not commit, archive OpenSpec, or update Linear as part of this change.

---

### Task 1: Persist Gate Evidence

**Files:**
- Create: `crewai/src/crew/evidence.py`
- Modify: `crewai/src/crew/tools/custom_tool.py:95-142,372-427`
- Test: `crewai/tests/test_evidence.py`
- Test: `crewai/tests/test_custom_tool.py`

**Interfaces:**
- Produces `record_gate_execution(gate: str, command: list[str], cwd: Path, exit_code: int, output: str) -> str`.
- Produces `load_attempt_evidence(change_id: str, attempt: int) -> dict`.
- Produces `parse_eslint_diagnostics(output: str) -> list[dict[str, object]]`.
- The verification tool returns the evidence execution ID with its existing command output.

- [ ] **Step 1: Write failing evidence tests**

```python
def test_record_gate_execution_persists_output_and_eslint_source_hash(tmp_path):
    execution_id = record_gate_execution(
        "lint", ["pnpm", "lint"], tmp_path, 1, ESLINT_FAILURE
    )
    evidence = load_attempt_evidence("dev-6", 1)
    run = evidence["executions"][0]
    assert run["id"] == execution_id
    assert run["exitCode"] == 1
    assert run["diagnostics"][0]["line"] == 12
    assert run["diagnostics"][0]["fileSha256"] == sha256(source)
```

- [ ] **Step 2: Run the focused tests and confirm they fail because the evidence module does not exist**

Run: `uv run --project crewai pytest crewai/tests/test_evidence.py -q`

- [ ] **Step 3: Implement the compact evidence module**

```python
def record_gate_execution(gate, command, cwd, exit_code, output):
    run = {
        "id": uuid4().hex,
        "gate": gate,
        "command": command,
        "cwd": relative(cwd),
        "exitCode": exit_code,
        "outputPath": write_output(output),
        "outputSha256": digest(output.encode()),
        "diagnostics": parse_eslint_diagnostics(output),
    }
    append_run(run)
    return run["id"]
```

Use `CREW_VERIFICATION_CHANGE_ID` and `CREW_VERIFICATION_ATTEMPT` to locate the active attempt. Parse only ESLint's file header plus `line:column severity message rule` lines. Add a SHA-256 only for files below `PROJECT_ROOT` that still exist.

- [ ] **Step 4: Append evidence from the allowlisted tools**

Record every `ejecutar_verificacion` run. Record `ejecutar_openspec` only for `validate` commands as the `openspec` gate. Append `Evidence: <id>` to the existing tool response without changing command behavior.

- [ ] **Step 5: Run evidence and tool tests**

Run: `uv run --project crewai pytest crewai/tests/test_evidence.py crewai/tests/test_custom_tool.py -q`
Expected: PASS.

### Task 2: Require Evidence In The Reviewer Result

**Files:**
- Modify: `crewai/src/crew/models.py:15-46`
- Modify: `crewai/src/crew/crew.py:210-215`
- Modify: `crewai/src/crew/config/tasks.yaml:175-238`
- Modify: `crewai/src/crew/main.py:450-572`
- Test: `crewai/tests/test_main.py`

**Interfaces:**
- `CrewResult` gains `attempt: int` and `evidence: dict[str, str]`.
- Produces `validate_reviewer_evidence(change_id: str, result: CrewResult) -> str | None` from `evidence.py`.
- `review_task()` sets `output_pydantic=CrewResult`.

- [ ] **Step 1: Write failing result-validation tests**

```python
def test_run_blocks_when_reviewer_claims_passed_lint_with_failed_evidence(...):
    result = reviewer_result(lint="passed", evidence={"lint": "lint-failed"})
    run_with(result)
    saved = load_result()
    assert saved["status"] == "blocked"
    assert saved["failure_stage"] == "verification_evidence"

def test_run_blocks_when_citation_is_stale(...):
    write_failed_lint_evidence(source_hash="old")
    source.write_text("changed")
    run_with(reviewer_result())
    assert load_result()["status"] == "blocked"
```

- [ ] **Step 2: Run the focused main tests and confirm the new assertions fail**

Run: `uv run --project crewai pytest crewai/tests/test_main.py -q`

- [ ] **Step 3: Extend the result model and review task**

```python
class CrewResult(BaseModel):
    ticket_id: str
    change_id: str
    attempt: int
    evidence: dict[str, str] = Field(default_factory=dict)
    ...
```

Set `output_pydantic=CrewResult` on the review task. Require the reviewer prompt to rerun every gate after its review, cite each returned evidence ID in `evidence`, and never infer a location from a prior attempt.

- [ ] **Step 4: Validate citations before saving a result**

```python
error = validate_reviewer_evidence(change_id, result)
if error:
    result = verification_evidence_failure(
        ticket_id, change_id, record_attempt, error, result.evidence
    )
```

The validator requires `python`, `lint`, `test`, `build`, and `openspec`; checks that each cited run belongs to `result.attempt`, has the expected gate name, matches the claimed `VerificationResult` status, and has no changed diagnostic source file. The generated failure is `blocked`, `configuration`, and `verification_evidence`.

- [ ] **Step 5: Run result-validation tests**

Run: `uv run --project crewai pytest crewai/tests/test_main.py -q`
Expected: PASS.

### Task 3: Preserve Evidence Across Attempts And Finalization

**Files:**
- Modify: `crewai/src/crew/main.py:506-568`
- Modify: `crewai/src/crew/finalizer.py:174-240,442-482`
- Modify: `crewai/tests/test_finalizer.py`
- Modify: `crewai/tests/test_main.py`

**Interfaces:**
- `main.run()` sets and restores `CREW_VERIFICATION_CHANGE_ID` and `CREW_VERIFICATION_ATTEMPT` around `Crew.kickoff()`.
- `_check_crew_result()` calls `validate_reviewer_evidence(change_id, result)` for approved results.

- [ ] **Step 1: Write failing lifecycle tests**

```python
def test_main_exposes_the_record_attempt_to_verification_tools(...):
    kickoff()
    assert seen_env == {"CREW_VERIFICATION_CHANGE_ID": "dev-6", "CREW_VERIFICATION_ATTEMPT": "4"}

def test_finalizer_rejects_approved_result_without_matching_evidence(...):
    result = approved_result(evidence={})
    assert finalize("DEV-6")["status"] == "repair"
```

- [ ] **Step 2: Run lifecycle tests and confirm they fail**

Run: `uv run --project crewai pytest crewai/tests/test_main.py crewai/tests/test_finalizer.py -q`

- [ ] **Step 3: Scope the evidence environment and add finalizer defense**

```python
previous = set_attempt_environment(change_id, record_attempt)
try:
    output = KotyAppCrew().crew().kickoff(inputs=inputs)
finally:
    restore_environment(previous)
```

The finalizer validates approved evidence again before running code gates. A missing or inconsistent citation returns its existing `repair` result and cannot archive or complete the ticket.

- [ ] **Step 4: Run lifecycle tests**

Run: `uv run --project crewai pytest crewai/tests/test_main.py crewai/tests/test_finalizer.py -q`
Expected: PASS.

### Task 4: Verify The Complete Workflow

**Files:**
- Modify: `scripts/tests/ralph.test.sh`
- Test: `crewai/tests/test_evidence.py`
- Test: `crewai/tests/test_main.py`
- Test: `crewai/tests/test_finalizer.py`

**Interfaces:**
- No new public interfaces.

- [ ] **Step 1: Add a regression scenario for a contradictory reviewer result**

The fixture must create a failed lint evidence record, emit a reviewer result claiming lint passed with that ID, and assert that the runner produces `blocked` without starting another worker.

- [ ] **Step 2: Run all Crew tests and the Ralph shell regression**

Run: `uv run --project crewai pytest crewai/tests -q && scripts/tests/ralph.test.sh`
Expected: PASS.

- [ ] **Step 3: Run project gates**

Run: `pnpm lint && pnpm test && pnpm build`
Expected: PASS.

- [ ] **Step 4: Inspect the diff and test status**

Run: `git diff --check && git status --short`
Expected: no whitespace errors; only intended files changed.
