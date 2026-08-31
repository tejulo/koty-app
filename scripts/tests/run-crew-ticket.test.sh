#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNER="$ROOT/scripts/run-crew-ticket.sh"

[[ -x "$RUNNER" ]] || {
  printf 'FAIL: scripts/run-crew-ticket.sh is missing or not executable\n' >&2
  exit 1
}

TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

create_fixture() {
  local fixture="$1"

  mkdir -p "$fixture/scripts" "$fixture/crewai" "$fixture/bin"
  cp "$RUNNER" "$fixture/scripts/run-crew-ticket.sh"
  cat >"$fixture/bin/uv" <<'UV'
#!/usr/bin/env bash
set -euo pipefail

[[ "$1" == "run" && "$2" == "--project" && "$4" == "run_crew" ]] || exit 2
sleep "${MOCK_DELAY_SECONDS:-0}"
printf '%s\n' 'CrewAI completed'
mkdir -p "$MOCK_ROOT/openspec/changes/dev-6"
printf '%s\n' '{"ticket_id":"DEV-6","change_id":"dev-6","status":"approved"}' > "$MOCK_ROOT/openspec/changes/dev-6/result.json"
UV
  chmod +x "$fixture/bin/uv"
}

fixture="$TEST_ROOT/complete"
create_fixture "$fixture"

result="$(
  PATH="$fixture/bin:$PATH" \
  MOCK_ROOT="$fixture" \
  CREW_TICKET_WAIT_SECONDS=2 \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6 --start
)"

[[ "$result" == *'"status":"approved"'* ]] || {
  printf 'FAIL: completed CrewAI result was not returned\n' >&2
  exit 1
}

[[ -s "$fixture/.agent/crew/dev-6/run.log" ]] || {
  printf 'FAIL: CrewAI output was not persisted\n' >&2
  exit 1
}

fixture="$TEST_ROOT/running"
create_fixture "$fixture"

result="$(
  PATH="$fixture/bin:$PATH" \
  MOCK_ROOT="$fixture" \
  MOCK_DELAY_SECONDS=2 \
  CREW_TICKET_WAIT_SECONDS=0 \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6 --start
)"

[[ "$result" == *'"status":"running"'* ]] || {
  printf 'FAIL: active CrewAI run was not reported\n' >&2
  exit 1
}

result="$(
  PATH="$fixture/bin:$PATH" \
  MOCK_ROOT="$fixture" \
  CREW_TICKET_WAIT_SECONDS=3 \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6
)"

[[ "$result" == *'"status":"approved"'* ]] || {
  printf 'FAIL: polling did not return the completed CrewAI result\n' >&2
  exit 1
}

fixture="$TEST_ROOT/timeout"
create_fixture "$fixture"
mkdir -p "$fixture/openspec/changes/dev-6"
printf '%s\n' '{"status":"approved"}' > "$fixture/openspec/changes/dev-6/result.json"

result="$(
  PATH="$fixture/bin:$PATH" \
  MOCK_ROOT="$fixture" \
  MOCK_DELAY_SECONDS=2 \
  CREW_TICKET_TIMEOUT_SECONDS=1 \
  CREW_TICKET_WAIT_SECONDS=2 \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6 --start
)"

[[ "$result" == *'"status":"retry"'* ]] || {
  printf 'FAIL: timed out CrewAI run returned a stale result\n' >&2
  exit 1
}

printf 'PASS: supervised CrewAI runner\n'
