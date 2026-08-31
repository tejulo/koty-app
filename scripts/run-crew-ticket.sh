#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TICKET_ID="${1:?Ticket requerido}"
START=false
RESUME=false
WAIT_SECONDS="${CREW_TICKET_WAIT_SECONDS:-600}"
TIMEOUT_SECONDS="${CREW_TICKET_TIMEOUT_SECONDS:-1800}"
STATE_DIR="$ROOT/.agent/crew/${TICKET_ID,,}"
PID_FILE="$STATE_DIR/pid"
LOG_FILE="$STATE_DIR/run.log"
CREW_LOG_FILE="$STATE_DIR/crew.log"
RESULT_FILE="$ROOT/openspec/changes/${TICKET_ID,,}/result.json"

shift
for option in "$@"; do
  case "$option" in
    --start)
      START=true
      ;;
    --resume)
      RESUME=true
      ;;
    *)
      printf 'Opción desconocida: %s\n' "$option" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$STATE_DIR"

running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(<"$PID_FILE")" 2>/dev/null
}

result() {
  [[ -f "$RESULT_FILE" ]] && cat "$RESULT_FILE"
}

if ! running && $START; then
  run_id="$(date '+%Y%m%d-%H%M%S')-$$"
  logs_dir="$STATE_DIR/logs"
  run_log="$logs_dir/$run_id.log"
  crew_log="$logs_dir/$run_id.crew.log"
  run_args=("$TICKET_ID")

  if $RESUME; then
    run_args+=(--resume)
  fi

  mkdir -p "$logs_dir"
  ln -sfn "logs/$run_id.log" "$LOG_FILE"
  ln -sfn "logs/$run_id.crew.log" "$CREW_LOG_FILE"
  rm -f "$PID_FILE"
  rm -f "$RESULT_FILE"
  setsid env CREWAI_OUTPUT_LOG_FILE="$crew_log" \
    timeout "$TIMEOUT_SECONDS" \
    uv run --project "$ROOT/crewai" run_crew "${run_args[@]}" \
    >"$run_log" 2>&1 &
  printf '%s\n' "$!" >"$PID_FILE"
fi

if ! running; then
  rm -f "$PID_FILE"
  result || printf '{"status":"retry","reason":"CrewAI terminó sin result.json"}\n'
  exit 0
fi

for ((elapsed = 0; elapsed < WAIT_SECONDS; elapsed++)); do
  sleep 1
  if ! running; then
    rm -f "$PID_FILE"
    result || printf '{"status":"retry","reason":"CrewAI terminó sin result.json"}\n'
    exit 0
  fi
done

printf '{"status":"running","ticket_id":"%s","log":"%s"}\n' \
  "$TICKET_ID" "${LOG_FILE#$ROOT/}"
