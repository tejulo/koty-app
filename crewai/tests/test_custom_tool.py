import os
import subprocess

import pytest
from crewai.tools.tool_failure import ToolFailure

import crew.tools.custom_tool as tools_module
from crew.tools.custom_tool import (
    PROJECT_ROOT,
    _validar_comando_openspec,
    completar_tarea_linear,
    ejecutar_openspec,
    marcar_tarea_en_progreso_linear,
)


@pytest.fixture(autouse=True)
def limpiar_evidencia_linear():
    tools_module._TICKETS_CONSULTADOS.clear()
    tools_module._TICKETS_INICIADOS.clear()
    tools_module._VERIFICACIONES_EXITOSAS.clear()
    tools_module._CAMBIOS_VALIDADOS.clear()
    tools_module._CAMBIOS_ARCHIVADOS.clear()
    yield
    tools_module._TICKETS_CONSULTADOS.clear()
    tools_module._TICKETS_INICIADOS.clear()
    tools_module._VERIFICACIONES_EXITOSAS.clear()
    tools_module._CAMBIOS_VALIDADOS.clear()
    tools_module._CAMBIOS_ARCHIVADOS.clear()


def test_iniciar_ticket_exige_busqueda_previa():
    resultado = marcar_tarea_en_progreso_linear.func("DEV-5")

    assert isinstance(resultado, ToolFailure)
    assert resultado.code == "TICKET_NOT_QUERIED"


def test_iniciar_ticket_actualiza_y_registra_evidencia(monkeypatch):
    llamada = {}
    tools_module._TICKETS_CONSULTADOS.add("DEV-5")

    def cambiar(ticket_id, estados_origen, state_id, estado_destino):
        llamada.update(
            ticket_id=ticket_id,
            estados_origen=estados_origen,
            state_id=state_id,
            estado_destino=estado_destino,
        )
        return {"identifier": "DEV-5", "state": {"name": "In Progress"}}

    monkeypatch.setattr(tools_module, "_cambiar_estado_linear", cambiar)

    resultado = marcar_tarea_en_progreso_linear.func("dev-5")

    assert resultado == "Ticket DEV-5 confirmado en In Progress."
    assert tools_module._TICKETS_INICIADOS == {"DEV-5"}
    assert llamada == {
        "ticket_id": "DEV-5",
        "estados_origen": {"Backlog", "Todo"},
        "state_id": "008d4363-c312-4d53-86d4-ad2210650291",
        "estado_destino": "In Progress",
    }


def test_iniciar_ticket_convierte_rechazo_en_tool_failure(monkeypatch):
    tools_module._TICKETS_CONSULTADOS.add("DEV-5")

    def cambiar(*args, **kwargs):
        raise RuntimeError("El ticket está en Canceled")

    monkeypatch.setattr(tools_module, "_cambiar_estado_linear", cambiar)

    resultado = marcar_tarea_en_progreso_linear.func("DEV-5")

    assert isinstance(resultado, ToolFailure)
    assert resultado.code == "LINEAR_START_REJECTED"
    assert "Canceled" in resultado.message
    assert not tools_module._TICKETS_INICIADOS


def test_completar_ticket_rechaza_evidencia_incompleta():
    tools_module._TICKETS_INICIADOS.add("DEV-5")

    resultado = completar_tarea_linear.func("DEV-5", "dev-5")

    assert isinstance(resultado, ToolFailure)
    assert resultado.code == "COMPLETION_GATE_REJECTED"
    assert "verificaciones" in resultado.message


def test_escritura_invalida_verificaciones(monkeypatch, tmp_path):
    monkeypatch.setattr(tools_module, "PROJECT_ROOT", tmp_path)
    tools_module._VERIFICACIONES_EXITOSAS.update(
        {"python", "lint", "test", "build"}
    )

    resultado = tools_module.escribir_archivo_raiz.func("src/app.py", "x = 1\n")

    assert "guardado correctamente" in resultado
    assert tools_module._VERIFICACIONES_EXITOSAS == set()


def test_escritura_openspec_invalida_validacion(monkeypatch, tmp_path):
    monkeypatch.setattr(tools_module, "PROJECT_ROOT", tmp_path)
    tools_module._CAMBIOS_VALIDADOS.add("dev-5")
    tools_module._CAMBIOS_ARCHIVADOS.add("dev-5")

    tools_module.escribir_archivo_raiz.func(
        "openspec/changes/dev-5/tasks.md",
        "- [x] Implementar\n",
    )

    assert "dev-5" not in tools_module._CAMBIOS_VALIDADOS
    assert "dev-5" not in tools_module._CAMBIOS_ARCHIVADOS


def test_verificacion_exitosa_registra_evidencia(monkeypatch):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", run)

    tools_module.ejecutar_verificacion.func("python")

    assert "python" in tools_module._VERIFICACIONES_EXITOSAS


def test_archive_exitoso_invalida_verificaciones_y_preserva_evidencia(monkeypatch):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", run)
    tools_module._VERIFICACIONES_EXITOSAS.update(
        {"python", "lint", "test", "build"}
    )

    tools_module.ejecutar_openspec.func(
        "validate dev-5 --strict --no-interactive"
    )
    tools_module.ejecutar_openspec.func("archive dev-5 --yes")

    assert tools_module._VERIFICACIONES_EXITOSAS == set()
    assert tools_module._CAMBIOS_VALIDADOS == {"dev-5"}
    assert tools_module._CAMBIOS_ARCHIVADOS == {"dev-5"}


def test_archive_sin_validate_no_ejecuta_subprocess(monkeypatch):
    def run(*args, **kwargs):
        raise AssertionError("subprocess no debe ejecutarse")

    monkeypatch.setattr(subprocess, "run", run)

    resultado = tools_module.ejecutar_openspec.func("archive dev-5 --yes")

    assert isinstance(resultado, ToolFailure)
    assert resultado.code == "CHANGE_NOT_VALIDATED"


def test_completar_ticket_actualiza_done_con_gate_completo(monkeypatch, tmp_path):
    monkeypatch.setattr(tools_module, "PROJECT_ROOT", tmp_path)
    archive = tmp_path / "openspec/changes/archive/2026-08-22-dev-5"
    archive.mkdir(parents=True)
    (archive / "tasks.md").write_text("- [x] Implementar\n", encoding="utf-8")

    tools_module._TICKETS_INICIADOS.add("DEV-5")
    tools_module._VERIFICACIONES_EXITOSAS.update(
        {"python", "lint", "test", "build"}
    )
    tools_module._CAMBIOS_VALIDADOS.add("dev-5")
    tools_module._CAMBIOS_ARCHIVADOS.add("dev-5")
    llamada = {}

    def cambiar(ticket_id, estados_origen, state_id, estado_destino):
        llamada.update(
            ticket_id=ticket_id,
            estados_origen=estados_origen,
            state_id=state_id,
            estado_destino=estado_destino,
        )
        return {"identifier": "DEV-5", "state": {"name": "Done"}}

    monkeypatch.setattr(tools_module, "_cambiar_estado_linear", cambiar)

    resultado = completar_tarea_linear.func("DEV-5", "dev-5")

    assert resultado == "Ticket DEV-5 confirmado en Done."
    assert llamada["state_id"] == "10a67bb1-f5aa-4fe6-ae85-213f792d5a48"
    assert llamada["estados_origen"] == {"In Progress"}


@pytest.mark.parametrize(
    "argumentos",
    [
        ["new", "change", "dev-5"],
        ["status", "--change", "dev-5"],
        ["validate", "dev-5", "--strict", "--no-interactive"],
        ["archive", "dev-5", "--yes"],
        ["list"],
        ["show", "dev-5"],
        ["instructions", "dev-5"],
    ],
)
def test_validar_comando_openspec_acepta_allowlist(argumentos):
    _validar_comando_openspec(argumentos)


@pytest.mark.parametrize(
    "argumentos",
    [[], ["remove", "dev-5"], ["new", "project", "dev-5"]],
)
def test_validar_comando_openspec_rechaza_comandos_no_permitidos(argumentos):
    with pytest.raises(ValueError):
        _validar_comando_openspec(argumentos)


@pytest.mark.parametrize(
    "argumentos",
    [
        ["new", "change", "dev-5", "extra"],
        ["validate", "dev-5", "--strict", "--no-interactive", "extra"],
        ["archive", "dev-5", "--yes", "extra"],
        ["list", "extra"],
        ["show", "dev-5", "extra"],
        ["status", "--change", "dev-5", "extra"],
        ["instructions", "dev-5", "extra"],
    ],
)
def test_validar_comando_openspec_rechaza_argumentos_extra(argumentos):
    with pytest.raises(ValueError):
        _validar_comando_openspec(argumentos)


@pytest.mark.parametrize(
    "argumentos",
    [
        ["new", "change"],
        ["validate", "--strict", "--no-interactive"],
        ["archive", "--yes"],
        ["show"],
        ["status", "--change"],
        ["instructions"],
    ],
)
def test_validar_comando_openspec_rechaza_change_id_ausente(argumentos):
    with pytest.raises(ValueError):
        _validar_comando_openspec(argumentos)


@pytest.mark.parametrize(
    "change_id",
    [
        "DEV-5",
        "dev_5",
        "dev--5",
        "-dev-5",
        "dev-5-",
        "dev 5",
        "dev/5",
    ],
)
def test_validar_comando_openspec_rechaza_change_id_invalido(change_id):
    comandos = [
        ["new", "change", change_id],
        ["validate", change_id, "--strict", "--no-interactive"],
        ["archive", change_id, "--yes"],
        ["show", change_id],
        ["status", "--change", change_id],
        ["instructions", change_id],
    ]

    for argumentos in comandos:
        with pytest.raises(ValueError):
            _validar_comando_openspec(argumentos)


def test_validar_comando_openspec_rechaza_bypass_no_validate():
    with pytest.raises(ValueError):
        _validar_comando_openspec(
            ["archive", "dev-5", "--yes", "--no-validate"]
        )


@pytest.mark.parametrize(
    "argumentos",
    [
        ["validate", "dev-5"],
        ["validate", "dev-5", "--strict"],
        ["validate", "dev-5", "--no-interactive", "--strict"],
        ["archive", "dev-5"],
    ],
)
def test_validar_comando_openspec_exige_flags_y_orden(argumentos):
    with pytest.raises(ValueError):
        _validar_comando_openspec(argumentos)


def test_ejecutar_openspec_invoca_la_dependencia_del_workspace(monkeypatch):
    llamada = {}

    def run(command, **kwargs):
        llamada["command"] = command
        llamada["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", run)

    ejecutar_openspec.func("validate dev-5 --strict --no-interactive")

    assert llamada == {
        "command": [
            "pnpm",
            "exec",
            "openspec",
            "validate",
            "dev-5",
            "--strict",
            "--no-interactive",
        ],
        "kwargs": {
            "cwd": PROJECT_ROOT,
            "capture_output": True,
            "text": True,
            "timeout": 60,
            "check": False,
            "env": {
                **os.environ,
                "OPENSPEC_TELEMETRY": "0",
            },
        },
    }


def test_ejecutar_openspec_preserva_el_entorno_del_padre(monkeypatch):
    llamada = {}
    monkeypatch.setenv("OPENSPEC_TELEMETRY", "valor-padre")
    monkeypatch.setenv("VARIABLE_EXISTENTE", "se-conserva")

    def run(command, **kwargs):
        llamada["env"] = kwargs["env"]
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", run)

    ejecutar_openspec.func("validate dev-5 --strict --no-interactive")

    assert llamada["env"]["OPENSPEC_TELEMETRY"] == "0"
    assert llamada["env"]["VARIABLE_EXISTENTE"] == "se-conserva"
    assert os.environ["OPENSPEC_TELEMETRY"] == "valor-padre"


def test_ejecutar_openspec_devuelve_salida_exitosa(monkeypatch):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, "validacion correcta\n", "")

    monkeypatch.setattr(subprocess, "run", run)

    salida = ejecutar_openspec.func(
        "validate dev-5 --strict --no-interactive"
    )

    assert "Éxito OpenSpec" in salida
    assert "Exit code: 0" in salida
    assert "STDOUT:\nvalidacion correcta" in salida


def test_ejecutar_openspec_devuelve_salida_fallida(monkeypatch):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, "detalle", "fallo concreto\n")

    monkeypatch.setattr(subprocess, "run", run)

    salida = ejecutar_openspec.func(
        "validate dev-5 --strict --no-interactive"
    )

    assert "Error de OpenSpec" in salida
    assert "Exit code: 2" in salida
    assert "STDOUT:\ndetalle" in salida
    assert "STDERR:\nfallo concreto" in salida


def test_ejecutar_openspec_informa_si_pnpm_no_esta_disponible(monkeypatch):
    def run(command, **kwargs):
        raise FileNotFoundError("pnpm")

    monkeypatch.setattr(subprocess, "run", run)

    salida = ejecutar_openspec.func(
        "validate dev-5 --strict --no-interactive"
    )

    assert "pnpm" in salida
    assert "dependencia local" in salida
