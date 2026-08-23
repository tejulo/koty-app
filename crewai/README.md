# Koty App CrewAI

Automatización del flujo de desarrollo de tickets utilizando:

* Linear
* CrewAI
* OpenSpec
* OpenCode Zen / Go
* uv
* pnpm

El objetivo de este módulo es tomar un ticket de Linear y ejecutar automáticamente un flujo de:

```text
Linear
  ↓
Requirements Analyst
  ↓
Software Architect
  ↓
OpenSpec
  ↓
Senior Software Developer
  ↓
Quality Reviewer
  ↓
OpenSpec Archive
```

---

# Requisitos

Antes de utilizar este módulo debes tener instalados:

* Python `>=3.10,<3.14`
* uv
* Node.js
* pnpm

Las versiones del proyecto estan fijadas en `../.mise.toml`. Desde la raiz del monorepo, usa el flujo de tu shell.

### Bash (Linux, macOS y WSL)

```bash
./scripts/bootstrap.sh
# ejecutar las instrucciones que imprime para activar mise en este shell
# completar crewai/.env
./scripts/doctor.sh
pnpm verify
cd crewai
uv run run_crew DEV-5
```

### PowerShell 5.1 o 7 (Windows)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
# ejecutar las instrucciones que imprime para activar mise en este shell
# completar crewai\.env
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
pnpm verify
Set-Location crewai
uv run run_crew DEV-5
```

En PowerShell 7, sustituye `powershell.exe` por `pwsh` en ambos comandos.

`bootstrap.sh` instala `mise` cuando hace falta, instala las versiones fijadas, sincroniza pnpm y uv con sus lockfiles y crea `crewai/.env` desde `.env.example` solo si no existe. Como ejecuta `doctor.sh` al final, puede devolver un codigo distinto de cero mientras falten credenciales o modelos en `crewai/.env`; completa esos valores y ejecuta nuevamente `./scripts/doctor.sh`.

El bootstrap no puede modificar el shell padre. Cuando termina correctamente imprime un bloque idempotente para agregar `~/.local/bin` y activar `mise` en Bash o Zsh. Los comandos bare `pnpm` y `uv` de este documento presuponen que ese bloque ya se ejecuto en la terminal actual.

En Windows, `bootstrap.ps1` instala `mise` mediante `winget` si es necesario y emite el bloque de activacion para PowerShell 5.1 o 7. Si `winget` acaba de instalar `mise`, abre una nueva sesion si el comando todavia no esta disponible.

Como alternativa sin modificar el shell, usa la ruta resuelta que muestra el bootstrap:

```bash
"$HOME/.local/bin/mise" exec -- pnpm verify
"$HOME/.local/bin/mise" exec -- uv run --project crewai run_crew DEV-5
```

Si `mise` ya existia en otra ruta, reemplaza `"$HOME/.local/bin/mise"` por la ruta impresa. La forma general es `mise exec -- <comando>`.

No se requiere activar manualmente `.venv`: los comandos `uv run` usan el entorno sincronizado. OpenSpec se instala como dependencia local del workspace Node y se ejecuta desde la raiz con `OPENSPEC_TELEMETRY=0 pnpm exec openspec`, sin instalacion global.

`DEV-5` esta archivado en `openspec/changes/archive/2026-08-18-dev-5/`. El comando del flujo muestra el formato aceptado; una ejecucion que pueda modificar o archivar artefactos debe usar un ticket activo.

Los ejemplos siguientes usan `TICKET_ACTIVO` y `CHANGE_ID_ACTIVO`. Antes de ejecutarlos, asigna el identificador real, por ejemplo `export TICKET_ACTIVO=DEV-123` y `export CHANGE_ID_ACTIVO=dev-123`.

En PowerShell, usa `$env:TICKET_ACTIVO = 'DEV-123'` y `$env:CHANGE_ID_ACTIVO = 'dev-123'`.

---

# Ubicación dentro del monorepo

Este proyecto vive dentro de:

```text
koty-app/
├── apps/
├── packages/
├── openspec/
│
└── crewai/
    ├── pyproject.toml
    ├── uv.lock
    ├── .env
    ├── .env.example
    └── src/
        └── crew/
```

OpenSpec se encuentra en la raíz del monorepo:

```text
koty-app/openspec/
```

Por esta razón, las herramientas internas de CrewAI ejecutan OpenSpec utilizando la raíz de `koty-app` como directorio de trabajo.

---

# Instalación

`./scripts/bootstrap.sh`, ejecutado desde la raiz, sincroniza el entorno con:

```bash
uv sync --project crewai --frozen
```

Esto crea:

```text
crewai/.venv/
```

e instala las dependencias definidas en:

```text
crewai/pyproject.toml
crewai/uv.lock
```

No es necesario utilizar `pip install` ni activar el entorno.

---

# Variables de entorno

El bootstrap crea `crewai/.env` desde `crewai/.env.example` si no existe y nunca sobrescribe un archivo existente.

Ejemplo:

```env
LINEAR_API_KEY=

OPENCODE_API_KEY=

ZEN_BASE_URL=https://opencode.ai/zen/go/v1

ZEN_ANALYST_MODEL=
ZEN_ARCHITECT_MODEL=
ZEN_CODER_MODEL=
ZEN_REVIEWER_MODEL=

CREWAI_TRACING_ENABLED=false
OTEL_SDK_DISABLED=true
```

## LINEAR_API_KEY

Token utilizado para consultar los tickets de Linear.

El Analyst recibe un identificador como:

```text
DEV-5
```

y obtiene la información real del ticket mediante la API de Linear.

---

## OPENCODE_API_KEY

API key utilizada para acceder a los modelos configurados mediante OpenCode Zen / Go.

---

## Modelos

Cada agente puede utilizar un modelo diferente:

```env
ZEN_ANALYST_MODEL=
ZEN_ARCHITECT_MODEL=
ZEN_CODER_MODEL=
ZEN_REVIEWER_MODEL=
```

Esto permite utilizar modelos económicos para análisis y modelos más potentes para arquitectura o programación.

---

# Ejecutar el Crew

Desde:

```text
koty-app/crewai/
```

ejecutar:

```bash
uv run run_crew "$TICKET_ACTIVO"
```

El programa normaliza el identificador. `DEV-5` y `dev-5` sirven para verificar esa normalizacion, pero no para una ejecucion que cambie artefactos porque el cambio ya esta archivado.

Por ejemplo:

```text
Entrada:
dev-5

Linear:
DEV-5

OpenSpec:
dev-5
```

Para trabajo real, reemplaza el ejemplo por el identificador de un ticket activo.

---

# Ejecutar sin argumento

También puede ejecutarse:

```bash
uv run run_crew
```

El programa solicitará:

```text
Ingresa el identificador de un ticket activo:
```

---

# Flujo completo

## 1. Requirements Analyst

El Analyst consulta Linear utilizando:

```text
Buscar Tarea en Linear
```

Su responsabilidad es identificar:

* título
* descripción
* objetivo
* alcance
* requisitos funcionales
* criterios de aceptación
* restricciones
* dependencias
* ambigüedades

No debe inventar requisitos.

Su resultado es entregado al Architect.

---

# 2. Software Architect

El Architect recibe el análisis del ticket y consulta:

```text
CONTEXT.md
```

También puede inspeccionar partes relevantes del repositorio.

No debe recorrer directorios generados como:

```text
.venv/
node_modules/
.git/
.next/
dist/
build/
__pycache__/
```

El Architect crea el cambio OpenSpec.

Por ejemplo:

```text
dev-5
```

y genera:

```text
openspec/
└── changes/
    └── dev-5/
        ├── proposal.md
        ├── design.md
        ├── tasks.md
        └── specs/
            └── ...
                └── spec.md
```

---

# Artifacts OpenSpec

## proposal.md

Define:

* problema
* objetivo
* alcance
* motivación
* impacto
* elementos fuera de alcance

---

## specs/

Define el comportamiento esperado del sistema.

Ejemplo:

```markdown
## ADDED Requirements

### Requirement: Crear workspace

El sistema SHALL crear la estructura requerida.

#### Scenario: Inicialización exitosa

- GIVEN un repositorio vacío
- WHEN se inicializa el workspace
- THEN deben existir las aplicaciones requeridas
```

Las specs funcionan como contrato funcional.

---

## design.md

Define las decisiones técnicas.

Puede contener:

* arquitectura
* componentes afectados
* flujo de datos
* dependencias
* interfaces
* configuración
* manejo de errores
* testing
* riesgos

---

## tasks.md

Es la checklist utilizada por el Programmer.

Ejemplo:

```markdown
- [ ] 1.1 Crear `apps/api/src/example.ts`
- [ ] 1.2 Agregar configuración
- [ ] 1.3 Crear tests
```

Cuando una tarea es completada:

```markdown
- [x] 1.1 Crear `apps/api/src/example.ts`
```

No deben quedar tareas pendientes antes del archivado.

Comprobar:

```bash
grep -n '\[ \]' "../openspec/changes/$CHANGE_ID_ACTIVO/tasks.md"
```

Si no devuelve resultados, no existen tareas pendientes.

---

# 3. Senior Software Developer

El Programmer lee:

```text
proposal.md
specs/
design.md
tasks.md
```

La interpretación es:

```text
proposal = intención y alcance

specs = contrato funcional

design = contrato técnico

tasks = checklist de implementación
```

El Programmer ejecuta las tareas de `tasks.md` en orden.

Antes de modificar un archivo existente debe leer su contenido.

Después de completar una tarea actualiza:

```text
[ ]
```

a:

```text
[x]
```

---

# Verificaciones del Programmer

Antes de finalizar, desde la raiz se ejecuta la puerta completa:

```bash
pnpm verify
```

Este comando incluye lint, Vitest, pruebas shell, builds, pytest y validacion estricta de OpenSpec.

Si cualquiera falla, el Programmer debe corregir el problema antes de finalizar.

---

# 4. Quality Reviewer

El Reviewer realiza una revisión independiente.

Debe volver a leer:

```text
proposal.md
specs/
design.md
tasks.md
```

y comprobar:

* Requirements implementados
* Scenarios implementados
* diseño respetado
* tareas completadas
* archivos existentes
* código correcto
* lint correcto
* tests correctos
* build correcto

Después ejecuta:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate "$CHANGE_ID_ACTIVO" --strict --no-interactive
```

Si cualquier comprobación falla:

```text
REVISIÓN RECHAZADA
```

y el cambio no se archiva.

---

# Archivado

Solo cuando todas las verificaciones son correctas, el Reviewer ejecuta:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec archive "$CHANGE_ID_ACTIVO" --yes
```

El parámetro:

```text
--yes
```

es necesario porque CrewAI ejecuta OpenSpec sin interacción manual.

Una vez archivado, el cambio deja de estar activo.

---

# Reintentar un ticket rechazado

Si el Reviewer rechaza una ejecución, normalmente **no debes borrar el cambio OpenSpec**.

Por ejemplo, conserva:

```text
openspec/changes/$CHANGE_ID_ACTIVO/
```

Corrige los problemas detectados y vuelve a ejecutar:

```bash
cd crewai
uv run run_crew "$TICKET_ACTIVO"
```

El Crew debe continuar utilizando el cambio existente.

---

# No borrar antes de reintentar

No borres:

```text
openspec/changes/$CHANGE_ID_ACTIVO/proposal.md
openspec/changes/$CHANGE_ID_ACTIVO/design.md
openspec/changes/$CHANGE_ID_ACTIVO/specs/
openspec/changes/$CHANGE_ID_ACTIVO/tasks.md
```

Tampoco borres el código ya implementado.

Solo elimina el cambio si realmente quieres reconstruir toda la planificación desde cero.

---

# Validaciones manuales

Antes de volver a ejecutar el Crew es útil comprobar manualmente:

```bash
cd ..
```

```bash
pnpm verify
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate "$CHANGE_ID_ACTIVO" --strict --no-interactive
```

Y revisar tareas pendientes:

```bash
grep -n '\[ \]' "openspec/changes/$CHANGE_ID_ACTIVO/tasks.md"
```

Si todo está correcto:

```bash
cd crewai
uv run run_crew "$TICKET_ACTIVO"
```

---

# Herramientas de los agentes

## Buscar Tarea en Linear

Disponible para:

```text
Requirements Analyst
```

Obtiene la información real del ticket desde Linear.

---

## Leer Archivo en Raiz

Permite leer archivos del monorepo.

Por seguridad no permite inspeccionar directorios generados como:

```text
.venv
node_modules
.git
__pycache__
```

Los archivos grandes son truncados para evitar superar la ventana de contexto del LLM.

---

## Listar Archivos en Raiz

Permite conocer la estructura de una parte del repositorio.

Tiene:

* profundidad máxima
* límite de archivos
* exclusión de directorios generados

Esto evita enviar accidentalmente miles de archivos al contexto del modelo.

---

## Escribir Archivo en Raiz

Permite crear o modificar archivos dentro del monorepo.

No devuelve nuevamente el contenido escrito para evitar duplicarlo dentro del contexto del agente.

---

## Ejecutar OpenSpec

Permite comandos OpenSpec controlados como:

```text
new
status
validate
archive
list
show
instructions
```

Se ejecutan siempre desde la raíz del repositorio.

---

## Ejecutar Verificacion

Permite únicamente:

```text
python
lint
test
build
```

No permite ejecutar comandos arbitrarios enviados por el LLM.

---

# Protección de ventana de contexto

Las tools tienen límites para evitar errores como:

```text
context window exceeds limit
```

En particular, no se listan:

```text
crewai/.venv/
node_modules/
.git/
.next/
dist/
build/
__pycache__/
```

Además se limita:

* cantidad de archivos listados
* profundidad del listado
* tamaño de archivos leídos
* tamaño de salida de comandos
* tamaño de logs

Los agentes utilizan también:

```python
respect_context_window=True
```

para permitir que CrewAI gestione el crecimiento del contexto.

---

# Tracing y OpenTelemetry

Tracing está desactivado:

```python
tracing=False
```

También puede configurarse mediante:

```env
CREWAI_TRACING_ENABLED=false
```

Para evitar intentos de exportación OpenTelemetry:

```env
OTEL_SDK_DISABLED=true
```

Esto evita mensajes como:

```text
opentelemetry.exporter.otlp...
Transient error Service Unavailable...
```

---

# Estructura interna

```text
crewai/
├── .env
├── .env.example
├── pyproject.toml
├── uv.lock
│
└── src/
    └── crew/
        ├── __init__.py
        ├── main.py
        ├── crew.py
        │
        ├── config/
        │   ├── agents.yaml
        │   └── tasks.yaml
        │
        └── tools/
            ├── __init__.py
            └── custom_tool.py
```

---

# agents.yaml

Define los agentes:

```text
analyst
arquitect
programer
reviewer
```

Cada agente tiene:

* role
* goal
* backstory

Los modelos utilizados se configuran en `.env`.

---

# tasks.yaml

Define el pipeline:

```text
analysis_task
architecture_task
coding_task
review_task
```

El proceso es secuencial:

```text
analysis_task
      ↓
architecture_task
      ↓
coding_task
      ↓
review_task
```

---

# crew.py

Construye:

* LLMs
* Agents
* Tasks
* Crew

El proceso utilizado es:

```python
Process.sequential
```

No se utiliza Manager porque el flujo es determinístico y no requiere delegación dinámica.

---

# main.py

Es el entrypoint de la aplicación.

Recibe:

```text
dev-5
```

normaliza el identificador y ejecuta:

```python
KotyAppCrew().crew().kickoff(...)
```

---

# Agregar dependencias Python

Usar:

```bash
uv add <paquete>
```

Ejemplo:

```bash
uv add requests
```

No utilizar:

```bash
pip install requests
```

Esto mantiene actualizados:

```text
pyproject.toml
uv.lock
```

---

# Sincronizar dependencias

Después de modificar `pyproject.toml`:

```bash
uv sync
```

Para instalar exactamente lo definido por el lockfile:

```bash
uv sync --frozen
```

---

# Entorno virtual

No requiere activacion manual. Usa `uv run ...` desde `crewai/`.

---

# Comandos frecuentes

## Ejecutar Crew

```bash
uv run run_crew "$TICKET_ACTIVO"
```

## Sincronizar Python

```bash
uv sync
```

## Validar Python

```bash
uv run python -m compileall -q src/crew
```

## Puerta completa del monorepo

Desde la raíz:

```bash
pnpm verify
```

## Estado OpenSpec

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec status --change "$CHANGE_ID_ACTIVO"
```

## Validar OpenSpec

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate "$CHANGE_ID_ACTIVO" --strict --no-interactive
```

## Buscar tareas pendientes

```bash
grep -n '\[ \]' "openspec/changes/$CHANGE_ID_ACTIVO/tasks.md"
```

## Archivar manualmente

Solo cuando todas las verificaciones sean correctas:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec archive "$CHANGE_ID_ACTIVO" --yes
```

Normalmente este último paso debe realizarlo el Reviewer automáticamente.

---

# Flujo recomendado para un desarrollador nuevo

Desde la raíz:

```bash
git clone <REPOSITORIO>
cd koty-app
```

Preparar, completar credenciales, diagnosticar y verificar en Bash (Linux, macOS o WSL):

```bash
./scripts/bootstrap.sh
# ejecutar las instrucciones que imprime para activar mise en este shell
# completar crewai/.env
./scripts/doctor.sh
pnpm verify
cd crewai
uv run run_crew DEV-5
```

El ultimo comando muestra el formato del entrypoint. Para una ejecucion que cambie artefactos, usa un ticket activo en lugar de `DEV-5`.

En Windows, usa el bloque PowerShell de requisitos al inicio de este documento.

---

# Resumen

El flujo completo es:

```text
uv run run_crew "$TICKET_ACTIVO"
        │
        ▼
Linear $TICKET_ACTIVO
        │
        ▼
Requirements Analyst
        │
        ▼
Software Architect
        │
        ▼
OpenSpec $CHANGE_ID_ACTIVO
        │
        ├── proposal.md
        ├── specs/
        ├── design.md
        └── tasks.md
        │
        ▼
Senior Software Developer
        │
        ├── implementación
        ├── python
        ├── lint
        ├── test
        └── build
        │
        ▼
Quality Reviewer
        │
        ├── revisión funcional
        ├── revisión técnica
        ├── validaciones
        └── OpenSpec validate
        │
        ▼
OpenSpec archive
```

La regla principal del sistema es:

> El ticket define qué construir, OpenSpec define el contrato y el diseño, el Programmer implementa ese contrato y el Reviewer solo permite el archivado cuando todas las verificaciones pasan.
