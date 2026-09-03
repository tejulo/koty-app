import json
from pathlib import Path

import crew.tools.custom_tool as tools


def test_command_output_is_bounded_and_full_evidence_is_retained(monkeypatch):
    full_output = "x" * 4_001
    recorded = []
    monkeypatch.setattr(tools, "_run", lambda *_args, **_kwargs: (1, full_output))
    monkeypatch.setattr(
        tools,
        "record_active_gate_execution",
        lambda *args: recorded.append(args) or "lint-evidence",
    )

    result = tools.ejecutar_verificacion.func("lint")

    assert len(result) <= 4_000
    assert result.endswith("Evidence: lint-evidence")
    assert recorded[0][-1] == full_output


def test_file_output_is_bounded_to_twelve_thousand_characters(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "PROJECT_ROOT", tmp_path)
    path = tmp_path / "large.txt"
    path.write_text("x" * 12_001, encoding="utf-8")

    result = tools.leer_archivo_raiz.func("large.txt")

    assert len(result) <= 12_000


def test_escribir_archivo_raiz_rejects_writes_outside_repair_scope(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("CREW_REPAIR_SCOPE", json.dumps(["openspec/changes/dev-40/specs"]))

    result = tools.escribir_archivo_raiz.func("apps/api/src/app.ts", "blocked")

    assert result == "Error: ruta fuera del repairScope"
    assert not (tmp_path / "apps/api/src/app.ts").exists()


def test_linear_output_is_bounded_and_references_full_evidence(monkeypatch):
    full_issue = {"description": "x" * 12_001}
    recorded = []
    monkeypatch.setenv("CREW_TICKET_ID", "DEV-40")
    monkeypatch.setattr(tools, "get_issue", lambda _: full_issue)
    monkeypatch.setattr(
        tools,
        "record_active_gate_execution",
        lambda *args: recorded.append(args) or "linear-evidence",
    )

    result = tools.buscar_tarea_linear.func()

    assert len(result.split("\n\nEvidence:")[0]) <= 12_000
    assert result.endswith("Evidence: linear-evidence")
    assert recorded[0][-1] == json.dumps(full_issue, ensure_ascii=False, indent=2)


def test_active_linear_evidence_reference_includes_the_full_output_path(monkeypatch):
    monkeypatch.setenv("CREW_TICKET_ID", "DEV-40")
    monkeypatch.setenv("CREW_VERIFICATION_CHANGE_ID", "dev-40")
    monkeypatch.setenv("CREW_VERIFICATION_ATTEMPT", "2")
    monkeypatch.setattr(tools, "get_issue", lambda _: {"description": "x" * 12_001})
    monkeypatch.setattr(tools, "record_active_gate_execution", lambda *_: "linear-evidence")
    monkeypatch.setattr(
        tools,
        "load_attempt_evidence",
        lambda *_: {"executions": [{"id": "linear-evidence", "outputPath": "openspec/changes/dev-40/attempts/2/linear.log"}]},
    )

    result = tools.buscar_tarea_linear.func()

    assert result.endswith("Evidence: linear-evidence (openspec/changes/dev-40/attempts/2/linear.log)")


def test_playwright_output_is_bounded_and_references_full_evidence(monkeypatch):
    full_output = "x" * 4_001
    recorded = []
    monkeypatch.setattr(tools.shutil, "which", lambda _: "/usr/bin/playwright-cli")
    monkeypatch.setattr(tools, "_run", lambda *_args, **_kwargs: (1, full_output))
    monkeypatch.setattr(
        tools,
        "record_active_gate_execution",
        lambda *args: recorded.append(args) or "playwright-evidence",
    )

    result = tools.ejecutar_playwright.func("snapshot")

    assert len(result) <= 4_000
    assert result.endswith("Evidence: playwright-evidence")
    assert recorded[0][-1] == full_output


def test_integration_bootstrap_output_is_bounded_and_references_full_evidence(monkeypatch):
    full_output = "x" * 4_001
    recorded = []
    monkeypatch.setattr(tools, "_run", lambda *_args, **_kwargs: (1, full_output))
    monkeypatch.setattr(
        tools,
        "record_active_gate_execution",
        lambda *args: recorded.append(args) or "integration-evidence",
    )

    result = tools.ejecutar_verificacion.func("integration")

    assert len(result) <= 4_000
    assert result.endswith("Evidence: integration-evidence")
    assert recorded[0][-1] == full_output
