import json
import os
import shlex
import shutil
import signal
import subprocess
import time
from pathlib import Path

import requests
from crewai.tools import tool
from crewai.tools.tool_failure import ToolFailure

from ..linear_api import get_issue


PROJECT_ROOT = Path(__file__).resolve().parents[4]
CREWAI_ROOT = Path(__file__).resolve().parents[3]

MAX_FILES = 120
MAX_FILE_CHARS = 20_000
MAX_COMMAND_CHARS = 12_000
MAX_DEPTH = 4

IGNORED_DIRS = {
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
    ".playwright-cli",
    "playwright-report",
    "test-results",
    "coverage",
    "dist",
    "build",
}

_dev_process: subprocess.Popen | None = None
_dev_log = None

DEV_LOG = Path("/tmp/koty-app-dev.log")


def _truncate(
    text: str,
    limit: int,
) -> str:
    if len(text) <= limit:
        return text

    head = limit // 3

    return (
        text[:head]
        + "\n\n...[TRUNCADO]...\n\n"
        + text[-(limit - head):]
    )


def _resolve(relative: str) -> Path:
    if not relative:
        raise ValueError("Ruta vacía")

    path = (
        PROJECT_ROOT / relative
    ).resolve()

    if not path.is_relative_to(PROJECT_ROOT):
        raise ValueError(
            "La ruta sale del repositorio"
        )

    return path


def _ignored(path: Path) -> bool:
    parts = set(
        path.relative_to(PROJECT_ROOT).parts
    )

    return bool(
        parts & IGNORED_DIRS
    )


def _run(
    command: list[str],
    cwd: Path = PROJECT_ROOT,
    timeout: int = 600,
    env: dict | None = None,
) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )

    except FileNotFoundError as error:
        return 127, str(error)

    except subprocess.TimeoutExpired:
        return 124, "Timeout"

    output = "\n\n".join(
        part
        for part in [
            f"Exit code: {result.returncode}",
            (
                f"STDOUT:\n{result.stdout.strip()}"
                if result.stdout.strip()
                else ""
            ),
            (
                f"STDERR:\n{result.stderr.strip()}"
                if result.stderr.strip()
                else ""
            ),
        ]
        if part
    )

    return (
        result.returncode,
        _truncate(
            output,
            MAX_COMMAND_CHARS,
        ),
    )


@tool("Buscar Tarea en Linear")
def buscar_tarea_linear(
    ticket_id: str,
) -> str | ToolFailure:
    """Obtiene un ticket real desde Linear."""

    try:
        issue = get_issue(ticket_id)

        return _truncate(
            json.dumps(
                issue,
                ensure_ascii=False,
                indent=2,
            ),
            MAX_FILE_CHARS,
        )

    except Exception as error:
        return ToolFailure(
            message=str(error),
            code="LINEAR_QUERY_FAILED",
            retryable=False,
        )


@tool("Leer Archivo en Raiz")
def leer_archivo_raiz(
    ruta_relativa: str,
) -> str:
    """Lee un archivo dentro del repositorio."""

    try:
        path = _resolve(ruta_relativa)

        if _ignored(path):
            return "Error: ruta ignorada"

        if not path.is_file():
            return (
                f"Error: no existe {ruta_relativa}"
            )

        return _truncate(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            ),
            MAX_FILE_CHARS,
        )

    except Exception as error:
        return f"Error: {error}"


@tool("Escribir Archivo en Raiz")
def escribir_archivo_raiz(
    ruta_relativa: str,
    contenido: str,
) -> str:
    """Crea o reemplaza un archivo del repositorio."""

    try:
        path = _resolve(ruta_relativa)

        if _ignored(path):
            return "Error: ruta ignorada"

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_text(
            contenido,
            encoding="utf-8",
        )

        return (
            f"Archivo guardado: {ruta_relativa}"
        )

    except Exception as error:
        return f"Error: {error}"


@tool("Listar Archivos en Raiz")
def listar_archivos_raiz(
    ruta_relativa: str = ".",
    profundidad_maxima: int = 2,
) -> str:
    """Lista archivos sin recorrer dependencias."""

    try:
        root = _resolve(ruta_relativa)

        if _ignored(root):
            return "Error: ruta ignorada"

        if not root.exists():
            return "Error: ruta inexistente"

        depth_limit = min(
            max(profundidad_maxima, 1),
            MAX_DEPTH,
        )

        files: list[str] = []

        for current, dirs, names in os.walk(
            root,
            followlinks=False,
        ):
            current_path = Path(current)

            depth = len(
                current_path
                .relative_to(root)
                .parts
            )

            dirs[:] = [
                directory
                for directory in dirs
                if directory not in IGNORED_DIRS
            ]

            if depth >= depth_limit:
                dirs[:] = []

            for name in sorted(names):
                path = current_path / name

                files.append(
                    path
                    .relative_to(PROJECT_ROOT)
                    .as_posix()
                )

                if len(files) >= MAX_FILES:
                    return (
                        "\n".join(files)
                        + "\n...[LISTADO TRUNCADO]"
                    )

        return (
            "\n".join(files)
            if files
            else "(vacío)"
        )

    except Exception as error:
        return f"Error: {error}"


@tool("Ejecutar OpenSpec")
def ejecutar_openspec(
    comando_openspec: str,
) -> str:
    """
    Ejecuta únicamente operaciones OpenSpec
    no destructivas.
    """

    try:
        args = shlex.split(
            comando_openspec
        )

        valid = (
            args == [
                "validate",
                "--all",
                "--strict",
            ]
            or (
                len(args) == 4
                and args[0] == "validate"
                and args[2:] == [
                    "--strict",
                    "--no-interactive",
                ]
            )
            or args == ["list"]
            or (
                len(args) == 2
                and args[0] == "show"
            )
            or (
                len(args) == 3
                and args[:2]
                == ["status", "--change"]
            )
        )

        if not valid:
            return (
                "Error: comando OpenSpec "
                "no permitido"
            )

        code, output = _run(
            [
                "pnpm",
                "exec",
                "openspec",
                *args,
            ],
            timeout=60,
            env={
                **os.environ,
                "OPENSPEC_TELEMETRY": "0",
            },
        )

        prefix = (
            "ÉXITO OPENSPEC"
            if code == 0
            else "ERROR OPENSPEC"
        )

        return f"{prefix}\n\n{output}"

    except Exception as error:
        return f"Error: {error}"


@tool("Ejecutar Verificacion")
def ejecutar_verificacion(
    verificacion: str,
) -> str:
    """Ejecuta python, lint, test o build."""

    commands = {
        "python": (
            [
                "uv",
                "run",
                "python",
                "-m",
                "compileall",
                "-q",
                "src/crew",
            ],
            CREWAI_ROOT,
        ),
        "lint": (
            ["pnpm", "lint"],
            PROJECT_ROOT,
        ),
        "test": (
            ["pnpm", "test"],
            PROJECT_ROOT,
        ),
        "build": (
            ["pnpm", "build"],
            PROJECT_ROOT,
        ),
    }

    name = verificacion.strip().lower()

    if name not in commands:
        return (
            "Error: usa python, lint, test o build"
        )

    command, cwd = commands[name]

    code, output = _run(
        command,
        cwd=cwd,
    )

    prefix = (
        "VERIFICACIÓN EXITOSA"
        if code == 0
        else "VERIFICACIÓN FALLIDA"
    )

    return (
        f"{prefix}: {name}\n\n{output}"
    )


PLAYWRIGHT_COMMANDS = {
    "open",
    "goto",
    "close",
    "snapshot",
    "click",
    "dblclick",
    "fill",
    "type",
    "select",
    "check",
    "uncheck",
    "hover",
    "press",
    "reload",
    "go-back",
    "go-forward",
    "screenshot",
    "console",
    "network",
    "tracing-start",
    "tracing-stop",
    "verify-element-visible",
    "verify-text-visible",
    "verify-list-visible",
    "verify-value",
    "dialog-accept",
    "dialog-dismiss",
}


def _playwright_env() -> dict:
    return {
        **os.environ,
        "PLAYWRIGHT_CLI_SESSION": os.environ.get(
            "PLAYWRIGHT_CLI_SESSION",
            "koty-crew",
        ),
    }


@tool("Ejecutar Playwright")
def ejecutar_playwright(
    argumentos: str,
) -> str:
    """Ejecuta comandos controlados de Playwright CLI."""

    if not shutil.which("playwright-cli"):
        return (
            "ERROR PLAYWRIGHT: "
            "playwright-cli no está instalado"
        )

    try:
        args = shlex.split(argumentos)

        if (
            not args
            or args[0] not in PLAYWRIGHT_COMMANDS
        ):
            return (
                "ERROR PLAYWRIGHT: "
                "comando no permitido"
            )

        code, output = _run(
            [
                "playwright-cli",
                *args,
            ],
            timeout=180,
            env=_playwright_env(),
        )

        prefix = (
            "PLAYWRIGHT OK"
            if code == 0
            else "PLAYWRIGHT ERROR"
        )

        return f"{prefix}\n\n{output}"

    except Exception as error:
        return (
            f"PLAYWRIGHT ERROR: {error}"
        )


def _local_url() -> str:
    return os.environ.get(
        "LOCAL_APP_URL",
        "http://127.0.0.1:3000",
    )


def _local_ready() -> bool:
    try:
        response = requests.get(
            _local_url(),
            timeout=2,
        )

        return response.status_code < 500

    except requests.RequestException:
        return False


def _dev_log_tail() -> str:
    if not DEV_LOG.exists():
        return ""

    return _truncate(
        DEV_LOG.read_text(
            encoding="utf-8",
            errors="replace",
        ),
        4000,
    )


def start_local_environment() -> str:
    global _dev_process
    global _dev_log

    if (
        _dev_process
        and _dev_process.poll() is None
    ):
        return f"READY {_local_url()}"

    command = shlex.split(
        os.environ.get(
            "LOCAL_DEV_COMMAND",
            "pnpm dev",
        )
    )

    _dev_log = DEV_LOG.open(
        "w",
        encoding="utf-8",
    )

    _dev_process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=_dev_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        text=True,
    )

    for _ in range(90):
        if _dev_process.poll() is not None:
            return (
                "ERROR LOCAL ENV\n"
                + _dev_log_tail()
            )

        if _local_ready():
            return f"READY {_local_url()}"

        time.sleep(1)

    return (
        "ERROR LOCAL ENV: timeout\n"
        + _dev_log_tail()
    )


def close_local_environment() -> None:
    global _dev_process
    global _dev_log

    if (
        _dev_process
        and _dev_process.poll() is None
    ):
        try:
            os.killpg(
                _dev_process.pid,
                signal.SIGTERM,
            )

            _dev_process.wait(timeout=10)

        except Exception:
            try:
                os.killpg(
                    _dev_process.pid,
                    signal.SIGKILL,
                )
            except Exception:
                pass

    if _dev_log:
        _dev_log.close()

    _dev_process = None
    _dev_log = None


def close_playwright_session() -> None:
    if not shutil.which("playwright-cli"):
        return

    subprocess.run(
        [
            "playwright-cli",
            "close",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        env=_playwright_env(),
        check=False,
    )


@tool("Gestionar Entorno Local")
def gestionar_entorno_local(
    accion: str,
) -> str:
    """Inicia o detiene el entorno local."""

    action = accion.strip().lower()

    if action == "start":
        return start_local_environment()

    if action == "status":
        return (
            f"READY {_local_url()}"
            if _local_ready()
            else "NOT_READY"
        )

    if action == "stop":
        close_local_environment()
        return "STOPPED"

    return "Error: usa start, status o stop"
