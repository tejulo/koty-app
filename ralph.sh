#!/usr/bin/env bash

set -uo pipefail

ROOT="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" \
  && pwd
)"

cd "$ROOT"

MAX_ITERATIONS=10
ONCE=false
UNTIL_FINALIZED=false
RESUME=false
REPLAN=false
MAX_ITERATIONS_SET=false
RUNTIME_AGENT="opencode"

DEFAULT_OPENCODE_AGENT="ralph-linear"
DEFAULT_MODEL="${RALPH_MODEL:-openai/gpt-5.6-terra}"
DEFAULT_VARIANT="${RALPH_VARIANT:-high}"

PROMPT_FILE=".agent/PROMPT.md"
HISTORY_DIR=".agent/history"

OPENCODE_ARGS=()


usage() {
  cat <<'EOF'
Usage:
  ./ralph.sh [options] [max_iterations] [-- opencode_options]

Options:
  -n, --max-iterations N
      Maximum number of iterations.

  --once
      Run exactly one iteration.

  --until-finalized
      Repeat the first selected ticket until it is finalized.

  --resume
       Start a new CrewAI execution for the selected ticket.

   --replan
       Invalidate persisted planning contracts for the selected ticket.

  -a, --agent opencode
      Runtime agent. Only opencode is supported.

  --login
      Open OpenCode TUI to configure authentication.

  --print-name
      Print the local runtime name.

  --ports
      No-op in local mode. No sandbox ports are required.

  -h, --help
      Show this help.

Examples:
  ./ralph.sh
  ./ralph.sh -n 50
  ./ralph.sh --once
  ./ralph.sh --until-finalized

  ./ralph.sh -n 50 -- \
    --agent ralph-linear \
    --model openai/gpt-5.6-sol \
    --variant high
EOF
}


die() {
  echo "[ERROR] $*" >&2
  exit 1
}


while (($#)); do
  case "$1" in
    -n|--max-iterations)
      [[ $# -ge 2 ]] || die "$1 requiere un valor"
      MAX_ITERATIONS="$2"
      MAX_ITERATIONS_SET=true
      shift 2
      ;;

    --once)
      ONCE=true
      shift
      ;;

    --until-finalized)
      UNTIL_FINALIZED=true
      shift
      ;;

    --resume)
      RESUME=true
      shift
      ;;

    --replan)
      REPLAN=true
      shift
      ;;

    -a|--agent)
      [[ $# -ge 2 ]] || die "$1 requiere un valor"
      RUNTIME_AGENT="$2"
      shift 2
      ;;

    --login)
      command -v opencode >/dev/null 2>&1 \
        || die "opencode no está instalado"

      exec opencode
      ;;

    --print-name)
      echo "local-opencode-$(basename "$ROOT")"
      exit 0
      ;;

    --ports)
      echo "Local mode: no sandbox port publishing is required."
      echo "Use LOCAL_APP_URL from crewai/.env."
      exit 0
      ;;

    -h|--help)
      usage
      exit 0
      ;;

    --)
      shift
      OPENCODE_ARGS=("$@")
      break
      ;;

    [0-9]*)
      MAX_ITERATIONS="$1"
      MAX_ITERATIONS_SET=true
      shift
      ;;

    *)
      die "Opción desconocida: $1"
      ;;
  esac
done


[[ "$RUNTIME_AGENT" == "opencode" ]] \
  || die "Solo se soporta --agent opencode"

[[ "$MAX_ITERATIONS" =~ ^[1-9][0-9]*$ ]] \
  || die "MAX_ITERATIONS debe ser mayor que 0"

$RESUME && $REPLAN \
  && die "--resume y --replan no se pueden combinar"

if $ONCE; then
  MAX_ITERATIONS=1
fi

if $UNTIL_FINALIZED && ! $MAX_ITERATIONS_SET; then
  MAX_ITERATIONS=0
fi

if $UNTIL_FINALIZED; then
  if $RESUME; then
    exec "$ROOT/scripts/coordinate-crew-ticket.sh" --resume
  fi
  if $REPLAN; then
    exec "$ROOT/scripts/coordinate-crew-ticket.sh" --replan
  fi
  exec "$ROOT/scripts/coordinate-crew-ticket.sh"
fi

export CREW_TICKET_WAIT_SECONDS="${CREW_TICKET_WAIT_SECONDS:-30}"

command -v opencode >/dev/null 2>&1 \
  || die "opencode no está instalado"

[[ -f "$PROMPT_FILE" ]] \
  || die "No existe $PROMPT_FILE"

[[ -f ".opencode/agents/ralph-linear.md" ]] \
  || die "No existe .opencode/agents/ralph-linear.md"

mkdir -p "$HISTORY_DIR"


if ((${#OPENCODE_ARGS[@]} == 0)); then
  OPENCODE_ARGS=(
    --agent "$DEFAULT_OPENCODE_AGENT"
    --model "$DEFAULT_MODEL"
    --variant "$DEFAULT_VARIANT"
  )
fi


locked_ticket=""

for ((iteration = 1; MAX_ITERATIONS == 0 || iteration <= MAX_ITERATIONS; iteration++)); do
  printf '\n'
  echo "============================================================"
  echo "Ralph iteration $iteration/$MAX_ITERATIONS"
  echo "============================================================"
  printf '\n'

  timestamp="$(date '+%Y%m%d-%H%M%S')"

  log_file="$HISTORY_DIR/iteration-$(
    printf '%03d' "$iteration"
  )-$timestamp.log"

  prompt="$(<"$PROMPT_FILE")"

  if [[ -n "$locked_ticket" ]]; then
    prompt+=$'\n\n## Ticket bloqueado\n\n'
    prompt+="Continue only ticket $locked_ticket."
    prompt+=$'\nResume at step 3. No consultes crew_queue ni proceses otro ticket.\n'
  fi

  opencode run \
    "${OPENCODE_ARGS[@]}" \
    "$prompt" \
    2>&1 | tee "$log_file"

  exit_code=${PIPESTATUS[0]}

  if ((exit_code != 0)); then
    echo
    echo "[ERROR] OpenCode terminó con código $exit_code"
    echo "[ERROR] Log: $log_file"
    exit "$exit_code"
  fi

  if grep -Fq \
    '<promise>COMPLETE</promise>' \
    "$log_file"
  then
    echo
    echo "Ralph COMPLETE"
    exit 0
  fi

  if grep -Fq \
    '<promise>BLOCKED:' \
    "$log_file"
  then
    echo
    echo "Ralph BLOCKED"
    exit 2
  fi

  if grep -Fq \
    '<promise>DECIDE:' \
    "$log_file"
  then
    echo
    echo "Ralph DECIDE"
    exit 3
  fi

  if $UNTIL_FINALIZED && [[ -z "$locked_ticket" ]]; then
    ticket_marker="$(
      grep -m1 -oE \
        '<promise>TICKET:[A-Za-z][A-Za-z0-9]*-[0-9]+</promise>' \
        "$log_file" || true
    )"

    [[ -n "$ticket_marker" ]] \
      || die "No se pudo identificar el primer ticket"

    locked_ticket="${ticket_marker#<promise>TICKET:}"
    locked_ticket="${locked_ticket%</promise>}"
  fi

  if $UNTIL_FINALIZED && grep -Fq \
    "<promise>FINALIZED:$locked_ticket</promise>" \
    "$log_file"
  then
    echo
    echo "Ralph finalized $locked_ticket"
    exit 0
  fi

  echo
  echo "Iteration $iteration finished."
done


echo
if $UNTIL_FINALIZED; then
  echo "Reached maximum iterations before finalizing $locked_ticket"
else
  echo "Reached maximum iterations: $MAX_ITERATIONS"
fi
exit 1
