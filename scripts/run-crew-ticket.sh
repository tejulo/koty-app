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
LOCK_FILE="$STATE_DIR/run.lock"
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
started=false

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf '{"status":"running","ticket_id":"%s","started":false,"log":"%s"}\n' \
    "$TICKET_ID" "${LOG_FILE#$ROOT/}"
  exit 0
fi

running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(<"$PID_FILE")" 2>/dev/null
}

result() {
  [[ -f "$RESULT_FILE" ]] || return 1
  python -c '
import json, sys
result = json.load(sys.stdin)
result["started"] = sys.argv[1] == "true"
print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
' "$started" <"$RESULT_FILE"
}

blocked() {
  [[ -f "$RESULT_FILE" ]] \
    && [[ "$(python -c 'import json, sys; print(json.load(sys.stdin).get("status", ""))' <"$RESULT_FILE")" == "blocked" ]]
}

if $START && ! $RESUME && blocked; then
  result
  exit 0
fi

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
  if [[ -f "$RESULT_FILE" ]]; then
    mkdir -p "$STATE_DIR/results"
    mv "$RESULT_FILE" "$STATE_DIR/results/$run_id.json"
  fi
  ln -sfn "logs/$run_id.log" "$LOG_FILE"
  ln -sfn "logs/$run_id.crew.log" "$CREW_LOG_FILE"
  rm -f "$PID_FILE"
  setsid env CREWAI_OUTPUT_LOG_FILE="$crew_log" \
    timeout "$TIMEOUT_SECONDS" \
    uv run --project "$ROOT/crewai" run_crew "${run_args[@]}" \
    >"$run_log" 2>&1 &
  printf '%s\n' "$!" >"$PID_FILE"
  started=true
fi

flock -u 9

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

printf '{"status":"running","ticket_id":"%s","started":%s,"log":"%s"}\n' \
  "$TICKET_ID" "$started" "${LOG_FILE#$ROOT/}"
