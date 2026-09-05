# DEV-40 Technical Design

## Phase Model

`ExecutionState` is stored locally at `.agent/crew/<ticket-id>/execution.json`.
Its closed `phase` values are `planning`, `implementing`, `verifying`,
`browser_testing`, `reviewing`, `approved`, and `blocked`. It stores the ticket
hash, current plan hash, per-phase attempt counts, selected profile, current
contract paths, and phase usage references. State is written to a temporary
file and atomically replaced so an interrupted write never leaves partial JSON.

Ralph continues to select tickets, select branches, supervise workers, and
finalize approved tickets. The Python supervisor owns only the phase loop; it
does not introduce a CrewAI manager or Flow.

## Contracts and Locations

Attempt artifacts are retained under
`openspec/changes/<change-id>/attempts/<attempt>/`:

| Artifact | Producer | Required hash relationship |
| --- | --- | --- |
| `ticket-contract.json` | Analyst | Contains ticket ID, change ID, source ticket hash, and `AC-*` criteria. |
| `context-catalog.json` | Supervisor | Records the attempt-scoped project-context sections used to render the body-free index and validates selected references. |
| `planning-checkpoint.json` | Supervisor | References the TicketContract and context-catalog hashes and stores the validated outline, units, and per-invocation status. |
| `plan-manifest.json` | Supervisor | References the TicketContract hash and hashes of proposal, design, tasks, and every OpenSpec spec; maps every `AC-*` to task IDs. |
| `previous-plan/` | Supervisor | Snapshot of active proposal, design, tasks, and specs before a replan replaces them. |
| `task-completion.json` | Supervisor | Records a successful Programmer phase against the original `tasks.md` path and hash without modifying the planned checklist. |
| `repair-pack.json` | Supervisor | References the current plan hash, failing evidence hash, and evidence paths without embedding full logs. |
| `browser-result.json` | Tester or supervisor | References the current plan hash and records passed, failed, or deterministic skipped status. |
| `review-pack.json` | Supervisor | References ticket and plan hashes, all acceptance mappings, OpenSpec hashes, changed files, gate evidence, and browser result. |
| `phase-usage-*.json` | Supervisor | Stores one file per role invocation. Architect filenames distinguish stage, unit, and invocation so a failed call and its retry never overwrite each other; ExecutionState aliases reference the latest applicable file. |

Before any role invocation or finalization, the supervisor rejects mismatched
ticket, plan, task-completion, repair, review, browser-result, or evidence
hashes. A changed ticket hash invalidates planning; all other stale or
inconsistent contracts are blocked rather than consumed.

## Portable Raw JSON Contract Transport

Every structured role invocation returns its contract as raw JSON text rather
than relying on a provider or CrewAI structured-output transport. This applies
to Analyst, both Architect invocation types, Tester, and Reviewer. Programmer
remains intentionally unstructured. The supervisor retains the exact raw
response as attempt evidence, parses it locally with the expected Pydantic
model, and treats that local validation as authoritative. Provider-side
decoding, schema enforcement, or a constructed model is not accepted as proof
that a contract is valid.

After local Pydantic parsing, the existing semantic, cross-contract, hash, and
stage-boundary validation remains mandatory and unchanged. A Pydantic failure
includes malformed JSON, a non-object response, or a response that does not
match the expected contract. The supervisor atomically records the raw output,
validation failure, role, expected model, invocation, and retry state as
attempt evidence. It records an invalid-output retry as `pending`, marks it
`consumed` before external dispatch, and retries that same structured invocation
at most once. The retry response is retained and locally validated in the same
way. A second invalid response, or a restart that finds a consumed retry without
a persisted validated result, blocks the current phase without advancing its
stage boundary.

The invalid-output retry is independent of, and does not relax or consume, the
existing Architect empty-response and length retry guarantees. Architect's
staged units, checkpoints, configured length budgets, and retry ownership remain
unchanged.

## Staged Architect Planning

After Analyst produces TicketContract, the supervisor builds an attempt-scoped
`context-catalog.json` whose index identifies project-context sections without
embedding their bodies. The Architect outline invocation receives exactly the
serialized TicketContract and that body-free context index. It returns a strict
`PlanOutline` that lists one `PlanUnitOutline` for proposal, design, tasks, and
each required spec. Each outline unit selects context references; the supervisor
rejects unknown references or a selection exceeding 12 references or 48,000
characters.

The supervisor then invokes Architect separately for each missing unit. Each
one-task artifact invocation receives exactly the serialized TicketContract,
the validated PlanOutline, the requested PlanUnitOutline, and the selected
context bodies for that unit, and returns one `PlanArtifactUnit`. Architect
remains tool-free, has delegation disabled, and does not receive prior
invocation conversation. The normal token budgets are 4,000 for the outline and
8,000 for each artifact unit, with low reasoning effort.

`planning-checkpoint.json` stores hash-bound catalog, TicketContract, outline,
validated units, and per-unit invocation status under the attempt directory.
The supervisor writes the checkpoint atomically after the outline, every unit
success, and every handled failure, then records its exact attempt path and file
SHA-256 together in an atomic ExecutionState replacement. On resume it requires
both fields, requires the expected attempt path, compares the persisted file
bytes before loading, and then validates the model-internal contract, catalog,
outline, and unit hashes. An orphan checkpoint, incomplete reference, or digest
mismatch blocks rather than being adopted. A valid resume reuses completed
units, invokes only missing units, and does not increment
`ExecutionState.last_attempt` for a unit retry. Ticket change and replan clear
both checkpoint reference fields while retaining prior attempt evidence.

CrewAI hidden retries are disabled for Architect with `max_retry_limit=0`. The
supervisor detects `LengthFinishReasonError` directly or anywhere in the
exception cause/context chain and retries only the failed artifact unit once
with a 16,000-token budget. Every successful or failed invocation has distinct
usage evidence recording stage, unit, invocation, status, effective limit,
error type, and raw usage when available. Exhaustion blocks planning without
discarding the checkpoint.

Supervisor retries are explicitly at-most-once because providers do not expose
a shared idempotency guarantee. Both the operation-wide empty-response retry
(for outline or artifact) and each per-unit length retry persist `pending`, then
persist `consumed` before external dispatch. A restart that sees `consumed`
without a checkpointed result blocks as uncertain/exhausted and never dispatches
that retry again. A crash before or during dispatch can therefore forfeit the
retry; this safety tradeoff prioritizes never exceeding configured retry counts.

Only after every unit validates SHALL the supervisor assemble the existing
PlanDraft shape and pass it through the existing `write_plan_draft()` path. No
other path may write active OpenSpec artifacts. The existing staged replacement,
rollback marker, OpenSpec preflight, PlanManifest creation, and final promotion
semantics remain unchanged.

## Verification Profiles

The selected profile is a closed enum recorded in the active change's
`design.md` and repeated in PlanManifest:

| Profile | Additional evidence |
| --- | --- |
| `standard` | None; supervisor persists a skipped browser result. |
| `browser` | Passing Tester browser evidence. |
| `operational` | ReviewPack maps every operational criterion to a versioned document, test, or source artifact and hash. |
| `browser_operational` | Both browser and operational evidence. |

### Selected Verification Profile

verification_profile: operational

DEV-40 selects `operational`. Architect includes the selected value in the
PlanDraft design content as exactly one `verification_profile: operational`;
the supervisor persists it to the active change. PlanManifest and
ExecutionState must repeat that exact value. For every ticket, planning fails
when this design field is missing, repeated, or outside the closed enum. Before executing
any base gate or selecting Tester, the supervisor rejects a missing profile, a
PlanManifest or ExecutionState profile that differs from the design value, or a
manifest whose declared base-gate list differs from the immutable sequence.

Every profile executes the immutable base sequence: `python`, `lint`, `test`,
`build`, `integration`, and strict OpenSpec validation. No profile may remove,
reorder around, or replace a base gate with an arbitrary command. Tester runs
only for `browser` and `browser_operational`.

## Retry Transitions

| Current phase | Event | Next phase | Required action |
| --- | --- | --- | --- |
| `planning` | TicketContract and PlanDraft validate; OpenSpec preflight passes | `implementing` | Supervisor persists OpenSpec artifacts, PlanManifest, and hashes. |
| `implementing` | Programmer completes | `verifying` | Persist TaskCompletion, Programmer usage, and the original `tasks.md` hash. |
| `verifying` | All six base gates pass | `browser_testing` or `reviewing` | Select browser phase only for browser profiles. |
| `verifying` | A recoverable base gate fails | `implementing` | Create RepairPack; only Programmer is eligible for the next LLM invocation. |
| `browser_testing` | Browser profile passes | `reviewing` | Persist browser evidence. |
| `browser_testing` | Browser profile fails recoverably | `implementing` | Create RepairPack; base gates run again after repair. |
| `browser_testing` | Non-browser profile | `reviewing` | Persist deterministic skipped browser result; do not invoke Tester. |
| `reviewing` | Reviewer approves valid ReviewPack | `approved` | Permit Ralph finalization. |
| `reviewing` | Recoverable reviewer verdict | `implementing` | Create RepairPack; only Programmer retries. |
| Any active phase | Requirements, configuration, or external dependency failure | `blocked` | Preserve evidence and do not invoke another role. |
| Any active phase | `--replan` or changed ticket hash | `planning` | Atomically invalidate plan-contract references while retaining attempt evidence. |

`MAX_TICKET_ATTEMPTS` counts Programmer repair attempts only.
`MAX_INFRASTRUCTURE_ATTEMPTS` retains its existing infrastructure-only meaning.
Planning retries `Invalid response from LLM call - None or empty.` from
Architect exactly once before blocking. A direct or wrapped
`LengthFinishReasonError` retries only its failed artifact unit once and does
not repeat the outline or completed units.
`--resume` continues the persisted phase without invalidating a valid plan.

## Role Isolation and Limits

Each role is a one-task CrewAI invocation. Analyst produces TicketContract;
Architect uses separate outline and artifact-unit crews to produce the staged
contracts as raw JSON text without tools; the supervisor locally validates them,
assembles the existing PlanDraft and
passes it to `write_plan_draft()` to write and hash the active OpenSpec artifacts
for PlanManifest. Programmer reads
PlanManifest and the current RepairPack; Tester receives browser inputs only
when required; Reviewer reads ReviewPack rather than other roles'
conversations. Analyst, Architect, Tester, and Reviewer use the raw JSON
transport; Programmer remains intentionally unstructured. Default limits are Analyst `4`/`2000`, Architect outline
`1`/`4000`, Architect artifact `1`/`8000`, Programmer `20`/`2500`, Tester
`8`/`600`, and Reviewer `8`/`800` for `max_iter`/`max_tokens`; an Architect
artifact length retry uses `16000` max tokens.

The supervisor stages each PlanDraft before replacing active plan artifacts.
It validates the draft profile before replacement and restores the
attempt-scoped `previous-plan/` snapshot if manifest validation or OpenSpec
preflight fails. A durable promotion marker restores that snapshot before a
subsequent planning run if the process is interrupted during replacement. This
recovery is the first operation in `run_planning()`, before contract, catalog,
or checkpoint validation and before any staged Architect invocation.

## Verification Strategy - Browser E2E: not_required

DEV-40 selects the `operational` profile and changes no browser surface, so it
requires operational ReviewPack evidence rather than Browser E2E. The
supervisor persists a deterministic skipped browser result; `browser` and
`browser_operational` profiles still require Tester for tickets whose selected
profile matches either value.
