# Reviewer Raw Result Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que el revisor concluya una ejecución aunque el modelo anteponga razonamiento a su objeto JSON final, sin desactivar sus herramientas ni aceptar resultados inválidos.

**Architecture:** La tarea final del revisor dejará de solicitar `output_pydantic=CrewResult`, porque CrewAI intenta validar esa respuesta dentro de `Task._export_output` y aborta `crew.kickoff()` antes de devolver su salida. El orquestador conservará la validación Pydantic, pero la aplicará a un objeto JSON `CrewResult` extraído del texto crudo ya devuelto por la crew. La extracción probará cada inicio de objeto JSON y aceptará solamente el primero que satisfaga el modelo completo.

**Tech Stack:** Python 3.12, CrewAI 1.15.16, Pydantic 2, pytest.

**Spec:** Diagnóstico en `.agent/crew/dev-36/logs/20260831-130118-468325.log:16369-16469` y contrato actual en `crewai/src/crew/models.py`.

## Global Constraints

- No actualizar CrewAI ni cambiar modelos o proveedores como parte de esta corrección.
- Mantener las herramientas configuradas para el revisor en `crewai/src/crew/crew.py`.
- No aceptar texto libre: el resultado final debe validar completamente contra `CrewResult`.
- No modificar ni borrar `.agent/crew/dev-36/`, `openspec/changes/dev-36/` ni los intentos históricos.
- Conservar la clasificación actual: una respuesta sin `CrewResult` válido se registra como fallo de infraestructura en runtime.
- No cambiar los presupuestos `MAX_TICKET_ATTEMPTS` o `MAX_INFRASTRUCTURE_ATTEMPTS`.

---

### Task 1: Evitar la conversión interna de CrewAI para el resultado del revisor

**Files:**
- Modify: `crewai/src/crew/crew.py:211-218`
- Modify: `crewai/tests/test_crew.py`

**Interfaces:**
- Consumes: `KotyAppCrew.review_task() -> Task`.
- Produces: una tarea de revisión que devuelve `TaskOutput.raw` sin que CrewAI intente convertirlo a `CrewResult` dentro de `Task._export_output`.

- [ ] **Step 1: Escribir la prueba que describe el límite de conversión**

Añadir una prueba que instancie la crew con las variables de entorno de prueba existentes y compruebe que el revisor mantiene sus herramientas, pero no define conversión Pydantic interna:

```python
def test_reviewer_leaves_final_result_as_raw_text(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")

    reviewer = KotyAppCrew()
    task = reviewer.review_task()

    assert task.output_pydantic is None
    assert reviewer.reviewer().tools
```

- [ ] **Step 2: Ejecutar la prueba y verificar que falla**

Run: `uv run pytest tests/test_crew.py::test_reviewer_leaves_final_result_as_raw_text -v`

Expected: FAIL porque `review_task()` actualmente usa `output_pydantic=CrewResult`.

- [ ] **Step 3: Eliminar solo la conversión Pydantic de `review_task()`**

Cambiar la construcción de la tarea para que conserve su configuración YAML y no pase `output_pydantic`:

```python
@task
def review_task(self) -> Task:
    return Task(
        config=self.tasks_config["review_task"],
    )
```

No cambiar `TesterResult`, `testing_task()`, los tools, ni la configuración del LLM.

- [ ] **Step 4: Ejecutar la prueba y verificar que pasa**

Run: `uv run pytest tests/test_crew.py::test_reviewer_leaves_final_result_as_raw_text -v`

Expected: PASS.

### Task 2: Validar un `CrewResult` únicamente después de obtener la salida cruda

**Files:**
- Modify: `crewai/src/crew/main.py:306-330`
- Modify: `crewai/tests/test_main.py`

**Interfaces:**
- Consumes: `parse_crew_result(output: object) -> CrewResult` y un objeto con atributos opcionales `pydantic` y `raw`.
- Produces: un `CrewResult` validado, o `RuntimeError` si ningún objeto JSON del texto crudo es un resultado válido.

- [ ] **Step 1: Escribir pruebas de extracción en el límite real**

Cubrir los tres casos sin llamar a un proveedor:

```python
def test_parse_crew_result_skips_reasoning_json_before_result():
    raw = '<think>{"step":"review"}</think>\n' + crew_result().model_dump_json()

    assert main_module.parse_crew_result(
        SimpleNamespace(pydantic=None, raw=raw)
    ) == crew_result()


def test_parse_crew_result_rejects_json_that_is_not_crew_result():
    with pytest.raises(RuntimeError, match="resultado estructurado"):
        main_module.parse_crew_result(
            SimpleNamespace(pydantic=None, raw='<think>{"step":"review"}</think>')
        )


def test_run_accepts_raw_reviewer_result_after_reasoning(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "PROJECT_ROOT", tmp_path)
    (tmp_path / "openspec" / "changes" / "dev-6").mkdir(parents=True)
    raw = '<think>{"step":"review"}</think>\n' + crew_result().model_dump_json()
    output = SimpleNamespace(pydantic=None, raw=raw)
    crew = SimpleNamespace(
        crew=lambda: SimpleNamespace(kickoff=lambda **_: output)
    )
    monkeypatch.setattr(main_module, "KotyAppCrew", lambda: crew)
    monkeypatch.setattr(main_module, "close_playwright_session", lambda: None)
    monkeypatch.setattr(main_module, "close_local_environment", lambda: None)
    monkeypatch.setattr(main_module.sys, "argv", ["run_crew", "DEV-6"])

    main_module.run()

    payload = json.loads(
        (tmp_path / "openspec" / "changes" / "dev-6" / "result.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload == crew_result().model_dump()
```

La tercera prueba debe simular `kickoff()` con `SimpleNamespace(pydantic=None, raw=raw)` para probar la secuencia completa que anteriormente quedaba sin cubrir: `kickoff()` devuelve, luego `run()` llama al parser y persiste el resultado.

- [ ] **Step 2: Ejecutar las pruebas y verificar que al menos la del JSON señuelo falla**

Run: `uv run pytest tests/test_main.py -k "reasoning or raw_reviewer or rejects_json" -v`

Expected: FAIL porque el parser actual usa `raw.find("{")` y valida el primer objeto, aunque sea parte del razonamiento.

- [ ] **Step 3: Hacer que el parser pruebe cada objeto JSON y valide el modelo completo**

Conservar los accesos rápidos para `output.pydantic`. Para texto crudo, recorrer cada carácter `{`, decodificar un objeto desde allí y retornar solo el primer payload que pase `CrewResult.model_validate`:

```python
decoder = json.JSONDecoder()

for start, character in enumerate(raw):
    if character != "{":
        continue

    try:
        payload, _ = decoder.raw_decode(raw[start:])
        return CrewResult.model_validate(payload)
    except (json.JSONDecodeError, ValidationError):
        continue

raise RuntimeError("Reviewer no devolvió un resultado estructurado válido")
```

Importar `ValidationError` desde `pydantic`. No convertir objetos JSON que no coincidan con el contrato en resultados parciales o por defecto.

- [ ] **Step 4: Ejecutar las pruebas de parser y flujo completo**

Run: `uv run pytest tests/test_main.py -k "reasoning or raw_reviewer or rejects_json" -v`

Expected: PASS.

- [ ] **Step 5: Ejecutar la suite Python completa**

Run: `uv run pytest`

Expected: PASS, incluyendo los tests existentes de ejecución, reanudación, presupuesto de infraestructura y logging de errores.

### Task 3: Verificar el launcher y recuperar DEV-36 con una ejecución nueva

**Files:**
- Test: `scripts/tests/ralph.test.sh`
- Runtime evidence only: `.agent/crew/dev-36/logs/` and `openspec/changes/dev-36/result.json`

**Interfaces:**
- Consumes: `ralph.sh --until-finalized --resume` y la propagación existente de `--resume` al primer ciclo.
- Produces: una segunda ejecución de DEV-36 sin alterar logs, intentos o estado de la ejecución fallida.

- [ ] **Step 1: Ejecutar la regresión del launcher sin cambios funcionales**

Run: `bash scripts/tests/ralph.test.sh`

Expected: PASS. Esta comprobación garantiza que `--resume` continúa enviándose una sola vez al launcher y no reinicia cada ciclo de Ralph.

- [ ] **Step 2: Comprobar formato y errores estáticos del cambio**

Run: `git diff --check`

Expected: PASS.

Run: `uv run python -m compileall -q src/crew`

Expected: PASS.

- [ ] **Step 3: Ejecutar DEV-36 como una ejecución nueva, solo después de aprobar y aplicar Tasks 1-2**

Run: `./ralph.sh --until-finalized --resume`

Expected: `execution.json` pasa a `number: 2`; no se eliminan `attempt-001.md`, `attempt-002.md` ni logs previos; la crew alcanza el revisor sin un `ConverterError` causado por el prefijo `<think>`.

- [ ] **Step 4: Inspeccionar el resultado real antes de diagnosticar DEV-36**

Run: `git diff --check`

Expected: PASS.

Revisar el último archivo en `.agent/crew/dev-36/logs/`, `execution.json` y `openspec/changes/dev-36/result.json`. Si DEV-36 falla después de este cambio, clasificar el nuevo fallo por su propio mensaje; no atribuirlo automáticamente a salida estructurada.

- [ ] **Step 5: Commit**

```bash
git add crewai/src/crew/crew.py crewai/src/crew/main.py crewai/tests/test_crew.py crewai/tests/test_main.py docs/superpowers/plans/2026-08-31-reviewer-raw-result-fallback.md
git commit -m "fix: parse reviewer result after crew completion"
```

No incluir artefactos DEV-36 ni cambios no relacionados de auditoría en este commit.

## Plan Self-Review

- Cobertura: evita la conversión que aborta `kickoff()`, conserva validación estricta, cubre prefijos de razonamiento y JSON señuelo, conserva recuperación y documenta la ejecución de DEV-36.
- Límites: no modifica modelo, proveedor, límites de intentos, herramientas ni artefactos históricos.
- Consistencia: `review_task()` produce texto crudo; `parse_crew_result()` es el único punto que convierte ese texto en `CrewResult`; `run()` conserva su tratamiento actual de errores de infraestructura.
