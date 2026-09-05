# Proposal: DEV-40 - Token-Efficient Ralph and CrewAI Core

## Problem

The current CrewAI workflow carries broad sequential task output between roles.
That grows LLM context, makes retry ownership unclear, and does not provide a
durable contract that a later phase or finalizer can validate. A recoverable
verification failure must not repeat planning work or weaken the repository's
authoritative verification gates.

## Objective

Replace implicit cross-role context with persisted, hash-validated phase
contracts while retaining Ralph as the local ticket, worker, branch, and
finalization supervisor.

## Scope

- Persist a TicketContract, PlanManifest, RepairPack, ReviewPack, phase usage,
  and browser result for the active OpenSpec change attempt.
- Drive Analyst, Architect, Programmer, Tester, and Reviewer as isolated
  phase invocations through a persisted execution state machine.
- Transport Analyst, Architect, Tester, and Reviewer contracts as raw JSON text
  and validate them locally with the authoritative Pydantic contract before
  semantic processing; Programmer remains intentionally unstructured.
- Preserve the base `python`, `lint`, `test`, `build`, `integration`, and
  strict OpenSpec validation gates for every verification profile.
- Support only `standard`, `browser`, `operational`, and
  `browser_operational` profiles.
- Add stale-hash validation, atomic state writes, deterministic retry
  transitions, `--resume`, and explicit `--replan` behavior.
- Generate Architect planning as a compact outline followed by bounded proposal,
  design, tasks, and spec units with durable checkpoints and supervisor-owned
  length retries.
- Preserve Ralph's local deterministic supervision and finalization boundary.

## Out of Scope

- Replacing Ralph's local coordinator, queue, branch, worker, or finalizer.
- Adding a CrewAI manager, dynamic delegation, a CrewAI Flow, or arbitrary
  verification commands.
- Removing any of the five existing roles.
- Changing application runtime behavior outside the CrewAI and Ralph workflow.

## Expected Impact

Recoverable failures return only the Programmer to implementation with a
compact RepairPack. Planning remains valid when its ticket and artifact hashes
match, Reviewer receives concise evidence through ReviewPack, and all profiles
continue to enforce the same six base gates. Persisted phase usage establishes
a measured baseline for token-limit calibration. Staged Architect calls avoid
requiring one response to contain the full plan and resume from validated units
after interruption without changing the final PlanDraft or PlanManifest.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Stale planning produces an incorrect repair | Validate ticket, plan, pack, and evidence hashes before each role and before finalization. |
| Compact evidence omits necessary proof | ReviewPack contains criterion mappings, artifact hashes, changed files, gate evidence IDs, and profile results. |
| A profile weakens verification | Profiles are a closed enum and may add evidence only; the supervisor always runs all six base gates. |
| Process interruption corrupts phase state | Write state to a temporary file and replace `execution.json` atomically. |
| Lower limits stop complex work early | Keep per-role limits configurable and persist the raw CrewAI usage payload when available. |
| A staged call exceeds its output limit | Disable hidden CrewAI retries and let the supervisor retry only that unit once with the configured retry budget. |
| Partial planning leaks into the active change | Checkpoint validated units under the attempt and promote only the assembled, validated PlanDraft. |
| Provider-specific structured output rejects or mutates a contract | Require raw JSON text, validate it locally with Pydantic, and persist the invalid output and one supervisor-owned retry. |

## Acceptance Criteria Traceability

| Criterion | Delta requirement |
| --- | --- |
| AC-001 Persist phase contracts and reuse valid planning on repair | Persisted phase contracts; Staged Architect artifact generation |
| AC-002 Preserve immutable base verification and conditional Tester execution | Immutable base verification; Closed verification profiles |
| AC-003 Retry only the phase able to repair a recoverable failure | Deterministic phase transitions |
| AC-004 Reject stale inputs and write state atomically | Hash validation and atomic execution state; Durable staged-planning checkpoints |
| AC-005 Give Reviewer complete, compact, hash-backed evidence | ReviewPack evidence |
| AC-006 Persist bounded role usage for token calibration | Token usage observability; Portable raw JSON contract transport; Bounded per-unit planning context; Supervisor-owned Architect length retries |
| AC-007 Support resume, explicit replan, and local Ralph supervision | Resume, replan, and Ralph supervision |
