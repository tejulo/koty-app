import json

import pytest

import crew.main as main_module
from crew.main import normalize
from crew.models import CrewResult, VerificationResult


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
