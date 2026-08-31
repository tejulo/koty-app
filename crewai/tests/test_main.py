import json
from types import SimpleNamespace

import pytest

import crew.main as main_module
from crew.main import normalize
from crew.models import CrewResult, VerificationResult


def crew_result(status="retryable_failure", failure_type="implementation"):
    return CrewResult(
        ticket_id="DEV-6",
        change_id="dev-6",
        status=status,
        failure_type=failure_type,
        failure_stage="runtime",
        summary="retry",
        verification=VerificationResult(
            python="skipped",
            lint="skipped",
            test="skipped",
            build="skipped",
            playwright="skipped",
            openspec="skipped",
        ),
    )


@pytest.mark.parametrize(
    ("raw_id", "expected"),
    [
        ("DEV-5", ("DEV-5", "dev-5")),
        (" dev-5 ", ("DEV-5", "dev-5")),
        ("Dev123-42", ("DEV123-42", "dev123-42")),
    ],
)
def test_normalize_accepts_valid_ticket_ids(raw_id, expected):
    assert normalize(raw_id) == expected


@pytest.mark.parametrize(
    "raw_id",
    ["", "   ", "DEV", "DEV-", "-5", "DEV 5", "DEV-5-extra"],
)
def test_normalize_rejects_invalid_ticket_ids(raw_id):
    with pytest.raises(ValueError):
        normalize(raw_id)


def test_save_attempt_records_structured_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)

    result = CrewResult(
        ticket_id="DEV-6",
        change_id="dev-6",
        status="retryable_failure",
        failure_type="test",
        failure_stage="verification",
        summary="tests failed",
        verification=VerificationResult(
            python="passed",
            lint="passed",
            test="failed",
            build="skipped",
            playwright="skipped",
            openspec="passed",
        ),
    )

    main_module.save_attempt("dev-6", 1, result)

    content = (change / "attempts" / "attempt-001.md").read_text(
        encoding="utf-8"
    )

    assert "# Attempt 1" in content
    assert "retryable_failure" in content
    assert "tests failed" in content
    assert '"test": "failed"' in content


def test_save_result_writes_valid_json(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)

    result = CrewResult(
        ticket_id="DEV-6",
        change_id="dev-6",
        status="blocked",
        failure_type="configuration",
        failure_stage="runtime",
        summary="Falta OPENCODE_API_KEY",
        verification=VerificationResult(
            python="skipped",
            lint="skipped",
            test="skipped",
            build="skipped",
            playwright="skipped",
            openspec="skipped",
        ),
    )

    main_module.save_result("dev-6", result)

    payload = json.loads((change / "result.json").read_text(encoding="utf-8"))

    assert payload["ticket_id"] == "DEV-6"
    assert payload["status"] == "blocked"


def test_run_ignores_historical_attempts_in_a_new_execution(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    attempts = change / "attempts"
    attempts.mkdir(parents=True)
    for number in range(1, 4):
        (attempts / f"attempt-{number:03}.md").touch()

    output = SimpleNamespace(pydantic=crew_result())
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    execution = json.loads(
        (
            tmp_path / ".agent" / "crew" / "dev-6" / "execution.json"
        ).read_text(encoding="utf-8")
    )
    assert execution == {
        "number": 1,
        "attempts": 1,
        "infrastructure_attempts": 0,
        "last_failure_type": "implementation",
    }


def test_resume_starts_a_new_execution(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)
    execution_path = (
        tmp_path / ".agent" / "crew" / "dev-6" / "execution.json"
    )
    execution_path.parent.mkdir(parents=True)
    execution_path.write_text(
        '{"number": 1, "attempts": 3}', encoding="utf-8"
    )

    output = SimpleNamespace(pydantic=crew_result())
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(
        main_module.sys, "argv", ["run_crew", "DEV-6", "--resume"]
    )

    main_module.run()

    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    assert execution == {
        "number": 2,
        "attempts": 1,
        "infrastructure_attempts": 0,
        "last_failure_type": "implementation",
    }


def test_resume_starts_first_execution_without_existing_state(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)

    output = SimpleNamespace(pydantic=crew_result())
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(
        main_module.sys, "argv", ["run_crew", "DEV-6", "--resume"]
    )

    main_module.run()

    execution = json.loads(
        (
            tmp_path / ".agent" / "crew" / "dev-6" / "execution.json"
        ).read_text(encoding="utf-8")
    )
    assert execution["number"] == 1


def test_parse_crew_result_accepts_json_after_reasoning():
    raw = '<think>reasoning</think>\n' + crew_result().model_dump_json()

    result = main_module.parse_crew_result(
        SimpleNamespace(pydantic=None, raw=raw)
    )

    assert result == crew_result()


def test_parse_crew_result_skips_json_inside_reasoning():
    raw = '<think>{"step":"review"}</think>\n' + crew_result().model_dump_json()

    result = main_module.parse_crew_result(
        SimpleNamespace(pydantic=None, raw=raw)
    )

    assert result == crew_result()


def test_parse_crew_result_normalizes_reviewer_check_details():
    payload = crew_result().model_dump()
    payload["verification"] = {
        "python": "passed (exit 0)",
        "lint": "passed (exit 0)",
        "test": "passed (62/62)",
        "build": "passed (exit 0)",
        "playwright": "not_required by design.md",
        "openspec_validate_strict": "passed (exit 0)",
    }

    result = main_module.parse_crew_result(
        SimpleNamespace(pydantic=None, raw=json.dumps(payload))
    )

    assert result.verification == VerificationResult(
        python="passed",
        lint="passed",
        test="passed",
        build="passed",
        playwright="skipped",
        openspec="passed",
    )


def test_run_accepts_raw_reviewer_result_after_reasoning(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    raw = '<think>{"step":"review"}</think>\n' + crew_result().model_dump_json()
    output = SimpleNamespace(pydantic=None, raw=raw)
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    payload = json.loads(
        (tmp_path / "openspec" / "changes" / "dev-6" / "result.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload == crew_result().model_dump()


def test_runtime_failure_returns_infrastructure_result():
    result = main_module.runtime_failure(
        "DEV-6", "dev-6", RuntimeError("invalid output")
    )

    assert result.status == "retryable_failure"
    assert result.failure_type == "infrastructure"


def test_run_writes_runtime_failure_to_stderr(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)

    def kickoff(**_):
        raise RuntimeError("provider returned invalid output")

    crew = SimpleNamespace(crew=lambda: SimpleNamespace(kickoff=kickoff))
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    assert "provider returned invalid output" in capsys.readouterr().err


def test_run_keeps_infrastructure_attempts_separate(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)
    execution_path = (
        tmp_path / ".agent" / "crew" / "dev-6" / "execution.json"
    )
    execution_path.parent.mkdir(parents=True)
    execution_path.write_text(
        """{
  "number": 1,
  "attempts": 3,
  "infrastructure_attempts": 1,
  "last_failure_type": "infrastructure"
}""",
        encoding="utf-8",
    )

    output = SimpleNamespace(
        pydantic=crew_result(failure_type="infrastructure")
    )
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    assert execution == {
        "number": 1,
        "attempts": 3,
        "infrastructure_attempts": 2,
        "last_failure_type": "infrastructure",
    }
