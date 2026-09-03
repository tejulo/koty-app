# Deterministic Ralph Supervisor

## Goal

Run a selected CrewAI ticket to a terminal result without repeatedly invoking OpenCode while the worker is still running.

## Scope

- Only `ralph.sh --until-finalized` changes behavior.
- The normal Ralph loop remains available for interactive OpenCode orchestration.
- No dependency, CrewAI task, or Linear API change is required.

## Design

`ralph.sh --until-finalized` delegates to `scripts/coordinate-crew-ticket.sh` before it requires OpenCode or loads the orchestration prompt.

The coordinator:

1. Gets one ticket from `crew_queue next`.
2. Ensures its branch is checked out, preserving the existing rule that a dirty worktree is allowed only when it already belongs to that ticket.
3. Starts the Linear ticket once.
4. Calls `finalize_ticket` and reacts to its terminal or retry states.
5. Starts or waits for `run-crew-ticket.sh` locally until the worker writes its result.
6. Finalizes an approved or archived change directly with `finalize_ticket`.

The coordinator uses JSON results as the source of truth and polls only local processes. It never invokes OpenCode. A retryable worker or finalization result waits a configurable short delay before the next attempt, preventing a busy loop.

## Status Mapping

| Source | Status | Coordinator action |
| --- | --- | --- |
| Queue | `empty` | Exit successfully. |
| Queue/finalizer | `blocked` | Print the reason and exit `2`. |
| Finalizer | `done` | Print the finalized ticket and exit successfully. |
| Finalizer | `not_ready` or `repair` | Start or restart CrewAI. |
| Finalizer | `retry` | Wait, then retry finalization. |
| Worker | `running` | Keep waiting locally. |
| Worker | `approved` or `archived` | Run finalization. |
| Worker | `retry` or `retryable_failure` | Wait, then start another CrewAI attempt. |
| Worker | `blocked` | Print the summary and exit `2`. |

## Configuration

- `CREW_TICKET_WAIT_SECONDS` defaults to `30` in deterministic mode because `coordinate-crew-ticket.sh` sets the polling interval before invoking the runner.
- `CREW_TICKET_TIMEOUT_SECONDS` defaults to `1800` in `run-crew-ticket.sh` and limits each supervised CrewAI process.
- `CREW_RETRY_DELAY_SECONDS` defaults to `5` seconds and prevents immediate retries after a failed worker or finalization.

## Verification

- Shell test stubs `crew_queue`, `finalize_ticket`, and `run-crew-ticket.sh`.
- The test proves `--until-finalized` completes one ticket without finding or executing `opencode`.
- The existing shell test runner executes the new test.
