import json
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError


CREWAI_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CREWAI_ROOT.parent

load_dotenv(CREWAI_ROOT / ".env")

os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"


from .crew import KotyAppCrew
from .models import (
    CrewExecution,
    CrewResult,
    VerificationResult,
)
from .tools.custom_tool import (
    close_local_environment,
    close_playwright_session,
)


class ArchivedChangeError(RuntimeError):
    pass


def normalize(raw_id: str) -> tuple[str, str]:
    raw_id = raw_id.strip()

    if not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9]*-\d+",
        raw_id,
    ):
        raise ValueError(
            "Ticket inválido. Ejemplo: DEV-5"
        )

    return raw_id.upper(), raw_id.lower()


def active_change(change_id: str) -> Path:
    return (
        PROJECT_ROOT
        / "openspec"
        / "changes"
        / change_id
    )


def archived_change(
    change_id: str,
) -> Path | None:
    archive = (
        PROJECT_ROOT
        / "openspec"
        / "changes"
        / "archive"
    )

    if not archive.exists():
        return None

    matches = sorted(
        archive.glob(f"*-{change_id}"),
        reverse=True,
    )

    return matches[0] if matches else None


def ensure_change(change_id: str) -> None:
    if active_change(change_id).exists():
        return

    if archived_change(change_id):
        raise ArchivedChangeError(
            f"{change_id} ya está archivado"
        )

    result = subprocess.run(
        [
            "pnpm",
            "exec",
            "openspec",
            "new",
            "change",
            change_id,
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "No se pudo crear el cambio OpenSpec"
        )


def attempts_dir(change_id: str) -> Path:
    return (
        active_change(change_id)
        / "attempts"
    )


def execution_path(change_id: str) -> Path:
    return (
        PROJECT_ROOT
        / ".agent"
        / "crew"
        / change_id
        / "execution.json"
    )


def load_execution(change_id: str) -> CrewExecution:
    path = execution_path(change_id)

    if not path.exists():
        return CrewExecution()

    return CrewExecution.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def save_execution(
    change_id: str,
    execution: CrewExecution,
) -> None:
    path = execution_path(change_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        execution.model_dump_json(indent=2),
        encoding="utf-8",
    )


def resume_execution(change_id: str) -> CrewExecution:
    path = execution_path(change_id)
    execution = (
        CrewExecution(number=load_execution(change_id).number + 1)
        if path.exists()
        else CrewExecution()
    )
    save_execution(change_id, execution)
    return execution


def attempt_files(
    change_id: str,
) -> list[Path]:
    path = attempts_dir(change_id)

    if not path.exists():
        return []

    return sorted(
        path.glob("attempt-*.md")
    )


def next_attempt(change_id: str) -> int:
    return len(
        attempt_files(change_id)
    ) + 1


def last_attempt(change_id: str) -> str:
    attempts = attempt_files(change_id)

    if not attempts:
        return "NONE"

    return (
        attempts[-1]
        .relative_to(PROJECT_ROOT)
        .as_posix()
    )


def save_result(
    change_id: str,
    result: CrewResult,
) -> None:
    path = active_change(change_id)

    if not path.exists():
        raise RuntimeError(
            "No existe el cambio OpenSpec activo"
        )

    (
        path / "result.json"
    ).write_text(
        result.model_dump_json(indent=2),
        encoding="utf-8",
    )


def save_attempt(
    change_id: str,
    attempt: int,
    result: CrewResult,
) -> None:
    path = attempts_dir(change_id)

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    verification = json.dumps(
        result.verification.model_dump(),
        indent=2,
        ensure_ascii=False,
    )

    content = f"""# Attempt {attempt}

## Status

{result.status}

## Failure

- Type: {result.failure_type}
- Stage: {result.failure_stage or "unknown"}

## Summary

{result.summary}

## Verification

~~~json
{verification}
~~~
"""

    (
        path
        / f"attempt-{attempt:03}.md"
    ).write_text(
        content,
        encoding="utf-8",
    )


def runtime_failure(
    ticket_id: str,
    change_id: str,
    error: Exception,
) -> CrewResult:
    message = str(error)

    configuration_error = any(
        marker in message.lower()
        for marker in [
            "falta ",
            "not found",
            "no está instalado",
        ]
    )

    return CrewResult(
        ticket_id=ticket_id,
        change_id=change_id,
        status=(
            "blocked"
            if configuration_error
            else "retryable_failure"
        ),
        failure_type=(
            "configuration"
            if configuration_error
            else "infrastructure"
        ),
        failure_stage="runtime",
        summary=message,
        verification=VerificationResult(
            python="skipped",
            lint="skipped",
            test="skipped",
            build="skipped",
            playwright="skipped",
            openspec="skipped",
        ),
    )


def parse_crew_result(output: object) -> CrewResult:
    pydantic = getattr(output, "pydantic", None)

    if isinstance(pydantic, CrewResult):
        return pydantic

    if pydantic is not None:
        return CrewResult.model_validate(pydantic)

    raw = getattr(output, "raw", None)

    if not isinstance(raw, str):
        raise RuntimeError(
            "Reviewer no devolvió un resultado estructurado"
        )

    decoder = json.JSONDecoder()

    for start, character in enumerate(raw):
        if character != "{":
            continue

        try:
            payload, _ = decoder.raw_decode(raw[start:])
            return CrewResult.model_validate(
                normalize_crew_result(payload)
            )
        except (json.JSONDecodeError, ValidationError):
            continue

    raise RuntimeError(
        "Reviewer no devolvió un resultado estructurado válido"
    )


def normalize_crew_result(payload: object) -> object:
    if not isinstance(payload, dict):
        return payload

    verification = payload.get("verification")

    if not isinstance(verification, dict):
        return payload

    checks = {
        name: normalize_check(
            verification.get(name)
            if name != "openspec"
            else verification.get(
                "openspec",
                verification.get(
                    "openspec_validate",
                    verification.get("openspec_validate_strict"),
                ),
            )
        )
        for name in (
            "python",
            "lint",
            "test",
            "build",
            "playwright",
            "openspec",
        )
    }

    return {**payload, "verification": checks}


def normalize_check(value: object) -> object:
    if isinstance(value, dict):
        value = value.get("result")

    if not isinstance(value, str):
        return value

    value = value.casefold()

    if value.startswith("pass"):
        return "passed"

    if value.startswith("fail"):
        return "failed"

    if value.startswith(("skip", "not_required")):
        return "skipped"

    return value


def max_attempts_result(
    ticket_id: str,
    change_id: str,
    max_attempts: int,
    execution: CrewExecution,
) -> CrewResult:
    return CrewResult(
        ticket_id=ticket_id,
        change_id=change_id,
        status="blocked",
        failure_type="max_attempts",
        failure_stage="orchestrator",
        summary=(
            f"Se alcanzaron {max_attempts} "
            f"intentos en la ejecución {execution.number} "
            "sin completar el ticket."
        ),
        verification=VerificationResult(
            python="skipped",
            lint="skipped",
            test="skipped",
            build="skipped",
            playwright="skipped",
            openspec="skipped",
        ),
    )


def execution_attempts(
    execution: CrewExecution,
) -> tuple[int, int]:
    if execution.last_failure_type == "infrastructure":
        return (
            execution.infrastructure_attempts,
            int(
                os.environ.get(
                    "MAX_INFRASTRUCTURE_ATTEMPTS",
                    "2",
                )
            ),
        )

    return (
        execution.attempts,
        int(
            os.environ.get(
                "MAX_TICKET_ATTEMPTS",
                "3",
            )
        ),
    )


def run():
    arguments = sys.argv[1:]
    raw_id = arguments[0] if arguments else input("Ticket: ")
    resume = "--resume" in arguments[1:]

    ticket_id, change_id = normalize(
        raw_id
    )

    try:
        ensure_change(change_id)

    except ArchivedChangeError:
        print(
            json.dumps(
                {
                    "ticket_id": ticket_id,
                    "change_id": change_id,
                    "status": "archived",
                    "summary": (
                        "El cambio ya está archivado. "
                        "Ejecuta finalize_ticket."
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    execution = (
        resume_execution(change_id)
        if resume
        else load_execution(change_id)
    )

    attempts, max_attempts = execution_attempts(execution)

    if attempts >= max_attempts:
        result = max_attempts_result(
            ticket_id,
            change_id,
            max_attempts,
            execution,
        )

        save_result(
            change_id,
            result,
        )

        print(
            result.model_dump_json(indent=2)
        )
        return

    try:
        record_attempt = next_attempt(change_id)
        output = (
            KotyAppCrew()
            .crew()
            .kickoff(
                inputs={
                    "ticket_id": ticket_id,
                    "change_id": change_id,
                    "attempt": execution.attempts + 1,
                    "last_attempt_path": (
                        last_attempt(change_id)
                    ),
                }
            )
        )

        result = parse_crew_result(output)

        if (
            result.ticket_id.upper()
            != ticket_id
        ):
            raise RuntimeError(
                "CrewResult pertenece "
                "a otro ticket"
            )

        if result.change_id != change_id:
            raise RuntimeError(
                "CrewResult pertenece "
                "a otro change_id"
            )

    except Exception as error:
        traceback.print_exc()
        result = runtime_failure(
            ticket_id,
            change_id,
            error,
        )

    finally:
        close_playwright_session()
        close_local_environment()

    save_result(
        change_id,
        result,
    )

    if result.status != "approved":
        execution.last_failure_type = result.failure_type
        if result.failure_type == "infrastructure":
            execution.infrastructure_attempts += 1
        else:
            execution.attempts += 1
        save_execution(change_id, execution)
        save_attempt(
            change_id,
            record_attempt,
            result,
        )

    print(
        result.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    run()
