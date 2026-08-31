#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

fixture="$TEST_ROOT/until-finalized"
mkdir -p "$fixture/.agent" "$fixture/.opencode/agents" "$fixture/bin"
cp "$ROOT/ralph.sh" "$fixture/ralph.sh"
cp "$ROOT/.agent/PROMPT.md" "$fixture/.agent/PROMPT.md"
cp "$ROOT/.opencode/agents/ralph-linear.md" "$fixture/.opencode/agents/ralph-linear.md"

cat >"$fixture/bin/opencode" <<'OPENCODE'
#!/usr/bin/env bash
set -euo pipefail

calls_file="$MOCK_ROOT/calls"
calls=0
[[ -f "$calls_file" ]] && calls="$(<"$calls_file")"
calls=$((calls + 1))
printf '%s\n' "$calls" >"$calls_file"

if [[ "$calls" == 1 ]]; then
  printf '%s\n' '<promise>TICKET:DEV-31</promise>'
  exit 0
fi

prompt="${!#}"
[[ "$prompt" == *'Continue only ticket DEV-31.'* ]] || exit 9
[[ "$prompt" == *'Resume at step 3.'* ]] || exit 10
printf '%s\n' '<promise>FINALIZED:DEV-31</promise>'
OPENCODE
chmod +x "$fixture/bin/opencode"

PATH="$fixture/bin:$PATH" MOCK_ROOT="$fixture" \
  "$fixture/ralph.sh" --until-finalized

[[ "$(<"$fixture/calls")" == 2 ]] || {
  printf 'FAIL: Ralph did not stop after finalizing the first ticket\n' >&2
  exit 1
}

printf 'PASS: Ralph until finalized\n'
