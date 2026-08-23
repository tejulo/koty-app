import pytest
from crewai.tools.tool_failure import ToolFailure

import crew.main as main_module
from crew.main import normalizar_ticket


@pytest.mark.parametrize(
    ("raw_id", "esperado"),
    [
        ("DEV-5", ("DEV-5", "dev-5")),
        (" dev-5 ", ("DEV-5", "dev-5")),
        ("Dev123-42", ("DEV123-42", "dev123-42")),
    ],
)
def test_normalizar_ticket_acepta_identificadores_validos(raw_id, esperado):
    assert normalizar_ticket(raw_id) == esperado


@pytest.mark.parametrize(
    "raw_id",
    ["", "   ", "DEV", "DEV-", "-5", "DEV 5", "DEV-5-extra"],
)
def test_normalizar_ticket_rechaza_identificadores_invalidos(raw_id):
    with pytest.raises(ValueError):
        normalizar_ticket(raw_id)


def test_finalizar_cambio_archivado_ejecuta_gates_y_completa(monkeypatch):
    llamadas_verificacion = []
    llamadas_openspec = []
    llamadas_completar = []

    monkeypatch.setattr(
        main_module,
        "_buscar_directorio_archivado",
        lambda change_id: f"archive/{change_id}",
    )

    def verificar(nombre):
        llamadas_verificacion.append(nombre)
        return f"VERIFICACIÓN EXITOSA\n\nVerificación: {nombre}"

    monkeypatch.setattr(
        main_module.ejecutar_verificacion,
        "func",
        verificar,
    )

    def openspec(comando):
        llamadas_openspec.append(comando)
        return "Éxito OpenSpec\n\nExit code: 0"

    monkeypatch.setattr(
        main_module.ejecutar_openspec,
        "func",
        openspec,
    )

    def completar(ticket_id, change_id):
        llamadas_completar.append((ticket_id, change_id))
        return "Ticket DEV-7 confirmado en Done."

    monkeypatch.setattr(
        main_module.completar_tarea_linear,
        "func",
        completar,
    )

    assert main_module.finalizar_cambio_archivado("DEV-7", "dev-7")

    assert llamadas_verificacion == ["python", "lint", "test", "build"]
    assert llamadas_openspec == ["validate --all --strict"]
    assert llamadas_completar == [("DEV-7", "dev-7")]


def test_finalizar_cambio_archivado_propaga_fallo_de_gates(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "_buscar_directorio_archivado",
        lambda change_id: f"archive/{change_id}",
    )
    monkeypatch.setattr(
        main_module.ejecutar_verificacion,
        "func",
        lambda nombre: "VERIFICACIÓN FALLIDA\n\nExit code: 1",
    )

    with pytest.raises(RuntimeError, match="Verificación posterior al archive"):
        main_module.finalizar_cambio_archivado("DEV-7", "dev-7")


def test_finalizar_cambio_archivado_propaga_tool_failure(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "_buscar_directorio_archivado",
        lambda change_id: f"archive/{change_id}",
    )
    monkeypatch.setattr(
        main_module.ejecutar_verificacion,
        "func",
        lambda nombre: f"VERIFICACIÓN EXITOSA\n\nVerificación: {nombre}",
    )
    monkeypatch.setattr(
        main_module.ejecutar_openspec,
        "func",
        lambda comando: "Éxito OpenSpec\n\nExit code: 0",
    )
    monkeypatch.setattr(
        main_module.completar_tarea_linear,
        "func",
        lambda ticket_id, change_id: ToolFailure(
            message="Linear rechazó Done",
            code="COMPLETION_GATE_REJECTED",
            retryable=False,
        ),
    )

    with pytest.raises(RuntimeError, match="Linear rechazó Done"):
        main_module.finalizar_cambio_archivado("DEV-7", "dev-7")
