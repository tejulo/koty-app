# Deterministic Ralph Supervisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `ralph.sh --until-finalized` supervise CrewAI locally without repeated OpenCode calls.

**Architecture:** Add a Bash coordinator that owns one selected ticket through queue lookup, branch selection, worker supervision, and finalization. Route only `--until-finalized` through it; keep normal Ralph/OpenCode behavior unchanged.

**Tech Stack:** Bash, existing `uv` CrewAI CLI commands, Git, shell test harness.

**Spec:** `docs/superpowers/specs/2026-08-31-deterministic-ralph-supervisor-design.md`

## Global Constraints

- Do not invoke OpenCode from deterministic `--until-finalized` mode.
- Keep the normal Ralph loop and its options unchanged.
- Use `crew_queue`, `run-crew-ticket.sh`, and `finalize_ticket` JSON as the source of truth.
- Preserve a dirty worktree only when it is already on the selected ticket branch.
- Default retry delay is exactly `5` seconds.
- Do not add dependencies or comments beyond behavior that is not self-evident.

---

### Task 1: Prove Deterministic Completion

**Files:**
- Modify: `scripts/tests/ralph.test.sh`
- Modify: `scripts/tests/run-bootstrap-tests.mjs`

**Interfaces:**
- Consumes: `./ralph.sh --until-finalized`.
- Produces: a regression test that fails while `--until-finalized` requires or invokes `opencode`.

- [ ] **Step 1: Write the failing test**

Create a fixture with `ralph.sh`, `scripts/coordinate-crew-ticket.sh`, `scripts/run-crew-ticket.sh`, a fake `uv` in `bin/`, and branch `feat/dev-31`. Have the `uv` stub emit these JSON results in order:

```bash
{"status":"ticket","ticket_id":"DEV-31","change_id":"dev-31","branch_name":"feat/dev-31"}
{"status":"started","ticket_id":"DEV-31"}
{"status":"not_ready","ticket_id":"DEV-31"}
{"status":"done","finalized":true,"ticket_id":"DEV-31"}
```

Have the runner stub emit:

```bash
{"status":"approved","ticket_id":"DEV-31"}
```

Make the `opencode` stub exit `99`. Assert `./ralph.sh --until-finalized` exits successfully, the runner was called once, and the output contains `Ralph finalized DEV-31`.

- [ ] **Step 2: Run test to verify it fails**

Run: `bash scripts/tests/ralph.test.sh`

Expected: failure because the current mode invokes `opencode` or cannot complete from the deterministic JSON stubs.

- [ ] **Step 3: Register the test if its name changes**

Keep `scripts/tests/run-bootstrap-tests.mjs` running `scripts/tests/ralph.test.sh`; update the registered path only if the test is split into a separate file.

### Task 2: Add the Local Ticket Coordinator

**Files:**
- Create: `scripts/coordinate-crew-ticket.sh`
- Modify: `ralph.sh:155-170`
- Test: `scripts/tests/ralph.test.sh`

**Interfaces:**
- Consumes: `crew_queue next`, `crew_queue start <ticket>`, `finalize_ticket <ticket>`, and `run-crew-ticket.sh <ticket> --start` JSON outputs.
- Produces: `scripts/coordinate-crew-ticket.sh`, exiting `0` for `empty` or finalized, `2` for blocked, and nonzero for unexpected statuses.

- [ ] **Step 1: Write the coordinator helpers**

Create `scripts/coordinate-crew-ticket.sh` with `set -euo pipefail`, repository-root resolution, and these helpers:

```bash
json_field() {
  python -c 'import json, sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"
}

run_queue() {
  (cd "$ROOT/crewai" && uv run crew_queue "$@")
}

run_finalizer() {
  (cd "$ROOT/crewai" && uv run finalize_ticket "$1")
}
```

Read one `run_queue next` result. Exit `0` for `empty`, exit `2` for `blocked`, and require `ticket` otherwise.

- [ ] **Step 2: Implement branch selection**

Keep the selected branch when it is already current. Otherwise require an empty `git status --porcelain` result and run:

```bash
git switch "$branch_name"
```

Print a clear error and exit `2` when switching would overwrite another ticket's dirty worktree.

- [ ] **Step 3: Implement the worker/finalizer state loop**

Run `run_queue start "$ticket_id"` once. Then loop over finalizer and worker results:

```bash
case "$finalizer_status" in
  done) exit 0 ;;
  blocked) exit 2 ;;
  not_ready|repair) worker_json="$("$ROOT/scripts/run-crew-ticket.sh" "$ticket_id" --start)" ;;
  retry) sleep "$RETRY_DELAY_SECONDS"; continue ;;
esac
```

For worker states, call the finalizer after `approved` or `archived`, exit `2` for `blocked`, and sleep then repeat for `retry` or `retryable_failure`. Treat all other states as an error.

- [ ] **Step 4: Route only deterministic mode through the coordinator**

Before `ralph.sh` exports `CREW_TICKET_WAIT_SECONDS`, adds OpenCode checks, or loads `.agent/PROMPT.md`, add:

```bash
if $UNTIL_FINALIZED; then
  exec "$ROOT/scripts/coordinate-crew-ticket.sh"
fi
```

This leaves ordinary Ralph iterations unchanged. Deterministic mode uses the coordinator's `30`-second polling default; the runner's direct default remains `600` seconds when `CREW_TICKET_WAIT_SECONDS` is unset outside the coordinator.

- [ ] **Step 5: Run the regression test**

Run: `bash scripts/tests/ralph.test.sh`

Expected: `PASS` and no `opencode` invocation.

### Task 3: Verify Both Ralph Modes

**Files:**
- Test: `scripts/tests/ralph.test.sh`
- Test: `scripts/tests/run-bootstrap-tests.mjs`

**Interfaces:**
- Consumes: the deterministic coordinator and existing normal `ralph.sh` path.
- Produces: evidence that deterministic completion avoids OpenCode and the existing bootstrap test registry still passes.

- [ ] **Step 1: Run shell syntax checks**

Run:

```bash
bash -n ralph.sh
bash -n scripts/coordinate-crew-ticket.sh
```

Expected: both commands exit `0` without output.

- [ ] **Step 2: Run the shell regression suite**

Run: `pnpm test:shell`

Expected: the Ralph test passes. If the pre-existing PowerShell bootstrap assertion fails, record it separately and do not change PowerShell files.

- [ ] **Step 3: Inspect the final diff**

Run:

```bash
git diff --check
git diff -- ralph.sh scripts/coordinate-crew-ticket.sh scripts/tests/ralph.test.sh
```

Expected: only the deterministic supervisor and its test are changed.
