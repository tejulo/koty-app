import os
import requests
from crewai.tools import tool

@tool("Buscar Tarea en Linear")
def buscar_tarea_linear(ticket_id: str) -> str:
    """
    Busca la información de una tarea en Linear usando su identificador (por ejemplo: KOTY-123).
    Devuelve el título y la descripción para que el agente pueda leerlos.
    """
    # 1. Buscamos la llave secreta
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        return "Error: No se encontró la llave LINEAR_API_KEY en el archivo .env"

    # 2. Preparamos la conexión a Linear
    url = "https://api.linear.app/graphql"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
    # 3. Le decimos a Linear exactamente qué queremos saber
    consulta_graphql = """
    query($id: String!) {
      issue(id: $id) {
        title
        description
      }
    }
    """
    
    variables = {"id": ticket_id}
    
    # 4. Hacemos la llamada a internet
    try:
        respuesta = requests.post(url, headers=headers, json={"query": consulta_graphql, "variables": variables})
        datos = respuesta.json()
        
        # 5. Extraemos el texto limpio para el agente
        tarea = datos.get("data", {}).get("issue", {})
        if not tarea:
            return f"No pude encontrar la tarea con el identificador: {ticket_id}"
            
        titulo = tarea.get("title", "Sin título")
        descripcion = tarea.get("description", "Sin descripción")
        
        return f"Título de la tarea: {titulo}\nDescripción: {descripcion}"
        
    except Exception as e:
        return f"Hubo un problema al conectar con internet: {str(e)}"

@tool("Ejecutar OpenSpec")
def ejecutar_openspec(instrucciones_adicionales: str) -> str:
    """
    Ejecuta el comando de terminal de OpenSpec para generar el plano técnico en la carpeta del proyecto.
    El agente debe enviar como argumento cualquier instrucción extra si es necesario, o un texto vacío.
    """
    try:
        # Aseguramos que el comando se ejecute en la raíz de tu proyecto
        # Subimos un nivel desde la carpeta de la herramienta hasta la raíz de koty-app
        directorio_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

        # El comando que se ejecutará en la terminal real
        comando = f"npx openspec generate"
        if instrucciones_adicionales:
             # Si el arquitecto quiere añadir notas directas a la terminal
             comando += f' --prompt "{instrucciones_adicionales}"'

        resultado = subprocess.run(
            comando,
            shell=True,
            cwd=directorio_raiz,
            capture_output=True,
            text=True,
            check=True # Generará un error si el comando de Node falla
        )
        return f"OpenSpec se ejecutó correctamente.\nSalida de la terminal:\n{resultado.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Error al ejecutar OpenSpec en la terminal. Verifica que Node y OpenSpec estén instalados.\nDetalle del error: {e.stderr}"
    except Exception as e:
        return f"Error inesperado al intentar usar OpenSpec: {str(e)}"
