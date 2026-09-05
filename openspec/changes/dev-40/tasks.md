# Tasks: DEV-40 - Token-Efficient Ralph and CrewAI Core

## Acceptance Criteria Mapping

| Criterion | Implementation task | Verification file |
| --- | --- | --- |
| AC-001 Persist TicketContract, PlanManifest, RepairPack, and ReviewPack; keep valid planning during repair | 2. Model and persist workflow contracts; 4. Implement the persistent phase machine | `crewai/tests/test_planning.py`; `crewai/tests/test_workflow.py`; `crewai/tests/test_main.py` |
| AC-002 Select an authoritative closed profile, reject missing or mismatched profiles and gate lists, retain six base gates, and invoke Tester only for validated browser profiles | 2. Model and persist workflow contracts; 4. Implement the persistent phase machine | `crewai/tests/test_workflow.py`; `crewai/tests/test_main.py` |
| AC-003 Retry recoverable base-gate, browser, and review failures through Programmer only | 4. Implement the persistent phase machine | `crewai/tests/test_main.py` |
| AC-004 Reject stale ticket, plan, pack, review, and evidence hashes; atomically save execution state | 2. Model and persist workflow contracts; 4. Implement the persistent phase machine; 5. Validate finalization and CLI semantics | `crewai/tests/test_workflow.py`; `crewai/tests/test_main.py`; `crewai/tests/test_finalizer.py` |
| AC-005 Build a complete, compact ReviewPack before review and finalization | 2. Model and persist workflow contracts; 5. Validate finalization and CLI semantics | `crewai/tests/test_workflow.py`; `crewai/tests/test_finalizer.py` |
| AC-006 Invoke isolated one-task roles without delegation, transport contracts as locally validated raw JSON, bound planning context, file, and Linear output, and persist configured token usage | 2. Model and persist workflow contracts; 3. Isolate CrewAI role invocations; 4. Implement the persistent phase machine | `crewai/tests/test_planning.py`; `crewai/tests/test_crew.py`; `crewai/tests/test_main.py`; `crewai/tests/test_custom_tool.py` |
| AC-007 Resume persisted state, explicitly replan, and preserve Ralph local supervision | 5. Validate finalization and CLI resume/replan semantics | `crewai/tests/test_finalizer.py`; `scripts/tests/run-crew-ticket.test.sh`; `scripts/tests/ralph.test.sh` |

## Implementation Checklist

- [ ] **1. Create DEV-40 OpenSpec artifacts**
  - Create this proposal, technical design, task checklist, and the
    `crew-supervision` behavioral delta.
  - Verify with `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive`.

- [ ] **2. Model and persist workflow contracts**
  - Add closed phase/profile models, contract and pack validation, hashing,
    attempt paths, and atomic execution-state persistence.
  - Define locally authoritative Pydantic validation for Analyst, Architect,
    Tester, and Reviewer raw JSON contract text, persist the raw response and
    validation result, and atomically track each structured invocation's
    at-most-once invalid-output retry; keep Programmer intentionally unstructured.
  - Add strict PlanOutline, PlanArtifactUnit, context catalog, and planning
    checkpoint contracts; build heading indexes and per-unit bundles limited to
    12 references and 48,000 characters; assemble the existing PlanDraft shape.
  - Add unit coverage in `crewai/tests/test_workflow.py` for valid contracts,
    stale hashes, complete acceptance mapping, selected-profile presence and
    design/manifest mismatch rejection, compact packs, and atomic saves.
  - Add `crewai/tests/test_planning.py` coverage for body-free indexes, bounded
    selected context, invalid references, strict unit structure, and PlanDraft
    assembly compatibility.

- [ ] **3. Isolate role invocations and bound outputs**
  - Split CrewAI execution into one-task role crews with raw JSON text outputs,
    per-role limits, and disabled dynamic delegation. The Architect outline crew
    receives exactly the serialized TicketContract and body-free context index;
    each artifact crew receives exactly the serialized TicketContract, validated
    PlanOutline, requested PlanUnitOutline, and selected context bodies. Other
    roles receive path-based inputs.
  - Split Architect into outline and artifact-unit crews with no tools,
    `max_retry_limit=0`, low reasoning effort, 4,000/8,000-token normal budgets,
    and a 16,000-token supervisor retry budget for artifact length failures.
  - Add coverage in `crewai/tests/test_crew.py` for role isolation, raw JSON
    contract outputs without provider-specific structured transport, bounded
    configuration, staged Architect inputs, and disabled delegation.

- [ ] **4. Implement the persistent phase machine**
  - Dispatch by persisted phase, run immutable base gates outside LLM context,
    create RepairPacks, persist token usage, and record deterministic browser
    skips for non-browser profiles.
  - Persist the context catalog and atomic planning checkpoint, resume from
    validated outline and units, and leave active OpenSpec files unchanged until
    the assembled PlanDraft is passed through the existing
    `write_plan_draft()` promotion path; do not add an alternate write path.
  - Detect direct or exception-chain `LengthFinishReasonError`, retry only the
    failed artifact unit once at the retry budget, persist every failed and
    successful invocation, and keep `last_attempt` stable across unit retries.
  - Parse Analyst, Architect, Tester, and Reviewer responses locally through
    their Pydantic contracts; persist invalid raw JSON and validation details,
    retry the same invocation once with an atomically consumed retry record, and
    block after a second invalid response or uncertain consumed retry without
    changing stage boundaries or Architect retry guarantees. Keep Programmer
    intentionally unstructured.
  - Add coverage in `crewai/tests/test_main.py` and
    `crewai/tests/test_custom_tool.py` for transitions, retry ownership,
    authoritative profile/gate-list validation before Tester selection, usage,
    12,000-character file and Linear response limits, and 4,000-character
    command response limits with referenced full evidence, local Pydantic
    validation, invalid-output retry auditability, and retry exhaustion.
  - Add workflow and main coverage for checkpoint paths and atomic reload,
    call order, direct and wrapped length failures, retry exhaustion, restart
    reuse, unique per-invocation usage evidence, unchanged active files, stable
    attempts, and exclusive promotion through `write_plan_draft()`.

- [ ] **5. Validate finalization and CLI resume/replan semantics**
  - Require current manifest and ReviewPack evidence before finalization; wire
    `--resume` and `--replan` through the CrewAI launcher, coordinator, and
    Ralph without changing Ralph's local supervisory role.
  - Add coverage in `crewai/tests/test_finalizer.py`,
    `scripts/tests/run-crew-ticket.test.sh`, and `scripts/tests/ralph.test.sh`.

- [ ] **6. Run focused and full verification**
  - Run planning, workflow, main, and crew unit suites, then all CrewAI and shell
    suites, `mise exec -- pnpm verify`, and
    `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive`.
