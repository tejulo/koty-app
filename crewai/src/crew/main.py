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
