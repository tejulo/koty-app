from pathlib import Path

import crew.finalizer as finalizer
from crew.models import CrewResult, VerificationResult


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
