import os
import subprocess

import pytest

from crew.tools.custom_tool import (
    PROJECT_ROOT,
    _validar_comando_openspec,
    ejecutar_openspec,
)


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
