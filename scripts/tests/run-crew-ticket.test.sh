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
printf '%s\n' start >>"$MOCK_ROOT/starts"
printf '%s\n' "$*" >>"$MOCK_ROOT/crew-arguments"
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

[[ "$result" == *'"started":true'* ]] || {
  printf 'FAIL: completed replacement did not report started=true\n' >&2
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

[[ "$result" == *'"started":false'* ]] || {
  printf 'FAIL: polling did not report started=false\n' >&2
  exit 1
}

fixture="$TEST_ROOT/single-flight"
create_fixture "$fixture"

PATH="$fixture/bin:$PATH" \
  MOCK_ROOT="$fixture" \
  MOCK_DELAY_SECONDS=2 \
  CREW_TICKET_WAIT_SECONDS=3 \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6 --start >"$fixture/first-result" &

sleep 1

result="$(
  PATH="$fixture/bin:$PATH" \
  MOCK_ROOT="$fixture" \
  CREW_TICKET_WAIT_SECONDS=0 \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6 --start
)"

[[ "$result" == *'"status":"running"'* ]] || {
  printf 'FAIL: concurrent CrewAI run was not reported as running\n' >&2
  exit 1
}

sleep 3

[[ "$(wc -l <"$fixture/starts")" == 1 ]] || {
  printf 'FAIL: concurrent CrewAI run started more than one worker\n' >&2
  exit 1
}

fixture="$TEST_ROOT/blocked"
create_fixture "$fixture"
mkdir -p "$fixture/openspec/changes/dev-6"
printf '%s\n' '{"status":"blocked"}' >"$fixture/openspec/changes/dev-6/result.json"

result="$(
  PATH="$fixture/bin:$PATH" \
  MOCK_ROOT="$fixture" \
  CREW_TICKET_WAIT_SECONDS=0 \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6 --start
)"

[[ "$result" == *'"status":"blocked"'* ]] || {
  printf 'FAIL: blocked CrewAI result did not stop a direct runner\n' >&2
  exit 1
}

[[ "$result" == *'"started":false'* ]] || {
  printf 'FAIL: blocked CrewAI result did not report started=false\n' >&2
  exit 1
}

sleep 1

[[ ! -e "$fixture/starts" ]] || {
  printf 'FAIL: direct runner bypassed blocked result without --resume\n' >&2
  exit 1
}

result="$(
  PATH="$fixture/bin:$PATH" \
  MOCK_ROOT="$fixture" \
  CREW_TICKET_WAIT_SECONDS=2 \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6 --start --resume
)"

[[ "$result" == *'"status":"approved"'* ]] || {
  printf 'FAIL: --resume did not replace the blocked CrewAI result\n' >&2
  exit 1
}

[[ "$(wc -l <"$fixture/starts")" == 1 ]] || {
  printf 'FAIL: --resume did not start exactly one worker\n' >&2
  exit 1
}

[[ "$(tail -n 1 "$fixture/crew-arguments")" == *'run_crew DEV-6 --resume' ]] || {
  printf 'FAIL: --resume was not passed to CrewAI without --replan\n' >&2
  exit 1
}

result="$(
  PATH="$fixture/bin:$PATH" \
  MOCK_ROOT="$fixture" \
  CREW_TICKET_WAIT_SECONDS=2 \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6 --start --replan
)"

[[ "$result" == *'"status":"approved"'* ]] || {
  printf 'FAIL: --replan did not start CrewAI\n' >&2
  exit 1
}

[[ "$(tail -n 1 "$fixture/crew-arguments")" == *'run_crew DEV-6 --replan' ]] || {
  printf 'FAIL: --replan was not passed to CrewAI\n' >&2
  exit 1
}

set +e
PATH="$fixture/bin:$PATH" MOCK_ROOT="$fixture" \
  "$fixture/scripts/run-crew-ticket.sh" DEV-6 --start --resume --replan >/dev/null 2>&1
conflicting_modes_exit=$?
set -e

[[ "$conflicting_modes_exit" != 0 ]] || {
  printf 'FAIL: runner accepted --resume with --replan\n' >&2
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

compgen -G "$fixture/.agent/crew/dev-6/results/*.json" >/dev/null || {
  printf 'FAIL: stale result was not preserved for diagnostics\n' >&2
  exit 1
}

printf 'PASS: supervised CrewAI runner\n'
