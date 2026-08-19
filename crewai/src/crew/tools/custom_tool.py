import os
import re
import shlex
import subprocess
from pathlib import Path

import requests
from crewai.tools import tool


# ============================================================
# Directorios principales
# ============================================================

# Archivo actual:
#
# koty-app/
# └── crewai/
#     └── src/
#         └── crew/
#             └── tools/
#                 └── custom_tool.py
#
# parents[4] => koty-app/

PROJECT_ROOT = Path(
    __file__
).resolve().parents[4]

CREWAI_ROOT = Path(
    __file__
).resolve().parents[3]


# ============================================================
# Límites para proteger la ventana de contexto del LLM
# ============================================================

MAX_ARCHIVOS_LISTADO = 120

MAX_CARACTERES_ARCHIVO = 20_000

MAX_CARACTERES_COMANDO = 12_000

MAX_PROFUNDIDAD_LISTADO = 4


# ============================================================
# Directorios que nunca deben ser explorados recursivamente
# ============================================================

DIRECTORIOS_IGNORADOS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    ".turbo",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".pnpm-store",
    "coverage",
    "dist",
    "build",
}


# ============================================================
# Helpers
# ============================================================

def _resolver_ruta(
    ruta_relativa: str,
) -> Path:
    """
    Convierte una ruta relativa en una ruta absoluta
    dentro del repositorio.

    También evita path traversal como:

        ../../etc/passwd
    """

    if not ruta_relativa:
        raise ValueError(
            "La ruta no puede estar vacía."
        )

    ruta = (
        PROJECT_ROOT / ruta_relativa
    ).resolve()

    if not ruta.is_relative_to(
        PROJECT_ROOT
    ):
        raise ValueError(
            f"La ruta '{ruta_relativa}' intenta "
            "salir de la raíz del repositorio."
        )

    return ruta


def _ruta_contiene_directorio_ignorado(
    ruta: Path,
) -> bool:
    """
    Comprueba si una ruta se encuentra dentro de
    .venv, node_modules, .git, etc.
    """

    try:
        partes = set(
            ruta
            .relative_to(PROJECT_ROOT)
            .parts
        )
    except ValueError:
        return True

    return bool(
        partes & DIRECTORIOS_IGNORADOS
    )


def _truncar_texto(
    texto: str,
    limite: int,
) -> str:
    """
    Evita enviar outputs gigantes al contexto del agente.

    Conserva el principio y el final del texto, porque
    el final suele contener los errores más relevantes.
    """

    if texto is None:
        return ""

    if len(texto) <= limite:
        return texto

    inicio_max = limite // 3
    final_max = limite - inicio_max

    inicio = texto[:inicio_max]
    final = texto[-final_max:]

    return (
        inicio
        + "\n\n"
        + "[... CONTENIDO TRUNCADO PARA PROTEGER "
        + "LA VENTANA DE CONTEXTO ...]"
        + "\n\n"
        + final
    )


# ============================================================
# Linear
# ============================================================

@tool("Buscar Tarea en Linear")
def buscar_tarea_linear(
    ticket_id: str,
) -> str:
    """
    Busca un ticket en Linear.

    Ejemplo:

        DEV-5
    """

    api_key = os.environ.get(
        "LINEAR_API_KEY"
    )

    if not api_key:
        return (
            "Error: Falta la variable "
            "LINEAR_API_KEY."
        )

    query = """
    query Issue($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        description
        priority
        priorityLabel

        state {
          name
        }

        project {
          name
        }

        team {
          key
          name
        }
      }
    }
    """

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.linear.app/graphql",
            json={
                "query": query,
                "variables": {
                    "id": ticket_id,
                },
            },
            headers=headers,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        if data.get("errors"):
            mensajes = [
                error.get(
                    "message",
                    "Error desconocido",
                )
                for error in data["errors"]
            ]

            return (
                "Error de Linear:\n"
                + "\n".join(mensajes)
            )

        issue = (
            data
            .get("data", {})
            .get("issue")
        )

        if not issue:
            return (
                f"No se encontró el ticket "
                f"'{ticket_id}'."
            )

        state = (
            issue.get("state")
            or {}
        )

        project = (
            issue.get("project")
            or {}
        )

        team = (
            issue.get("team")
            or {}
        )

        descripcion = (
            issue.get("description")
            or "Sin descripción"
        )

        resultado = "\n".join(
            [
                (
                    "Identificador: "
                    f"{issue.get('identifier', ticket_id)}"
                ),
                (
                    "Título: "
                    f"{issue.get('title', 'Sin título')}"
                ),
                (
                    "Estado: "
                    f"{state.get('name', 'Sin estado')}"
                ),
                (
                    "Prioridad: "
                    f"{issue.get('priorityLabel', 'Sin prioridad')}"
                ),
                (
                    "Proyecto: "
                    f"{project.get('name', 'Sin proyecto')}"
                ),
                (
                    "Equipo: "
                    f"{team.get('name', 'Sin equipo')}"
                ),
                "",
                "Descripción:",
                descripcion,
            ]
        )

        return _truncar_texto(
            resultado,
            MAX_CARACTERES_ARCHIVO,
        )

    except requests.Timeout:
        return (
            "Error: La solicitud a Linear "
            "excedió el tiempo máximo."
        )

    except requests.RequestException as error:
        return (
            "Error de conexión con Linear: "
            f"{error}"
        )

    except Exception as error:
        return (
            "Error procesando Linear: "
            f"{error}"
        )


# ============================================================
# OpenSpec
# ============================================================

def _validar_comando_openspec(
    argumentos: list[str],
) -> None:
    """
    Permite solamente un conjunto controlado de
    comandos OpenSpec.
    """

    if not argumentos:
        raise ValueError(
            "El comando OpenSpec está vacío."
        )

    comando = argumentos[0]
    change_id: str | None = None

    if comando == "new":
        if len(argumentos) == 3 and argumentos[:2] == ["new", "change"]:
            change_id = argumentos[2]
    elif comando == "validate":
        if (
            len(argumentos) == 4
            and argumentos[2:] == ["--strict", "--no-interactive"]
        ):
            change_id = argumentos[1]
    elif comando == "archive":
        if len(argumentos) == 3 and argumentos[2] == "--yes":
            change_id = argumentos[1]
    elif comando == "list":
        if argumentos == ["list"]:
            return
    elif comando == "show":
        if len(argumentos) == 2:
            change_id = argumentos[1]
    elif comando == "status":
        if len(argumentos) == 3 and argumentos[1] == "--change":
            change_id = argumentos[2]
    elif comando == "instructions":
        if len(argumentos) == 2:
            change_id = argumentos[1]
    else:
        raise ValueError(
            f"Comando OpenSpec no permitido: "
            f"'{comando}'."
        )

    if change_id is None:
        raise ValueError(
            f"Argumentos no permitidos para OpenSpec '{comando}'."
        )

    if not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
        change_id,
    ):
        raise ValueError(
            "El change-id debe usar kebab-case en minúsculas."
        )


@tool("Ejecutar OpenSpec")
def ejecutar_openspec(
    comando_openspec: str,
) -> str:
    """
    Ejecuta OpenSpec desde la raíz del repositorio.

    Ejemplos:

        new change dev-5

        status --change dev-5

        validate dev-5 --strict --no-interactive

        archive dev-5 --yes
    """

    try:
        argumentos = shlex.split(
            comando_openspec
        )

        _validar_comando_openspec(
            argumentos
        )

        resultado = subprocess.run(
            [
                "pnpm",
                "exec",
                "openspec",
                *argumentos,
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            env={
                **os.environ,
                "OPENSPEC_TELEMETRY": "0",
            },
        )

        stdout = _truncar_texto(
            resultado.stdout.strip(),
            MAX_CARACTERES_COMANDO,
        )

        stderr = _truncar_texto(
            resultado.stderr.strip(),
            MAX_CARACTERES_COMANDO,
        )

        partes = [
            (
                "Exit code: "
                f"{resultado.returncode}"
            )
        ]

        if stdout:
            partes.append(
                f"STDOUT:\n{stdout}"
            )

        if stderr:
            partes.append(
                f"STDERR:\n{stderr}"
            )

        salida = "\n\n".join(
            partes
        )

        if resultado.returncode == 0:
            return (
                "Éxito OpenSpec\n\n"
                + salida
            )

        return (
            "Error de OpenSpec\n\n"
            + salida
        )

    except FileNotFoundError:
        return (
            "Error: No se encontró 'pnpm'. Comprueba "
            "que pnpm esté disponible y que la "
            "dependencia local de OpenSpec esté "
            "instalada en el workspace."
        )

    except subprocess.TimeoutExpired:
        return (
            "Error: OpenSpec excedió el timeout "
            "de 60 segundos."
        )

    except ValueError as error:
        return (
            "Error en el comando OpenSpec: "
            f"{error}"
        )

    except Exception as error:
        return (
            "Error crítico ejecutando OpenSpec: "
            f"{error}"
        )


# ============================================================
# Escritura
# ============================================================

@tool("Escribir Archivo en Raiz")
def escribir_archivo_raiz(
    ruta_relativa: str,
    contenido: str,
) -> str:
    """
    Crea o sobrescribe un archivo dentro del
    repositorio.

    La ruta siempre debe ser relativa al root.
    """

    try:
        ruta = _resolver_ruta(
            ruta_relativa
        )

        ruta.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        ruta.write_text(
            contenido,
            encoding="utf-8",
        )

        # Importante:
        #
        # NO devolvemos nuevamente el contenido.
        # Eso duplicaría código dentro del contexto del agente.

        return (
            "Archivo guardado correctamente: "
            f"{ruta_relativa}"
        )

    except Exception as error:
        return (
            "Error al guardar archivo: "
            f"{error}"
        )


# ============================================================
# Lectura
# ============================================================

@tool("Leer Archivo en Raiz")
def leer_archivo_raiz(
    ruta_relativa: str,
) -> str:
    """
    Lee un archivo del repositorio.

    Se bloquea la lectura de .venv, node_modules,
    .git y otros directorios generados.
    """

    try:
        ruta = _resolver_ruta(
            ruta_relativa
        )

        if _ruta_contiene_directorio_ignorado(
            ruta
        ):
            return (
                "Error: No está permitido leer "
                "archivos dentro de directorios "
                "generados o internos."
            )

        if not ruta.exists():
            return (
                f"Error: No existe el archivo "
                f"'{ruta_relativa}'."
            )

        if not ruta.is_file():
            return (
                f"Error: '{ruta_relativa}' "
                "no es un archivo."
            )

        contenido = ruta.read_text(
            encoding="utf-8"
        )

        return _truncar_texto(
            contenido,
            MAX_CARACTERES_ARCHIVO,
        )

    except UnicodeDecodeError:
        return (
            f"Error: '{ruta_relativa}' no parece "
            "ser un archivo de texto."
        )

    except Exception as error:
        return (
            "Error al leer archivo: "
            f"{error}"
        )


# ============================================================
# Listado
# ============================================================

@tool("Listar Archivos en Raiz")
def listar_archivos_raiz(
    ruta_relativa: str,
    profundidad_maxima: int = 2,
) -> str:
    """
    Lista archivos de una carpeta del repositorio
    sin incluir dependencias o artefactos generados.

    Ejemplos:

        ruta_relativa = "."
        profundidad_maxima = 2

        ruta_relativa = "openspec/changes/dev-5/specs"
        profundidad_maxima = 4
    """

    try:
        ruta = _resolver_ruta(
            ruta_relativa
        )

        if _ruta_contiene_directorio_ignorado(
            ruta
        ):
            return (
                "Error: No se permite listar "
                "directorios generados."
            )

        if not ruta.exists():
            return (
                f"Error: No existe la ruta "
                f"'{ruta_relativa}'."
            )

        if ruta.is_file():
            return (
                ruta
                .relative_to(PROJECT_ROOT)
                .as_posix()
            )

        profundidad_maxima = max(
            1,
            min(
                profundidad_maxima,
                MAX_PROFUNDIDAD_LISTADO,
            ),
        )

        archivos: list[str] = []

        for (
            directorio_actual,
            directorios,
            nombres_archivos,
        ) in os.walk(
            ruta,
            followlinks=False,
        ):
            directorio_actual_path = Path(
                directorio_actual
            )

            # Evitar entrar físicamente en estos directorios.
            directorios[:] = [
                nombre
                for nombre in directorios
                if nombre
                not in DIRECTORIOS_IGNORADOS
            ]

            try:
                profundidad = len(
                    directorio_actual_path
                    .relative_to(ruta)
                    .parts
                )
            except ValueError:
                continue

            if (
                profundidad
                >= profundidad_maxima
            ):
                directorios[:] = []

            for nombre in sorted(
                nombres_archivos
            ):
                archivo = (
                    directorio_actual_path
                    / nombre
                )

                relativo = (
                    archivo
                    .relative_to(PROJECT_ROOT)
                    .as_posix()
                )

                archivos.append(
                    relativo
                )

                if (
                    len(archivos)
                    >= MAX_ARCHIVOS_LISTADO
                ):
                    return (
                        "\n".join(archivos)
                        + "\n\n"
                        + "[LISTADO TRUNCADO: "
                        + f"máximo {MAX_ARCHIVOS_LISTADO} "
                        + "archivos]"
                    )

        if not archivos:
            return (
                "No se encontraron archivos "
                f"dentro de '{ruta_relativa}'."
            )

        return "\n".join(
            archivos
        )

    except Exception as error:
        return (
            "Error al listar archivos: "
            f"{error}"
        )


# ============================================================
# Verificaciones
# ============================================================

@tool("Ejecutar Verificacion")
def ejecutar_verificacion(
    verificacion: str,
) -> str:
    """
    Ejecuta exclusivamente verificaciones
    predefinidas.

    Valores permitidos:

        python
        lint
        test
        build
    """

    verificaciones = {
        "python": {
            "cwd": CREWAI_ROOT,
            "command": [
                "uv",
                "run",
                "python",
                "-m",
                "compileall",
                "-q",
                "src/crew",
            ],
        },

        "lint": {
            "cwd": PROJECT_ROOT,
            "command": [
                "pnpm",
                "lint",
            ],
        },

        "test": {
            "cwd": PROJECT_ROOT,
            "command": [
                "pnpm",
                "test",
            ],
        },

        "build": {
            "cwd": PROJECT_ROOT,
            "command": [
                "pnpm",
                "build",
            ],
        },
    }

    nombre = (
        verificacion
        .strip()
        .lower()
    )

    config = verificaciones.get(
        nombre
    )

    if not config:
        permitidas = ", ".join(
            verificaciones.keys()
        )

        return (
            "Error: Verificación no permitida. "
            f"Opciones: {permitidas}"
        )

    try:
        resultado = subprocess.run(
            config["command"],
            cwd=config["cwd"],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )

        stdout = _truncar_texto(
            resultado.stdout.strip(),
            MAX_CARACTERES_COMANDO,
        )

        stderr = _truncar_texto(
            resultado.stderr.strip(),
            MAX_CARACTERES_COMANDO,
        )

        partes = [
            f"Verificación: {nombre}",
            (
                "Exit code: "
                f"{resultado.returncode}"
            ),
        ]

        if stdout:
            partes.append(
                f"STDOUT:\n{stdout}"
            )

        if stderr:
            partes.append(
                f"STDERR:\n{stderr}"
            )

        salida = "\n\n".join(
            partes
        )

        if resultado.returncode == 0:
            return (
                "VERIFICACIÓN EXITOSA\n\n"
                + salida
            )

        return (
            "VERIFICACIÓN FALLIDA\n\n"
            + salida
        )

    except FileNotFoundError as error:
        return (
            "Error: No se encontró una herramienta "
            "necesaria para ejecutar la verificación: "
            f"{error}"
        )

    except subprocess.TimeoutExpired:
        return (
            f"Error: La verificación '{nombre}' "
            "excedió el timeout de 10 minutos."
        )

    except Exception as error:
        return (
            "Error ejecutando verificación: "
            f"{error}"
        )
