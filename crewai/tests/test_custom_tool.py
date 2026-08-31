from pathlib import Path

import crew.tools.custom_tool as tools_module
from crewai.tools.tool_failure import ToolFailure


def test_buscar_tarea_linear_returns_truncated_issue_json(monkeypatch):
    monkeypatch.setattr(
        tools_module,
        "get_issue",
        lambda ticket_id: {
            "identifier": ticket_id,
            "title": "Preparar migraciones reproducibles con Prisma",
        },
    )

    result = tools_module.buscar_tarea_linear.func("DEV-6")

    assert '"identifier": "DEV-6"' in result
    assert "Preparar migraciones" in result


def test_buscar_tarea_linear_converts_errors_to_tool_failure(monkeypatch):
    def fail(_ticket_id):
        raise RuntimeError("Linear rechazó consulta")

    monkeypatch.setattr(tools_module, "get_issue", fail)

    result = tools_module.buscar_tarea_linear.func("DEV-6")

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


def test_ejecutar_verificacion_schema_limits_checks():
    schema = tools_module.ejecutar_verificacion.args_schema.model_json_schema()

    assert schema["properties"]["verificacion"]["enum"] == [
        "python",
        "lint",
        "test",
        "build",
    ]


def test_ejecutar_verificacion_rejects_unknown_check():
    result = tools_module.ejecutar_verificacion.func("deploy")

    assert result == "Error: usa python, lint, test o build"
