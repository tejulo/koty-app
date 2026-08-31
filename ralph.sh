#!/usr/bin/env bash

set -uo pipefail

ROOT="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" \
  && pwd
)"

cd "$ROOT"

MAX_ITERATIONS=10
ONCE=false
RUNTIME_AGENT="opencode"

DEFAULT_OPENCODE_AGENT="ralph-linear"
DEFAULT_MODEL="${RALPH_MODEL:-openai/gpt-5.5}"
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
      shift 2
      ;;

    --once)
      ONCE=true
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

if $ONCE; then
  MAX_ITERATIONS=1
fi

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


for ((iteration = 1; iteration <= MAX_ITERATIONS; iteration++)); do
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

  echo
  echo "Iteration $iteration finished."
done


echo
echo "Reached maximum iterations: $MAX_ITERATIONS"
exit 1
