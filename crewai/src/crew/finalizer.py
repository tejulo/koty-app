import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


CREWAI_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CREWAI_ROOT.parent

load_dotenv(CREWAI_ROOT / ".env")


from .linear_api import complete_issue, get_issue
from .models import CrewResult


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


def _run(
    command: list[str],
    cwd: Path = PROJECT_ROOT,
    timeout: int = 600,
) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"Falló {' '.join(command)}"
        )

    return result.stdout.strip()


def _find_change(
    change_id: str,
) -> tuple[Path, bool] | None:
    active = (
        PROJECT_ROOT
        / "openspec"
        / "changes"
        / change_id
    )

    if active.exists():
        return active, False

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

    if not matches:
        return None

    return matches[0], True


def _has_pending_tasks(
    change: Path,
) -> bool:
    tasks = change / "tasks.md"

    if not tasks.is_file():
        raise RuntimeError(
            "No existe tasks.md"
        )

    content = tasks.read_text(
        encoding="utf-8"
    )

    return bool(
        re.search(
            r"^\s*-\s*\[\s\]",
            content,
            flags=re.MULTILINE,
        )
    )


def _browser_strategy(
    change: Path,
) -> str:
    design = change / "design.md"

    if not design.is_file():
        raise RuntimeError(
            "No existe design.md"
        )

    content = design.read_text(
        encoding="utf-8"
    )

    match = re.search(
        r"Browser E2E:\s*"
        r"(required|not_required)",
        content,
    )

    if not match:
        raise RuntimeError(
            "design.md no define Browser E2E"
        )

    return match.group(1)


def _current_branch() -> str:
    return _run(
        [
            "git",
            "branch",
            "--show-current",
        ]
    )


def _check_branch(
    change_id: str,
) -> None:
    branch = _current_branch()

    pattern = (
        rf"^[^/]+/"
        rf"{re.escape(change_id)}"
        rf"(?:-|$)"
    )

    if not re.match(
        pattern,
        branch,
    ):
        raise RuntimeError(
            f"Branch incorrecta: {branch}"
        )


def _check_crew_result(
    ticket_id: str,
    change_id: str,
    result: CrewResult,
    browser_strategy: str,
) -> None:
    if (
        result.ticket_id.upper()
        != ticket_id
    ):
        raise RuntimeError(
            "result.json pertenece a otro ticket"
        )

    if result.change_id != change_id:
        raise RuntimeError(
            "result.json pertenece a otro change"
        )

    if result.status != "approved":
        raise RuntimeError(
            f"Crew no aprobado: {result.status}"
        )

    required = {
        "python": result.verification.python,
        "lint": result.verification.lint,
        "test": result.verification.test,
        "build": result.verification.build,
        "openspec": result.verification.openspec,
    }

    failed = [
        name
        for name, status in required.items()
        if status != "passed"
    ]

    if failed:
        raise RuntimeError(
            "Verificaciones no aprobadas: "
            + ", ".join(failed)
        )

    playwright = (
        result.verification.playwright
    )

    if (
        browser_strategy == "required"
        and playwright != "passed"
    ):
        raise RuntimeError(
            "Playwright es obligatorio"
        )

    if (
        browser_strategy == "not_required"
        and playwright
        not in {
            "passed",
            "skipped",
        }
    ):
        raise RuntimeError(
            "Playwright no aprobado"
        )


def _run_code_gates() -> None:
    _run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "compileall",
            "-q",
            "src/crew",
        ],
        cwd=CREWAI_ROOT,
    )

    for command in [
        ["pnpm", "lint"],
        ["pnpm", "test"],
        ["pnpm", "build"],
    ]:
        _run(
            command,
            cwd=PROJECT_ROOT,
        )


def _commit(
    ticket_id: str,
) -> None:
    status = _run(
        [
            "git",
            "status",
            "--porcelain",
        ]
    )

    if not status:
        return

    branch = _current_branch()

    commit_type = branch.split(
        "/",
        1,
    )[0]

    if commit_type == "hotfix":
        commit_type = "fix"

    allowed = {
        "feat",
        "fix",
        "refactor",
        "docs",
        "test",
        "chore",
        "build",
        "ci",
    }

    if commit_type not in allowed:
        commit_type = "chore"

    issue = get_issue(ticket_id)

    title = " ".join(
        issue["title"].split()
    )

    _run(
        [
            "git",
            "add",
            "-A",
        ]
    )

    _run(
        [
            "git",
            "commit",
            "-m",
            (
                f"{commit_type}: "
                f"[{ticket_id}] {title}"
            ),
        ]
    )


def _write_failure(
    change: Path,
    stage: str,
    error: Exception,
    retry_with_crew: bool,
) -> None:
    attempts = change / "attempts"

    attempts.mkdir(
        parents=True,
        exist_ok=True,
    )

    if retry_with_crew:
        existing = list(
            attempts.glob(
                "attempt-*.md"
            )
        )

        number = len(existing) + 1

        filename = (
            f"attempt-{number:03}.md"
        )

    else:
        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        filename = (
            f"finalizer-{timestamp}.md"
        )

    content = f"""# Finalizer Failure

## Stage

{stage}

## Error

{error}
"""

    (
        attempts / filename
    ).write_text(
        content,
        encoding="utf-8",
    )


def finalize(
    raw_ticket_id: str,
) -> dict:
    ticket_id, change_id = normalize(
        raw_ticket_id
    )

    found = _find_change(change_id)

    if not found:
        return {
            "status": "not_ready",
            "finalized": False,
            "ticket_id": ticket_id,
            "change_id": change_id,
            "reason": (
                "No existe el cambio OpenSpec"
            ),
        }

    change, archived = found

    result_file = (
        change / "result.json"
    )

    if not result_file.is_file():
        return {
            "status": "not_ready",
            "finalized": False,
            "ticket_id": ticket_id,
            "change_id": change_id,
            "reason": "No existe result.json",
        }

    try:
        result = (
            CrewResult.model_validate_json(
                result_file.read_text(
                    encoding="utf-8"
                )
            )
        )
    except Exception as error:
        return {
            "status": "blocked",
            "finalized": False,
            "ticket_id": ticket_id,
            "change_id": change_id,
            "stage": "result",
            "reason": (
                f"result.json inválido: {error}"
            ),
        }

    if result.status != "approved":
        return {
            "status": "not_ready",
            "finalized": False,
            "ticket_id": ticket_id,
            "change_id": change_id,
            "reason": result.status,
        }

    stage = "setup"

    try:
        stage = "branch"

        _check_branch(change_id)

        stage = "tasks"

        if _has_pending_tasks(change):
            raise RuntimeError(
                "tasks.md tiene tareas pendientes"
            )

        stage = "design"

        browser_strategy = (
            _browser_strategy(change)
        )

        stage = "crew_result"

        _check_crew_result(
            ticket_id,
            change_id,
            result,
            browser_strategy,
        )

        stage = "verification"

        _run_code_gates()

        if not archived:
            stage = "openspec_validate"

            _run(
                [
                    "pnpm",
                    "exec",
                    "openspec",
                    "validate",
                    change_id,
                    "--strict",
                    "--no-interactive",
                ]
            )

            stage = "archive"

            _run(
                [
                    "pnpm",
                    "exec",
                    "openspec",
                    "archive",
                    change_id,
                    "--yes",
                ]
            )

            found = _find_change(
                change_id
            )

            if (
                not found
                or not found[1]
            ):
                raise RuntimeError(
                    "OpenSpec archive no confirmado"
                )

            change, archived = found

        stage = "post_archive"

        _run(
            [
                "pnpm",
                "exec",
                "openspec",
                "validate",
                "--all",
                "--strict",
            ]
        )

        stage = "git"

        _commit(ticket_id)

        stage = "linear"

        complete_issue(ticket_id)

        return {
            "status": "done",
            "finalized": True,
            "ticket_id": ticket_id,
            "change_id": change_id,
        }

    except Exception as error:
        current = _find_change(
            change_id
        )

        if current:
            change, now_archived = current
        else:
            now_archived = archived

        retry_with_crew = (
            not now_archived
            and stage
            in {
                "tasks",
                "design",
                "crew_result",
                "verification",
                "openspec_validate",
                "archive",
            }
        )

        if current:
            _write_failure(
                change,
                stage,
                error,
                retry_with_crew,
            )

        message = str(error).lower()

        blocked = any(
            marker in message
            for marker in [
                "branch incorrecta",
                "author identity unknown",
                "please tell me who you are",
                "not a git repository",
                "no existe design.md",
                "no define browser e2e",
                "result.json inválido",
            ]
        )

        if blocked:
            status = "blocked"

        elif retry_with_crew:
            status = "repair"

        else:
            status = "retry"

        return {
            "status": status,
            "finalized": False,
            "ticket_id": ticket_id,
            "change_id": change_id,
            "stage": stage,
            "reason": str(error),
        }


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="finalize_ticket",
        description=(
            "Finaliza un ticket aprobado por CrewAI."
        ),
    )

    parser.add_argument(
        "ticket_id",
        help=(
            "Identificador del ticket de Linear. "
            "Ejemplo: DEV-5"
        ),
    )

    args = parser.parse_args()

    result = finalize(
        args.ticket_id
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
