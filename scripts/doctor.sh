#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MISE_BIN="$(command -v mise || true)"
if [[ -z "$MISE_BIN" && -n "${HOME:-}" && -x "$HOME/.local/bin/mise" ]]; then
  MISE_BIN="$HOME/.local/bin/mise"
fi
FAILED=0

report_error() {
  printf 'ERROR: %s\n' "$1" >&2
  FAILED=1
}

check_version() {
  local tool="$1"
  local expected="$2"
  local actual output

  if ! output="$("$MISE_BIN" exec -- "$tool" --version 2>/dev/null)"; then
    report_error "$tool version check failed"
    return
  fi

  case "$tool" in
    node) actual="${output#v}" ;;
    python) actual="${output#Python }" ;;
    uv)
      actual="${output#uv }"
      actual="${actual%%[[:space:]]*}"
      ;;
    *) actual="$output" ;;
  esac

  if [[ "$actual" != "$expected" ]]; then
    report_error "$tool version: expected $expected, got $actual"
  else
    printf 'OK: %s version %s\n' "$tool" "$expected"
  fi
}

check_command() {
  local failure_message="$1"
  shift

  if "$MISE_BIN" exec -- "$@" >/dev/null 2>&1; then
    printf 'OK: %s\n' "$failure_message"
  else
    report_error "$failure_message failed"
  fi
}

check_environment() {
  local env_file="$ROOT_DIR/crewai/.env"
  local key missing parser

  if [[ ! -f "$env_file" ]]; then
    report_error "missing environment file: crewai/.env"
    return
  fi

  parser=$'import sys\nfrom dotenv import dotenv_values\n\nrequired = (\n    "LINEAR_API_KEY",\n    "OPENCODE_API_KEY",\n    "ZEN_BASE_URL",\n    "ZEN_ANALYST_MODEL",\n    "ZEN_ARCHITECT_MODEL",\n    "ZEN_CODER_MODEL",\n    "ZEN_REVIEWER_MODEL",\n)\nvalues = dotenv_values(sys.argv[1])\nfor key in required:\n    if not values.get(key):\n        print(key)'

  if ! missing="$("$MISE_BIN" exec -- uv run --project crewai --no-sync python -c "$parser" "$env_file" 2>/dev/null)"; then
    report_error "environment file validation failed"
    return
  fi

  while IFS= read -r key; do
    [[ -n "$key" ]] && report_error "empty environment variable: $key"
  done <<<"$missing"
}

if [[ -z "$MISE_BIN" || ! -x "$MISE_BIN" ]]; then
  report_error "mise is not available"
  exit 1
fi

cd "$ROOT_DIR"

check_version node "20.20.2"
check_version pnpm "11.3.0"
check_version uv "0.11.16"
check_version python "3.12.13"
check_environment
check_command "pnpm frozen lockfile check" pnpm install --frozen-lockfile --lockfile-only
check_command "uv lock check" uv lock --project crewai --check
OPENSPEC_TELEMETRY=0 check_command "OpenSpec strict validation" pnpm exec openspec validate --all --strict
check_command "crew import" uv run --project crewai --no-sync python -c "import crew; print('crew import ok')"

if [[ "$FAILED" -ne 0 ]]; then
  exit 1
fi

printf 'OK: environment checks passed\n'
