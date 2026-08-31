import json
import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv


CREWAI_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = CREWAI_ROOT.parent

load_dotenv(CREWAI_ROOT / ".env")


from .linear_api import (
    next_issue,
    start_issue,
)


def _required(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise ValueError(f"Falta {name}")

    return value


def _existing_branch(
    change_id: str,
) -> str | None:
    result = subprocess.run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)",
            "refs/heads",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    pattern = re.compile(
        rf"^[^/]+/{re.escape(change_id)}(?:-|$)"
    )

    matches = [
        branch.strip()
        for branch in result.stdout.splitlines()
        if pattern.match(branch.strip())
    ]

    if len(matches) > 1:
        raise RuntimeError(
            f"Hay múltiples branches para {change_id}"
        )

    return matches[0] if matches else None


def command_next() -> dict:
    result = next_issue(
        email=_required(
            "LINEAR_QUEUE_ASSIGNEE_EMAIL"
        ),
        milestone=_required(
            "LINEAR_QUEUE_MILESTONE"
        ),
    )

    if result["status"] == "ticket":
        existing = _existing_branch(
            result["change_id"]
        )

        if existing:
            result["branch_name"] = existing

    return result


def command_start(ticket_id: str) -> dict:
    issue = start_issue(ticket_id)

    return {
        "status": "started",
        "ticket_id": issue["identifier"],
        "linear_state": issue["state"]["name"],
    }


def run():
    import argparse

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser("next")

    start = subparsers.add_parser("start")
    start.add_argument("ticket_id")

    args = parser.parse_args()

    try:
        if args.command == "next":
            result = command_next()
        else:
            result = command_start(
                args.ticket_id
            )

    except ValueError as error:
        result = {
            "status": "blocked",
            "reason": str(error),
        }

    except Exception as error:
        result = {
            "status": "retry",
            "reason": str(error),
        }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    run()
