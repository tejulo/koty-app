# CrewAI Linear Status Transitions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the analyst to move the current Linear ticket to `In Progress` at workflow start and the reviewer to move it to `Done` only after deterministic verification and OpenSpec archive gates pass.

**Architecture:** Keep the existing sequential crew. Add two agent-specific Linear mutation tools backed by a shared GraphQL client and in-process evidence sets populated only by successful search, verification, validation, and archive calls; file writes invalidate stale evidence. Configure mutating agents to raise on `ToolFailure` so a rejected transition aborts the crew.

**Tech Stack:** Python 3.12, CrewAI 1.15.16 classic YAML configuration, `requests`, Pydantic-backed CrewAI tools, pytest, Linear GraphQL API, OpenSpec CLI.

## Global Constraints

- Keep CrewAI pinned at `1.15.16`; upgrading to `1.15.17` is outside this change.
- Linear scope is team key `DEV` and project name `koty-app`.
- `In Progress` state ID is `008d4363-c312-4d53-86d4-ad2210650291`.
- `Done` state ID is `10a67bb1-f5aa-4fe6-ae85-213f792d5a48`.
- Mutations send only `stateId` and always verify the resulting state with a fresh query.
- A failure after `In Progress` does not restore the previous state automatically.
- Do not expose a generic tool that accepts an arbitrary Linear state ID.
- Do not call real Linear, OpenSpec, or project verification commands from tests.

---

### Task 1: Linear GraphQL Client and Analyst Start Tool

**Files:**
- Modify: `crewai/src/crew/tools/custom_tool.py:1-337`
- Test: `crewai/tests/test_custom_tool.py`

**Interfaces:**
- Produces: `_obtener_tarea_linear(ticket_id: str) -> dict[str, Any]`
- Produces: `_cambiar_estado_linear(ticket_id: str, estados_origen: set[str], state_id: str, estado_destino: str) -> dict[str, Any]`
- Produces: `marcar_tarea_en_progreso_linear(ticket_id: str) -> str | ToolFailure`
- Produces: `_TICKETS_CONSULTADOS: set[str]` and `_TICKETS_INICIADOS: set[str]`
- Consumes: `LINEAR_API_KEY` and the existing `requests` dependency.

- [ ] **Step 1: Add failing tests for required search-before-start behavior**

Append these imports and tests to `crewai/tests/test_custom_tool.py`:

```python
from crewai.tools.tool_failure import ToolFailure

import crew.tools.custom_tool as tools_module
from crew.tools.custom_tool import (
    marcar_tarea_en_progreso_linear,
)


@pytest.fixture(autouse=True)
def limpiar_evidencia_linear():
    tools_module._TICKETS_CONSULTADOS.clear()
    tools_module._TICKETS_INICIADOS.clear()
    yield
    tools_module._TICKETS_CONSULTADOS.clear()
    tools_module._TICKETS_INICIADOS.clear()


def test_iniciar_ticket_exige_busqueda_previa():
    resultado = marcar_tarea_en_progreso_linear.func("DEV-5")

    assert isinstance(resultado, ToolFailure)
    assert resultado.code == "TICKET_NOT_QUERIED"


def test_iniciar_ticket_actualiza_y_registra_evidencia(monkeypatch):
    llamada = {}
    tools_module._TICKETS_CONSULTADOS.add("DEV-5")

    def cambiar(ticket_id, estados_origen, state_id, estado_destino):
        llamada.update(
            ticket_id=ticket_id,
            estados_origen=estados_origen,
            state_id=state_id,
            estado_destino=estado_destino,
        )
        return {"identifier": "DEV-5", "state": {"name": "In Progress"}}

    monkeypatch.setattr(tools_module, "_cambiar_estado_linear", cambiar)

    resultado = marcar_tarea_en_progreso_linear.func("dev-5")

    assert resultado == "Ticket DEV-5 confirmado en In Progress."
    assert tools_module._TICKETS_INICIADOS == {"DEV-5"}
    assert llamada == {
        "ticket_id": "DEV-5",
        "estados_origen": {"Backlog", "Todo"},
        "state_id": "008d4363-c312-4d53-86d4-ad2210650291",
        "estado_destino": "In Progress",
    }


def test_iniciar_ticket_convierte_rechazo_en_tool_failure(monkeypatch):
    tools_module._TICKETS_CONSULTADOS.add("DEV-5")

    def cambiar(*args, **kwargs):
        raise RuntimeError("El ticket está en Canceled")

    monkeypatch.setattr(tools_module, "_cambiar_estado_linear", cambiar)

    resultado = marcar_tarea_en_progreso_linear.func("DEV-5")

    assert isinstance(resultado, ToolFailure)
    assert resultado.code == "LINEAR_START_REJECTED"
    assert "Canceled" in resultado.message
    assert not tools_module._TICKETS_INICIADOS
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```bash
uv run pytest tests/test_custom_tool.py -k "iniciar_ticket" -v
```

Expected: collection fails because `marcar_tarea_en_progreso_linear` and the evidence sets do not exist.

- [ ] **Step 3: Add the shared Linear helpers and evidence sets**

In `crewai/src/crew/tools/custom_tool.py`, add `Any` and `ToolFailure` imports, constants, and helpers before the Linear tools:

```python
from typing import Any

from crewai.tools.tool_failure import ToolFailure

LINEAR_URL = "https://api.linear.app/graphql"
LINEAR_TEAM_KEY = "DEV"
LINEAR_PROJECT_NAME = "koty-app"
LINEAR_IN_PROGRESS_STATE_ID = "008d4363-c312-4d53-86d4-ad2210650291"
LINEAR_DONE_STATE_ID = "10a67bb1-f5aa-4fe6-ae85-213f792d5a48"

_TICKETS_CONSULTADOS: set[str] = set()
_TICKETS_INICIADOS: set[str] = set()


def _normalizar_ticket_id(ticket_id: str) -> str:
    normalizado = ticket_id.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]*-\d+", normalizado):
        raise ValueError("El ticket debe usar un identificador como DEV-5.")
    return normalizado


def _solicitar_linear(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        raise RuntimeError("Falta la variable LINEAR_API_KEY.")

    response = requests.post(
        LINEAR_URL,
        json={"query": query, "variables": variables},
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        mensajes = "; ".join(
            error.get("message", "Error desconocido")
            for error in payload["errors"]
        )
        raise RuntimeError(f"Linear rechazó la operación: {mensajes}")
    return payload.get("data", {})


def _obtener_tarea_linear(ticket_id: str) -> dict[str, Any]:
    query = """
    query Issue($id: String!) {
      issue(id: $id) {
        id identifier title description priority priorityLabel
        state { id name }
        project { id name }
        team { id key name }
      }
    }
    """
    issue = _solicitar_linear(query, {"id": ticket_id}).get("issue")
    if not issue:
        raise RuntimeError(f"No se encontró el ticket '{ticket_id}'.")
    if (issue.get("team") or {}).get("key") != LINEAR_TEAM_KEY:
        raise RuntimeError("El ticket no pertenece al team dev.")
    if (issue.get("project") or {}).get("name") != LINEAR_PROJECT_NAME:
        raise RuntimeError("El ticket no pertenece al proyecto koty-app.")
    return issue


def _cambiar_estado_linear(
    ticket_id: str,
    estados_origen: set[str],
    state_id: str,
    estado_destino: str,
) -> dict[str, Any]:
    issue = _obtener_tarea_linear(ticket_id)
    estado_actual = (issue.get("state") or {}).get("name")
    if estado_actual not in estados_origen:
        permitidos = ", ".join(sorted(estados_origen))
        raise RuntimeError(
            f"El ticket está en '{estado_actual}'; se esperaba {permitidos}."
        )

    mutation = """
    mutation IssueUpdate($id: String!, $stateId: String!) {
      issueUpdate(id: $id, input: {stateId: $stateId}) { success }
    }
    """
    resultado = _solicitar_linear(
        mutation,
        {"id": ticket_id, "stateId": state_id},
    ).get("issueUpdate") or {}
    if not resultado.get("success"):
        raise RuntimeError("Linear no confirmó issueUpdate.")

    actualizado = _obtener_tarea_linear(ticket_id)
    estado_confirmado = (actualizado.get("state") or {}).get("name")
    if estado_confirmado != estado_destino:
        raise RuntimeError(
            f"La postcondición falló: estado recibido '{estado_confirmado}'."
        )
    return actualizado
```

Refactor `buscar_tarea_linear` to call `_normalizar_ticket_id` and `_obtener_tarea_linear`. After a successful scoped query, execute:

```python
_TICKETS_CONSULTADOS.add(issue["identifier"].upper())
```

Keep its current concise formatting and truncation behavior. Convert helper exceptions to `ToolFailure(message=str(error), code="LINEAR_QUERY_FAILED", retryable=False)`.

- [ ] **Step 4: Implement the analyst mutation tool**

Add below `buscar_tarea_linear`:

```python
@tool("Marcar Tarea en Progreso")
def marcar_tarea_en_progreso_linear(ticket_id: str) -> str | ToolFailure:
    """Moves the previously queried Linear ticket from Backlog/Todo to In Progress."""
    try:
        normalizado = _normalizar_ticket_id(ticket_id)
        if normalizado not in _TICKETS_CONSULTADOS:
            return ToolFailure(
                message="Debes buscar este ticket antes de iniciarlo.",
                code="TICKET_NOT_QUERIED",
                retryable=False,
            )
        _cambiar_estado_linear(
            normalizado,
            {"Backlog", "Todo"},
            LINEAR_IN_PROGRESS_STATE_ID,
            "In Progress",
        )
        _TICKETS_INICIADOS.add(normalizado)
        return f"Ticket {normalizado} confirmado en In Progress."
    except Exception as error:
        return ToolFailure(
            message=str(error),
            code="LINEAR_START_REJECTED",
            retryable=False,
        )
```

- [ ] **Step 5: Run the focused and existing tests**

Run:

```bash
uv run pytest tests/test_custom_tool.py -k "iniciar_ticket" -v
uv run pytest tests/test_custom_tool.py -v
```

Expected: all selected tests pass; all existing OpenSpec tool tests remain green.

- [ ] **Step 6: Commit the analyst transition**

```bash
git add crewai/src/crew/tools/custom_tool.py crewai/tests/test_custom_tool.py
git commit -m "feat: start Linear tickets from analyst"
```

---

### Task 2: Verification Evidence and Reviewer Completion Gate

**Files:**
- Modify: `crewai/src/crew/tools/custom_tool.py:402-916`
- Test: `crewai/tests/test_custom_tool.py`

**Interfaces:**
- Consumes: `_TICKETS_INICIADOS` and `_cambiar_estado_linear` from Task 1.
- Produces: `_VERIFICACIONES_EXITOSAS`, `_CAMBIOS_VALIDADOS`, `_CAMBIOS_ARCHIVADOS`.
- Produces: `completar_tarea_linear(ticket_id: str, change_id: str) -> str | ToolFailure`.

- [ ] **Step 1: Add failing tests for evidence invalidation and completion rejection**

Extend the autouse fixture to clear the three new evidence sets, then add:

```python
from crew.tools.custom_tool import completar_tarea_linear


def test_completar_ticket_rechaza_evidencia_incompleta():
    tools_module._TICKETS_INICIADOS.add("DEV-5")

    resultado = completar_tarea_linear.func("DEV-5", "dev-5")

    assert isinstance(resultado, ToolFailure)
    assert resultado.code == "COMPLETION_GATE_REJECTED"
    assert "verificaciones" in resultado.message


def test_escritura_invalida_verificaciones(monkeypatch, tmp_path):
    monkeypatch.setattr(tools_module, "PROJECT_ROOT", tmp_path)
    tools_module._VERIFICACIONES_EXITOSAS.update(
        {"python", "lint", "test", "build"}
    )

    resultado = tools_module.escribir_archivo_raiz.func("src/app.py", "x = 1\n")

    assert "guardado correctamente" in resultado
    assert tools_module._VERIFICACIONES_EXITOSAS == set()


def test_escritura_openspec_invalida_validacion(monkeypatch, tmp_path):
    monkeypatch.setattr(tools_module, "PROJECT_ROOT", tmp_path)
    tools_module._CAMBIOS_VALIDADOS.add("dev-5")
    tools_module._CAMBIOS_ARCHIVADOS.add("dev-5")

    tools_module.escribir_archivo_raiz.func(
        "openspec/changes/dev-5/tasks.md",
        "- [x] Implementar\n",
    )

    assert "dev-5" not in tools_module._CAMBIOS_VALIDADOS
    assert "dev-5" not in tools_module._CAMBIOS_ARCHIVADOS
```

- [ ] **Step 2: Run the evidence tests and verify they fail**

Run:

```bash
uv run pytest tests/test_custom_tool.py -k "completar_ticket or invalida" -v
```

Expected: collection fails because the evidence sets and completion tool do not exist.

- [ ] **Step 3: Add evidence sets and write invalidation**

Add with the existing Linear sets:

```python
_VERIFICACIONES_EXITOSAS: set[str] = set()
_CAMBIOS_VALIDADOS: set[str] = set()
_CAMBIOS_ARCHIVADOS: set[str] = set()


def _invalidar_evidencia_por_escritura(ruta: Path) -> None:
    _VERIFICACIONES_EXITOSAS.clear()
    partes = ruta.relative_to(PROJECT_ROOT).parts
    if len(partes) >= 3 and partes[:2] == ("openspec", "changes"):
        change_id = partes[2]
        if change_id != "archive":
            _CAMBIOS_VALIDADOS.discard(change_id)
            _CAMBIOS_ARCHIVADOS.discard(change_id)
```

Call `_invalidar_evidencia_por_escritura(ruta)` immediately after a successful `ruta.write_text(...)` in `escribir_archivo_raiz`.

- [ ] **Step 4: Record real verification, validation, and archive outcomes**

In `ejecutar_verificacion`, update evidence before returning:

```python
if resultado.returncode == 0:
    _VERIFICACIONES_EXITOSAS.add(nombre)
    return "VERIFICACIÓN EXITOSA\n\n" + salida

_VERIFICACIONES_EXITOSAS.discard(nombre)
return "VERIFICACIÓN FALLIDA\n\n" + salida
```

Change `ejecutar_openspec` to return `str | ToolFailure`. Before invoking
`subprocess.run`, reject an archive without current validation evidence:

```python
if (
    argumentos[0] == "archive"
    and argumentos[1] not in _CAMBIOS_VALIDADOS
):
    return ToolFailure(
        message="El cambio debe validarse antes de archivarse.",
        code="CHANGE_NOT_VALIDATED",
        retryable=False,
    )
```

Then use the already parsed `argumentos` and update evidence only on exit code zero:

```python
if resultado.returncode == 0:
    if argumentos[0] == "validate":
        _CAMBIOS_VALIDADOS.add(argumentos[1])
    elif argumentos[0] == "archive":
        _CAMBIOS_ARCHIVADOS.add(argumentos[1])
    return "Éxito OpenSpec\n\n" + salida

if argumentos[0] == "validate" and len(argumentos) > 1:
    _CAMBIOS_VALIDADOS.discard(argumentos[1])
if argumentos[0] == "archive" and len(argumentos) > 1:
    _CAMBIOS_ARCHIVADOS.discard(argumentos[1])
return "Error de OpenSpec\n\n" + salida
```

- [ ] **Step 5: Add tests that successful commands record evidence**

Add:

```python
def test_verificacion_exitosa_registra_evidencia(monkeypatch):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", run)

    tools_module.ejecutar_verificacion.func("python")

    assert "python" in tools_module._VERIFICACIONES_EXITOSAS


def test_validate_y_archive_registran_evidencia(monkeypatch):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(subprocess, "run", run)

    tools_module.ejecutar_openspec.func(
        "validate dev-5 --strict --no-interactive"
    )
    tools_module.ejecutar_openspec.func("archive dev-5 --yes")

    assert tools_module._CAMBIOS_VALIDADOS == {"dev-5"}
    assert tools_module._CAMBIOS_ARCHIVADOS == {"dev-5"}


def test_archive_sin_validate_no_ejecuta_subprocess(monkeypatch):
    def run(*args, **kwargs):
        raise AssertionError("subprocess no debe ejecutarse")

    monkeypatch.setattr(subprocess, "run", run)

    resultado = tools_module.ejecutar_openspec.func("archive dev-5 --yes")

    assert isinstance(resultado, ToolFailure)
    assert resultado.code == "CHANGE_NOT_VALIDATED"
```

- [ ] **Step 6: Add the reviewer completion tool and archive postcondition helper**

Add after the Linear start tool:

```python
def _buscar_directorio_archivado(change_id: str) -> Path:
    activos = PROJECT_ROOT / "openspec" / "changes" / change_id
    if activos.exists():
        raise RuntimeError("El cambio OpenSpec todavía está activo.")

    archive_root = PROJECT_ROOT / "openspec" / "changes" / "archive"
    candidatos = sorted(archive_root.glob(f"*-{change_id}"))
    if len(candidatos) != 1 or not candidatos[0].is_dir():
        raise RuntimeError("No existe un único archive confirmado para el cambio.")

    tasks_path = candidatos[0] / "tasks.md"
    if not tasks_path.is_file():
        raise RuntimeError("El archive no contiene tasks.md.")
    tasks = tasks_path.read_text(encoding="utf-8")
    if re.search(r"^\s*-\s*\[ \]", tasks, flags=re.MULTILINE):
        raise RuntimeError("El archive conserva tareas pendientes.")
    return candidatos[0]


@tool("Completar Tarea en Linear")
def completar_tarea_linear(
    ticket_id: str,
    change_id: str,
) -> str | ToolFailure:
    """Moves the current ticket to Done only after all local completion gates pass."""
    try:
        normalizado = _normalizar_ticket_id(ticket_id)
        if normalizado not in _TICKETS_INICIADOS:
            raise RuntimeError("Este proceso no inició el ticket indicado.")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", change_id):
            raise RuntimeError("El change-id no usa kebab-case válido.")
        if change_id != normalizado.lower():
            raise RuntimeError("El change-id no corresponde al ticket iniciado.")

        requeridas = {"python", "lint", "test", "build"}
        faltantes = sorted(requeridas - _VERIFICACIONES_EXITOSAS)
        if faltantes:
            raise RuntimeError(
                "Faltan verificaciones exitosas: " + ", ".join(faltantes)
            )
        if change_id not in _CAMBIOS_VALIDADOS:
            raise RuntimeError("Falta OpenSpec validate exitoso vigente.")
        if change_id not in _CAMBIOS_ARCHIVADOS:
            raise RuntimeError("Falta OpenSpec archive exitoso.")

        _buscar_directorio_archivado(change_id)
        _cambiar_estado_linear(
            normalizado,
            {"In Progress"},
            LINEAR_DONE_STATE_ID,
            "Done",
        )
        return f"Ticket {normalizado} confirmado en Done."
    except Exception as error:
        return ToolFailure(
            message=str(error),
            code="COMPLETION_GATE_REJECTED",
            retryable=False,
        )
```

- [ ] **Step 7: Add the successful completion test**

```python
def test_completar_ticket_actualiza_done_con_gate_completo(monkeypatch, tmp_path):
    monkeypatch.setattr(tools_module, "PROJECT_ROOT", tmp_path)
    archive = tmp_path / "openspec/changes/archive/2026-08-22-dev-5"
    archive.mkdir(parents=True)
    (archive / "tasks.md").write_text("- [x] Implementar\n", encoding="utf-8")

    tools_module._TICKETS_INICIADOS.add("DEV-5")
    tools_module._VERIFICACIONES_EXITOSAS.update(
        {"python", "lint", "test", "build"}
    )
    tools_module._CAMBIOS_VALIDADOS.add("dev-5")
    tools_module._CAMBIOS_ARCHIVADOS.add("dev-5")
    llamada = {}

    def cambiar(ticket_id, estados_origen, state_id, estado_destino):
        llamada.update(
            ticket_id=ticket_id,
            estados_origen=estados_origen,
            state_id=state_id,
            estado_destino=estado_destino,
        )
        return {"identifier": "DEV-5", "state": {"name": "Done"}}

    monkeypatch.setattr(tools_module, "_cambiar_estado_linear", cambiar)

    resultado = completar_tarea_linear.func("DEV-5", "dev-5")

    assert resultado == "Ticket DEV-5 confirmado en Done."
    assert llamada["state_id"] == "10a67bb1-f5aa-4fe6-ae85-213f792d5a48"
    assert llamada["estados_origen"] == {"In Progress"}
```

- [ ] **Step 8: Run all custom tool tests**

Run:

```bash
uv run pytest tests/test_custom_tool.py -v
```

Expected: all tests pass, including existing OpenSpec allowlist tests.

- [ ] **Step 9: Commit the reviewer completion gate**

```bash
git add crewai/src/crew/tools/custom_tool.py crewai/tests/test_custom_tool.py
git commit -m "feat: gate Linear completion after review"
```

---

### Task 3: Agent, Task, and Crew Wiring

**Files:**
- Modify: `crewai/src/crew/config/agents.yaml`
- Modify: `crewai/src/crew/config/tasks.yaml`
- Modify: `crewai/src/crew/crew.py:29-193`
- Create: `crewai/tests/test_crew.py`

**Interfaces:**
- Consumes: `marcar_tarea_en_progreso_linear` and `completar_tarea_linear` from Tasks 1-2.
- Produces: analyst with search/start tools and reviewer with read/verify/OpenSpec/complete tools.

- [ ] **Step 1: Write failing agent wiring tests**

Create `crewai/tests/test_crew.py`:

```python
from crew.crew import KotyAppCrew


def test_analyst_solo_recibe_tools_linear_de_inicio(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ANALYST_MODEL", "openai/gpt-4o-mini")

    agent = KotyAppCrew().analyst()

    assert {tool.name for tool in agent.tools} == {
        "Buscar Tarea en Linear",
        "Marcar Tarea en Progreso",
    }


def test_reviewer_recibe_completar_linear(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")

    agent = KotyAppCrew().reviewer()

    assert "Completar Tarea en Linear" in {tool.name for tool in agent.tools}
    assert "Marcar Tarea en Progreso" not in {tool.name for tool in agent.tools}
```

- [ ] **Step 2: Run the wiring tests and verify they fail**

Run:

```bash
uv run pytest tests/test_crew.py -v
```

Expected: FAIL because the new tools are not imported or assigned.

- [ ] **Step 3: Update agent responsibilities in YAML**

In `crewai/src/crew/config/agents.yaml`, extend `analyst.goal` and `analyst.backstory` with:

```yaml
    Debes iniciar el ticket en Linear antes de producir el análisis.

    Después de recuperar y validar el ticket, lo mueves a In Progress.
    Si Linear no confirma esa transición, detienes tu trabajo y no produces
    un análisis que habilite las etapas siguientes.
```

Extend `reviewer.goal` and `reviewer.backstory` with:

```yaml
    Solo al terminar satisfactoriamente debes completar el ticket en Linear.

    Done es la última acción del flujo. Solo la solicitas después de que todas
    las verificaciones pasaron, OpenSpec validó el cambio y el archive quedó
    confirmado. Si la tool rechaza la transición, la revisión no está aprobada.
```

- [ ] **Step 4: Make transition order explicit in tasks YAML**

In `analysis_task`, replace the initial instruction with these steps before the existing analysis list:

```yaml
    PASO 1:
    Usa obligatoriamente 'Buscar Tarea en Linear' para obtener
    el ticket '{ticket_id}'.

    PASO 2:
    Inmediatamente después usa 'Marcar Tarea en Progreso' con
    ticket_id='{ticket_id}'. No continúes si Linear no confirma
    el estado In Progress.

    PASO 3:
    Analiza el contenido recuperado.
```

Change its expected output to include `confirmación real de In Progress`.

At the end of `review_task`, after the existing archive step, add:

```yaml
    PASO 7:
    Verifica el resultado real del archive. Después vuelve a ejecutar
    'Ejecutar Verificacion' para python, lint, test y build, porque archive
    modifica archivos del repositorio.

    PASO 8:
    Solo si esas verificaciones posteriores al archive fueron exitosas usa
    'Completar Tarea en Linear' con ticket_id='{ticket_id}' y
    change_id='{change_id}'. Esta debe ser tu última acción.

    Si Linear no confirma Done, la revisión queda rechazada.
```

Change the review expected output to require the real `Done` confirmation when approved.

- [ ] **Step 5: Wire tools and failure policies in `crew.py`**

Add imports:

```python
from crewai.tools.tool_failure import ToolFailurePolicy

from .tools.custom_tool import (
    completar_tarea_linear,
    marcar_tarea_en_progreso_linear,
)
```

Add `marcar_tarea_en_progreso_linear` to `analyst.tools`, add `completar_tarea_linear` to `reviewer.tools`, and set this on both mutating agents:

```python
tool_failure_policy=ToolFailurePolicy.RAISE,
```

Add `# type: ignore[index]` to each `agents_config[...]` and `tasks_config[...]` access as required by `crewai/AGENTS.md`.

- [ ] **Step 6: Run wiring and complete test suites**

Run:

```bash
uv run pytest tests/test_crew.py -v
uv run pytest -v
uv run python -m compileall -q src/crew
```

Expected: all tests pass and compileall prints no errors.

- [ ] **Step 7: Validate YAML and construct the full crew without kickoff**

Run:

```bash
OPENCODE_API_KEY=test \
ZEN_ANALYST_MODEL=openai/gpt-4o-mini \
ZEN_ARCHITECT_MODEL=openai/gpt-4o-mini \
ZEN_CODER_MODEL=openai/gpt-4o-mini \
ZEN_REVIEWER_MODEL=openai/gpt-4o-mini \
uv run python -c "from crew.crew import KotyAppCrew; c=KotyAppCrew().crew(); assert len(c.agents) == 4; assert len(c.tasks) == 4; print('Crew wiring valid')"
```

Expected: `Crew wiring valid` with no LLM or Linear call.

- [ ] **Step 8: Review the final diff**

Run:

```bash
git diff --check
```

Expected: no whitespace errors; diff contains only the approved transition behavior and tests.

- [ ] **Step 9: Commit the CrewAI wiring**

```bash
git add crewai/src/crew/config/agents.yaml crewai/src/crew/config/tasks.yaml crewai/src/crew/crew.py crewai/tests/test_crew.py
git commit -m "feat: wire Linear status transitions into crew"
```
