from pathlib import Path

import pytest

import crew.finalizer as finalizer
from crew.models import CrewResult, VerificationResult


def test_check_crew_result_rejects_missing_evidence():
    result = CrewResult(
        ticket_id="DEV-6",
        change_id="dev-6",
        attempt=1,
        status="approved",
        summary="approved",
        verification=VerificationResult(
            python="passed",
            lint="passed",
            test="passed",
            build="passed",
            integration="passed",
            playwright="skipped",
            openspec="passed",
        ),
    )

    with pytest.raises(RuntimeError, match="Evidencia inválida"):
        finalizer._check_crew_result("DEV-6", "dev-6", result, "not_required")


def test_finalize_archives_without_unsupported_json_flag(
    monkeypatch, tmp_path
):
    change = tmp_path / "dev-6"
    change.mkdir()
    (change / "tasks.md").write_text("- [x] completed\n", encoding="utf-8")
    (change / "design.md").write_text(
        "Browser E2E: not_required\n", encoding="utf-8"
    )
    (change / "result.json").write_text(
        CrewResult(
            ticket_id="DEV-6",
            change_id="dev-6",
            status="approved",
            summary="approved",
            verification=VerificationResult(
                python="passed",
                lint="passed",
                test="passed",
                build="passed",
                integration="passed",
                playwright="skipped",
                openspec="passed",
            ),
        ).model_dump_json(),
        encoding="utf-8",
    )

    commands = []
    checks = iter([(change, False), (change, True)])
    monkeypatch.setattr(finalizer, "_find_change", lambda _: next(checks))
    monkeypatch.setattr(finalizer, "_check_branch", lambda _: None)
    monkeypatch.setattr(finalizer, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(finalizer, "_run_code_gates", lambda: None)
    monkeypatch.setattr(finalizer, "complete_issue", lambda _: None)
    monkeypatch.setattr(finalizer, "_commit", lambda _: None)

    def run(command, cwd=Path("."), timeout=600):
        commands.append(command)
        return ""

    monkeypatch.setattr(finalizer, "_run", run)

    assert finalizer.finalize("DEV-6")["status"] == "done"
    assert [
        "pnpm",
        "exec",
        "openspec",
        "archive",
        "dev-6",
        "--yes",
    ] in commands


def test_run_code_gates_starts_database_before_integration_test(monkeypatch):
    commands = []

    monkeypatch.setattr(
        finalizer,
        "_run",
        lambda command, **_: commands.append(command) or "",
    )

    finalizer._run_code_gates()

    assert commands[-2:] == [
        ["pnpm", "db:start"],
        ["pnpm", "--filter", "@koty-app/api", "test:integration"],
    ]


def test_finalize_reports_a_blocked_crew_result(tmp_path, monkeypatch):
    change = tmp_path / "dev-6"
    change.mkdir()
    (change / "result.json").write_text(
        CrewResult(
            ticket_id="DEV-6",
            change_id="dev-6",
            status="blocked",
            failure_type="configuration",
            summary="Docker unavailable",
            verification=VerificationResult(
                python="skipped",
                lint="skipped",
                test="skipped",
                build="skipped",
                integration="skipped",
                playwright="skipped",
                openspec="skipped",
            ),
        ).model_dump_json(),
        encoding="utf-8",
    )
    monkeypatch.setattr(finalizer, "_find_change", lambda _: (change, False))

    result = finalizer.finalize("DEV-6")

    assert result["status"] == "blocked"
    assert result["reason"] == "blocked"


def test_commit_excludes_runtime_artifacts(monkeypatch):
    commands = []
    monkeypatch.setattr(finalizer, "_current_branch", lambda: "feat/dev-6")
    monkeypatch.setattr(finalizer, "get_issue", lambda _: {"title": "Title"})
    monkeypatch.setattr(
        finalizer,
        "_run",
        lambda command, **_: commands.append(command) or "M crewai/src/crew/main.py\n?? .agent/crew/dev-6/\n",
    )

    finalizer._commit("DEV-6")

    assert ["git", "add", "--all", "--", ".", ":(exclude).agent"] in commands


def test_commit_rejects_previously_staged_runtime_artifacts(monkeypatch):
    monkeypatch.setattr(finalizer, "_current_branch", lambda: "feat/dev-6")
    monkeypatch.setattr(
        finalizer,
        "_run",
        lambda command, **_: ".agent/crew/dev-6/execution.json"
        if command[:3] == ["git", "diff", "--cached"]
        else "M crewai/src/crew/main.py",
    )

    with pytest.raises(RuntimeError, match="runtime"):
        finalizer._commit("DEV-6")


def test_finalizer_failure_uses_finalization_diagnostics_path(tmp_path):
    change = tmp_path / "dev-6"
    change.mkdir()

    finalizer._write_failure(
        change,
        "verification",
        RuntimeError("gate failed"),
    )

    assert list((change / "attempts").glob("attempt-*.md")) == []
    diagnostics = list((change / "finalization").glob("finalizer-*.md"))
    assert len(diagnostics) == 1
    assert "gate failed" in diagnostics[0].read_text(encoding="utf-8")
