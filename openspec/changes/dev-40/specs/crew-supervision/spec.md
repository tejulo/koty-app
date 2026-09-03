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
`browser_operational` verification profiles. Architect SHALL record exactly one
selected profile in the active change design, and PlanManifest and
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
as separate one-task CrewAI executions with dynamic delegation disabled. A role
SHALL receive only paths to the phase-specific contracts it requires and SHALL
not receive another role's conversation output. The system SHALL not introduce
a CrewAI manager or Flow.

#### Scenario: Each role receives only its phase contract paths
- GIVEN a role invocation prepared by the supervisor
- WHEN the CrewAI task is created
- THEN the Crew contains exactly one task for that role
- AND its inputs contain only the required contract, pack, evidence, or scenario paths
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

#### Scenario: Explicit replan retains evidence
- GIVEN a ticket with persisted execution state and attempt evidence
- WHEN the ticket is invoked with `--replan`
- THEN the supervisor clears plan-contract references and transitions to `planning`
- AND prior attempt evidence remains under the active OpenSpec change

#### Scenario: Ralph remains the local supervisor
- GIVEN `ralph.sh --until-finalized` processes a ticket
- WHEN CrewAI reports `approved`
- THEN Ralph performs its existing local finalization supervision
- AND Ralph does not invoke OpenCode
