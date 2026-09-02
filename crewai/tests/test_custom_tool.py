import json
from pathlib import Path

import crew.tools.custom_tool as tools_module
from crewai.tools.tool_failure import ToolFailure


def test_buscar_tarea_linear_uses_the_injected_ticket(monkeypatch):
    monkeypatch.setenv("CREW_TICKET_ID", "DEV-6")
    monkeypatch.setattr(
        tools_module,
        "get_issue",
        lambda ticket_id: {
            "identifier": ticket_id,
            "title": "Preparar migraciones reproducibles con Prisma",
        },
    )

    result = tools_module.buscar_tarea_linear.func()

    assert '"identifier": "DEV-6"' in result
    assert "Preparar migraciones" in result


def test_buscar_tarea_linear_converts_errors_to_tool_failure(monkeypatch):
    monkeypatch.setenv("CREW_TICKET_ID", "DEV-6")

    def fail(_ticket_id):
        raise RuntimeError("Linear rechazó consulta")

    monkeypatch.setattr(tools_module, "get_issue", fail)

    result = tools_module.buscar_tarea_linear.func()

    assert isinstance(result, ToolFailure)
    assert result.code == "LINEAR_QUERY_FAILED"
    assert result.retryable is False


def test_ejecutar_openspec_rejects_mutating_commands(monkeypatch):
    calls = []
    monkeypatch.setattr(tools_module, "_run", lambda *args, **kwargs: calls.append(args))

    result = tools_module.ejecutar_openspec.func("archive dev-6 --yes")

    assert result == "Error: comando OpenSpec no permitido"
    assert calls == []


def test_ejecutar_openspec_runs_allowed_validation(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return 0, "Exit code: 0"

    monkeypatch.setattr(tools_module, "_run", run)

    result = tools_module.ejecutar_openspec.func(
        "validate dev-6 --strict --no-interactive"
    )

    assert result.startswith("ÉXITO OPENSPEC")
    assert calls[0][0] == [
        "pnpm",
        "exec",
        "openspec",
        "validate",
        "dev-6",
        "--strict",
        "--no-interactive",
    ]


def test_escribir_archivo_raiz_rejects_writes_outside_repair_scope(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(tools_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv(
        "CREW_REPAIR_SCOPE",
        json.dumps(["openspec/changes/dev-6/specs"]),
    )

    result = tools_module.escribir_archivo_raiz.func("apps/api/src/app.ts", "blocked")

    assert result == "Error: ruta fuera del repairScope"
    assert not (tmp_path / "apps" / "api" / "src" / "app.ts").exists()


def test_ejecutar_verificacion_dispatches_known_check(monkeypatch):
    calls = []

    def run(command, cwd=Path("."), **kwargs):
        calls.append((command, cwd))
        return 0, "Exit code: 0"

    monkeypatch.setattr(tools_module, "_run", run)

    result = tools_module.ejecutar_verificacion.func("python")

    assert result.startswith("VERIFICACIÓN EXITOSA: python")
    assert calls[0][0] == [
        "uv",
        "run",
        "python",
        "-m",
        "compileall",
        "-q",
        "src/crew",
    ]


def test_ejecutar_verificacion_runs_integration_after_database_bootstrap(
    monkeypatch,
):
    calls = []
    evidence = []

    def run(command, cwd=Path("."), **kwargs):
        calls.append((command, cwd))
        return 0, "Exit code: 0"

    monkeypatch.setattr(tools_module, "_run", run)
    monkeypatch.setattr(
        tools_module,
        "record_active_gate_execution",
        lambda *args: evidence.append(args) or "integration-evidence",
    )

    result = tools_module.ejecutar_verificacion.func("integration")

    assert result.endswith("Evidence: integration-evidence")
    assert [command for command, _ in calls] == [
        ["pnpm", "db:start"],
        ["pnpm", "--filter", "@koty-app/api", "test:integration"],
    ]
    assert evidence == [
        (
            "integration",
            ["pnpm", "--filter", "@koty-app/api", "test:integration"],
            tools_module.PROJECT_ROOT,
            0,
            "Exit code: 0",
        )
    ]


def test_ejecutar_verificacion_records_database_bootstrap_failure(
    monkeypatch,
):
    calls = []
    evidence = []

    def run(command, cwd=Path("."), **kwargs):
        calls.append((command, cwd))
        return 1, "Exit code: 1\nSTDERR:\nDocker unavailable"

    monkeypatch.setattr(tools_module, "_run", run)
    monkeypatch.setattr(
        tools_module,
        "record_active_gate_execution",
        lambda *args: evidence.append(args) or "bootstrap-evidence",
    )

    result = tools_module.ejecutar_verificacion.func("integration")

    assert result.startswith("VERIFICACIÓN FALLIDA: integration")
    assert "No se pudo iniciar la base de datos" in result
    assert [command for command, _ in calls] == [["pnpm", "db:start"]]
    assert evidence == [
        (
            "integration",
            ["pnpm", "db:start"],
            tools_module.PROJECT_ROOT,
            1,
            "Exit code: 1\nSTDERR:\nDocker unavailable",
        )
    ]


def test_ejecutar_verificacion_records_active_evidence(monkeypatch):
    monkeypatch.setattr(tools_module, "_run", lambda *args, **kwargs: (0, "ok"))
    monkeypatch.setattr(
        tools_module,
        "record_active_gate_execution",
        lambda *args: "evidence-1",
    )

    result = tools_module.ejecutar_verificacion.func("lint")

    assert result.endswith("Evidence: evidence-1")


def test_ejecutar_verificacion_schema_limits_checks():
    schema = tools_module.ejecutar_verificacion.args_schema.model_json_schema()

    assert schema["properties"]["verificacion"]["enum"] == [
        "python",
        "lint",
        "test",
        "build",
        "integration",
    ]


def test_ejecutar_verificacion_rejects_unknown_check():
    result = tools_module.ejecutar_verificacion.func("deploy")

    assert result == "Error: usa python, lint, test, build o integration"
