import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .evidence import record_active_gate_execution
from .integration_env import environment


CREWAI_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CREWAI_ROOT.parent


@dataclass(frozen=True)
class GateRun:
    name: str
    passed: bool
    evidence_id: str | None
    output: str


def _run(
    command: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def run_gate(name: str, change_id: str) -> GateRun:
    commands = {
        "python": (["uv", "run", "python", "-m", "compileall", "-q", "src/crew"], CREWAI_ROOT),
        "lint": (["pnpm", "lint"], PROJECT_ROOT),
        "test": (["pnpm", "test"], PROJECT_ROOT),
        "build": (["pnpm", "build"], PROJECT_ROOT),
        "openspec": (
            ["pnpm", "exec", "openspec", "validate", change_id, "--strict", "--no-interactive"],
            PROJECT_ROOT,
        ),
    }
    if name == "integration":
        bootstrap = ["pnpm", "db:start"]
        code, output = _run(bootstrap, PROJECT_ROOT, environment(PROJECT_ROOT))
        if code:
            evidence_id = record_active_gate_execution(name, bootstrap, PROJECT_ROOT, code, output)
            return GateRun(name, False, evidence_id, output)
        command = ["pnpm", "--filter", "@koty-app/api", "test:integration"]
        cwd = PROJECT_ROOT
        env = environment(PROJECT_ROOT)
    else:
        command, cwd = commands[name]
        env = None
    code, output = _run(command, cwd, env)
    evidence_id = record_active_gate_execution(name, command, cwd, code, output)
    return GateRun(name, code == 0, evidence_id, output)


def diagnose_gate_failure(name: str, output: str) -> dict[str, object]:
    delta_missing = name == "openspec" and (
        "No delta sections found" in output
        or "Change must have at least one delta" in output
    )
    category = "openspec_delta_missing" if delta_missing else f"{name}_failure"
    hint = (
        "Agrega '## ADDED Requirements' antes de los Requirements del spec."
        if delta_missing
        else f"Revisa la salida de {name}."
    )
    return {
        "category": category,
        "fingerprint": hashlib.sha256(
            f"{category}:{re.sub(r'plandepo_test_[A-Za-z0-9]+', 'plandepo_test', output)}".encode()
        ).hexdigest(),
        "repairHint": hint,
        "repairScope": ["openspec/changes/<change>/specs"] if delta_missing else [],
    }
