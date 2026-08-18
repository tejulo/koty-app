import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Ayudamos a Python a encontrar la ruta correcta
ruta_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ruta_src)

from crew.crew import KotyAppCrew

def run():
    """
    Punto de entrada principal para ejecutar el equipo de trabajo.
    """
    # 1. Capturamos el ticket que escribes en la terminal (ej. DEV-5)
    if len(sys.argv) > 1:
        ticket_id = sys.argv[1]
    else:
        ticket_id = input("Por favor, ingresa el identificador del ticket de Linear (ej. DEV-5): ")

    print(f"Despertando al equipo para trabajar en el ticket: {ticket_id}...")

    # 2. Conectamos el ticket con nuestro archivo tasks.yaml
    datos_de_entrada = {
        'ticket_id': ticket_id
    }

    # 3. Iniciamos el proceso
    try:
        KotyAppCrew().crew().kickoff(inputs=datos_de_entrada)
        print("\n¡El equipo ha terminado exitosamente su trabajo de planificación y código!")
    except Exception as error:
        print(f"\nHubo un problema durante la ejecución del equipo: {error}")

if __name__ == "__main__":
    run()
