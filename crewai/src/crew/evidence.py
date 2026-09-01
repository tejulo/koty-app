import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GATES = (
    "python",
    "lint",
    "test",
    "build",
    "integration",
    "openspec",
)
NEST_DI_METADATA = re.compile(
    r"NEST_DI_METADATA_MISSING:\s*(.+)"
)
DIAGNOSTIC = re.compile(
    r"^\s+(\d+):(\d+)\s+(?:error|warning)\s+.+?\s+(\S+)\s*$"
)


def attempt_path(change_id: str, attempt: int) -> Path:
    return (
        PROJECT_ROOT
        / "openspec"
        / "changes"
        / change_id
        / "attempts"
        / f"attempt-{attempt:03}.verification.json"
    )


def load_attempt_evidence(change_id: str, attempt: int) -> dict:
    path = attempt_path(change_id, attempt)
    if not path.exists():
        return {"schemaVersion": 1, "attempt": attempt, "executions": []}
    return json.loads(path.read_text(encoding="utf-8"))


def diagnose_integration_failure(output: str) -> dict[str, object]:
    match = NEST_DI_METADATA.search(output)
    affected = (
        sorted(
            name.strip()
            for name in match.group(1).split(",")
            if name.strip()
        )
        if match
        else []
    )
    category = "shared_test_harness" if affected else "unclassified"
    fingerprint = _digest(
        json.dumps(
            {
                "category": category,
                "affected": affected,
                "output": "" if affected else _normalize_output(output),
            },
            sort_keys=True,
        ).encode()
    )
    return {
        "category": category,
        "affected": affected,
        "fingerprint": fingerprint,
        "repairHint": (
            "Configura Vitest con SWC y decoratorMetadata."
            if affected
            else "Revisa la salida de integración."
        ),
        "repairScope": (
            [
                "apps/api/vitest.config.integration.ts",
                "apps/api/package.json",
                "pnpm-lock.yaml",
            ]
            if affected
            else []
        ),
    }


def save_integration_diagnosis(
    change_id: str,
    attempt: int,
    diagnosis: dict[str, object],
) -> Path:
    path = attempt_path(change_id, attempt).with_name(
        f"attempt-{attempt:03}.integration-diagnosis.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(diagnosis, indent=2), encoding="utf-8")
    return path


def parse_eslint_diagnostics(output: str) -> list[dict[str, object]]:
    current: Path | None = None
    diagnostics: list[dict[str, object]] = []
    for line in output.splitlines():
        path = _source_path(line.strip())
        if path:
            current = path
            continue
        match = DIAGNOSTIC.match(line)
        if not match or not current:
            continue
        diagnostics.append(
            {
                "path": current.relative_to(PROJECT_ROOT).as_posix(),
                "line": int(match.group(1)),
                "column": int(match.group(2)),
                "rule": match.group(3),
                "fileSha256": _digest(current.read_bytes()),
            }
        )
    return diagnostics


def record_gate_execution(
    gate: str,
    command: list[str],
    cwd: Path,
    exit_code: int,
    output: str,
) -> str:
    change_id = os.environ["CREW_VERIFICATION_CHANGE_ID"]
    attempt = int(os.environ["CREW_VERIFICATION_ATTEMPT"])
    path = attempt_path(change_id, attempt)
    path.parent.mkdir(parents=True, exist_ok=True)
    execution_id = uuid4().hex
    output_path = path.with_name(f"{path.stem}.{execution_id}.log")
    output_path.write_text(output, encoding="utf-8")
    evidence = load_attempt_evidence(change_id, attempt)
    evidence["executions"].append(
        {
            "id": execution_id,
            "gate": gate,
            "command": command,
            "cwd": _relative(cwd),
            "exitCode": exit_code,
            "createdAt": datetime.now(UTC).isoformat(),
            "outputPath": _relative(output_path),
            "outputSha256": _digest(output.encode()),
            "diagnostics": parse_eslint_diagnostics(output)
            if gate == "lint"
            else [],
        }
    )
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return execution_id


def record_active_gate_execution(
    gate: str,
    command: list[str],
    cwd: Path,
    exit_code: int,
    output: str,
) -> str | None:
    if not os.environ.get("CREW_VERIFICATION_CHANGE_ID"):
        return None
    return record_gate_execution(gate, command, cwd, exit_code, output)


def validate_reviewer_evidence(
    change_id: str,
    result: object,
    expected_attempt: int | None = None,
) -> str | None:
    evidence_ids = getattr(result, "evidence", {})
    attempt = getattr(result, "attempt", None)
    verification = getattr(result, "verification", None)
    if not isinstance(attempt, int) or attempt < 1:
        return "El resultado no declara un intento válido"
    if expected_attempt is not None and attempt != expected_attempt:
        return "La evidencia no corresponde al intento actual"
    if not isinstance(evidence_ids, dict):
        return "El resultado no declara evidencia válida"
    runs = {
        run["id"]: run
        for run in load_attempt_evidence(change_id, attempt)["executions"]
    }
    for gate in GATES:
        execution_id = evidence_ids.get(gate)
        run = runs.get(execution_id)
        status = getattr(verification, gate, None)
        if not isinstance(execution_id, str) or not run:
            return f"Falta evidencia para {gate}"
        if run["gate"] != gate:
            return f"La evidencia {execution_id} no corresponde a {gate}"
        if status == "passed" and run["exitCode"] != 0:
            return f"{gate} fue declarado aprobado con evidencia fallida"
        if status == "failed" and run["exitCode"] == 0:
            return f"{gate} fue declarado fallido con evidencia aprobada"
        if status not in {"passed", "failed"}:
            return f"{gate} no tiene un estado verificable"
        if _stale(run):
            return f"La evidencia {execution_id} de {gate} está obsoleta"
    return None


def _source_path(value: str) -> Path | None:
    candidate = Path(value)
    path = candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
    try:
        path = path.resolve()
    except OSError:
        return None
    if path.is_file() and path.is_relative_to(PROJECT_ROOT):
        return path
    return None


def _stale(run: dict) -> bool:
    for diagnostic in run["diagnostics"]:
        path = _source_path(str(diagnostic["path"]))
        if not path or _digest(path.read_bytes()) != diagnostic["fileSha256"]:
            return True
    return False


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _normalize_output(output: str) -> str:
    return re.sub(
        r"plandepo_test_[A-Za-z0-9]+",
        "plandepo_test",
        output,
    )
