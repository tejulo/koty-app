import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


CREWAI_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CREWAI_ROOT.parent
PROFILE_PATTERN = re.compile(r"^verification_profile:\s*(\S+)\s*$", re.MULTILINE)

load_dotenv(CREWAI_ROOT / ".env")


from .linear_api import complete_issue, get_issue
from .evidence import validate_reviewer_evidence
from .integration_env import environment
from .models import CrewResult, PlanManifest, ReviewPack, TicketContract
from . import workflow


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
    env: dict[str, str] | None = None,
) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
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

    evidence_error = validate_reviewer_evidence(change_id, result)
    if evidence_error:
        raise RuntimeError(f"Evidencia inválida: {evidence_error}")

    required = {
        "python": result.verification.python,
        "lint": result.verification.lint,
        "test": result.verification.test,
        "build": result.verification.build,
        "integration": result.verification.integration,
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


def _state_path(reference: str) -> Path:
    candidate = Path(reference)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise RuntimeError("ExecutionState contiene una ruta fuera del proyecto")
    path = (workflow.PROJECT_ROOT / candidate).resolve()
    if not path.is_relative_to(workflow.PROJECT_ROOT.resolve()):
        raise RuntimeError("ExecutionState contiene una ruta fuera del proyecto")
    return path


def _selected_profile(change_id: str) -> str:
    design = workflow.PROJECT_ROOT / "openspec" / "changes" / change_id / "design.md"
    match = PROFILE_PATTERN.search(design.read_text(encoding="utf-8")) if design.is_file() else None
    if not match or match.group(1) not in {"standard", "browser", "operational", "browser_operational"}:
        raise ValueError("OpenSpec design has no valid verification_profile")
    return match.group(1)


def _check_review_pack(ticket_id: str, change_id: str) -> str:
    try:
        state = workflow.load_execution(ticket_id)
        if (
            state.ticket_id != ticket_id
            or state.change_id != change_id
            or state.phase != "approved"
            or not state.ticket_sha256
            or not state.plan_sha256
            or not state.profile
            or not state.ticket_contract_path
            or not state.plan_manifest_path
            or not state.review_pack_path
        ):
            raise ValueError("ExecutionState has no current approved contracts")

        contract_path = _state_path(state.ticket_contract_path)
        plan_path = _state_path(state.plan_manifest_path)
        review_path = _state_path(state.review_pack_path)
        if workflow.file_sha256(plan_path) != state.plan_sha256:
            raise ValueError("PlanManifest plan hash is stale")
        contract = workflow.load_model(contract_path, TicketContract)
        manifest = workflow.load_model(plan_path, PlanManifest)
        selected_profile = _selected_profile(change_id)
        artifact_paths = {
            name: workflow.PROJECT_ROOT / "openspec" / "changes" / change_id / name
            for name in manifest.artifacts
        }
        workflow.validate_plan_manifest(
            manifest,
            [criterion.id for criterion in contract.acceptance_criteria],
            expected_profile=selected_profile,
            expected_ticket_sha256=state.ticket_sha256,
            ticket_contract_path=contract_path,
            artifact_paths=artifact_paths,
        )
        if manifest.ticket_id != ticket_id or manifest.change_id != change_id:
            raise ValueError("PlanManifest does not match the current ticket")

        review = workflow.load_model(review_path, ReviewPack)
        workflow.validate_review_pack(review, expected_plan_sha256=state.plan_sha256)
        if (
            review.ticket_id != ticket_id
            or review.change_id != change_id
            or review.ticket_sha256 != state.ticket_sha256
            or state.profile != selected_profile
            or review.profile != selected_profile
        ):
            raise ValueError("ReviewPack does not match the current execution")
        if review.incomplete_tasks:
            raise ValueError("ReviewPack has incomplete tasks")
        return selected_profile
    except (OSError, ValueError) as error:
        raise RuntimeError(f"ReviewPack invalid: {error}") from error


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
        ["pnpm", "db:start"],
        [
            "pnpm",
            "--filter",
            "@koty-app/api",
            "test:integration",
        ],
    ]:
        _run(
            command,
            cwd=PROJECT_ROOT,
            env=environment(PROJECT_ROOT)
            if command[1:] == ["db:start"]
            or command[-1:] == ["test:integration"]
            else None,
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

    staged = _run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
        ]
    )
    if any(
        path.startswith(".agent/")
        for path in staged.splitlines()
    ):
        raise RuntimeError(
            "Hay artifacts runtime indexados"
        )

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
            "--all",
            "--",
            ".",
            ":(exclude).agent",
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
) -> None:
    diagnostics = change / "finalization"

    diagnostics.mkdir(
        parents=True,
        exist_ok=True,
    )
    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S-%f"
    )
    filename = f"finalizer-{timestamp}.md"

    content = f"""# Finalizer Failure

## Stage

{stage}

## Error

{error}
"""

    (
        diagnostics / filename
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
            "status": "blocked" if result.status == "blocked" else "not_ready",
            "finalized": False,
            "ticket_id": ticket_id,
            "change_id": change_id,
            "reason": result.status,
        }

    stage = "setup"

    try:
        stage = "branch"

        _check_branch(change_id)

        stage = "review_pack"

        profile = _check_review_pack(ticket_id, change_id)
        browser_strategy = "required" if profile in {"browser", "browser_operational"} else "not_required"

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
                "design",
                "review_pack",
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
