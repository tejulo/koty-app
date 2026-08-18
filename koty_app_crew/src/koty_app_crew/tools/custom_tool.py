import os
import requests
import subprocess
from crewai.tools import tool

@tool("Buscar Tarea en Linear")
def buscar_tarea_linear(ticket_id: str) -> str:
    """
    Busca un ticket en Linear por su identificador (ej. DEV-5) y devuelve su título y descripción.
    """
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        return "Error: Falta la variable LINEAR_API_KEY en el archivo .env"
    
    query = """
    query Issue($id: String!) {
      issue(id: $id) {
        title
        description
      }
    }
    """
    
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            "https://api.linear.app/graphql",
            json={"query": query, "variables": {"id": ticket_id}},
            headers=headers
        )
        data = response.json()
        
        if "errors" in data:
            return f"Error de Linear: {data['errors'][0]['message']}"
            
        issue = data.get("data", {}).get("issue")
        if not issue:
            return f"No se encontró el ticket {ticket_id} en Linear."
            
        titulo = issue.get("title", "Sin título")
        descripcion = issue.get("description", "Sin descripción")
        
        return f"Título de la tarea: {titulo}\nDescripción: {descripcion}"
        
    except Exception as e:
        return f"Error al conectar con Linear: {str(e)}"

@tool("Ejecutar OpenSpec")
def ejecutar_openspec(comando_openspec: str) -> str:
    """
    Ejecuta el programa OpenSpec en la RAÍZ del proyecto.
    NO uses el comando 'generate'.
    Debes pasar solo los argumentos válidos, por ejemplo: 'new change "Resumen del ticket"' o 'init'.
    """
    try:
        comando_completo = f"npx openspec {comando_openspec}"
        
        # El timeout=30 cortará el comando si se queda esperando una respuesta
        resultado = subprocess.run(
            comando_completo,
            shell=True,
            cwd="..", 
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if resultado.returncode == 0:
            return f"Éxito:\n{resultado.stdout}"
        else:
            return f"Error de OpenSpec:\n{resultado.stderr}\n{resultado.stdout}"
            
    except subprocess.TimeoutExpired:
        return "Error: El comando tardó más de 30 segundos y se congeló. OpenSpec probablemente estaba haciendo una pregunta interactiva (como Y/n). Usa otro comando."
    except Exception as e:
        return f"Error crítico: {str(e)}"


@tool("Escribir Archivo en Raiz")
def escribir_archivo_raiz(ruta_relativa: str, contenido: str) -> str:
    """
    Escribe un archivo garantizando que se guarde en la RAÍZ del proyecto.
    Solo debes pasar la ruta del archivo (ej: 'package.json' o 'apps/web/package.json').
    La herramienta se encarga automáticamente de guardarlo en el lugar correcto.
    """
    try:
        # Forzamos la ruta un nivel arriba automáticamente
        ruta_completa = os.path.abspath(os.path.join("..", ruta_relativa))
        
        # Creamos las carpetas intermedias (como apps/web/) si no existen
        os.makedirs(os.path.dirname(ruta_completa), exist_ok=True)
        
        # Escribimos el archivo
        with open(ruta_completa, 'w', encoding='utf-8') as f:
            f.write(contenido)
            
        return f"Archivo guardado exitosamente en la raíz: {ruta_completa}"
    except Exception as e:
        return f"Error al guardar archivo: {str(e)}"
