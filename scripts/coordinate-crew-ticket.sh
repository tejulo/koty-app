#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export CREW_TICKET_WAIT_SECONDS="${CREW_TICKET_WAIT_SECONDS:-30}"
RETRY_DELAY_SECONDS="${CREW_RETRY_DELAY_SECONDS:-5}"
RESUME=false

if [[ "${1:-}" == "--resume" ]]; then
  RESUME=true
fi

json_field() {
  python -c 'import json, sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$1"
}

queue() {
  (cd "$ROOT/crewai" && uv run crew_queue "$@")
}

finalize() {
  (cd "$ROOT/crewai" && uv run finalize_ticket "$1")
}

block() {
  printf 'Ralph BLOCKED: %s\n' "$1" >&2
  exit 2
}

printf 'Ralph selecting a CrewAI ticket\n'

next="$(queue next)"
next_status="$(printf '%s' "$next" | json_field status)"

case "$next_status" in
  empty)
    printf 'Ralph COMPLETE\n'
    exit 0
    ;;
  blocked)
    block "$(printf '%s' "$next" | json_field reason)"
    ;;
  ticket)
    ;;
  *)
    printf 'Ralph error: invalid queue result: %s\n' "$next" >&2
    exit 1
    ;;
esac

ticket_id="$(printf '%s' "$next" | json_field ticket_id)"
branch_name="$(printf '%s' "$next" | json_field branch_name)"
current_branch="$(git branch --show-current)"

if [[ "$current_branch" != "$branch_name" ]]; then
  [[ -z "$(git status --porcelain)" ]] \
    || block 'dirty working tree'
  if git show-ref --verify --quiet "refs/heads/$branch_name"; then
    git switch "$branch_name"
  else
    git switch -c "$branch_name"
  fi
fi

started="$(queue start "$ticket_id")"
[[ "$(printf '%s' "$started" | json_field status)" == started ]] \
  || block "$(printf '%s' "$started" | json_field reason)"

printf 'Ralph supervising %s\n' "$ticket_id"

while true; do
  finalization="$(finalize "$ticket_id")"
  finalization_status="$(printf '%s' "$finalization" | json_field status)"

  case "$finalization_status" in
    done)
      printf 'Ralph finalized %s\n' "$ticket_id"
      exit 0
      ;;
    blocked)
      $RESUME || block "$(printf '%s' "$finalization" | json_field reason)"
      ;;
    retry)
      sleep "$RETRY_DELAY_SECONDS"
      continue
      ;;
    not_ready|repair)
      ;;
    *)
      printf 'Ralph error: invalid finalizer result: %s\n' "$finalization" >&2
      exit 1
      ;;
  esac

  worker_args=("$ticket_id" --start)
  if $RESUME; then
    worker_args+=(--resume)
  fi
  worker="$("$ROOT/scripts/run-crew-ticket.sh" "${worker_args[@]}")"
  worker_status="$(printf '%s' "$worker" | json_field status)"
  worker_started="$(printf '%s' "$worker" | json_field started)"

  if [[ "$worker_started" == "True" ]]; then
    RESUME=false
  fi

  case "$worker_status" in
    approved|archived|running)
      ;;
    blocked)
      $RESUME || block "$(printf '%s' "$worker" | json_field summary)"
      ;;
    retry|retryable_failure)
      sleep "$RETRY_DELAY_SECONDS"
      ;;
    *)
      printf 'Ralph error: invalid worker result: %s\n' "$worker" >&2
      exit 1
      ;;
  esac
done
