import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# Configuración temprana
# ============================================================
#
# Es importante configurar esto ANTES de importar CrewAI,
# porque OpenTelemetry puede inicializarse durante los imports.
#

CREWAI_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(CREWAI_ROOT / ".env")


# Desactivar tracing de CrewAI.
os.environ["CREWAI_TRACING_ENABLED"] = "false"

# Desactivar completamente el SDK de OpenTelemetry.
#
# Esto evita mensajes como:
#
# opentelemetry.exporter.otlp...
# Transient error Service Unavailable...
#
os.environ["OTEL_SDK_DISABLED"] = "true"


# Importar CrewAI solamente después de configurar el entorno.
from crew.crew import KotyAppCrew
from crew.tools.custom_tool import (
    _CAMBIOS_ARCHIVADOS,
    _CAMBIOS_VALIDADOS,
    _TICKETS_CONSULTADOS,
    _TICKETS_INICIADOS,
    _buscar_directorio_archivado,
    completar_tarea_linear,
    ejecutar_openspec,
    ejecutar_verificacion,
)
from crewai.tools.tool_failure import ToolFailure


def normalizar_ticket(raw_id: str) -> tuple[str, str]:
    """
    Convierte el identificador ingresado a los formatos utilizados
    por Linear y OpenSpec.

    Ejemplos de entrada aceptados:

        DEV-5
        dev-5
        Dev-5

    Resultado:

        ticket_id = DEV-5
        change_id = dev-5
    """

    raw_id = raw_id.strip()

    if not raw_id:
        raise ValueError(
            "El identificador del ticket es obligatorio."
        )

    if not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9]*-\d+",
        raw_id,
    ):
        raise ValueError(
            "Formato de ticket inválido. "
            "Usa un identificador como DEV-5 o dev-5."
        )

    ticket_id = raw_id.upper()
    change_id = raw_id.lower()

    return ticket_id, change_id


def _exigir_resultado_exitoso(
    etiqueta: str,
    resultado: str | ToolFailure,
    prefijo_exitoso: str,
) -> str:
    if isinstance(resultado, ToolFailure):
        raise RuntimeError(resultado.message)

    print(resultado)

    if not resultado.startswith(prefijo_exitoso):
        raise RuntimeError(
            f"{etiqueta} falló o no confirmó OK.\n{resultado}"
        )

    return resultado


def finalizar_cambio_archivado(ticket_id: str, change_id: str) -> bool:
    """Resume a run killed after OpenSpec archive but before Linear Done."""
    try:
        _buscar_directorio_archivado(change_id)
    except RuntimeError:
        return False

    print(
        "Cambio OpenSpec ya archivado; ejecutando gates finales "
        "y completando Linear."
    )

    _TICKETS_CONSULTADOS.add(ticket_id)
    _TICKETS_INICIADOS.add(ticket_id)
    _CAMBIOS_VALIDADOS.add(change_id)
    _CAMBIOS_ARCHIVADOS.add(change_id)

    for verificacion in ("python", "lint", "test", "build"):
        resultado = ejecutar_verificacion.func(verificacion)
        _exigir_resultado_exitoso(
            f"Verificación posterior al archive '{verificacion}'",
            resultado,
            "VERIFICACIÓN EXITOSA",
        )

    resultado_openspec = ejecutar_openspec.func("validate --all --strict")
    _exigir_resultado_exitoso(
        "OpenSpec validate --all --strict",
        resultado_openspec,
        "Éxito OpenSpec",
    )

    _CAMBIOS_VALIDADOS.add(change_id)
    _CAMBIOS_ARCHIVADOS.add(change_id)
    resultado_linear = completar_tarea_linear.func(ticket_id, change_id)
    _exigir_resultado_exitoso(
        "Completar Tarea en Linear",
        resultado_linear,
        f"Ticket {ticket_id} confirmado en Done.",
    )
    return True


def run():
    """
    Punto de entrada principal de Koty App Crew.

    Ejemplos:

        uv run run_crew dev-5

        uv run run_crew DEV-5
    """

    if len(sys.argv) > 1:
        raw_id = sys.argv[1]
    else:
        raw_id = input(
            "Ingresa el identificador del ticket "
            "(ej. DEV-5 o dev-5): "
        )

    try:
        ticket_id, change_id = normalizar_ticket(
            raw_id
        )

        print()
        print("=" * 60)
        print("Koty App Crew")
        print("=" * 60)
        print(f"Ticket Linear:   {ticket_id}")
        print(f"Cambio OpenSpec: {change_id}")
        print("=" * 60)
        print()

        inputs = {
            "ticket_id": ticket_id,
            "change_id": change_id,
        }

        if finalizar_cambio_archivado(ticket_id, change_id):
            print()
            print("=" * 60)
            print("Ejecución finalizada")
            print("=" * 60)
            return

        resultado = (
            KotyAppCrew()
            .crew()
            .kickoff(inputs=inputs)
        )

        print()
        print("=" * 60)
        print("Ejecución finalizada")
        print("=" * 60)

        if resultado:
            print(resultado)

    except KeyboardInterrupt:
        print()
        print("Ejecución cancelada por el usuario.")
        raise SystemExit(130)

    except Exception as error:
        print()
        print("=" * 60)
        print("La ejecución del equipo falló")
        print("=" * 60)
        print(f"Error: {error}")

        raise SystemExit(1)


if __name__ == "__main__":
    run()
