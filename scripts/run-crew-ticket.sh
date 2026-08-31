#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TICKET_ID="${1:?Ticket requerido}"
START="${2:-}"
WAIT_SECONDS="${CREW_TICKET_WAIT_SECONDS:-600}"
TIMEOUT_SECONDS="${CREW_TICKET_TIMEOUT_SECONDS:-1800}"
STATE_DIR="$ROOT/.agent/crew/${TICKET_ID,,}"
PID_FILE="$STATE_DIR/pid"
LOG_FILE="$STATE_DIR/run.log"
RESULT_FILE="$ROOT/openspec/changes/${TICKET_ID,,}/result.json"

mkdir -p "$STATE_DIR"

running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(<"$PID_FILE")" 2>/dev/null
}

result() {
  [[ -f "$RESULT_FILE" ]] && cat "$RESULT_FILE"
}

if ! running && [[ "$START" == "--start" ]]; then
  rm -f "$PID_FILE"
  rm -f "$RESULT_FILE"
  : >"$LOG_FILE"
  setsid timeout "$TIMEOUT_SECONDS" \
    uv run --project "$ROOT/crewai" run_crew "$TICKET_ID" \
    >"$LOG_FILE" 2>&1 &
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
