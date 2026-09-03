# Token-Efficient Ralph and CrewAI Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace implicit sequential CrewAI context with persisted phase contracts so recoverable tickets re-run only the role that can fix the failure.

**Architecture:** Keep Ralph as the local queue and finalization supervisor. Build a Python phase machine that invokes one CrewAI role at a time, validates persisted contracts, runs authoritative gates outside LLM context, and passes compact repair or review packs by path.

**Tech Stack:** Python 3.12, CrewAI 1.15.16, Pydantic 2, Bash, pytest, pnpm, OpenSpec.

**Spec:** `docs/superpowers/specs/2026-09-02-token-efficient-crewai-core-design.md`

## Global Constraints

- Preserve Analyst, Architect, Programmer, Tester, and Reviewer; do not add dynamic delegation or a CrewAI manager.
- Preserve base gates `python`, `lint`, `test`, `build`, `integration`, and strict `openspec` validation for every profile.
- Allow only `standard`, `browser`, `operational`, and `browser_operational` profiles.
- Tester runs only for browser profiles; all other profiles persist a deterministic skipped browser result.
- Persist attempt artifacts below `openspec/changes/<change-id>/attempts/`; keep process state under `.agent/crew/<ticket-id>/`.
- Reject stale ticket, plan, repair, review, and evidence hashes before invoking a role or finalizing a ticket.
- Use `uv` for Python commands and `mise exec --` for pnpm commands.
- Do not commit unless the user explicitly requests a commit.

---

### Task 1: Create DEV-40 OpenSpec Artifacts

**Files:**
- Create: `openspec/changes/dev-40/proposal.md`
- Create: `openspec/changes/dev-40/design.md`
- Create: `openspec/changes/dev-40/tasks.md`
- Create: `openspec/changes/dev-40/specs/crew-supervision/spec.md`

**Interfaces:**
- Consumes: `DEV-40` acceptance criteria and the approved design specification.
- Produces: the change contract that Architect, Programmer, Reviewer, and finalizer validate.

- [ ] **Step 1: Create the active OpenSpec change**

Run:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec new change dev-40
```

Expected: `openspec/changes/dev-40/` exists and no archived ticket is reused.

- [ ] **Step 2: Write the failing OpenSpec expectation as a strict validation command**

Run:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate dev-40 --strict --no-interactive
```

Expected: failure until the proposal, design, tasks, and delta requirement are written.

- [ ] **Step 3: Write the proposal and behavioral delta**

Document these requirements in `spec.md`:

```markdown
### Requirement: Persisted phase contracts
The system SHALL persist a ticket contract, plan manifest, repair pack, and review pack with hashes before a later phase consumes them.

#### Scenario: Repair keeps valid planning
- GIVEN a valid ticket contract and plan manifest
- WHEN a base gate fails
- THEN only Programmer is eligible for the next LLM invocation.

### Requirement: Immutable base verification
The system SHALL execute python, lint, test, build, integration, and strict OpenSpec validation for every profile.

#### Scenario: Profile cannot remove a gate
- GIVEN any supported verification profile
- WHEN the supervisor prepares verification
- THEN all six base gates remain required.
```

Add requirements for conditional Tester invocation, stale-hash rejection, atomic state writes, ReviewPack evidence, token usage persistence, `--resume`, `--replan`, and Ralph local supervision.

- [ ] **Step 4: Write the technical design and task checklist**

`design.md` must define the closed profile enum, `ExecutionState` phases, artifact locations, hash relationships, and the exact retry transitions. `tasks.md` must map each criterion to an implementation task and a test file.

- [ ] **Step 5: Validate the OpenSpec change**

Run:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate dev-40 --strict --no-interactive
```

Expected: pass.

### Task 2: Model and Persist Workflow Contracts

**Files:**
- Modify: `crewai/src/crew/models.py`
- Create: `crewai/src/crew/workflow.py`
- Create: `crewai/tests/test_workflow.py`

**Interfaces:**
- Consumes: ticket ID, change ID, OpenSpec artifact files, `GateRun`, and role output.
- Produces: `TicketContract`, `PlanManifest`, `RepairPack`, `ReviewPack`, `ExecutionState`, and atomic load/save helpers.

- [ ] **Step 1: Write failing contract and persistence tests**

```python
def test_plan_manifest_rejects_an_unmapped_acceptance_criterion():
    manifest = PlanManifest(
        ticket_id="DEV-40",
        change_id="dev-40",
        ticket_sha256="a" * 64,
        artifacts={"proposal.md": "b" * 64},
        profile="standard",
        acceptance_map={"AC-001": ["1.1"]},
    )

    with pytest.raises(ValueError, match="AC-002"):
        validate_plan_manifest(manifest, ["AC-001", "AC-002"])


def test_save_execution_replaces_the_state_atomically(tmp_path, monkeypatch):
    monkeypatch.setattr(workflow, "PROJECT_ROOT", tmp_path)
    replaced = []
    monkeypatch.setattr(workflow.os, "replace", lambda source, target: replaced.append(target))

    workflow.save_execution("dev-40", ExecutionState())

    assert replaced[0].name == "execution.json"
```

- [ ] **Step 2: Run the new tests to confirm the interfaces are absent**

Run:

```bash
uv run --project crewai pytest crewai/tests/test_workflow.py -v
```

Expected: import or attribute failures for the new models and helpers.

- [ ] **Step 3: Add Pydantic models and one focused workflow module**

Define the closed literals and models in `models.py`:

```python
Phase = Literal[
    "planning", "implementing", "verifying", "browser_testing",
    "reviewing", "approved", "blocked",
]
VerificationProfile = Literal[
    "standard", "browser", "operational", "browser_operational",
]

class AcceptanceCriterion(BaseModel):
    id: str = Field(pattern=r"AC-[0-9]{3}")
    text: str = Field(min_length=1)

class TicketContract(BaseModel):
    schema_version: Literal[1] = 1
    ticket_id: str
    change_id: str
    ticket_sha256: str = Field(pattern=r"[0-9a-f]{64}")
    acceptance_criteria: list[AcceptanceCriterion]
    objective: str
    in_scope: list[str]
    constraints: list[str]
    dependencies: list[str]
    ambiguities: list[str]
```

Put hashing, paths, atomic JSON writes, and validation in `workflow.py`. Its public functions must be:

```python
def ticket_contract_path(change_id: str, attempt: int) -> Path: ...
def plan_manifest_path(change_id: str, attempt: int) -> Path: ...
def repair_pack_path(change_id: str, attempt: int) -> Path: ...
def review_pack_path(change_id: str, attempt: int) -> Path: ...
def browser_result_path(change_id: str, attempt: int) -> Path: ...
def file_sha256(path: Path) -> str: ...
def save_model(path: Path, model: BaseModel) -> None: ...
def load_model(path: Path, model_type: type[ModelT]) -> ModelT: ...
def validate_plan_manifest(manifest: PlanManifest, criterion_ids: list[str]) -> None: ...
```

- [ ] **Step 4: Add pack creation tests and implementation**

Test that `build_repair_pack()` references evidence by ID and output path without embedding command output, and that `build_review_pack()` includes all criterion mappings, modified paths, gate evidence IDs, profile, and browser result. Implement both functions with `file_sha256()` values for every referenced file.

- [ ] **Step 5: Run the contract suite**

Run:

```bash
uv run --project crewai pytest crewai/tests/test_workflow.py -v
```

Expected: pass, including stale plan and stale repair-pack rejection.

### Task 3: Isolate CrewAI Role Invocations and Bound Their Outputs

**Files:**
- Modify: `crewai/src/crew/crew.py`
- Modify: `crewai/src/crew/config/tasks.yaml`
- Modify: `crewai/src/crew/models.py`
- Modify: `crewai/.env.example`
- Modify: `crewai/tests/test_crew.py`

**Interfaces:**
- Consumes: `TicketContract`, `PlanManifest`, `RepairPack`, `ReviewPack`, and phase-specific inputs.
- Produces: `analyst_crew()`, `architect_crew()`, `programmer_crew()`, `tester_crew()`, and `reviewer_crew()`; each returns a one-task `Crew`.

- [ ] **Step 1: Write failing isolation and configuration tests**

```python
def test_programmer_crew_contains_only_the_coding_task(monkeypatch):
    configure_models(monkeypatch)

    crew = KotyAppCrew().programmer_crew()

    assert [task.name for task in crew.tasks] == ["coding_task"]


def test_analyst_has_the_documented_token_budget(monkeypatch):
    configure_models(monkeypatch)
    monkeypatch.setenv("ZEN_ANALYST_MAX_TOKENS", "800")

    assert KotyAppCrew().analyst().llm.max_tokens == 800
```

- [ ] **Step 2: Run the tests to confirm existing sequential crews do not satisfy them**

Run:

```bash
uv run --project crewai pytest crewai/tests/test_crew.py -v
```

Expected: failure because `programmer_crew()` and per-role token configuration do not exist.

- [ ] **Step 3: Add role-specific LLM limits and one-task crews**

Change `_zen_llm()` to accept a max-token environment variable and use the documented defaults from the design. Keep `temperature=0.2`, `allow_delegation=False`, and `respect_context_window=True`.

```python
def _zen_llm(model_env: str, max_tokens_env: str, default_max_tokens: int) -> LLM:
    return LLM(
        model=_required(model_env),
        base_url=os.environ.get("ZEN_BASE_URL", DEFAULT_ZEN_BASE_URL),
        api_key=_required("OPENCODE_API_KEY"),
        temperature=0.2,
        max_tokens=int(os.environ.get(max_tokens_env, default_max_tokens)),
    )

def programmer_crew(self) -> Crew:
    return self._crew([self.programer()], [self.coding_task()])
```

Set `max_iter` to 4, 12, 20, 8, and 8 for Analyst through Reviewer. Add the five `ZEN_*_MAX_TOKENS` variables to `.env.example`.

- [ ] **Step 4: Make task inputs path-based and structured**

Set `output_pydantic=TicketContract` for `analysis_task`. Update prompts so Architect reads `{ticket_contract_path}` and writes `PlanManifest`; Programmer reads `{plan_manifest_path}` and `{repair_pack_path}` when present; Tester reads profile/scenario paths; Reviewer reads `{review_pack_path}`. Remove the Programmer instruction to run all global gates; authoritative gates run only in the supervisor.

- [ ] **Step 5: Run CrewAI unit tests**

Run:

```bash
uv run --project crewai pytest crewai/tests/test_crew.py -v
```

Expected: pass; every phase has one task, Analyst output is structured, and Reviewer keeps no authority to run gates.

### Task 4: Implement the Persistent Phase Machine

**Files:**
- Modify: `crewai/src/crew/main.py`
- Modify: `crewai/tests/test_main.py`
- Modify: `crewai/src/crew/tools/custom_tool.py`
- Modify: `crewai/tests/test_custom_tool.py`

**Interfaces:**
- Consumes: `ExecutionState`, workflow contracts, single-role crews, `run_gate()`, and controlled tools.
- Produces: `run_phase()`, `transition()`, `run_ticket()`, persisted phase usage, and deterministic skipped Tester results.

- [ ] **Step 1: Write state transition tests before replacing the current orchestration block**

```python
def test_repair_runs_only_programmer_when_plan_is_current(tmp_path, monkeypatch):
    state = prepared_state(tmp_path, phase="implementing")
    calls = []
    monkeypatch.setattr(main, "kickoff_role", lambda role, **_: calls.append(role) or programmer_output())
    monkeypatch.setattr(main, "run_base_gates", lambda *_: passed_gates())

    main.run_ticket("DEV-40", "dev-40", state)

    assert calls == ["programmer", "reviewer"]


def test_standard_profile_persists_skipped_browser_result(tmp_path):
    state = prepared_state(tmp_path, profile="standard", phase="browser_testing")

    next_state = main.advance_phase("DEV-40", "dev-40", state)

    assert next_state.phase == "reviewing"
    assert load_model(
        workflow.browser_result_path("dev-40", state.last_attempt),
        TesterResult,
    ).status == "skipped"
```

- [ ] **Step 2: Run targeted tests and confirm they fail**

Run:

```bash
uv run --project crewai pytest crewai/tests/test_main.py -k "repair_runs_only or standard_profile" -v
```

Expected: failure because the current `run()` always starts planning and delivery crews.

- [ ] **Step 3: Add explicit phase advancement**

Use a loop that dispatches by `ExecutionState.phase`; do not use a CrewAI Flow.

```python
def advance_phase(ticket_id: str, change_id: str, state: ExecutionState) -> ExecutionState:
    if state.phase == "planning":
        return run_planning(ticket_id, change_id, state)
    if state.phase == "implementing":
        return run_programmer(ticket_id, change_id, state)
    if state.phase == "verifying":
        return run_verification(ticket_id, change_id, state)
    if state.phase == "browser_testing":
        return run_browser_testing(ticket_id, change_id, state)
    if state.phase == "reviewing":
        return run_review(ticket_id, change_id, state)
    return state
```

`run_planning()` invokes Analyst then Architect, saves and validates contracts, and runs only the OpenSpec preflight before setting `implementing`. `run_verification()` runs all base gates exactly once, produces RepairPack on the first failure, or selects browser/reviewing based on profile. `run_review()` builds ReviewPack only after all required evidence exists.

- [ ] **Step 4: Persist phase usage and reject stale inputs**

After each kickoff, write an attempt artifact containing phase, role, configured model and limits, and the serializable CrewAI usage payload when available. Before every role invocation, validate ticket hash, plan hashes, and the current pack hash. Move mismatches to `planning` only for changed tickets; otherwise return a blocked configuration result.

- [ ] **Step 5: Bound tool output without weakening evidence access**

Set `MAX_FILE_CHARS = 12_000` and `MAX_COMMAND_CHARS = 4_000`. Ensure tool output returns evidence references. Add tests that a 4,001-character command output is truncated while the full evidence file remains recorded, and that `escribir_archivo_raiz` still rejects paths outside `CREW_REPAIR_SCOPE`.

- [ ] **Step 6: Run main and controlled-tool tests**

Run:

```bash
uv run --project crewai pytest crewai/tests/test_main.py crewai/tests/test_custom_tool.py -v
```

Expected: pass, including no Analyst/Architect invocation during a valid repair and no Tester invocation for non-browser profiles.

### Task 5: Validate Finalization and CLI Resume/Replan Semantics

**Files:**
- Modify: `crewai/src/crew/finalizer.py`
- Modify: `crewai/tests/test_finalizer.py`
- Modify: `scripts/run-crew-ticket.sh`
- Modify: `scripts/coordinate-crew-ticket.sh`
- Modify: `ralph.sh`
- Modify: `scripts/tests/run-crew-ticket.test.sh`
- Modify: `scripts/tests/ralph.test.sh`

**Interfaces:**
- Consumes: approved `CrewResult`, current `PlanManifest`, current `ReviewPack`, and persisted execution state.
- Produces: finalization only when profile evidence and hashes are valid; `--resume` continuation and `--replan` planning invalidation.

- [ ] **Step 1: Write failing finalizer and shell regression tests**

```python
def test_finalizer_rejects_review_pack_with_a_different_plan_hash(tmp_path, monkeypatch):
    write_approved_result(tmp_path, plan_sha256="a" * 64)
    write_review_pack(tmp_path, plan_sha256="b" * 64)

    with pytest.raises(RuntimeError, match="ReviewPack.*plan"):
        finalizer._check_review_pack("DEV-40", "dev-40")
```

Add shell fixtures that assert `--replan` reaches `run_crew DEV-40 --replan`, while `--resume` continues the current phase and does not append `--replan`.

- [ ] **Step 2: Run the focused tests to confirm failure**

Run:

```bash
uv run --project crewai pytest crewai/tests/test_finalizer.py -v
bash scripts/tests/run-crew-ticket.test.sh
bash scripts/tests/ralph.test.sh
```

Expected: failure because neither finalizer pack validation nor `--replan` command propagation exists.

- [ ] **Step 3: Add finalizer evidence checks**

Before archiving, require a current PlanManifest and ReviewPack. Check matching ticket ID, change ID, plan hash, profile, gate evidence IDs, task completion, and browser result for browser profiles. For operational profiles, require the artifact/hash evidence recorded in ReviewPack.

- [ ] **Step 4: Add CLI plumbing**

Add `--replan` as a mutually exclusive run mode with `--resume` in `main.py`, `run-crew-ticket.sh`, coordinator, and Ralph deterministic mode. `--replan` clears plan-contract references atomically and starts at `planning`; it never clears old attempt evidence. `--resume` keeps the persisted phase and existing contracts.

- [ ] **Step 5: Run finalizer and shell suites**

Run:

```bash
uv run --project crewai pytest crewai/tests/test_finalizer.py -v
bash scripts/tests/run-crew-ticket.test.sh
bash scripts/tests/ralph.test.sh
```

Expected: pass; Ralph deterministic mode still never invokes OpenCode.

### Task 6: Update Documentation and Run the Full Verification Set

**Files:**
- Modify: `crewai/README.md`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `crewai/.env.example`
- Test: `crewai/tests/test_main.py`
- Test: `crewai/tests/test_crew.py`
- Test: `crewai/tests/test_workflow.py`
- Test: `crewai/tests/test_finalizer.py`
- Test: `scripts/tests/run-crew-ticket.test.sh`
- Test: `scripts/tests/ralph.test.sh`

**Interfaces:**
- Consumes: the implemented commands, profile enum, artifact paths, and token metrics.
- Produces: accurate operator documentation and end-to-end verification evidence.

- [ ] **Step 1: Update operator documentation**

Document the phase sequence, profiles, base gates, `.agent/` versus OpenSpec artifact locations, token metrics, `--resume`, and `--replan`. State that `--replan` is the only manual planning invalidation and that it preserves prior attempt evidence.

- [ ] **Step 2: Run focused Python suites**

Run:

```bash
uv run --project crewai pytest crewai/tests/test_main.py crewai/tests/test_crew.py crewai/tests/test_workflow.py crewai/tests/test_finalizer.py crewai/tests/test_custom_tool.py crewai/tests/test_gates.py crewai/tests/test_evidence.py -v
```

Expected: pass.

- [ ] **Step 3: Run shell suites**

Run:

```bash
pnpm test:shell
```

Expected: pass, including deterministic Ralph supervision.

- [ ] **Step 4: Validate DEV-40 OpenSpec and complete repository verification**

Run:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate dev-40 --strict --no-interactive
pnpm verify
```

Expected: both commands pass. If integration leaves PostgreSQL running, run `pnpm db:stop` after verification.

- [ ] **Step 5: Review the final diff before an optional commit**

Run:

```bash
git diff --check
git status --short
git diff -- crewai scripts ralph.sh README.md AGENTS.md openspec/changes/dev-40
```

Expected: only DEV-40 implementation, tests, OpenSpec, and documentation changes are present. Create a Conventional Commit only when explicitly requested.
