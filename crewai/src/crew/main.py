import json
import os
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


CREWAI_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CREWAI_ROOT.parent

load_dotenv(CREWAI_ROOT / ".env")

os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"


from .crew import KotyAppCrew
from .models import CrewResult, VerificationResult
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


def max_attempts_result(
    ticket_id: str,
    change_id: str,
    max_attempts: int,
) -> CrewResult:
    return CrewResult(
        ticket_id=ticket_id,
        change_id=change_id,
        status="blocked",
        failure_type="max_attempts",
        failure_stage="orchestrator",
        summary=(
            f"Se alcanzaron {max_attempts} "
            "intentos sin completar el ticket."
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


def run():
    raw_id = (
        sys.argv[1]
        if len(sys.argv) > 1
        else input("Ticket: ")
    )

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

    attempt = next_attempt(change_id)

    max_attempts = int(
        os.environ.get(
            "MAX_TICKET_ATTEMPTS",
            "3",
        )
    )

    if attempt > max_attempts:
        result = max_attempts_result(
            ticket_id,
            change_id,
            max_attempts,
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
        output = (
            KotyAppCrew()
            .crew()
            .kickoff(
                inputs={
                    "ticket_id": ticket_id,
                    "change_id": change_id,
                    "attempt": attempt,
                    "last_attempt_path": (
                        last_attempt(change_id)
                    ),
                }
            )
        )

        if output.pydantic is None:
            raise RuntimeError(
                "Reviewer no devolvió "
                "CrewResult estructurado"
            )

        if isinstance(
            output.pydantic,
            CrewResult,
        ):
            result = output.pydantic
        else:
            result = CrewResult.model_validate(
                output.pydantic
            )

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
        save_attempt(
            change_id,
            attempt,
            result,
        )

    print(
        result.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    run()
