import os
import re
import unicodedata
from typing import Any

import requests


LINEAR_URL = "https://api.linear.app/graphql"


def _required(name: str) -> str:
    value = os.environ.get(name)

    if not value:
        raise ValueError(f"Falta {name}")

    return value


def _graphql(
    query: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = requests.post(
        LINEAR_URL,
        json={
            "query": query,
            "variables": variables or {},
        },
        headers={
            "Authorization": _required("LINEAR_API_KEY"),
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    if payload.get("errors"):
        messages = "; ".join(
            error.get("message", "Error desconocido")
            for error in payload["errors"]
        )

        raise RuntimeError(
            f"Linear GraphQL: {messages}"
        )

    return payload["data"]


def normalize_ticket(ticket_id: str) -> str:
    ticket_id = ticket_id.strip().upper()

    if not re.fullmatch(
        r"[A-Z][A-Z0-9]*-\d+",
        ticket_id,
    ):
        raise ValueError(
            "Ticket inválido. Ejemplo: DEV-5"
        )

    return ticket_id


def get_issue(ticket_id: str) -> dict[str, Any]:
    ticket_id = normalize_ticket(ticket_id)

    query = """
    query Issue($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        description
        priority
        priorityLabel

        state {
          id
          name
          type
        }

        team {
          id
          key
          name
        }

        project {
          id
          name
        }

        projectMilestone {
          id
          name
        }

        labels {
          nodes {
            name
          }
        }
      }
    }
    """

    issue = _graphql(
        query,
        {"id": ticket_id},
    ).get("issue")

    if not issue:
        raise RuntimeError(
            f"No existe el ticket {ticket_id}"
        )

    _validate_scope(issue)

    return issue


def _validate_scope(issue: dict[str, Any]) -> None:
    team_key = os.environ.get(
        "LINEAR_TEAM_KEY",
        "DEV",
    )

    project_name = os.environ.get(
        "LINEAR_PROJECT_NAME",
        "koty-app",
    )

    if (issue.get("team") or {}).get("key") != team_key:
        raise RuntimeError(
            f"El ticket no pertenece al team {team_key}"
        )

    if (
        (issue.get("project") or {}).get("name")
        != project_name
    ):
        raise RuntimeError(
            f"El ticket no pertenece a {project_name}"
        )


def _assigned_issues(
    email: str,
    only_unblocked: bool = False,
) -> list[dict[str, Any]]:
    blocked_filter = (
        "hasBlockedByRelations: { eq: false }"
        if only_unblocked
        else ""
    )

    query = f"""
    query Issues(
      $email: String!,
      $after: String
    ) {{
      issues(
        first: 50,
        after: $after,
        filter: {{
          assignee: {{
            email: {{ eq: $email }}
          }}
          {blocked_filter}
        }}
      ) {{
        nodes {{
          id
          identifier
          title
          priority

          state {{
            name
            type
          }}

          team {{
            key
          }}

          project {{
            name
          }}

          projectMilestone {{
            name
          }}

          labels {{
            nodes {{
              name
            }}
          }}
        }}

        pageInfo {{
          hasNextPage
          endCursor
        }}
      }}
    }}
    """

    result: list[dict[str, Any]] = []
    cursor = None

    while True:
        connection = _graphql(
            query,
            {
                "email": email,
                "after": cursor,
            },
        )["issues"]

        result.extend(connection["nodes"])

        page_info = connection["pageInfo"]

        if not page_info["hasNextPage"]:
            break

        cursor = page_info["endCursor"]

    return result


def _matches_queue(
    issue: dict[str, Any],
    milestone: str,
) -> bool:
    state_type = (
        issue.get("state") or {}
    ).get("type")

    return (
        (issue.get("team") or {}).get("key")
        == os.environ.get("LINEAR_TEAM_KEY", "DEV")
        and
        (issue.get("project") or {}).get("name")
        == os.environ.get(
            "LINEAR_PROJECT_NAME",
            "koty-app",
        )
        and
        (issue.get("projectMilestone") or {}).get("name")
        == milestone
        and state_type
        in {
            "backlog",
            "unstarted",
            "started",
        }
    )


def _priority(issue: dict[str, Any]) -> tuple[int, int]:
    priority = issue.get("priority") or 99

    number = int(
        issue["identifier"].rsplit("-", 1)[1]
    )

    return priority, number


def _slug(value: str) -> str:
    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = (
        value
        .encode("ascii", "ignore")
        .decode()
    )

    value = re.sub(
        r"[^a-zA-Z0-9]+",
        "-",
        value,
    )

    return value.strip("-").lower()[:50]


def _branch_type(issue: dict[str, Any]) -> str:
    labels = {
        node["name"].casefold()
        for node
        in issue.get("labels", {}).get("nodes", [])
    }

    mapping = {
        "bug": "fix",
        "fix": "fix",
        "documentation": "docs",
        "docs": "docs",
        "refactor": "refactor",
        "test": "test",
        "chore": "chore",
        "build": "build",
        "ci": "ci",
    }

    for label, branch_type in mapping.items():
        if label in labels:
            return branch_type

    return "feat"


def _ticket_result(
    issue: dict[str, Any],
) -> dict[str, Any]:
    ticket_id = issue["identifier"].upper()
    change_id = ticket_id.lower()

    return {
        "status": "ticket",
        "ticket_id": ticket_id,
        "change_id": change_id,
        "title": issue["title"],
        "branch_name": (
            f"{_branch_type(issue)}/"
            f"{change_id}-"
            f"{_slug(issue['title'])}"
        ),
    }


def next_issue(
    email: str,
    milestone: str,
) -> dict[str, Any]:
    all_issues = [
        issue
        for issue in _assigned_issues(email)
        if _matches_queue(issue, milestone)
    ]

    if not all_issues:
        return {
            "status": "empty",
        }

    unblocked_ids = {
        issue["id"]
        for issue in _assigned_issues(
            email,
            only_unblocked=True,
        )
    }

    started = [
        issue
        for issue in all_issues
        if issue["state"]["type"] == "started"
    ]

    if started:
        issue = sorted(
            started,
            key=_priority,
        )[0]

        if issue["id"] not in unblocked_ids:
            return {
                "status": "blocked",
                "ticket_id": issue["identifier"],
                "reason": (
                    f"{issue['identifier']} "
                    "está bloqueado por otro ticket"
                ),
            }

        return _ticket_result(issue)

    candidates = [
        issue
        for issue in all_issues
        if issue["id"] in unblocked_ids
    ]

    if not candidates:
        return {
            "status": "blocked",
            "reason": (
                "Todos los tickets pendientes "
                "del hito están bloqueados"
            ),
        }

    issue = sorted(
        candidates,
        key=_priority,
    )[0]

    return _ticket_result(issue)


def _change_state(
    ticket_id: str,
    target_name: str,
    allowed_types: set[str],
) -> dict[str, Any]:
    issue = get_issue(ticket_id)

    current = issue["state"]

    if current["name"] == target_name:
        return issue

    if current["type"] not in allowed_types:
        raise RuntimeError(
            f"{ticket_id} está en '{current['name']}'"
        )

    query = """
    query States($teamId: String!) {
      team(id: $teamId) {
        states {
          nodes {
            id
            name
          }
        }
      }
    }
    """

    states = _graphql(
        query,
        {"teamId": issue["team"]["id"]},
    )["team"]["states"]["nodes"]

    target = next(
        (
            state
            for state in states
            if state["name"] == target_name
        ),
        None,
    )

    if not target:
        raise RuntimeError(
            f"No existe el estado '{target_name}'"
        )

    mutation = """
    mutation UpdateIssue(
      $id: String!,
      $stateId: String!
    ) {
      issueUpdate(
        id: $id,
        input: {
          stateId: $stateId
        }
      ) {
        success
      }
    }
    """

    result = _graphql(
        mutation,
        {
            "id": issue["id"],
            "stateId": target["id"],
        },
    )["issueUpdate"]

    if not result["success"]:
        raise RuntimeError(
            f"Linear rechazó update de {ticket_id}"
        )

    updated = get_issue(ticket_id)

    if updated["state"]["name"] != target_name:
        raise RuntimeError(
            "Linear no confirmó el estado esperado"
        )

    return updated


def start_issue(ticket_id: str) -> dict[str, Any]:
    return _change_state(
        ticket_id,
        os.environ.get(
            "LINEAR_IN_PROGRESS_STATE",
            "In Progress",
        ),
        {
            "backlog",
            "unstarted",
            "started",
        },
    )


def complete_issue(ticket_id: str) -> dict[str, Any]:
    return _change_state(
        ticket_id,
        os.environ.get(
            "LINEAR_DONE_STATE",
            "Done",
        ),
        {
            "started",
            "completed",
        },
    )
