#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM="$(uname -s)"

case "$PLATFORM" in
  Linux|Darwin) ;;
  *)
    printf 'Unsupported platform: %s\n' "$PLATFORM" >&2
    exit 1
    ;;
esac

MISE_BIN="$(command -v mise || true)"
if [[ -z "$MISE_BIN" && -x "$HOME/.local/bin/mise" ]]; then
  MISE_BIN="$HOME/.local/bin/mise"
fi

if [[ -z "$MISE_BIN" ]]; then
  curl -fsSL "https://mise.run" | sh
  MISE_BIN="$HOME/.local/bin/mise"
fi

if [[ ! -x "$MISE_BIN" ]]; then
  printf 'mise executable not found: %s\n' "$MISE_BIN" >&2
  exit 1
fi

cd "$ROOT_DIR"
"$MISE_BIN" install
"$MISE_BIN" exec -- pnpm install --frozen-lockfile
"$MISE_BIN" exec -- uv sync --project crewai --frozen

if [[ ! -e "$ROOT_DIR/crewai/.env" ]]; then
  cp "$ROOT_DIR/crewai/.env.example" "$ROOT_DIR/crewai/.env"
fi

if "$ROOT_DIR/scripts/doctor.sh"; then
  printf 'Entorno preparado.\nEl bootstrap no puede modificar el shell padre.\n'

  case "${SHELL:-}" in
    */bash)
      printf '%s\n' \
        'Para habilitar mise en Bash, ejecuta:' \
        "  grep -qxF 'export PATH=\"\$HOME/.local/bin:\$PATH\"' \"\$HOME/.bashrc\" || printf '%s\\n' 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> \"\$HOME/.bashrc\"" \
        "  grep -qxF 'eval \"\$(mise activate bash)\"' \"\$HOME/.bashrc\" || printf '%s\\n' 'eval \"\$(mise activate bash)\"' >> \"\$HOME/.bashrc\"" \
        '  source "$HOME/.bashrc"' \
        'Luego ejecuta:' \
        '  pnpm verify' \
        '  cd crewai' \
        '  uv run run_crew DEV-5'
      ;;
    */zsh)
      printf '%s\n' \
        'Para habilitar mise en Zsh, ejecuta:' \
        "  grep -qxF 'export PATH=\"\$HOME/.local/bin:\$PATH\"' \"\$HOME/.zshrc\" || printf '%s\\n' 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> \"\$HOME/.zshrc\"" \
        "  grep -qxF 'eval \"\$(mise activate zsh)\"' \"\$HOME/.zshrc\" || printf '%s\\n' 'eval \"\$(mise activate zsh)\"' >> \"\$HOME/.zshrc\"" \
        '  source "$HOME/.zshrc"' \
        'Luego ejecuta:' \
        '  pnpm verify' \
        '  cd crewai' \
        '  uv run run_crew DEV-5'
      ;;
    *)
      printf 'Shell no compatible detectado: %s\n' "${SHELL:-desconocido}"
      printf 'Usa mise exec sin depender de la configuracion del shell:\n'
      ;;
  esac

  if [[ "${SHELL:-}" == */bash || "${SHELL:-}" == */zsh ]]; then
    printf 'Alternativa sin modificar tu shell:\n'
  fi
  printf '  %q exec -- pnpm verify\n' "$MISE_BIN"
  printf '  %q exec -- uv run --project crewai run_crew DEV-5\n' "$MISE_BIN"
else
  doctor_status=$?
  printf 'Corrige los errores reportados por doctor y ejecuta nuevamente:\n  ./scripts/doctor.sh\n' >&2
  exit "$doctor_status"
fi
