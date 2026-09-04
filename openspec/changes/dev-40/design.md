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
| `plan-manifest.json` | Supervisor | References the TicketContract hash and hashes of proposal, design, tasks, and every OpenSpec spec; maps every `AC-*` to task IDs. |
| `previous-plan/` | Supervisor | Snapshot of active proposal, design, tasks, and specs before a replan replaces them. |
| `task-completion.json` | Supervisor | Records a successful Programmer phase against the original `tasks.md` path and hash without modifying the planned checklist. |
| `repair-pack.json` | Supervisor | References the current plan hash, failing evidence hash, and evidence paths without embedding full logs. |
| `browser-result.json` | Tester or supervisor | References the current plan hash and records passed, failed, or deterministic skipped status. |
| `review-pack.json` | Supervisor | References ticket and plan hashes, all acceptance mappings, OpenSpec hashes, changed files, gate evidence, and browser result. |
| `phase-usage.json` | Supervisor | Records phase, role, model, configured limits, attempt, and raw CrewAI usage when available. |

Before any role invocation or finalization, the supervisor rejects mismatched
ticket, plan, task-completion, repair, review, browser-result, or evidence
hashes. A changed ticket hash invalidates planning; all other stale or
inconsistent contracts are blocked rather than consumed.

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
Architect exactly once before blocking.
`--resume` continues the persisted phase without invalidating a valid plan.

## Role Isolation and Limits

Each role is a one-task CrewAI invocation. Analyst produces TicketContract;
Architect receives the serialized contract and project context, then produces
PlanDraft content without tools; the supervisor writes and hashes that content
as the active OpenSpec artifacts and PlanManifest. Programmer reads
PlanManifest and the current RepairPack; Tester receives browser inputs only
when required; Reviewer reads ReviewPack rather than other roles'
conversations. Default limits are Analyst `4`/`2000`, Architect `1`/`4000`,
Programmer `20`/`2500`, Tester `8`/`600`, and Reviewer `8`/`800` for
`max_iter`/`max_tokens`.

The supervisor stages each PlanDraft before replacing active plan artifacts.
It validates the draft profile before replacement and restores the
attempt-scoped `previous-plan/` snapshot if manifest validation or OpenSpec
preflight fails. A durable promotion marker restores that snapshot before a
subsequent replan if the process is interrupted during replacement.

## Verification Strategy - Browser E2E: not_required

DEV-40 selects the `operational` profile and changes no browser surface, so it
requires operational ReviewPack evidence rather than Browser E2E. The
supervisor persists a deterministic skipped browser result; `browser` and
`browser_operational` profiles still require Tester for tickets whose selected
profile matches either value.
