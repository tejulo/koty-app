import json
import os
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import crew.evidence as evidence_module
import crew.main as main_module
from crew.main import normalize
from crew.models import (
    CrewResult,
    ReviewVerdict,
    TesterResult as BrowserTesterResult,
    VerificationResult,
)


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
            integration="skipped",
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


def test_crew_result_keeps_attempt_and_evidence():
    result = CrewResult(
        ticket_id="DEV-6",
        change_id="dev-6",
        attempt=2,
        evidence={"lint": "evidence-1"},
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

    assert result.attempt == 2
    assert result.evidence == {"lint": "evidence-1"}


def test_verification_result_requires_integration_status():
    with pytest.raises(ValidationError, match="integration"):
        VerificationResult(
            python="passed",
            lint="passed",
            test="passed",
            build="passed",
            playwright="skipped",
            openspec="passed",
        )


def test_execution_attempts_uses_stable_default_budgets(monkeypatch):
    monkeypatch.delenv("MAX_TICKET_ATTEMPTS", raising=False)
    monkeypatch.delenv("MAX_INFRASTRUCTURE_ATTEMPTS", raising=False)

    ticket_attempts = main_module.execution_attempts(
        main_module.CrewExecution()
    )
    infrastructure_attempts = main_module.execution_attempts(
        main_module.CrewExecution(last_failure_type="infrastructure")
    )

    assert ticket_attempts == (0, 3)
    assert infrastructure_attempts == (0, 2)


def test_apply_failure_accounting_grants_one_shared_repair_credit():
    execution = main_module.CrewExecution()
    diagnosis = {
        "category": "shared_test_harness",
        "fingerprint": "metadata-missing",
    }

    main_module.apply_failure_accounting(
        execution,
        crew_result(),
        diagnosis,
    )

    assert execution.attempts == 0
    assert execution.diagnostic_repair_attempts == 1
    assert execution.diagnosed_fingerprints == ["metadata-missing"]

    main_module.apply_failure_accounting(
        execution,
        crew_result(),
        diagnosis,
    )

    assert execution.attempts == 1
    assert execution.diagnostic_repair_attempts == 1


def test_apply_failure_accounting_has_a_fixed_single_shared_repair_credit(
    monkeypatch,
):
    monkeypatch.setenv("MAX_DIAGNOSTIC_REPAIR_ATTEMPTS", "2")
    execution = main_module.CrewExecution()

    main_module.apply_failure_accounting(
        execution,
        crew_result(),
        {"category": "shared_test_harness", "fingerprint": "first"},
    )
    main_module.apply_failure_accounting(
        execution,
        crew_result(),
        {"category": "shared_test_harness", "fingerprint": "second"},
    )

    assert execution.diagnostic_repair_attempts == 1
    assert execution.attempts == 1


def test_run_records_shared_integration_diagnosis_without_charging_ticket(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(evidence_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)

    def kickoff(**_):
        evidence_id = evidence_module.record_gate_execution(
            "integration",
            ["pnpm", "test:integration"],
            tmp_path,
            1,
            "NEST_DI_METADATA_MISSING: AuditController",
        )
        result = crew_result()
        result.evidence = {}
        result.verification = VerificationResult(
            python="skipped",
            lint="skipped",
            test="skipped",
            build="skipped",
            integration="skipped",
            playwright="skipped",
            openspec="skipped",
        )
        return SimpleNamespace(pydantic=result)

    crew = SimpleNamespace(crew=lambda: SimpleNamespace(kickoff=kickoff))
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    execution = main_module.load_execution("dev-6")
    assert execution.attempts == 0
    assert execution.diagnostic_repair_attempts == 1
    assert execution.last_diagnosis_path == (
        "openspec/changes/dev-6/attempts/"
        "attempt-001.integration-diagnosis.json"
    )


def test_diagnose_result_links_the_failed_gate_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(evidence_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("CREW_VERIFICATION_CHANGE_ID", "dev-6")
    monkeypatch.setenv("CREW_VERIFICATION_ATTEMPT", "1")
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    evidence_id = evidence_module.record_gate_execution(
        "openspec",
        ["pnpm", "exec", "openspec", "validate"],
        tmp_path,
        1,
        "No delta sections found",
    )

    diagnosis, path = main_module.diagnose_result("dev-6", 1, crew_result())

    assert diagnosis["evidence"] == {
        "id": evidence_id,
        "gate": "openspec",
        "outputPath": next(
            item["outputPath"]
            for item in main_module.load_attempt_evidence("dev-6", 1)["executions"]
        ),
    }
    assert json.loads((tmp_path / path).read_text(encoding="utf-8"))["evidence"] == (
        diagnosis["evidence"]
    )


def test_diagnose_result_records_reviewer_feedback_without_failed_gate(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    result = crew_result(status="retryable_failure", failure_type="implementation")
    result.summary = "Falta cubrir el escenario de mora."

    diagnosis, path = main_module.diagnose_result("dev-6", 1, result)

    assert diagnosis["category"] == "reviewer_feedback"
    assert diagnosis["repairHint"] == result.summary
    assert json.loads((tmp_path / path).read_text(encoding="utf-8"))["repairScope"] == []


def test_run_passes_last_repair_diagnosis_to_crew(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    execution_path = tmp_path / ".agent" / "crew" / "dev-6" / "execution.json"
    execution_path.parent.mkdir(parents=True)
    execution_path.write_text(
        '{"last_diagnosis_path":"attempts/attempt-001.repair-diagnosis.json"}',
        encoding="utf-8",
    )
    diagnosis_path = tmp_path / "attempts" / "attempt-001.repair-diagnosis.json"
    diagnosis_path.parent.mkdir()
    diagnosis_path.write_text(
        '{"repairScope":["openspec/changes/<change>/specs"]}',
        encoding="utf-8",
    )
    seen = {}

    def kickoff(**kwargs):
        seen.update(kwargs["inputs"])
        seen["repair_scope"] = os.environ.get("CREW_REPAIR_SCOPE")
        return SimpleNamespace(
            pydantic=crew_result(status="approved", failure_type="none")
        )

    crew = SimpleNamespace(crew=lambda: SimpleNamespace(kickoff=kickoff))
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    assert seen["last_repair_diagnosis_path"] == (
        "attempts/attempt-001.repair-diagnosis.json"
    )
    assert seen["repair_scope"] == '["openspec/changes/dev-6/specs"]'
    assert main_module.load_execution("dev-6").last_diagnosis_path is None


def test_run_clears_last_integration_diagnosis_after_approval(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)
    execution_path = tmp_path / ".agent" / "crew" / "dev-6" / "execution.json"
    execution_path.parent.mkdir(parents=True)
    execution_path.write_text(
        '{"last_diagnosis_path":"attempts/attempt-001.integration-diagnosis.json"}',
        encoding="utf-8",
    )
    approved = ReviewVerdict(
        ticket_id="DEV-6",
        change_id="dev-6",
        status="approved",
        summary="approved",
    )
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(
            kickoff=lambda **_: SimpleNamespace(
                pydantic=crew_result(status="approved", failure_type="none")
            )
        )
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    assert main_module.load_execution("dev-6").last_diagnosis_path is None


def test_reserve_attempt_persists_after_an_approved_run(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    execution = main_module.CrewExecution(last_attempt=1)

    attempt = main_module.reserve_attempt("dev-6", execution)

    assert attempt == 2
    assert execution.last_attempt == 2


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
            integration="skipped",
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
            integration="skipped",
            playwright="skipped",
            openspec="skipped",
        ),
    )

    main_module.save_result("dev-6", result)

    payload = json.loads((change / "result.json").read_text(encoding="utf-8"))

    assert payload["ticket_id"] == "DEV-6"
    assert payload["status"] == "blocked"


def test_save_result_publishes_with_atomic_replace(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    replaced = []
    original_replace = main_module.os.replace
    monkeypatch.setattr(
        main_module.os,
        "replace",
        lambda source, target: replaced.append((source, target)) or original_replace(source, target),
    )

    main_module.save_result("dev-6", crew_result())

    assert len(replaced) == 1
    assert replaced[0][1].name == "result.json"


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
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
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
        "last_attempt": 4,
        "attempts": 1,
        "infrastructure_attempts": 0,
        "diagnostic_repair_attempts": 0,
        "diagnosed_fingerprints": [],
            "last_diagnosis_path": (
                "openspec/changes/dev-6/attempts/"
                "attempt-004.repair-diagnosis.json"
            ),
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
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(
        main_module.sys, "argv", ["run_crew", "DEV-6", "--resume"]
    )

    main_module.run()

    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    assert execution == {
        "number": 2,
        "last_attempt": 1,
        "attempts": 1,
        "infrastructure_attempts": 0,
        "diagnostic_repair_attempts": 0,
        "diagnosed_fingerprints": [],
        "last_diagnosis_path": (
            "openspec/changes/dev-6/attempts/"
            "attempt-001.repair-diagnosis.json"
        ),
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
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
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
        "integration": "passed (exit 0)",
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
        integration="passed",
        playwright="skipped",
        openspec="passed",
    )


def test_parse_review_verdict_accepts_structured_reviewer_output():
    verdict = ReviewVerdict(
        ticket_id="DEV-6",
        change_id="dev-6",
        status="approved",
        summary="reviewed",
    )

    result = main_module.parse_review_verdict(SimpleNamespace(pydantic=verdict))

    assert result == verdict


def test_review_verdict_accepts_the_documented_max_attempts_type():
    verdict = ReviewVerdict(
        ticket_id="DEV-6",
        change_id="dev-6",
        status="blocked",
        failure_type="max_attempts",
        summary="No quedan intentos.",
    )

    assert verdict.failure_type == "max_attempts"


def test_required_browser_e2e_failure_overrides_reviewer_approval(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)
    (change / "design.md").write_text("Browser E2E: required", encoding="utf-8")
    result = crew_result(status="approved", failure_type="none")
    output = SimpleNamespace(
        tasks_output=[
            SimpleNamespace(
                pydantic=BrowserTesterResult(
                    status="failed",
                    summary="El escenario de acceso falla.",
                )
            )
        ]
    )

    checked = main_module.apply_tester_result("dev-6", output, result)

    assert checked.status == "retryable_failure"
    assert checked.failure_stage == "playwright"
    assert checked.verification.playwright == "failed"


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
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    payload = json.loads(
        (tmp_path / "openspec" / "changes" / "dev-6" / "result.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload == {
        **crew_result().model_dump(),
        "attempt": 1,
    }


def test_run_validates_evidence_from_raw_reviewer_result(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(evidence_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)

    def kickoff(**_):
        evidence_ids = {
            gate: evidence_module.record_gate_execution(
                gate,
                [gate],
                tmp_path,
                0,
                "",
            )
            for gate in (
                "python",
                "lint",
                "test",
                "build",
                "integration",
                "openspec",
            )
        }
        result = crew_result(status="approved", failure_type="none")
        result.attempt = 1
        result.evidence = evidence_ids
        result.verification = VerificationResult(
            python="passed",
            lint="passed",
            test="passed",
            build="passed",
            integration="passed",
            playwright="skipped",
            openspec="passed",
        )
        return SimpleNamespace(pydantic=None, raw=result.model_dump_json())

    crew = SimpleNamespace(crew=lambda: SimpleNamespace(kickoff=kickoff))
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    payload = json.loads((change / "result.json").read_text(encoding="utf-8"))

    assert payload["status"] == "approved"


def test_run_blocks_reviewer_result_that_contradicts_evidence(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(evidence_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)
    monkeypatch.setenv("CREW_VERIFICATION_CHANGE_ID", "dev-6")
    monkeypatch.setenv("CREW_VERIFICATION_ATTEMPT", "1")
    evidence_ids = {
        gate: evidence_module.record_gate_execution(
            gate, [gate], tmp_path, 1 if gate == "lint" else 0, ""
        )
        for gate in ("python", "lint", "test", "build", "openspec")
    }
    result = crew_result(status="approved")
    result.attempt = 1
    result.evidence = evidence_ids
    result.verification = VerificationResult(
        python="passed",
        lint="passed",
        test="passed",
        build="passed",
        integration="passed",
        playwright="skipped",
        openspec="passed",
    )
    output = SimpleNamespace(pydantic=result)
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    payload = json.loads((change / "result.json").read_text(encoding="utf-8"))
    assert payload["status"] == "blocked"
    assert payload["failure_stage"] == "verification_evidence"


def test_run_exposes_current_attempt_to_verification_tools(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    seen = {}

    def kickoff(**_):
        seen["change"] = os.environ.get("CREW_VERIFICATION_CHANGE_ID")
        seen["attempt"] = os.environ.get("CREW_VERIFICATION_ATTEMPT")
        seen["ticket"] = os.environ.get("CREW_TICKET_ID")
        return SimpleNamespace(pydantic=crew_result())

    crew = SimpleNamespace(crew=lambda: SimpleNamespace(kickoff=kickoff))
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    assert seen == {
        "change": "dev-6",
        "attempt": "1",
        "ticket": "DEV-6",
    }


def test_run_stops_after_an_invalid_openspec_preflight(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(evidence_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    delivery_calls = []

    planning = SimpleNamespace(kickoff=lambda **_: SimpleNamespace(raw="planned"))
    delivery = SimpleNamespace(
        kickoff=lambda **_: delivery_calls.append(True) or SimpleNamespace(raw="reviewed")
    )
    crew = SimpleNamespace(
        planning_crew=lambda: planning,
        delivery_crew=lambda: delivery,
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(
        main_module,
        "run_gate",
        lambda name, _: SimpleNamespace(
            name=name,
            passed=False,
            evidence_id="openspec-failed",
            output="No delta sections found",
        ),
    )
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    payload = json.loads(
        (tmp_path / "openspec" / "changes" / "dev-6" / "result.json").read_text(
            encoding="utf-8"
        )
    )
    assert delivery_calls == []
    assert payload["status"] == "retryable_failure"
    assert payload["failure_stage"] == "openspec_preflight"
    diagnosis_path = (
        tmp_path
        / "openspec"
        / "changes"
        / "dev-6"
        / "attempts"
        / "attempt-001.repair-diagnosis.json"
    )
    assert json.loads(diagnosis_path.read_text(encoding="utf-8"))["category"] == (
        "openspec_delta_missing"
    )


def test_run_uses_supervisor_gate_evidence_after_delivery(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(evidence_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    approved = ReviewVerdict(
        ticket_id="DEV-6",
        change_id="dev-6",
        status="approved",
        summary="approved",
    )
    planning = SimpleNamespace(kickoff=lambda **_: SimpleNamespace(raw="planned"))
    delivery = SimpleNamespace(kickoff=lambda **_: SimpleNamespace(pydantic=approved))
    crew = SimpleNamespace(
        planning_crew=lambda: planning,
        delivery_crew=lambda: delivery,
    )
    calls = []
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(
        main_module,
        "run_gate",
        lambda name, _: calls.append(name)
        or SimpleNamespace(
            name=name,
            passed=True,
            evidence_id=f"{name}-evidence",
            output="passed",
        ),
    )
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    payload = json.loads(
        (tmp_path / "openspec" / "changes" / "dev-6" / "result.json").read_text(
            encoding="utf-8"
        )
    )
    assert calls == [
        "openspec",
        "python",
        "lint",
        "test",
        "build",
        "integration",
        "openspec",
    ]
    assert payload["status"] == "approved"
    assert payload["evidence"]["openspec"] == "openspec-evidence"


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
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    assert execution == {
        "number": 1,
        "last_attempt": 1,
        "attempts": 3,
        "infrastructure_attempts": 2,
        "diagnostic_repair_attempts": 0,
        "diagnosed_fingerprints": [],
            "last_diagnosis_path": (
                "openspec/changes/dev-6/attempts/"
                "attempt-001.repair-diagnosis.json"
            ),
        "last_failure_type": "infrastructure",
    }


def test_run_uses_runner_attempt_for_reviewer_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    result = crew_result(status="approved", failure_type="none")
    result.attempt = 999
    seen = {}
    output = SimpleNamespace(pydantic=result)
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(
        main_module,
        "validate_reviewer_evidence",
        lambda _, actual, expected: seen.update(
            actual=actual.attempt,
            expected=expected,
        ) or None,
    )
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    assert seen == {"actual": 1, "expected": 1}
    result_payload = json.loads(
        (tmp_path / "openspec" / "changes" / "dev-6" / "result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result_payload["attempt"] == 1


def test_run_does_not_charge_budgets_for_blocked_result(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)
    execution_path = tmp_path / ".agent" / "crew" / "dev-6" / "execution.json"
    execution_path.parent.mkdir(parents=True)
    execution_path.write_text(
        '{"number": 1, "attempts": 1, "infrastructure_attempts": 1, '
        '"last_failure_type": "infrastructure"}',
        encoding="utf-8",
    )
    output = SimpleNamespace(
        pydantic=crew_result(status="blocked", failure_type="configuration")
    )
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    assert execution == {
        "number": 1,
        "last_attempt": 1,
        "attempts": 1,
        "infrastructure_attempts": 1,
        "diagnostic_repair_attempts": 0,
        "diagnosed_fingerprints": [],
        "last_diagnosis_path": None,
        "last_failure_type": "infrastructure",
    }
    assert (change / "attempts" / "attempt-001.md").is_file()


def test_run_charges_ticket_budget_without_changing_infrastructure_budget(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    change = tmp_path / "openspec" / "changes" / "dev-6"
    change.mkdir(parents=True)
    execution_path = tmp_path / ".agent" / "crew" / "dev-6" / "execution.json"
    execution_path.parent.mkdir(parents=True)
    execution_path.write_text(
        '{"attempts": 1, "infrastructure_attempts": 1}', encoding="utf-8"
    )
    output = SimpleNamespace(pydantic=crew_result(failure_type="implementation"))
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "validate_reviewer_evidence", lambda *_: None)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    assert execution == {
        "number": 1,
        "last_attempt": 1,
        "attempts": 2,
        "infrastructure_attempts": 1,
        "diagnostic_repair_attempts": 0,
        "diagnosed_fingerprints": [],
        "last_diagnosis_path": (
            "openspec/changes/dev-6/attempts/"
            "attempt-001.repair-diagnosis.json"
        ),
        "last_failure_type": "implementation",
    }
