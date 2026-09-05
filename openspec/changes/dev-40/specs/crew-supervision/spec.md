# crew-supervision Specification

## Purpose

Define a persisted, token-efficient CrewAI phase machine that keeps Ralph as
the local supervisor while retaining authoritative repository verification and
hash-backed evidence for review and finalization.

## ADDED Requirements

### Requirement: Persisted phase contracts

The system SHALL persist a TicketContract, PlanManifest, TaskCompletion,
RepairPack, and ReviewPack with hashes before a later phase consumes them.

#### Scenario: Repair keeps valid planning
- GIVEN a valid TicketContract and PlanManifest
- WHEN a base gate fails
- THEN only Programmer is eligible for the next LLM invocation
- AND Analyst and Architect are not invoked again

### Requirement: Portable raw JSON contract transport

Analyst, Architect, Tester, and Reviewer invocations SHALL return exactly one
contract as raw JSON text. Programmer SHALL remain intentionally unstructured.
The supervisor SHALL retain the exact raw response as attempt evidence and
locally parse it with the expected Pydantic model. Local Pydantic validation
SHALL be authoritative; the system SHALL NOT rely on provider or CrewAI
structured-output decoding, schema enforcement, or constructed model output as
evidence that a contract is valid.

After successful local Pydantic parsing, the existing semantic,
cross-contract, hash, and stage-boundary validation SHALL remain required and
unchanged. Malformed JSON, a non-object response, or a schema mismatch SHALL be
an invalid output.

For an invalid output, the supervisor SHALL atomically persist the raw response,
validation failure, role, expected contract model, invocation identifier, and
retry state. It SHALL persist the retry as `pending`, mark it `consumed` before
external dispatch, and retry only that structured invocation once. It SHALL
retain and locally validate the retry response identically. A second invalid
output, or a restart that observes a consumed retry without a persisted validated
result, SHALL block the current phase without advancing its stage boundary.

This invalid-output retry SHALL be independent of the existing Architect
empty-response and `LengthFinishReasonError` retry guarantees and SHALL NOT
relax, consume, or replace either guarantee.

#### Scenario: Local validation accepts a portable contract
- GIVEN a structured role returns a raw JSON object for its expected contract
- WHEN the supervisor receives the response
- THEN it retains the exact raw response as attempt evidence
- AND it validates the response locally with the expected Pydantic model before semantic processing
- AND existing semantic, cross-contract, hash, and stage-boundary validation proceeds unchanged

#### Scenario: Invalid output retries once with auditable evidence
- GIVEN a structured role returns malformed JSON or a JSON object that fails its expected Pydantic model
- WHEN the supervisor handles the response
- THEN it atomically persists the raw response, validation failure, invocation identifier, and `pending` retry state
- AND it marks that retry `consumed` before dispatching the same invocation once
- AND it retains the retry response and validation result as separate attempt evidence
- AND a second invalid response blocks the current phase without advancing its stage boundary

#### Scenario: Consumed invalid-output retry is not redispatched after restart
- GIVEN an invalid-output retry is durably `consumed`
- AND no locally validated result for that retry was persisted before the process stopped
- WHEN the supervisor restarts
- THEN it blocks the current phase
- AND it does not dispatch the invalid-output retry again
- AND the raw response, retry state, and existing phase evidence remain auditable

### Requirement: Staged Architect artifact generation

After TicketContract validation, the system SHALL invoke Architect once for a
strict PlanOutline and separately for one strict PlanArtifactUnit for proposal,
design, tasks, and each required spec. Every Architect invocation SHALL be a
one-task Crew with no tools, delegation, manager, Flow, or prior invocation
conversation. The supervisor SHALL assemble validated units into the existing
PlanDraft shape, SHALL pass it through the existing `write_plan_draft()` path,
and SHALL preserve the existing PlanManifest and atomic promotion boundary. No
alternate path SHALL write active OpenSpec artifacts.

#### Scenario: Complete units assemble the existing plan contract
- GIVEN a validated PlanOutline and one valid unit for every required artifact
- WHEN the supervisor completes staged planning
- THEN it assembles the units into the existing PlanDraft shape
- AND it promotes no active OpenSpec file before all units validate
- AND it passes the assembled PlanDraft through `write_plan_draft()`
- AND PlanManifest creation and promotion validation proceed unchanged

### Requirement: Bounded per-unit planning context

The system SHALL build an attempt-scoped project context catalog whose rendered
index omits section bodies. Each PlanOutline unit SHALL select only known
context references, limited by default to 12 references and 48,000 rendered
characters. The outline invocation SHALL receive exactly the serialized
TicketContract and body-free context index. Each artifact invocation SHALL
receive exactly the serialized TicketContract, validated PlanOutline, requested
PlanUnitOutline, and only the selected context bodies for that unit.

#### Scenario: Oversized or unknown context selection is rejected
- GIVEN an outline unit selects an unknown reference or exceeds a context bound
- WHEN the supervisor validates the PlanOutline
- THEN planning fails before an artifact-unit LLM invocation
- AND the active OpenSpec artifacts remain unchanged

#### Scenario: Artifact unit receives selected context only
- GIVEN a valid outline unit selects a bounded subset of catalog references
- WHEN the supervisor invokes Architect for that unit
- THEN the prompt includes the serialized TicketContract, validated PlanOutline, requested PlanUnitOutline, and selected section bodies
- AND it does not include unselected project-context section bodies

#### Scenario: Outline receives the body-free index only
- GIVEN a TicketContract and an attempt-scoped context catalog
- WHEN the supervisor invokes Architect for the outline
- THEN the prompt includes exactly the serialized TicketContract and rendered context index
- AND the rendered index contains no project-context section body

### Requirement: Durable staged-planning checkpoints

The system SHALL atomically persist an attempt-scoped context catalog and
planning checkpoint after outline completion, every artifact-unit success, and
every handled failure. The checkpoint SHALL bind TicketContract, catalog,
outline, units, and invocation status by hash. ExecutionState SHALL atomically
reference both its exact expected attempt path and its persisted file SHA-256.
Resume SHALL require both reference fields, compare the file bytes before model
loading, validate and reuse completed units, and invoke only missing units. A
checkpoint without a state reference, an incomplete reference, an unexpected
attempt path, or a digest mismatch SHALL block rather than be adopted. Ticket
change and replan SHALL clear both active checkpoint reference fields while
retaining prior evidence.

#### Scenario: Resume reuses validated units
- GIVEN planning stopped after one or more units were checkpointed
- WHEN the supervisor resumes with matching ticket, catalog, and checkpoint hashes
- THEN it does not regenerate the outline or completed units
- AND it continues with the first missing unit in the same planning attempt
- AND active OpenSpec artifacts remain unchanged until final assembly validates

#### Scenario: Stale or orphan checkpoint blocks
- GIVEN a planning checkpoint file is not referenced by ExecutionState or its bytes do not match the referenced SHA-256
- WHEN the supervisor resumes planning
- THEN it blocks before loading the checkpoint or invoking Architect
- AND it does not adopt the checkpoint as current control state

### Requirement: Supervisor-owned Architect length retries

Architect SHALL use `max_retry_limit=0`. The supervisor SHALL recognize a
`LengthFinishReasonError` raised directly or present in the exception cause or
context chain, persist failed-call usage, and retry only the failed artifact unit
once with the configured 16,000-token retry budget. Normal outline and artifact
budgets SHALL default to 4,000 and 8,000 tokens. A unit retry SHALL not increment
`ExecutionState.last_attempt`, and retry exhaustion SHALL block planning while
preserving the checkpoint and invocation evidence.

The supervisor SHALL apply at-most-once dispatch semantics to the operation-wide
empty-response retry for both outline and artifact calls and to each per-unit
length retry. It SHALL atomically persist `pending` and SHALL move it to
`consumed` before external dispatch. If a restart observes `consumed` without a
persisted result, planning SHALL block as uncertain or exhausted and SHALL NOT
dispatch that retry again. A crash before or during dispatch MAY forfeit the
retry so configured retry counts are never exceeded without provider
idempotency.

#### Scenario: Wrapped length failure retries only its unit
- GIVEN proposal and design units are already checkpointed
- AND the tasks unit fails with a wrapped `LengthFinishReasonError`
- WHEN the supervisor handles the failure
- THEN it records distinct failed-invocation usage for the tasks unit
- AND it retries only the tasks unit once with the retry token budget
- AND it does not regenerate the outline, proposal, or design units
- AND `ExecutionState.last_attempt` remains unchanged

#### Scenario: Direct length failure uses the same retry path
- GIVEN an artifact unit's first call raises `LengthFinishReasonError` directly
- WHEN the supervisor handles the failure
- THEN it records distinct failed-invocation usage for that unit
- AND it retries only that unit once with the same retry budget used for a wrapped error
- AND `ExecutionState.last_attempt` remains unchanged

#### Scenario: Length retry exhaustion preserves progress
- GIVEN an artifact unit has already consumed its one length retry
- WHEN that retry raises a direct or wrapped `LengthFinishReasonError`
- THEN planning enters `blocked`
- AND the latest checkpoint and usage evidence retain all completed and failed invocations
- AND no active OpenSpec artifact is replaced

#### Scenario: Crash after retry consumption does not redispatch
- GIVEN an empty-response or per-unit length retry is durably `consumed`
- AND no result for that retry was persisted before the process stopped
- WHEN planning restarts
- THEN planning enters `blocked`
- AND the retry is not dispatched again
- AND the checkpoint, ExecutionState, and `last_attempt` remain preserved

### Requirement: Immutable base verification

The system SHALL execute `python`, `lint`, `test`, `build`, `integration`, and
strict OpenSpec validation for every profile.

#### Scenario: Profile cannot remove a gate
- GIVEN any supported verification profile
- WHEN the supervisor prepares verification
- THEN all six base gates remain required
- AND no profile may substitute an arbitrary command for a base gate

### Requirement: Authoritative verification profiles and conditional Tester invocation

The system SHALL accept only `standard`, `browser`, `operational`, and
`browser_operational` verification profiles. Architect SHALL return exactly one
selected profile in its PlanDraft design content; the supervisor SHALL persist
it to the active change design. PlanManifest and
ExecutionState SHALL repeat that exact value. Before any base gate or Tester
selection, the supervisor SHALL reject a missing profile, a profile outside the
closed enum, a design/PlanManifest/ExecutionState mismatch, or a manifest that
declares a base-gate list other than `python`, `lint`, `test`, `build`,
`integration`, and strict OpenSpec validation. Tester SHALL run only when the
validated selected profile is `browser` or `browser_operational`.

#### Scenario: Mismatched manifest profile is rejected before verification
- GIVEN an active change design with `verification_profile: browser`
- AND a PlanManifest with profile `standard`
- WHEN the supervisor prepares verification
- THEN the supervisor rejects the manifest before executing a base gate or invoking Tester
- AND it does not persist a skipped browser result

#### Scenario: Non-browser profile skips Tester deterministically
- GIVEN matching design, PlanManifest, and ExecutionState profiles of `standard` or `operational`
- WHEN base verification passes
- THEN the supervisor persists a browser result with status `skipped`
- AND transitions directly to reviewing without invoking Tester

### Requirement: Hash validation and atomic execution state

The system SHALL reject stale ticket, plan, task-completion, repair, review,
browser-result, and evidence hashes before invoking a role or finalizing a ticket. The system
SHALL write `.agent/crew/<ticket-id>/execution.json` through a temporary file
and atomic replacement.

#### Scenario: Stale repair pack is rejected
- GIVEN a RepairPack whose plan hash differs from the current ExecutionState
- WHEN the supervisor prepares a Programmer invocation
- THEN the supervisor rejects the pack before the LLM call
- AND the ticket enters `blocked` unless a changed ticket hash requires planning

#### Scenario: Interrupted state save preserves valid JSON
- GIVEN an existing execution state file
- WHEN a state write is interrupted before replacement
- THEN the existing execution state remains readable
- AND no partial `execution.json` is consumed

### Requirement: Deterministic phase transitions

The system SHALL use the phases `planning`, `implementing`, `verifying`,
`browser_testing`, `reviewing`, `approved`, and `blocked` and SHALL retry only
the phase able to address a recoverable failure.

#### Scenario: Reviewer repair returns to Programmer
- GIVEN a current ReviewPack and a recoverable Reviewer verdict
- WHEN the supervisor processes the verdict
- THEN it creates a RepairPack and transitions to `implementing`
- AND only Programmer is eligible for the next LLM invocation

### Requirement: Complete ReviewPack evidence

The system SHALL create ReviewPack only after base gates and required browser
testing pass. ReviewPack SHALL include ticket and plan hashes, acceptance
criterion mappings, OpenSpec artifact hashes, hash-bound task-completion
evidence, changed files, diff summary, verification profile, gate evidence IDs,
and browser result.

#### Scenario: ReviewPack substantiates every acceptance criterion
- GIVEN a ticket ready for review
- WHEN the supervisor creates ReviewPack
- THEN every acceptance criterion maps to one or more tasks
- AND every referenced source or OpenSpec file has a hash
- AND TaskCompletion binds the original `tasks.md` path and hash without
  modifying its checklist
- AND Reviewer receives the ReviewPack paths rather than prior role conversation output

### Requirement: Isolated role invocation without delegation

The system SHALL invoke Analyst, Architect, Programmer, Tester, and Reviewer
as separate one-task CrewAI executions with dynamic delegation disabled.
Analyst, Architect, Tester, and Reviewer SHALL return raw JSON text that the
supervisor validates locally under the Portable raw JSON contract transport
requirement; Programmer SHALL remain intentionally unstructured. Roles
SHALL receive only paths to their phase-specific contracts, except the Architect
outline invocation, which receives exactly the serialized TicketContract and
body-free context index, and each Architect artifact invocation, which receives
exactly the serialized TicketContract, validated PlanOutline, requested
PlanUnitOutline, and selected context bodies. No role SHALL receive another
role's conversation output. The system SHALL not introduce a CrewAI manager or
Flow.

#### Scenario: Each role receives only its phase inputs
- GIVEN a role invocation prepared by the supervisor
- WHEN the CrewAI task is created
- THEN the Crew contains exactly one task for that role
- AND the Architect outline and artifact invocations receive only their exact staged inputs
- AND Analyst, Architect, Tester, and Reviewer responses are raw JSON text validated locally by the supervisor
- AND Programmer remains intentionally unstructured
- AND every other role receives only the required contract, pack, evidence, or scenario paths
- AND no prior role conversation output is supplied

#### Scenario: Dynamic delegation remains disabled
- GIVEN any of the five role crews
- WHEN its CrewAI configuration is inspected
- THEN `allow_delegation` is `False`
- AND no manager or dynamic role-selection mechanism is configured

### Requirement: Token usage observability and bounded role output

The system SHALL persist phase, role, configured model and limits, attempt, and
the raw CrewAI usage payload when available after each role invocation. The
system SHALL limit controlled file responses to 12,000 characters and command
responses to 4,000 characters while retaining complete output as referenced
evidence.

The system SHALL limit controlled Linear responses to 12,000 characters while
retaining complete content as referenced controlled evidence.

#### Scenario: Oversized command output retains evidence
- GIVEN a controlled command that writes more than 4,000 characters
- WHEN the command result is returned to a role
- THEN the returned result is limited to 4,000 characters and an evidence reference
- AND the full output remains in the referenced evidence file

#### Scenario: Oversized Linear response is bounded
- GIVEN a controlled Linear query that returns more than 12,000 characters
- WHEN the response is returned to a role
- THEN the returned response is limited to 12,000 characters
- AND the truncation preserves a reference to the full controlled evidence when available

### Requirement: Resume, replan, and Ralph local supervision

The system SHALL let `--resume` continue the persisted valid phase and SHALL
let `--replan` atomically invalidate planning references while retaining prior
attempt evidence. Ralph SHALL remain responsible for local queue, branch,
worker, and finalization supervision.

Before any planning contract, catalog, or checkpoint validation and before any
staged Architect invocation, the system SHALL recover a pending plan-promotion
marker by restoring its attempt-scoped previous-plan snapshot.

#### Scenario: Explicit replan retains evidence
- GIVEN a ticket with persisted execution state and attempt evidence
- WHEN the ticket is invoked with `--replan`
- THEN the supervisor clears plan-contract references and transitions to `planning`
- AND prior attempt evidence remains under the active OpenSpec change

#### Scenario: Pending promotion is recovered before early planning failure
- GIVEN a prior process stopped after partially replacing active OpenSpec files
- AND its durable promotion marker and previous-plan snapshot remain
- WHEN resumed staged planning later fails before `write_plan_draft()`
- THEN the previous active OpenSpec plan is restored before that failure
- AND no staged Architect invocation precedes restoration

#### Scenario: Ralph remains the local supervisor
- GIVEN `ralph.sh --until-finalized` processes a ticket
- WHEN CrewAI reports `approved`
- THEN Ralph performs its existing local finalization supervision
- AND Ralph does not invoke OpenCode
