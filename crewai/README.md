# Koty App CrewAI

Automatización del flujo de desarrollo de tickets utilizando:

* Linear
* CrewAI
* OpenSpec
* OpenCode Zen / Go
* uv
* pnpm

El objetivo de este modulo es tomar un ticket de Linear y ejecutar una maquina de fases persistente:

```text
Linear
  ↓
Requirements Analyst
  ↓
Architect: outline
  ↓
Architect: una unidad por artefacto
  ↓
OpenSpec preflight
  ↓
Senior Software Developer
  ↓
Puertas base
  ↓
Tester (solo perfiles de navegador)
  ↓
Quality Reviewer
  ↓
Approved / blocked
```

Las fases persistidas son `planning`, `implementing`, `verifying`,
`browser_testing`, `reviewing`, `approved` y `blocked`. Cada invocacion usa un
CrewAI aislado de una sola tarea y recibe solo sus entradas de fase, no la
conversacion completa de otro rol. Ralph mantiene la cola, el branch, el worker
y la finalizacion local.

Los perfiles de verificacion cerrados son `standard`, `browser`,
`operational` y `browser_operational`. Todos ejecutan las puertas inmutables
`python`, `lint`, `test`, `build`, `integration` y validacion estricta de
OpenSpec.

| Perfil | Evidencia adicional |
| --- | --- |
| `standard` | Ninguna; el supervisor persiste un resultado de navegador `skipped`. |
| `browser` | Evidencia Browser E2E aprobada de Tester. |
| `operational` | ReviewPack relaciona cada criterio operacional con un documento, prueba o artefacto fuente versionado y su hash. |
| `browser_operational` | Ambas evidencias: Browser E2E aprobada y evidencia operacional con hash. |

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
export TICKET_ACTIVO=DEV-123
uv run run_crew "$TICKET_ACTIVO"
```

### PowerShell 5.1 o 7 (Windows)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
# ejecutar las instrucciones que imprime para activar mise en este shell
# completar crewai\.env
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
pnpm verify
Set-Location crewai
$env:TICKET_ACTIVO = 'DEV-123'
uv run run_crew $env:TICKET_ACTIVO
```

En PowerShell 7, sustituye `powershell.exe` por `pwsh` en ambos comandos.

`bootstrap.sh` instala `mise` cuando hace falta, instala las versiones fijadas, sincroniza pnpm y uv con sus lockfiles y crea `crewai/.env` desde `.env.example` solo si no existe. Como ejecuta `doctor.sh` al final, puede devolver un codigo distinto de cero mientras falten credenciales o modelos en `crewai/.env`; completa esos valores y ejecuta nuevamente `./scripts/doctor.sh`.

El bootstrap no puede modificar el shell padre. Cuando termina correctamente imprime un bloque idempotente para agregar `~/.local/bin` y activar `mise` en Bash o Zsh. Los comandos bare `pnpm` y `uv` de este documento presuponen que ese bloque ya se ejecuto en la terminal actual.

En Windows, `bootstrap.ps1` instala `mise` mediante `winget` si es necesario y emite el bloque de activacion para PowerShell 5.1 o 7. Si `winget` acaba de instalar `mise`, abre una nueva sesion si el comando todavia no esta disponible.

Como alternativa sin modificar el shell, usa la ruta resuelta que muestra el bootstrap:

```bash
"$HOME/.local/bin/mise" exec -- pnpm verify
"$HOME/.local/bin/mise" exec -- uv run --project crewai run_crew "$TICKET_ACTIVO"
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

El bootstrap correspondiente a la plataforma, ejecutado desde la raiz (`./scripts/bootstrap.sh` en Unix o `scripts/bootstrap.ps1` en Windows), sincroniza el entorno con:

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
LINEAR_QUEUE_ASSIGNEE_EMAIL=
LINEAR_QUEUE_MILESTONE=

MAX_TICKET_ATTEMPTS=3
MAX_INFRASTRUCTURE_ATTEMPTS=2

OPENCODE_API_KEY=

ZEN_BASE_URL=https://opencode.ai/zen/go/v1

ZEN_ANALYST_MODEL=
ZEN_ARCHITECT_MODEL=
ZEN_CODER_MODEL=
ZEN_TESTER_MODEL=
ZEN_REVIEWER_MODEL=

ZEN_ANALYST_MAX_TOKENS=2000
ZEN_ARCHITECT_OUTLINE_MAX_TOKENS=4000
ZEN_ARCHITECT_ARTIFACT_MAX_TOKENS=8000
ZEN_ARCHITECT_RETRY_MAX_TOKENS=16000
ZEN_ARCHITECT_LENGTH_RETRIES=1
ZEN_ARCHITECT_MAX_CONTEXT_REFS=12
ZEN_ARCHITECT_MAX_CONTEXT_CHARS=48000
ZEN_CODER_MAX_TOKENS=2500
ZEN_TESTER_MAX_TOKENS=600
ZEN_REVIEWER_MAX_TOKENS=800

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
ZEN_TESTER_MODEL=
ZEN_REVIEWER_MODEL=
```

Esto permite utilizar modelos económicos para análisis y modelos más potentes para arquitectura o programación.

Los limites predeterminados `max_iter`/`max_tokens` son Analyst `4`/`2000`,
Architect outline `1`/`4000`, Architect artifact `1`/`8000`, Programmer
`20`/`2500`, Tester `8`/`600` y Reviewer `8`/`800`. Architect usa esfuerzo de
razonamiento `low`; su unico reintento por longitud usa `16000` tokens.
El proveedor y el Agent de Architect tienen sus reintentos ocultos
desactivados (`max_retries=0` y `max_retry_limit=0`): los reintentos descritos
abajo pertenecen al supervisor.

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

El programa normaliza el identificador. Usa un ticket activo para cualquier
ejecucion que pueda crear o modificar artefactos; `DEV-5` solo sirve para
verificar la normalizacion porque su cambio ya esta archivado.

Para continuar una ejecucion interrumpida sin invalidar contratos validos:

```bash
uv run run_crew "$TICKET_ACTIVO" --resume
```

Para invalidar manualmente la planificacion y volver a `planning`:

```bash
uv run run_crew "$TICKET_ACTIVO" --replan
```

`--resume` y `--replan` son mutuamente excluyentes. Durante una planificacion
interrumpida, `--resume` exige que ExecutionState contenga la ruta exacta del
checkpoint del intento y el SHA-256 de sus bytes, valida ambos junto con los
hashes internos del catalogo, contrato, outline y unidades, reutiliza el outline
y las unidades completas y continua con la primera unidad faltante. Un archivo
de checkpoint huerfano o una ruta/hash ausente o divergente bloquea la ejecucion
en vez de adoptar estado. `--resume` no desbloquea un estado `blocked`.
`--replan` es la unica invalidacion manual de planificacion: elimina de forma
atomica las referencias de contratos y la ruta/hash del checkpoint actual,
incluso desde `blocked`, conserva toda la evidencia de intentos anteriores y
comienza otro intento en `planning`. No
garantiza que desaparezca la causa subyacente del bloqueo. Un cambio en el hash
del ticket invalida la planificacion automaticamente.

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

# Ejecución supervisada por Ralph

Para ejecutar CrewAI desde el supervisor local, usa desde la raíz:

```bash
./ralph.sh --until-finalized
```

Este modo no invoca OpenCode. `scripts/coordinate-crew-ticket.sh` selecciona un ticket mediante `crew_queue next`, cambia o crea su branch, inicia Linear, ejecuta `scripts/run-crew-ticket.sh` y reintenta la finalización hasta obtener `done`, `blocked` o un error no recuperable.

Configura `LINEAR_QUEUE_ASSIGNEE_EMAIL` y `LINEAR_QUEUE_MILESTONE` en `crewai/.env`; ambos son necesarios para `crew_queue next`. `./ralph.sh --until-finalized --resume` solo continua una fase persistida no terminal y no reinicia ni desbloquea un resultado `blocked`. Un cambio en el hash del ticket es la invalidacion automatica separada. `--replan` es la unica invalidacion manual de planificacion: el coordinador y runner la aceptan desde `blocked`, reinician `planning`, conservan la evidencia de intentos anteriores y vuelven a ejecutar el flujo. No garantiza que desaparezca la causa subyacente del bloqueo.

El coordinador sondea cada 30 segundos por defecto (`CREW_TICKET_WAIT_SECONDS`) y espera 5 segundos entre reintentos (`CREW_RETRY_DELAY_SECONDS`). El runner cancela una ejecución después de 1800 segundos (`CREW_TICKET_TIMEOUT_SECONDS`) y conserva estado, logs y resultados bajo `.agent/crew/<ticket>/`; esos artefactos no se versionan.

El estado de proceso se guarda en `.agent/crew/<ticket>/execution.json`. Los
artefactos de intentos que deben sobrevivir con el cambio se guardan en
`openspec/changes/<change-id>/attempts/<attempt>/`: TicketContract,
`context-catalog.json`, `planning-checkpoint.json`, PlanManifest, RepairPack,
resultado de navegador, ReviewPack, evidencia y metricas de uso. Cada llamada
de Architect conserva evidencia distinta por etapa, unidad e invocacion,
incluidos estado, limite efectivo, tipo de error y uso crudo cuando existe; una
llamada fallida nunca es sobrescrita por su reintento.

Estados JSON relevantes:

* `crew_queue`: `empty`, `blocked`, `ticket`, `retry`.
* `run-crew-ticket.sh`: `running`, `approved`, `archived`, `retry`, `retryable_failure`, `blocked`.
* `finalize_ticket`: `done`, `not_ready`, `repair`, `retry`, `blocked`.

Pruebas focalizadas:

```bash
bash scripts/tests/run-crew-ticket.test.sh
bash scripts/tests/ralph.test.sh
pnpm test:shell
```

---

# Ejecutar sin argumento

También puede ejecutarse:

```bash
uv run run_crew
```

El programa solicitará:

```text
Ticket:
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

Su `TicketContract` se persiste antes de iniciar la planificacion de Architect.

---

# 2. Staged Software Architect

El supervisor convierte las secciones `##` y `###` de `CONTEXT.md` en el
catalogo persistido
`openspec/changes/<change-id>/attempts/<attempt>/context-catalog.json`. La
primera llamada de Architect recibe exactamente el `TicketContract` serializado
y un indice del catalogo con referencias, titulos y tamanos, pero sin los cuerpos
de las secciones. Devuelve un `PlanOutline` con una unidad para `proposal.md`,
`design.md`, `tasks.md` y cada spec requerida.

Despues se ejecuta un Crew aislado por cada unidad. Cada llamada recibe
exactamente el `TicketContract`, el `PlanOutline` validado, la unidad solicitada
y solo los cuerpos de contexto seleccionados por esa unidad. Cada seleccion
admite por defecto hasta 12 referencias y 48000 caracteres. Architect no tiene
tools, delegacion, manager, Flow ni conversacion de llamadas anteriores.

El supervisor persiste
`openspec/changes/<change-id>/attempts/<attempt>/planning-checkpoint.json`
despues del outline, de cada unidad valida y de cada fallo de artefacto manejado.
Un `LengthFinishReasonError` directo o envuelto reintenta una sola vez y solo la
unidad de artefacto fallida, con el presupuesto `16000`; el estado durable evita
repetir el retry al reiniciar. El outline no recibe reintentos por longitud.
Durante toda la operacion de planificacion, la respuesta exacta
`Invalid response from LLM call - None or empty.` admite un unico reintento,
tambien persistido y ligado al outline o unidad que lo consumio; otros errores o
mensajes no lo consumen. Ambos reintentos usan semantica de supervisor
at-most-once: el estado durable cambia de `pending` a `consumed` antes de llamar
al proveedor. Si el proceso muere antes o durante esa llamada y no alcanza a
persistir el resultado, el reinicio bloquea por resultado incierto o presupuesto
agotado y no repite la llamada. Esta eleccion puede perder un reintento, pero
garantiza que el supervisor nunca exceda el limite configurado sin depender de
idempotencia del proveedor.

Solo cuando todas las unidades validan, el supervisor ensambla el `PlanDraft`
existente y lo pasa por `write_plan_draft()`. La creacion de PlanManifest, el
preflight, el rollback y la promocion atomica existentes no cambian. Los
reinicios recuperan cualquier marcador de promocion pendiente al entrar en
planificacion, antes de validar contratos, catalogo o checkpoint y antes de una
llamada de Architect. Asi una planificacion posterior que falle temprano no
puede dejar activos archivos reemplazados parcialmente. Los artefactos activos
mantienen esta forma:

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

# Verificaciones autoritativas

El supervisor, no el Programmer, ejecuta las puertas base de la maquina de
fases, una por una:

```bash
cd crewai
uv run python -m compileall -q src/crew
cd ..
pnpm lint
pnpm test
pnpm build
pnpm db:start
pnpm --filter @koty-app/api test:integration
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate "$CHANGE_ID_ACTIVO" --strict --no-interactive
```

La puerta `integration` inicia PostgreSQL con `pnpm db:start` y despues ejecuta
la suite de integracion de la API; deten PostgreSQL con `pnpm db:stop` cuando
ya no se necesite. `pnpm verify` es una verificacion completa separada para el
desarrollo del repositorio: no sustituye esta secuencia de puertas ni ejecuta la
puerta `integration`.

Si una puerta o una revision recuperable falla, el supervisor crea un
RepairPack y vuelve solo a Programmer con sus rutas de evidencia. Analyst y
Architect no se vuelven a invocar mientras TicketContract y PlanManifest sigan
vigentes.

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

En la ejecución supervisada, el Reviewer devuelve un `ReviewVerdict`
estructurado. `main.py` ejecuta las puertas autoritativas y valida que el
resultado cite evidencia vigente para `python`, `lint`, `test`, `build`,
`integration` y `openspec`; el resultado de Playwright depende de la estrategia
`Browser E2E` del diseño.

Si cualquier comprobación falla:

```text
REVISIÓN RECHAZADA
```

y el cambio no se archiva.

---

# Archivado

Solo cuando todas las verificaciones son correctas, `finalize_ticket` ejecuta:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec archive "$CHANGE_ID_ACTIVO" --yes
```

El parámetro:

```text
--yes
```

es necesario porque CrewAI ejecuta OpenSpec sin interacción manual.

Después valida todos los cambios OpenSpec, crea el commit sin incluir `.agent/`
y completa el ticket en Linear. El Reviewer no archiva ni completa tickets por
su cuenta.

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

La tool permite únicamente operaciones controladas y no destructivas:

```text
list
show <change-id>
status --change <change-id>
validate --all --strict
validate <change-id> --strict --no-interactive
```

Se ejecutan siempre desde la raíz del repositorio. La creación y el archivado
son responsabilidad de `main.py` y `finalize_ticket`, no de esta tool.

---

## Ejecutar Verificacion

Permite únicamente:

```text
python
lint
test
build
integration
```

`integration` inicia PostgreSQL y ejecuta la suite de `apps/api`; detén el
contenedor con `pnpm db:stop` cuando ya no lo necesites. No permite ejecutar
comandos arbitrarios enviados por el LLM.

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

Analyst, Programmer, Tester y Reviewer utilizan:

```python
respect_context_window=True
```

para permitir que CrewAI gestione el crecimiento del contexto. Architect usa
explicitamente `respect_context_window=False`: cada llamada staged recibe
contexto acotado y debe fallar antes que resumir o perder contenido del plan.

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
        ├── queue.py
        ├── finalizer.py
        ├── models.py
        ├── planning.py
        ├── evidence.py
        ├── gates.py
        ├── integration_env.py
        ├── linear_api.py
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
tester
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
architect_outline_task
architect_artifact_task
coding_task
testing_task
review_task
```

En la ejecucion supervisada cada rol se ejecuta como un CrewAI de una sola
tarea dentro de una maquina de fases persistente:

```text
planning: analyst -> architect outline -> una llamada por artefacto -> OpenSpec preflight
implementing: programmer
verifying: puertas base
browser_testing: tester solo para perfiles de navegador
reviewing: reviewer
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
<ticket-activo>
```

normaliza el identificador y ejecuta la fase persistida. `--resume` conserva
la fase y los contratos actuales; `--replan` es la unica invalidacion manual
de planificacion y conserva evidencia de intentos anteriores. El resultado
estructurado se guarda en `result.json` dentro del cambio OpenSpec activo.

```python
run_ticket(ticket_id, change_id, state)
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

La aprobacion del Reviewer permite que Ralph y `finalize_ticket` realicen la
finalizacion local; el Reviewer no archiva ni completa tickets por su cuenta.

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
export TICKET_ACTIVO=DEV-123
uv run run_crew "$TICKET_ACTIVO"
```

El ultimo comando ejecuta un ticket activo de ejemplo; reemplaza `DEV-123` por
el identificador real antes de ejecutar el flujo.

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
Architect outline
        │
        ▼
Architect artifact units
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
        └── implementacion
        │
        ▼
Puertas base
        ├── python
        ├── lint
        ├── test
        ├── build
        ├── integration
        └── OpenSpec validate estricto
        │
        ▼
Tester (solo perfiles browser)
        │
        ▼
Quality Reviewer
        │
        ▼
OpenSpec archive
```

La regla principal del sistema es:

> El ticket define qué construir, OpenSpec define el contrato y el diseño, el Programmer implementa ese contrato y el Reviewer solo permite el archivado cuando todas las verificaciones pasan.
