from pathlib import Path

import crew.gates as gates


def test_run_openspec_gate_records_canonical_validation(monkeypatch, tmp_path):
    recorded = {}

    def run(command, *_args, **_):
        recorded["command"] = command
        return 0, "Change 'dev-8' is valid"

    monkeypatch.setattr(gates, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(gates, "CREWAI_ROOT", tmp_path / "crewai")
    monkeypatch.setattr(gates, "_run", run)
    monkeypatch.setattr(
        gates,
        "record_active_gate_execution",
        lambda *args: recorded.setdefault("evidence", "openspec-evidence"),
    )

    result = gates.run_gate("openspec", "dev-8")

    assert result.passed is True
    assert result.evidence_id == "openspec-evidence"
    assert recorded["command"] == [
        "pnpm",
        "exec",
        "openspec",
        "validate",
        "dev-8",
        "--strict",
        "--no-interactive",
    ]


def test_diagnose_openspec_delta_failure_gives_a_repair_hint():
    diagnosis = gates.diagnose_gate_failure(
        "openspec",
        "No delta sections found. Add headers such as \"## ADDED Requirements\".",
    )

    assert diagnosis["category"] == "openspec_delta_missing"
    assert diagnosis["repairHint"] == (
        "Agrega '## ADDED Requirements' antes de los Requirements del spec."
    )
    assert diagnosis["repairScope"] == ["openspec/changes/<change>/specs"]
