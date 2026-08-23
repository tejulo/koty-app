#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP_SOURCE="$REPO_ROOT/scripts/bootstrap.sh"
DOCTOR_SOURCE="$REPO_ROOT/scripts/doctor.sh"

if [[ ! -f "$BOOTSTRAP_SOURCE" ]]; then
  printf 'FAIL: scripts/bootstrap.sh is missing\n' >&2
  exit 1
fi

TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

sha256_file() {
  local file="$1"
  local output

  if command -v sha256sum >/dev/null 2>&1; then
    output="$(sha256sum "$file")"
  elif command -v shasum >/dev/null 2>&1; then
    output="$(shasum -a 256 "$file")"
  else
    printf 'FAIL: no SHA-256 command is available\n' >&2
    return 1
  fi

  printf '%s\n' "${output%%[[:space:]]*}"
}

UV_BIN="$(command -v uv || true)"
[[ -n "$UV_BIN" ]] || fail "uv is required to prepare the shell test environment"
"$UV_BIN" sync --project "$REPO_ROOT/crewai" --frozen >/dev/null
PROJECT_PYTHON_BIN="$REPO_ROOT/crewai/.venv/bin/python"
[[ -x "$PROJECT_PYTHON_BIN" ]] || fail "uv did not create the project Python environment"

assert_contains() {
  local file="$1"
  local expected="$2"

  grep -Fqx -- "$expected" "$file" || fail "missing log entry: $expected"
}

assert_mise_commands() {
  local log="$1"
  local root="$2"
  local expected="$log.expected"

  printf '%s\n' \
    "$root|install" \
    "$root|exec -- pnpm install --frozen-lockfile" \
    "$root|exec -- uv sync --project crewai --frozen" >"$expected"
  cmp -s "$expected" "$log" || fail "unexpected mise commands in $log"
}

assert_not_called() {
  local log="$1"
  local command="$2"

  [[ ! -s "$log" ]] || fail "$command was unexpectedly called: $(<"$log")"
}

assert_output_contains() {
  local file="$1"
  local expected="$2"

  grep -Fq -- "$expected" "$file" || fail "missing output: $expected"
}

assert_output_excludes() {
  local file="$1"
  local unexpected="$2"

  if grep -Fq -- "$unexpected" "$file"; then
    fail "output contains protected content"
  fi
}

assert_lines_in_order() {
  local file="$1"
  shift
  local expected line previous=0

  for expected in "$@"; do
    line="$(grep -nF -- "$expected" "$file" | cut -d: -f1 | head -n 1 || true)"
    [[ -n "$line" ]] || fail "missing ordered output: $expected"
    ((line > previous)) || fail "output is out of order: $expected"
    previous="$line"
  done
}

assert_file_unchanged() {
  local before="$1"
  local file="$2"
  local expected_hash="$3"

  cmp -s "$before" "$file" || fail "$file content changed"
  [[ "$(sha256_file "$file")" == "$expected_hash" ]] || fail "$file hash changed"
}

create_mise() {
  local path="$1"

  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'MISE'
#!/usr/bin/env bash
set -euo pipefail
printf '%s|%s\n' "$PWD" "$*" >>"$BOOTSTRAP_TEST_MISE_LOG"
MISE
  chmod +x "$path"
}

create_forbidden_curl() {
  local path="$1"

  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'CURL'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$BOOTSTRAP_TEST_CURL_LOG"
exit 99
CURL
  chmod +x "$path"
}

create_forbidden_python() {
  local path="$1"

  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'PYTHON'
#!/usr/bin/env bash
exit 96
PYTHON
  chmod +x "$path"
}

create_fixture() {
  local fixture="$1"

  mkdir -p "$fixture/scripts" "$fixture/crewai"
  cp "$BOOTSTRAP_SOURCE" "$fixture/scripts/bootstrap.sh"
  cp "$REPO_ROOT/pnpm-lock.yaml" "$fixture/pnpm-lock.yaml"
  cp "$REPO_ROOT/crewai/uv.lock" "$fixture/crewai/uv.lock"
  printf 'LINEAR_API_KEY=\n' >"$fixture/crewai/.env.example"
  cat >"$fixture/scripts/doctor.sh" <<'DOCTOR'
#!/usr/bin/env bash
set -euo pipefail
[[ -f crewai/.env ]]
[[ "$(<"$BOOTSTRAP_TEST_MISE_LOG")" == *"|exec -- uv sync --project crewai --frozen" ]]
printf '%s\n' "$PWD" >>"$BOOTSTRAP_TEST_DOCTOR_LOG"
exit "${BOOTSTRAP_TEST_DOCTOR_EXIT:-0}"
DOCTOR
  chmod +x "$fixture/scripts/doctor.sh"
}

create_doctor_mise() {
  local path="$1"

  mkdir -p "$(dirname "$path")"
  cat >"$path" <<'MISE'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$#" -eq 11 && "$1" == "exec" && "$2" == "--" && "$3" == "uv" && "$4" == "run" && "$5" == "--project" && "$6" == "crewai" && "$7" == "--no-sync" && "$8" == "python" && "$9" == "-c" ]]; then
  printf '%s|dotenv-check|%s\n' "$PWD" "${11}" >>"$DOCTOR_TEST_MISE_LOG"
  "$DOCTOR_TEST_PYTHON_BIN" -c "${10}" "${11}"
  exit
fi

printf '%s|%s\n' "$PWD" "$*" >>"$DOCTOR_TEST_MISE_LOG"

case "$*" in
  "exec -- node --version")
    [[ "$#" -eq 4 && "$1" == "exec" && "$2" == "--" && "$3" == "node" && "$4" == "--version" ]] || exit 97
    [[ "${DOCTOR_TEST_FAIL_COMMAND:-}" != "node-version" ]] || exit 1
    printf 'v%s\n' "${DOCTOR_TEST_NODE_VERSION:-20.20.2}"
    ;;
  "exec -- pnpm --version")
    [[ "$#" -eq 4 && "$1" == "exec" && "$2" == "--" && "$3" == "pnpm" && "$4" == "--version" ]] || exit 97
    [[ "${DOCTOR_TEST_FAIL_COMMAND:-}" != "pnpm-version" ]] || exit 1
    printf '%s\n' "${DOCTOR_TEST_PNPM_VERSION:-11.3.0}"
    ;;
  "exec -- uv --version")
    [[ "$#" -eq 4 && "$1" == "exec" && "$2" == "--" && "$3" == "uv" && "$4" == "--version" ]] || exit 97
    [[ "${DOCTOR_TEST_FAIL_COMMAND:-}" != "uv-version" ]] || exit 1
    printf 'uv %s\n' "${DOCTOR_TEST_UV_VERSION:-0.11.16 (x86_64-unknown-linux-musl)}"
    ;;
  "exec -- python --version")
    [[ "$#" -eq 4 && "$1" == "exec" && "$2" == "--" && "$3" == "python" && "$4" == "--version" ]] || exit 97
    [[ "${DOCTOR_TEST_FAIL_COMMAND:-}" != "python-version" ]] || exit 1
    printf 'Python %s\n' "${DOCTOR_TEST_PYTHON_VERSION:-3.12.13}"
    ;;
  "exec -- pnpm install --frozen-lockfile --lockfile-only")
    [[ "$#" -eq 6 && "$1" == "exec" && "$2" == "--" && "$3" == "pnpm" && "$4" == "install" && "$5" == "--frozen-lockfile" && "$6" == "--lockfile-only" ]] || exit 97
    [[ "${DOCTOR_TEST_FAIL_COMMAND:-}" != "pnpm-frozen" ]]
    ;;
  "exec -- uv lock --project crewai --check")
    [[ "$#" -eq 7 && "$1" == "exec" && "$2" == "--" && "$3" == "uv" && "$4" == "lock" && "$5" == "--project" && "$6" == "crewai" && "$7" == "--check" ]] || exit 97
    [[ "${DOCTOR_TEST_FAIL_COMMAND:-}" != "uv-lock" ]]
    ;;
  "exec -- pnpm exec openspec validate --all --strict")
    [[ "$#" -eq 8 && "$1" == "exec" && "$2" == "--" && "$3" == "pnpm" && "$4" == "exec" && "$5" == "openspec" && "$6" == "validate" && "$7" == "--all" && "$8" == "--strict" ]] || exit 97
    printf '%s\n' "${OPENSPEC_TELEMETRY-unset}" >>"$DOCTOR_TEST_OPENSPEC_ENV_LOG"
    [[ "${DOCTOR_TEST_FAIL_COMMAND:-}" != "openspec" ]]
    ;;
  "exec -- uv run --project crewai --no-sync python -c import crew; print('crew import ok')")
    [[ "$#" -eq 10 && "$1" == "exec" && "$2" == "--" && "$3" == "uv" && "$4" == "run" && "$5" == "--project" && "$6" == "crewai" && "$7" == "--no-sync" && "$8" == "python" && "$9" == "-c" && "${10}" == "import crew; print('crew import ok')" ]] || exit 97
    [[ "${DOCTOR_TEST_FAIL_COMMAND:-}" != "crew-import" ]]
    ;;
  *) exit 98 ;;
esac
MISE
  chmod +x "$path"
}

create_doctor_fixture() {
  local fixture="$1"

  mkdir -p "$fixture/scripts" "$fixture/crewai"
  cp "$DOCTOR_SOURCE" "$fixture/scripts/doctor.sh"
  cp "$REPO_ROOT/.mise.toml" "$fixture/.mise.toml"
  cp "$REPO_ROOT/pnpm-lock.yaml" "$fixture/pnpm-lock.yaml"
  cp "$REPO_ROOT/crewai/uv.lock" "$fixture/crewai/uv.lock"
}

write_doctor_env() {
  local path="$1"

  cat >"$path" <<'ENV'
LINEAR_API_KEY=linear-secret-value
OPENCODE_API_KEY=opencode-secret-value
ZEN_BASE_URL=https://example.invalid/private
ZEN_ANALYST_MODEL=analyst-secret-model
ZEN_ARCHITECT_MODEL=architect-secret-model
ZEN_CODER_MODEL=coder-secret-model
ZEN_REVIEWER_MODEL=reviewer-secret-model
ENV
}

run_doctor() {
  local fixture="$1"
  local mise_bin="$2"
  local log="$3"

  (
    cd "$TEST_ROOT"
    env \
      HOME="$TEST_ROOT/doctor-empty-home" \
      PATH="$(dirname "$mise_bin"):$TEST_ROOT/doctor-forbidden-bin:/usr/bin:/bin" \
      DOCTOR_TEST_MISE_LOG="$log" \
      DOCTOR_TEST_PYTHON_BIN="$PROJECT_PYTHON_BIN" \
      DOCTOR_TEST_OPENSPEC_ENV_LOG="$log.openspec-env" \
      OPENSPEC_TELEMETRY=valor-padre \
      DOCTOR_TEST_FAIL_COMMAND="${DOCTOR_TEST_FAIL_COMMAND:-}" \
      DOCTOR_TEST_NODE_VERSION="${DOCTOR_TEST_NODE_VERSION:-}" \
      DOCTOR_TEST_PNPM_VERSION="${DOCTOR_TEST_PNPM_VERSION:-}" \
      DOCTOR_TEST_UV_VERSION="${DOCTOR_TEST_UV_VERSION:-}" \
      DOCTOR_TEST_PYTHON_VERSION="${DOCTOR_TEST_PYTHON_VERSION:-}" \
      DOCTOR_TEST_OPENSPEC_FAIL="${DOCTOR_TEST_OPENSPEC_FAIL:-0}" \
      "$fixture/scripts/doctor.sh"
  )
}

run_doctor_with_home_mise() {
  local fixture="$1"
  local home="$2"
  local log="$3"

  (
    cd "$TEST_ROOT"
    env \
      HOME="$home" \
      PATH="$TEST_ROOT/doctor-forbidden-bin:/usr/bin:/bin" \
      DOCTOR_TEST_MISE_LOG="$log" \
      DOCTOR_TEST_PYTHON_BIN="$PROJECT_PYTHON_BIN" \
      DOCTOR_TEST_OPENSPEC_ENV_LOG="$log.openspec-env" \
      OPENSPEC_TELEMETRY=valor-padre \
      "$fixture/scripts/doctor.sh"
  )
}

run_bootstrap() {
  local fixture="$1"
  local home="$2"
  local fake_bin="$3"
  local os="$4"
  local mise_log="$5"
  local curl_log="$6"
  local shell="${7:-/bin/bash}"

  (
    cd "$TEST_ROOT"
    env \
      HOME="$home" \
      PATH="$TEST_ROOT/bootstrap-command-bin:$fake_bin:/usr/bin:/bin" \
      BOOTSTRAP_TEST_UNAME="$os" \
      BOOTSTRAP_TEST_MISE_LOG="$mise_log" \
      BOOTSTRAP_TEST_CURL_LOG="$curl_log" \
      BOOTSTRAP_TEST_DOCTOR_LOG="$mise_log.doctor" \
      BOOTSTRAP_TEST_DOCTOR_EXIT="${BOOTSTRAP_TEST_DOCTOR_EXIT:-0}" \
      SHELL="$shell" \
      "$fixture/scripts/bootstrap.sh"
  )
}

run_worker_lint_without_contract_dist() (
  local contracts_dist="$REPO_ROOT/packages/contracts/dist"
  local saved_dist="$TEST_ROOT/contracts-dist.saved"

  restore_contract_dist() {
    if [[ -e "$saved_dist" ]]; then
      mv "$saved_dist" "$contracts_dist"
    fi
  }

  trap restore_contract_dist EXIT

  if [[ -d "$contracts_dist" ]]; then
    mv "$contracts_dist" "$saved_dist"
  fi

  (
    cd "$REPO_ROOT/apps/worker"
    mise exec -- pnpm exec tsc --project tsconfig.eslint.json --noEmit --rootDir ../..
    mise exec -- pnpm lint
  )
)

portable_hash_bin="$TEST_ROOT/portable-hash-bin"
mkdir -p "$portable_hash_bin"
cat >"$portable_hash_bin/shasum" <<'SHASUM'
#!/bin/bash
[[ "$1" == "-a" && "$2" == "256" ]] || exit 97
printf 'portable-shasum  %s\n' "$3"
SHASUM
chmod +x "$portable_hash_bin/shasum"
[[ "$(PATH="$portable_hash_bin" sha256_file "$BOOTSTRAP_SOURCE")" == "portable-shasum" ]] || fail "sha256_file did not fall back to shasum"

assert_output_contains "$REPO_ROOT/package.json" '"test:shell": "node scripts/tests/run-bootstrap-tests.mjs"'
assert_output_contains "$REPO_ROOT/package.json" '"verify": "pnpm lint && pnpm test && pnpm test:shell && pnpm build && pnpm crew:check"'
assert_output_contains "$REPO_ROOT/package.json" '"crew:check": "uv run --project crewai pytest crewai/tests -v && OPENSPEC_TELEMETRY=0 pnpm exec openspec validate --all --strict"'
assert_output_contains "$REPO_ROOT/scripts/tests/run-bootstrap-tests.mjs" "process.platform === 'win32'"
assert_output_contains "$REPO_ROOT/scripts/tests/run-bootstrap-tests.mjs" 'powershell.exe'
assert_output_contains "$REPO_ROOT/.gitignore" '*.tsbuildinfo'
assert_output_excludes "$REPO_ROOT/apps/api/package.json" '--fix'
assert_output_excludes "$REPO_ROOT/apps/worker/package.json" '--fix'

mkdir -p "$TEST_ROOT/bootstrap-command-bin"
cat >"$TEST_ROOT/bootstrap-command-bin/uname" <<'UNAME'
#!/usr/bin/env bash
set -euo pipefail
[[ "$1" == "-s" ]] || exit 97
printf '%s\n' "$BOOTSTRAP_TEST_UNAME"
UNAME
chmod +x "$TEST_ROOT/bootstrap-command-bin/uname"

unsupported_fixture="$TEST_ROOT/unsupported"
create_fixture "$unsupported_fixture"
mkdir -p "$TEST_ROOT/unsupported-bin" "$TEST_ROOT/unsupported-home"
create_forbidden_curl "$TEST_ROOT/unsupported-bin/curl"
if run_bootstrap "$unsupported_fixture" "$TEST_ROOT/unsupported-home" "$TEST_ROOT/unsupported-bin" "Windows_NT" "$TEST_ROOT/unsupported-mise.log" "$TEST_ROOT/unsupported-curl.log" >"$TEST_ROOT/unsupported.out" 2>&1; then
  fail "unsupported platform was accepted"
fi
grep -Fq "Unsupported platform: Windows_NT" "$TEST_ROOT/unsupported.out" || fail "unsupported platform error was not reported"
assert_not_called "$TEST_ROOT/unsupported-curl.log" "curl for unsupported platform"

install_fixture="$TEST_ROOT/install"
install_home="$TEST_ROOT/install-home"
install_bin="$TEST_ROOT/install-bin"
installer_mise="$TEST_ROOT/installer-mise"
create_fixture "$install_fixture"
create_mise "$installer_mise"
mkdir -p "$install_home" "$install_bin"
cat >"$install_bin/curl" <<'CURL'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$BOOTSTRAP_TEST_CURL_LOG"
cat <<'INSTALLER'
#!/usr/bin/env sh
set -eu
mkdir -p "$HOME/.local/bin"
cp "$BOOTSTRAP_TEST_MISE_SOURCE" "$HOME/.local/bin/mise"
chmod +x "$HOME/.local/bin/mise"
INSTALLER
CURL
chmod +x "$install_bin/curl"
(
  export BOOTSTRAP_TEST_CURL_LOG="$TEST_ROOT/curl.log"
  export BOOTSTRAP_TEST_MISE_SOURCE="$installer_mise"
  run_bootstrap "$install_fixture" "$install_home" "$install_bin" "Linux" "$TEST_ROOT/install-mise.log" "$TEST_ROOT/curl.log" >"$TEST_ROOT/install.out" 2>&1
)
[[ -x "$install_home/.local/bin/mise" ]] || fail "mise was not installed"
assert_contains "$TEST_ROOT/curl.log" "-fsSL https://mise.run"

expected_root="$install_fixture"
assert_mise_commands "$TEST_ROOT/install-mise.log" "$expected_root"
cmp -s "$install_fixture/crewai/.env.example" "$install_fixture/crewai/.env" || fail ".env was not created from the example"
assert_contains "$TEST_ROOT/install-mise.log.doctor" "$install_fixture"
assert_output_contains "$TEST_ROOT/install.out" "Entorno preparado."
assert_lines_in_order "$TEST_ROOT/install.out" \
  "El bootstrap no puede modificar el shell padre." \
  "Para habilitar mise en Bash, ejecuta:" \
  "  grep -qxF 'export PATH=\"\$HOME/.local/bin:\$PATH\"' \"\$HOME/.bashrc\" || printf '%s\\n' 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> \"\$HOME/.bashrc\"" \
  "  grep -qxF 'eval \"\$(mise activate bash)\"' \"\$HOME/.bashrc\" || printf '%s\\n' 'eval \"\$(mise activate bash)\"' >> \"\$HOME/.bashrc\"" \
  "  source \"\$HOME/.bashrc\"" \
  "Luego ejecuta:" \
  "  pnpm verify" \
  "  cd crewai" \
  "  uv run run_crew DEV-5" \
  "Alternativa sin modificar tu shell:" \
  "  $install_home/.local/bin/mise exec -- pnpm verify" \
  "  $install_home/.local/bin/mise exec -- uv run --project crewai run_crew DEV-5"
assert_output_excludes "$TEST_ROOT/install.out" "Completa crewai/.env"

for shell_case in zsh fish; do
  shell_fixture="$TEST_ROOT/shell-$shell_case"
  shell_home="$TEST_ROOT/shell-$shell_case-home"
  if [[ "$shell_case" == "fish" ]]; then
    shell_bin="$TEST_ROOT/shell-$shell_case bin"
  else
    shell_bin="$TEST_ROOT/shell-$shell_case-bin"
  fi
  create_fixture "$shell_fixture"
  create_mise "$shell_bin/mise"
  create_forbidden_curl "$shell_bin/curl"
  mkdir -p "$shell_home"
  run_bootstrap "$shell_fixture" "$shell_home" "$shell_bin" "Linux" "$TEST_ROOT/shell-$shell_case-mise.log" "$TEST_ROOT/shell-$shell_case-curl.log" "/bin/$shell_case" >"$TEST_ROOT/shell-$shell_case.out" 2>&1
done

assert_lines_in_order "$TEST_ROOT/shell-zsh.out" \
  "Para habilitar mise en Zsh, ejecuta:" \
  "  grep -qxF 'export PATH=\"\$HOME/.local/bin:\$PATH\"' \"\$HOME/.zshrc\" || printf '%s\\n' 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> \"\$HOME/.zshrc\"" \
  "  grep -qxF 'eval \"\$(mise activate zsh)\"' \"\$HOME/.zshrc\" || printf '%s\\n' 'eval \"\$(mise activate zsh)\"' >> \"\$HOME/.zshrc\"" \
  "  source \"\$HOME/.zshrc\"" \
  "  pnpm verify" \
  "  uv run run_crew DEV-5"
assert_output_contains "$TEST_ROOT/shell-fish.out" "Shell no compatible detectado: /bin/fish"
assert_output_contains "$TEST_ROOT/shell-fish.out" "Usa mise exec sin depender de la configuracion del shell:"
escaped_shell_bin="${shell_bin// /\\ }"
assert_output_contains "$TEST_ROOT/shell-fish.out" "  $escaped_shell_bin/mise exec -- pnpm verify"
assert_output_contains "$TEST_ROOT/shell-fish.out" "  $escaped_shell_bin/mise exec -- uv run --project crewai run_crew DEV-5"
assert_output_excludes "$TEST_ROOT/shell-fish.out" "  pnpm verify"
assert_output_excludes "$TEST_ROOT/shell-fish.out" "  uv run run_crew DEV-5"

existing_fixture="$TEST_ROOT/existing"
existing_home="$TEST_ROOT/existing-home"
existing_bin="$TEST_ROOT/existing-bin"
create_fixture "$existing_fixture"
create_mise "$existing_bin/mise"
create_forbidden_curl "$existing_bin/curl"
mkdir -p "$existing_home"
printf 'KEEP=this value\nSECOND=byte-stable\n' >"$existing_fixture/crewai/.env"
for immutable in crewai/.env pnpm-lock.yaml crewai/uv.lock; do
  mkdir -p "$TEST_ROOT/bootstrap-before/$(dirname "$immutable")"
  cp "$existing_fixture/$immutable" "$TEST_ROOT/bootstrap-before/$immutable"
  sha256_file "$existing_fixture/$immutable" >"$TEST_ROOT/bootstrap-before/$immutable.sha256"
done
run_bootstrap "$existing_fixture" "$existing_home" "$existing_bin" "Darwin" "$TEST_ROOT/existing-first-mise.log" "$TEST_ROOT/existing-first-curl.log" >"$TEST_ROOT/existing-first.out" 2>&1
run_bootstrap "$existing_fixture" "$existing_home" "$existing_bin" "Darwin" "$TEST_ROOT/existing-second-mise.log" "$TEST_ROOT/existing-second-curl.log" >"$TEST_ROOT/existing-second.out" 2>&1
for immutable in crewai/.env pnpm-lock.yaml crewai/uv.lock; do
  assert_file_unchanged "$TEST_ROOT/bootstrap-before/$immutable" "$existing_fixture/$immutable" "$(<"$TEST_ROOT/bootstrap-before/$immutable.sha256")"
done
[[ ! -e "$existing_home/.local/bin/mise" ]] || fail "mise was installed despite being available"
assert_mise_commands "$TEST_ROOT/existing-first-mise.log" "$existing_fixture"
assert_mise_commands "$TEST_ROOT/existing-second-mise.log" "$existing_fixture"
assert_contains "$TEST_ROOT/existing-first-mise.log.doctor" "$existing_fixture"
assert_contains "$TEST_ROOT/existing-second-mise.log.doctor" "$existing_fixture"
assert_not_called "$TEST_ROOT/existing-first-curl.log" "curl with mise in PATH on first run"
assert_not_called "$TEST_ROOT/existing-second-curl.log" "curl with mise in PATH on second run"

failure_fixture="$TEST_ROOT/doctor-failure"
failure_home="$TEST_ROOT/doctor-failure-home"
failure_bin="$TEST_ROOT/doctor-failure-bin"
create_fixture "$failure_fixture"
create_mise "$failure_bin/mise"
create_forbidden_curl "$failure_bin/curl"
mkdir -p "$failure_home"
export BOOTSTRAP_TEST_DOCTOR_EXIT=37
set +e
run_bootstrap "$failure_fixture" "$failure_home" "$failure_bin" "Linux" "$TEST_ROOT/doctor-failure-mise.log" "$TEST_ROOT/doctor-failure-curl.log" >"$TEST_ROOT/doctor-failure.out" 2>&1
failure_status=$?
set -e
unset BOOTSTRAP_TEST_DOCTOR_EXIT
[[ "$failure_status" -eq 37 ]] || fail "bootstrap returned $failure_status instead of the doctor status"
assert_contains "$TEST_ROOT/doctor-failure-mise.log.doctor" "$failure_fixture"
assert_output_contains "$TEST_ROOT/doctor-failure.out" "Corrige los errores reportados por doctor"
assert_output_contains "$TEST_ROOT/doctor-failure.out" "  ./scripts/doctor.sh"
assert_output_excludes "$TEST_ROOT/doctor-failure.out" "Completa crewai/.env"
assert_output_excludes "$TEST_ROOT/doctor-failure.out" "Entorno preparado."
assert_output_excludes "$TEST_ROOT/doctor-failure.out" "uv run run_crew DEV-5"

local_fixture="$TEST_ROOT/local-bin"
local_home="$TEST_ROOT/local-bin-home"
local_bin="$TEST_ROOT/local-bin-path"
create_fixture "$local_fixture"
create_mise "$local_home/.local/bin/mise"
create_forbidden_curl "$local_bin/curl"
run_bootstrap "$local_fixture" "$local_home" "$local_bin" "Linux" "$TEST_ROOT/local-bin-mise.log" "$TEST_ROOT/local-bin-curl.log"
assert_mise_commands "$TEST_ROOT/local-bin-mise.log" "$local_fixture"
assert_not_called "$TEST_ROOT/local-bin-curl.log" "curl with mise in HOME local bin"

if grep -Fq 'BOOTSTRAP_POST_HOOK' "$BOOTSTRAP_SOURCE"; then
  fail "BOOTSTRAP_POST_HOOK remains in bootstrap.sh"
fi
for hook in BOOTSTRAP_OS BOOTSTRAP_UNAME BOOTSTRAP_MISE_INSTALL_URL BOOTSTRAP_INSTALL_URL; do
  assert_output_excludes "$BOOTSTRAP_SOURCE" "$hook"
done
assert_output_excludes "$DOCTOR_SOURCE" "DOCTOR_MISE_BIN"

[[ -f "$DOCTOR_SOURCE" ]] || fail "scripts/doctor.sh is missing"

doctor_fixture="$TEST_ROOT/doctor"
doctor_mise="$TEST_ROOT/doctor bin/mise"
doctor_log="$TEST_ROOT/doctor-mise.log"
create_forbidden_python "$TEST_ROOT/doctor-forbidden-bin/python3"
create_doctor_fixture "$doctor_fixture"
create_doctor_mise "$doctor_mise"
write_doctor_env "$doctor_fixture/crewai/.env"

cat >"$doctor_fixture/crewai/.env" <<'ENV'
LINEAR_API_KEY=linear-secret-value
OPENCODE_API_KEY=opencode-secret-value
ZEN_BASE_URL=https://example.invalid/private
ZEN_ANALYST_MODEL=
ZEN_ARCHITECT_MODEL=architect-secret-model
ZEN_CODER_MODEL=coder-secret-model
ZEN_REVIEWER_MODEL=reviewer-secret-model
ENV
export DOCTOR_TEST_NODE_VERSION="20.20.1"
export DOCTOR_TEST_PNPM_VERSION="11.2.0"
if run_doctor "$doctor_fixture" "$doctor_mise" "$TEST_ROOT/multiple-errors.log" >"$TEST_ROOT/multiple-errors.out" 2>&1; then
  fail "multiple doctor errors were accepted"
fi
unset DOCTOR_TEST_NODE_VERSION DOCTOR_TEST_PNPM_VERSION
assert_lines_in_order "$TEST_ROOT/multiple-errors.out" \
  "ERROR: node version: expected 20.20.2, got 20.20.1" \
  "ERROR: pnpm version: expected 11.3.0, got 11.2.0" \
  "ERROR: empty environment variable: ZEN_ANALYST_MODEL"
for protected in linear-secret-value opencode-secret-value architect-secret-model coder-secret-model reviewer-secret-model; do
  assert_output_excludes "$TEST_ROOT/multiple-errors.out" "$protected"
done
write_doctor_env "$doctor_fixture/crewai/.env"

if run_doctor "$doctor_fixture" "$TEST_ROOT/missing/mise" "$TEST_ROOT/missing-mise.log" >"$TEST_ROOT/missing-mise.out" 2>&1; then
  fail "missing mise was accepted"
fi
assert_output_contains "$TEST_ROOT/missing-mise.out" "ERROR: mise is not available"

export DOCTOR_TEST_NODE_VERSION="20.20.1"
if run_doctor "$doctor_fixture" "$doctor_mise" "$TEST_ROOT/wrong-version.log" >"$TEST_ROOT/wrong-version.out" 2>&1; then
  fail "wrong Node version was accepted"
fi
unset DOCTOR_TEST_NODE_VERSION
assert_output_contains "$TEST_ROOT/wrong-version.out" "ERROR: node version: expected 20.20.2, got 20.20.1"

for version_case in \
  "DOCTOR_TEST_PNPM_VERSION|11.2.0|pnpm|11.3.0" \
  "DOCTOR_TEST_UV_VERSION|0.11.15 (x86_64-unknown-linux-musl)|uv|0.11.16" \
  "DOCTOR_TEST_PYTHON_VERSION|3.12.12|python|3.12.13"; do
  IFS='|' read -r variable actual tool expected <<<"$version_case"
  export "$variable=$actual"
  if run_doctor "$doctor_fixture" "$doctor_mise" "$TEST_ROOT/wrong-$tool-version.log" >"$TEST_ROOT/wrong-$tool-version.out" 2>&1; then
    fail "wrong $tool version was accepted"
  fi
  unset "$variable"
  reported_actual="${actual%% *}"
  assert_output_contains "$TEST_ROOT/wrong-$tool-version.out" "ERROR: $tool version: expected $expected, got $reported_actual"
done

cat >"$doctor_fixture/.mise.toml" <<'TOML'
[tools]
node = "0.0.0"
python = "0.0.0"
uv = "0.0.0"
pnpm = "0.0.0"
TOML
if ! run_doctor "$doctor_fixture" "$doctor_mise" "$TEST_ROOT/binding-versions.log" >"$TEST_ROOT/binding-versions.out" 2>&1; then
  fail "doctor did not use the exact binding versions from the plan: $(<"$TEST_ROOT/binding-versions.out")"
fi

fallback_home="$TEST_ROOT/doctor-home"
create_doctor_mise "$fallback_home/.local/bin/mise"
if ! run_doctor_with_home_mise "$doctor_fixture" "$fallback_home" "$TEST_ROOT/home-mise.log" >"$TEST_ROOT/home-mise.out" 2>&1; then
  fail "doctor did not use mise from HOME local bin: $(<"$TEST_ROOT/home-mise.out")"
fi

mv "$doctor_fixture/crewai/.env" "$doctor_fixture/crewai/.env.saved"
if run_doctor "$doctor_fixture" "$doctor_mise" "$TEST_ROOT/missing-env.log" >"$TEST_ROOT/missing-env.out" 2>&1; then
  fail "missing environment file was accepted"
fi
assert_output_contains "$TEST_ROOT/missing-env.out" "ERROR: missing environment file: crewai/.env"
mv "$doctor_fixture/crewai/.env.saved" "$doctor_fixture/crewai/.env"

cat >"$doctor_fixture/crewai/.env" <<'ENV'
# python-dotenv syntax, including comments, quotes, and duplicate keys.
LINEAR_API_KEY = "linear-secret-value # quoted"
OPENCODE_API_KEY='opencode-secret-value'
ZEN_BASE_URL=
ZEN_BASE_URL=https://example.invalid/private # the last duplicate wins
ZEN_ANALYST_MODEL = analyst-secret-model
ZEN_ARCHITECT_MODEL="architect-secret-model"
ZEN_CODER_MODEL="" # an inline comment after an empty quoted value
ZEN_REVIEWER_MODEL=reviewer-secret-model
ENV
if run_doctor "$doctor_fixture" "$doctor_mise" "$TEST_ROOT/empty-variable.log" >"$TEST_ROOT/empty-variable.out" 2>&1; then
  fail "empty environment variable was accepted"
fi
assert_output_contains "$TEST_ROOT/empty-variable.out" "ERROR: empty environment variable: ZEN_CODER_MODEL"
if grep -Fq "ZEN_BASE_URL" "$TEST_ROOT/empty-variable.out"; then
  fail "doctor did not honor the last duplicate environment key"
fi
write_doctor_env "$doctor_fixture/crewai/.env"

for failure_case in \
  "node-version|node version check" \
  "pnpm-version|pnpm version check" \
  "uv-version|uv version check" \
  "python-version|python version check" \
  "pnpm-frozen|pnpm frozen lockfile check" \
  "uv-lock|uv lock check" \
  "openspec|OpenSpec strict validation" \
  "crew-import|crew import"; do
  IFS='|' read -r command message <<<"$failure_case"
  export DOCTOR_TEST_FAIL_COMMAND="$command"
  if run_doctor "$doctor_fixture" "$doctor_mise" "$TEST_ROOT/$command-failure.log" >"$TEST_ROOT/$command-failure.out" 2>&1; then
    fail "$command failure was not propagated"
  fi
  unset DOCTOR_TEST_FAIL_COMMAND
  assert_output_contains "$TEST_ROOT/$command-failure.out" "ERROR: $message failed"
done

printf 'UNUSED=$(touch %s)\n' "$TEST_ROOT/env-executed" >>"$doctor_fixture/crewai/.env"
for immutable in crewai/.env pnpm-lock.yaml crewai/uv.lock; do
  mkdir -p "$TEST_ROOT/before/$(dirname "$immutable")"
  cp "$doctor_fixture/$immutable" "$TEST_ROOT/before/$immutable"
  sha256_file "$doctor_fixture/$immutable" >"$TEST_ROOT/before/$immutable.sha256"
done
if ! run_doctor "$doctor_fixture" "$doctor_mise" "$doctor_log" >"$TEST_ROOT/doctor-valid.out" 2>&1; then
  fail "valid environment was rejected: $(<"$TEST_ROOT/doctor-valid.out")"
fi
assert_output_contains "$TEST_ROOT/doctor-valid.out" "OK: environment checks passed"
[[ ! -e "$TEST_ROOT/env-executed" ]] || fail "environment file content was executed"
for immutable in crewai/.env pnpm-lock.yaml crewai/uv.lock; do
  assert_file_unchanged "$TEST_ROOT/before/$immutable" "$doctor_fixture/$immutable" "$(<"$TEST_ROOT/before/$immutable.sha256")"
done

for protected in \
  linear-secret-value \
  opencode-secret-value \
  https://example.invalid/private \
  analyst-secret-model \
  architect-secret-model \
  coder-secret-model \
  reviewer-secret-model; do
  assert_output_excludes "$TEST_ROOT/doctor-valid.out" "$protected"
done

cat >"$TEST_ROOT/doctor-commands.expected" <<EOF
$doctor_fixture|exec -- node --version
$doctor_fixture|exec -- pnpm --version
$doctor_fixture|exec -- uv --version
$doctor_fixture|exec -- python --version
$doctor_fixture|dotenv-check|$doctor_fixture/crewai/.env
$doctor_fixture|exec -- pnpm install --frozen-lockfile --lockfile-only
$doctor_fixture|exec -- uv lock --project crewai --check
$doctor_fixture|exec -- pnpm exec openspec validate --all --strict
$doctor_fixture|exec -- uv run --project crewai --no-sync python -c import crew; print('crew import ok')
EOF
cmp -s "$TEST_ROOT/doctor-commands.expected" "$doctor_log" || fail "unexpected doctor commands"
assert_contains "$doctor_log.openspec-env" "0"

run_worker_lint_without_contract_dist

printf 'PASS: bootstrap behavior\n'
