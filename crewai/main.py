import os
import sys

# Tomamos el número de ticket que escribas (como DEV-5)
argumentos = " ".join(sys.argv[1:])

print("Iniciando el entorno de Koty App...")

# Ejecutamos el comando completo automáticamente con la ruta correcta
comando = f"PYTHONPATH=src python3 src/crew/main.py {argumentos}"
os.system(comando)
