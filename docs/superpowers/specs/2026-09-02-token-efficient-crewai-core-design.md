# Token-Efficient Ralph and CrewAI Core

## Goal

Reduce token consumption for ticket automation while preserving the five roles,
the authoritative quality gates, OpenSpec, Linear finalization, and local Ralph
supervision.

## Scope

- Replace implicit context propagation between sequential CrewAI tasks with
  persisted, phase-specific contracts.
- Re-run only the phase that can address a recoverable failure.
- Keep the base gates for every ticket: `python`, `lint`, `test`, `build`,
  `integration`, and strict `openspec` validation.
- Support closed verification profiles that add evidence requirements without
  allowing a profile to remove a base gate or execute arbitrary commands.
- Record CrewAI token usage emitted by each phase.

## Non-Goals

- Replacing Ralph's local queue, branch, worker, and finalization supervision.
- Replacing OpenSpec, Linear, or the existing controlled verification tools.
- Introducing dynamic delegation, a CrewAI manager, or arbitrary verification
  commands.
- Removing Analyst, Architect, Programmer, Tester, or Reviewer.

## Architecture

`ralph.sh --until-finalized` continues to call the local coordinator. The
coordinator continues to own ticket selection, branch selection, worker
supervision, and finalization. CrewAI execution becomes a persistent phase
machine in `main.py` instead of two sequential crews that pass full prior task
outputs to later tasks.

```text
Ralph coordinator
  -> queue, branch, worker, finalizer
  -> planning: Analyst -> Architect -> OpenSpec preflight
  -> implementing: Programmer
  -> verifying: base gates
       failure -> implementing with RepairPack
  -> browser testing: Tester only when required
       failure -> implementing with RepairPack
  -> reviewing: Reviewer with ReviewPack
  -> approved -> finalizer
```

The persisted states are `planning`, `implementing`, `verifying`,
`browser_testing`, `reviewing`, `approved`, and `blocked`.

Each role runs in an isolated CrewAI invocation. A role receives the paths to
its required contracts rather than output from unrelated roles. This preserves
role independence and removes implicit sequential-context growth.

## Persisted Contracts

### TicketContract

Analyst produces a structured `TicketContract` and stores it in the active
change attempt directory. It contains:

- schema version, ticket ID, change ID, and source ticket hash;
- objective, in-scope work, constraints, dependencies, and ambiguities;
- acceptance criteria with stable `AC-*` identifiers.

Architect consumes this contract instead of a free-form Analyst output. The
ticket hash makes a ticket update an explicit planning invalidation.

### PlanManifest

Architect creates `PlanManifest` beside the active change artifacts. It
contains:

- hashes for proposal, design, tasks, and every spec;
- the selected verification profile;
- a complete mapping from each `AC-*` criterion to one or more task IDs;
- the OpenSpec change ID and manifest schema version.

The supervisor validates the manifest before implementation. Planning remains
valid only while its ticket and artifact hashes match the execution state.

### RepairPack

The Python supervisor creates a `RepairPack` after a recoverable base-gate,
browser, or review failure. It contains the phase, failing gate or reviewer
stage, evidence ID and hash, repair hint, allowed repair scope, and references
to the relevant artifact and log files. It never embeds complete logs or copies
the full OpenSpec artifacts.

Programmer receives the manifest and the current repair pack. A repair pack
whose plan hash differs from the current execution state is rejected before an
LLM call.

### ReviewPack

The supervisor creates `ReviewPack` only after base gates and required browser
testing pass. It contains:

- ticket and manifest hashes;
- acceptance-criterion to task mapping;
- OpenSpec artifact hashes and incomplete-task status;
- changed-file paths and diff summary;
- verification profile, gate statuses, evidence IDs, and browser result.

ReviewPack must reference every source and OpenSpec file needed to substantiate
the acceptance mapping. Reviewer inspects the referenced files only; it does
not receive Programmer or Tester conversation output.

### ExecutionState

`ExecutionState` remains local at `.agent/crew/<ticket>/execution.json`. It
stores the current phase, ticket and plan hashes, phase attempt counts, and
paths to the current contracts. State writes use a temporary file followed by
atomic replacement.

Attempt contracts, evidence, repair packs, and review packs are stored under
the active OpenSpec change attempt directory so they are retained with the
archived change. Runtime process files remain unversioned under `.agent/`.

## Verification Profiles

Every profile requires the base gates. Profiles are closed values selected by
Architect, recorded in `design.md`, and repeated in `PlanManifest`.

| Profile | Additional requirement |
| --- | --- |
| `standard` | None. |
| `browser` | Browser E2E evidence from Tester. |
| `operational` | ReviewPack maps every operational criterion to a versioned document, test, or source artifact with its hash. |
| `browser_operational` | Both browser and operational evidence. |

The supervisor rejects a profile that is missing, differs between design and
manifest, or attempts to alter the base gate list.

## Failure and Retry Semantics

- The initial run starts at `planning`.
- A valid TicketContract and PlanManifest move directly to `implementing` on a
  recoverable repair; Analyst and Architect are not re-run.
- A failed base gate creates RepairPack and returns to `implementing`.
- A required Browser E2E failure creates RepairPack and returns to
  `implementing`. After code changes, all base gates run again before Tester.
- A recoverable Reviewer verdict creates RepairPack and returns to
  `implementing`.
- Requirements, configuration, or external-dependency failures enter
  `blocked`.
- `MAX_TICKET_ATTEMPTS` counts Programmer repair attempts only.
- `MAX_INFRASTRUCTURE_ATTEMPTS` keeps its current infrastructure-only meaning.
- `--resume` continues the persisted phase. `--replan` explicitly invalidates
  planning. A changed ticket hash also invalidates planning.

## Token Controls and Observability

The LLM configuration adds per-role `max_iter` and `max_tokens` environment
settings. Initial defaults are:

| Role | max_iter | max_tokens |
| --- | ---: | ---: |
| Analyst | 4 | 800 |
| Architect | 12 | 1200 |
| Programmer | 20 | 2500 |
| Tester | 8 | 600 |
| Reviewer | 8 | 800 |

Each phase persists the token-usage value returned by CrewAI when available.
The recorded phase, role, model, limits, attempt, and raw usage payload provide
a baseline for later calibration without relying on unobserved estimates.

Tester is not invoked for `standard` or `operational`; the supervisor writes a
deterministic skipped browser result. Structured outputs keep Analyst,
Architect, Tester, and Reviewer summaries bounded. Programmer reports only
changed files, completed tasks, and status; controlled tools retain detailed
logs as referenced evidence.

Controlled tools limit a file or Linear response to 12,000 characters and a
command response to 4,000 characters. Full command output remains in the
attempt evidence file and is referenced by RepairPack rather than returned to
the agent.

## Testing

- Unit tests cover valid and invalid contract, manifest, pack, and hash
  validation.
- Unit tests cover all phase transitions, resume behavior, explicit replan,
  blocked outcomes, and attempt accounting.
- Supervisor tests prove a repair does not invoke Analyst or Architect.
- Profile tests prove every profile retains all base gates and only browser
  profiles invoke Tester.
- ReviewPack tests verify compact, complete evidence references and stale
  evidence rejection.
- Shell tests preserve Ralph's deterministic `--until-finalized` behavior and
  prove it does not invoke OpenCode.

## Risks and Decisions

- A stale contract can cause incorrect implementation. Ticket and artifact
  hashes make staleness a deterministic replan condition.
- A compact review pack can omit evidence. The pack carries hashes, required
  references, and acceptance mappings; the reviewer can inspect referenced
  files independently.
- Lower agent limits can stop a complex task early. Limits are configuration,
  usage is recorded per phase, and gates remain authoritative.
- A CrewAI Flow would add another orchestration layer without reducing LLM
  context. The existing Python supervisor remains the single phase owner.
