# Verified Crew Gates Design

## Goal

Prevent Ralph from retrying an implementation based on stale or invented verification diagnoses while preserving the Crew reviewer as the source of the final verdict.

## Scope

This change covers the four code gates (`python`, `lint`, `test`, and `build`) and the OpenSpec gate. Browser E2E remains governed by the existing tester result and browser strategy.

## Requirements

- Every gate execution persists immutable evidence for the current Crew attempt.
- Evidence records the gate name, command, working directory, exit code, timestamps, raw output, output SHA-256, normalized diagnostics, and source-file SHA-256 values.
- The coding task receives the preceding attempt's structured failure evidence.
- A diagnostic whose source-file SHA-256 no longer matches the worktree is stale. The coding task must rerun that gate before editing from its coordinates.
- The reviewer keeps the final verdict, but must cite one evidence record for every code and OpenSpec gate it reports.
- Ralph validates cited evidence before accepting the reviewer result.
- A claimed `passed` gate with nonzero cited evidence, missing evidence, stale evidence, or a mismatched gate blocks the ticket for human review. Ralph must not automatically retry it.
- Retryable failures retain the current fixed maximum of three attempts. A changed or reduced diagnostic does not extend the limit.

## Design

### Evidence Store

Create `openspec/changes/<change-id>/attempts/attempt-<number>.verification.json` after each gate execution. The record is append-only and contains a schema version and an array of executions. A gate can execute more than once; each execution has a generated identifier. The final reviewer cites the execution identifier it used.

The existing verification tool owns evidence creation. It writes raw command output to an adjacent `.log` file and stores the relative path and SHA-256 in the JSON record. The JSON contains parsed ESLint diagnostics when the output matches ESLint's `path:line:column` format; unparseable output remains available as raw evidence and is not guessed from line numbers.

Each parsed diagnostic stores the SHA-256 of its source file at gate time. The coding prompt receives the latest failed execution and diagnostics. It must treat coordinates as invalid when the current file hash differs, and must rerun the failed gate before using that evidence to edit code.

### Reviewer Contract

Extend `CrewResult` with a required `evidence` mapping from `python`, `lint`, `test`, `build`, and `openspec` to execution IDs. `playwright` remains sourced from the tester result and does not require a code-gate evidence ID.

Configure the final review task with `output_pydantic=CrewResult`. CrewAI exposes that typed result from the final task through `CrewOutput.pydantic`; the existing parser continues to reject malformed fallback JSON.

Before writing `result.json`, `main.run` loads the cited evidence, verifies that each ID belongs to the current attempt and gate, and compares the evidence exit code with the reviewer status. It also rejects a citation whose diagnostic source files have changed after the evidence run. A disagreement is persisted as a `blocked` result with `failure_type="configuration"`, `failure_stage="verification_evidence"`, and a summary containing the gate, evidence ID, exit code, and evidence path. No retryable result is emitted for that condition.

### Attempt Lifecycle

The first run of an attempt creates an empty evidence document. Developer and reviewer gate invocations append entries to it. The reviewer must execute fresh gates after reviewing the code and cite those executions. The runner does not trust claims in free-form summaries.

Normal `retryable_failure` results continue to increment `CrewExecution.attempts`; the default remains `MAX_TICKET_ATTEMPTS=3`. A verification-evidence contradiction is blocked and is never retried by `coordinate-crew-ticket.sh`.

## Error Handling

- Missing, malformed, foreign-attempt, foreign-gate, or stale citations block with a deterministic reason.
- Failed gates may be cited only with `failed`; passed gates may be cited only with exit code zero.
- The evidence writer handles an unreadable diagnostic source file by omitting its source hash. The citation remains valid only as raw output; it cannot claim a normalized source coordinate.
- Evidence paths are repository-relative and command arguments stay allowlisted. No secrets are copied into the structured record.

## Testing

- Unit tests cover evidence append/load, output hashing, diagnostic extraction, and source-hash freshness.
- Unit tests prove that a reviewer result with a missing, mismatched, failed, or stale citation becomes `blocked`.
- Unit tests prove a complete, matching reviewer result remains valid.
- Integration tests run an actual failing lint command, persist its evidence, alter the diagnosed file, and confirm that the old diagnostic is stale.
- Existing retry tests prove three retryable failures still exhaust the fixed limit and a blocked evidence contradiction does not start another Crew execution.

## Non-Goals

- Do not make the supervisor the author of the final review verdict.
- Do not add retries beyond the fixed three-attempt policy.
- Do not alter ticket finalization, OpenSpec archival, or browser-test behavior except for validating code-gate evidence before a reviewer result is accepted.
