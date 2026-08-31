#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

fixture="$TEST_ROOT/until-finalized"
mkdir -p "$fixture/.agent" "$fixture/.opencode/agents" "$fixture/bin" "$fixture/crewai" "$fixture/scripts"
cp "$ROOT/ralph.sh" "$fixture/ralph.sh"
cp "$ROOT/.agent/PROMPT.md" "$fixture/.agent/PROMPT.md"
cp "$ROOT/.opencode/agents/ralph-linear.md" "$fixture/.opencode/agents/ralph-linear.md"

if [[ -f "$ROOT/scripts/coordinate-crew-ticket.sh" ]]; then
  cp "$ROOT/scripts/coordinate-crew-ticket.sh" "$fixture/scripts/coordinate-crew-ticket.sh"
else
  printf '%s\n' '#!/usr/bin/env bash' 'exit 98' >"$fixture/scripts/coordinate-crew-ticket.sh"
fi

cat >"$fixture/bin/git" <<'GIT'
#!/usr/bin/env bash

if [[ "$*" == 'branch --show-current' ]]; then
  printf '%s\n' 'feat/dev-31'
fi
GIT
chmod +x "$fixture/bin/git"

cat >"$fixture/bin/uv" <<'UV'
#!/usr/bin/env bash

set -euo pipefail

case "$*" in
  'run crew_queue next')
    printf '%s\n' '{"status":"ticket","ticket_id":"DEV-31","change_id":"dev-31","branch_name":"feat/dev-31"}'
    ;;
  'run crew_queue start DEV-31')
    printf '%s\n' '{"status":"started","ticket_id":"DEV-31"}'
    ;;
  'run finalize_ticket DEV-31')
    if [[ "${MOCK_MODE:-}" == waiting ]]; then
      printf '%s\n' '{"status":"retry"}'
    elif [[ -f "$MOCK_ROOT/finalized" ]]; then
      printf '%s\n' '{"status":"done","finalized":true,"ticket_id":"DEV-31"}'
    else
      : >"$MOCK_ROOT/finalized"
      printf '%s\n' '{"status":"not_ready","ticket_id":"DEV-31"}'
    fi
    ;;
  *)
    exit 97
    ;;
esac
UV
chmod +x "$fixture/bin/uv"

cat >"$fixture/bin/opencode" <<'OPENCODE'
#!/usr/bin/env bash
: >"$MOCK_ROOT/opencode-called"
exit 99
OPENCODE
chmod +x "$fixture/bin/opencode"

cat >"$fixture/scripts/run-crew-ticket.sh" <<'RUNNER'
#!/usr/bin/env bash

[[ "${CREW_TICKET_WAIT_SECONDS:-}" == 30 ]] || exit 96

printf '%s\n' 1 >>"$MOCK_ROOT/runner-calls"
printf '%s\n' '{"status":"approved","ticket_id":"DEV-31"}'
RUNNER
chmod +x "$fixture/scripts/run-crew-ticket.sh"

set +e
output="$(PATH="$fixture/bin:$PATH" MOCK_ROOT="$fixture" "$fixture/ralph.sh" --until-finalized)"
exit_code=$?
set -e

[[ "$exit_code" == 0 ]] || {
  printf 'FAIL: Ralph coordinator exited %s\n' "$exit_code" >&2
  exit 1
}
[[ ! -f "$fixture/opencode-called" ]] || {
  printf 'FAIL: Ralph invoked OpenCode while supervising CrewAI\n' >&2
  exit 1
}

[[ "$(wc -l <"$fixture/runner-calls")" == 1 ]]
[[ "$output" == *'Ralph finalized DEV-31'* ]]

set +e
waiting_output="$(MOCK_MODE=waiting PATH="$fixture/bin:$PATH" MOCK_ROOT="$fixture" \
  timeout 1 "$fixture/ralph.sh" --until-finalized -n 10)"
waiting_exit_code=$?
set -e

[[ "$waiting_exit_code" == 124 ]]
[[ "$waiting_output" == *'Ralph selecting a CrewAI ticket'* ]] || {
  printf 'FAIL: Ralph did not report progress before waiting\n' >&2
  exit 1
}

printf 'PASS: Ralph until finalized\n'
