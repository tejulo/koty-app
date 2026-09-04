# Tasks: DEV-40 - Token-Efficient Ralph and CrewAI Core

## Acceptance Criteria Mapping

| Criterion | Implementation task | Verification file |
| --- | --- | --- |
| AC-001 Persist TicketContract, PlanManifest, RepairPack, and ReviewPack; keep valid planning during repair | 2. Model and persist workflow contracts | `crewai/tests/test_workflow.py` |
| AC-002 Select an authoritative closed profile, reject missing or mismatched profiles and gate lists, retain six base gates, and invoke Tester only for validated browser profiles | 2. Model and persist workflow contracts; 4. Implement the persistent phase machine | `crewai/tests/test_workflow.py`; `crewai/tests/test_main.py` |
| AC-003 Retry recoverable base-gate, browser, and review failures through Programmer only | 4. Implement the persistent phase machine | `crewai/tests/test_main.py` |
| AC-004 Reject stale ticket, plan, pack, review, and evidence hashes; atomically save execution state | 2. Model and persist workflow contracts; 5. Validate finalization and CLI semantics | `crewai/tests/test_workflow.py`; `crewai/tests/test_finalizer.py` |
| AC-005 Build a complete, compact ReviewPack before review and finalization | 2. Model and persist workflow contracts; 5. Validate finalization and CLI semantics | `crewai/tests/test_workflow.py`; `crewai/tests/test_finalizer.py` |
| AC-006 Invoke isolated one-task roles without delegation, bound file and Linear output, and persist configured token usage | 3. Isolate CrewAI role invocations; 4. Implement the persistent phase machine | `crewai/tests/test_crew.py`; `crewai/tests/test_main.py`; `crewai/tests/test_custom_tool.py` |
| AC-007 Resume persisted state, explicitly replan, and preserve Ralph local supervision | 5. Validate finalization and CLI resume/replan semantics | `crewai/tests/test_finalizer.py`; `scripts/tests/run-crew-ticket.test.sh`; `scripts/tests/ralph.test.sh` |

## Implementation Checklist

- [ ] **1. Create DEV-40 OpenSpec artifacts**
  - Create this proposal, technical design, task checklist, and the
    `crew-supervision` behavioral delta.
  - Verify with `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive`.

- [ ] **2. Model and persist workflow contracts**
  - Add closed phase/profile models, contract and pack validation, hashing,
    attempt paths, and atomic execution-state persistence.
  - Add unit coverage in `crewai/tests/test_workflow.py` for valid contracts,
    stale hashes, complete acceptance mapping, selected-profile presence and
    design/manifest mismatch rejection, compact packs, and atomic saves.

- [ ] **3. Isolate role invocations and bound outputs**
  - Split CrewAI execution into one-task role crews with structured outputs,
    per-role limits, and disabled dynamic delegation. Architect receives the
    serialized TicketContract and project context because it has no filesystem
    tools; other roles receive path-based inputs.
  - Add coverage in `crewai/tests/test_crew.py` for role isolation, bounded
    configuration, role-specific task inputs, and disabled delegation.

- [ ] **4. Implement the persistent phase machine**
  - Dispatch by persisted phase, run immutable base gates outside LLM context,
    create RepairPacks, persist token usage, and record deterministic browser
    skips for non-browser profiles.
  - Add coverage in `crewai/tests/test_main.py` and
    `crewai/tests/test_custom_tool.py` for transitions, retry ownership,
    authoritative profile/gate-list validation before Tester selection, usage,
    12,000-character file and Linear response limits, and 4,000-character
    command response limits with referenced full evidence.

- [ ] **5. Validate finalization and CLI resume/replan semantics**
  - Require current manifest and ReviewPack evidence before finalization; wire
    `--resume` and `--replan` through the CrewAI launcher, coordinator, and
    Ralph without changing Ralph's local supervisory role.
  - Add coverage in `crewai/tests/test_finalizer.py`,
    `scripts/tests/run-crew-ticket.test.sh`, and `scripts/tests/ralph.test.sh`.

- [ ] **6. Run focused and full verification**
  - Run the CrewAI unit suites, shell suites, `mise exec -- pnpm verify`, and
    `OPENSPEC_TELEMETRY=0 mise exec -- pnpm exec openspec validate dev-40 --strict --no-interactive`.
