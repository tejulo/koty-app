import hashlib
from types import SimpleNamespace

import crew.evidence as evidence


def test_diagnose_integration_failure_classifies_nest_metadata():
    output = (
        "NEST_DI_METADATA_MISSING: AuditController, "
        "OutboxEchoController\n"
        'Datasource "db": PostgreSQL database "plandepo_test_abc123"'
    )

    diagnosis = evidence.diagnose_integration_failure(output)

    assert diagnosis["category"] == "shared_test_harness"
    assert diagnosis["affected"] == [
        "AuditController",
        "OutboxEchoController",
    ]
    assert diagnosis["repairScope"] == [
        "apps/api/vitest.config.integration.ts",
        "apps/api/package.json",
        "pnpm-lock.yaml",
    ]


def test_diagnose_integration_failure_uses_stable_fingerprint():
    first = evidence.diagnose_integration_failure(
        "NEST_DI_METADATA_MISSING: AuditController\n"
        "plandepo_test_aaa111"
    )
    second = evidence.diagnose_integration_failure(
        "NEST_DI_METADATA_MISSING: AuditController\n"
        "plandepo_test_bbb222"
    )

    assert first["fingerprint"] == second["fingerprint"]


def test_save_integration_diagnosis_writes_attempt_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "PROJECT_ROOT", tmp_path)
    diagnosis = evidence.diagnose_integration_failure(
        "NEST_DI_METADATA_MISSING: AuditController"
    )

    path = evidence.save_integration_diagnosis("dev-6", 2, diagnosis)

    assert path.relative_to(tmp_path).as_posix() == (
        "openspec/changes/dev-6/attempts/"
        "attempt-002.integration-diagnosis.json"
    )
    assert path.read_text(encoding="utf-8")


def test_record_gate_execution_persists_lint_diagnostic(tmp_path, monkeypatch):
    source = tmp_path / "apps/api/src/example.ts"
    source.parent.mkdir(parents=True)
    source.write_text("const value = null;\n", encoding="utf-8")
    monkeypatch.setattr(evidence, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("CREW_VERIFICATION_CHANGE_ID", "dev-6")
    monkeypatch.setenv("CREW_VERIFICATION_ATTEMPT", "1")

    execution_id = evidence.record_gate_execution(
        "lint",
        ["pnpm", "lint"],
        tmp_path,
        1,
        f"{source}\n  1:7  error  Unexpected null  no-null\n",
    )

    run = evidence.load_attempt_evidence("dev-6", 1)["executions"][0]

    assert run["id"] == execution_id
    assert run["exitCode"] == 1
    assert run["diagnostics"] == [
        {
            "path": "apps/api/src/example.ts",
            "line": 1,
            "column": 7,
            "rule": "no-null",
            "fileSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    ]


def test_reviewer_evidence_rejects_a_pass_claim_for_failed_lint(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(evidence, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("CREW_VERIFICATION_CHANGE_ID", "dev-6")
    monkeypatch.setenv("CREW_VERIFICATION_ATTEMPT", "1")
    evidence_ids = {
        gate: evidence.record_gate_execution(
            gate, [gate], tmp_path, 1 if gate == "lint" else 0, ""
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
    result = SimpleNamespace(
        attempt=1,
        evidence=evidence_ids,
        verification=SimpleNamespace(
            python="passed",
            lint="passed",
            test="passed",
            build="passed",
            integration="passed",
            openspec="passed",
        ),
    )

    assert "lint" in evidence.validate_reviewer_evidence("dev-6", result)


def test_reviewer_evidence_rejects_stale_lint_diagnostic(tmp_path, monkeypatch):
    source = tmp_path / "apps/api/src/example.ts"
    source.parent.mkdir(parents=True)
    source.write_text("const value = null;\n", encoding="utf-8")
    monkeypatch.setattr(evidence, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("CREW_VERIFICATION_CHANGE_ID", "dev-6")
    monkeypatch.setenv("CREW_VERIFICATION_ATTEMPT", "1")
    evidence_ids = {
        gate: evidence.record_gate_execution(
            gate,
            [gate],
            tmp_path,
            1 if gate == "lint" else 0,
            f"{source}\n  1:7  error  Unexpected null  no-null\n"
            if gate == "lint"
            else "",
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
    source.write_text("const value = 1;\n", encoding="utf-8")
    result = SimpleNamespace(
        attempt=1,
        evidence=evidence_ids,
        verification=SimpleNamespace(
            python="passed",
            lint="failed",
            test="passed",
            build="passed",
            integration="passed",
            openspec="passed",
        ),
    )

    assert "obsoleta" in evidence.validate_reviewer_evidence("dev-6", result)


def test_reviewer_evidence_rejects_a_different_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("CREW_VERIFICATION_CHANGE_ID", "dev-6")
    monkeypatch.setenv("CREW_VERIFICATION_ATTEMPT", "1")
    evidence_ids = {
        gate: evidence.record_gate_execution(gate, [gate], tmp_path, 0, "")
        for gate in (
            "python",
            "lint",
            "test",
            "build",
            "integration",
            "openspec",
        )
    }
    result = SimpleNamespace(
        attempt=1,
        evidence=evidence_ids,
        verification=SimpleNamespace(
            python="passed",
            lint="passed",
            test="passed",
            build="passed",
            integration="passed",
            openspec="passed",
        ),
    )

    assert "intento actual" in evidence.validate_reviewer_evidence(
        "dev-6", result, expected_attempt=2
    )
