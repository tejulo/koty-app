# PLAN-DEPTO

PLAN-DEPTO es un sistema SaaS de administracion de alquileres para el mercado paraguayo. Este repositorio contiene el scaffolding inicial del monorepo y las herramientas auxiliares de especificacion y automatizacion.

La especificacion funcional y tecnica del producto esta en [`CONTEXT.md`](./CONTEXT.md). Ese documento describe el objetivo de V1 y sus incrementos; no representa funcionalidades ya implementadas.

## Estado Actual

El repositorio contiene el scaffolding y parte de la infraestructura del incremento 0; el dominio funcional completo aun no esta implementado.

| Componente | Estado actual |
| --- | --- |
| Web | Next.js 16 con App Router, Tailwind CSS y una pagina inicial estatica. |
| API | NestJS 11 con prefijo `api/v1` por defecto, health checks, OpenAPI/Swagger y modulos de infraestructura; aun sin el dominio funcional completo. |
| Worker | Scaffolding TypeScript con entrypoint ejecutable y cierre controlado por senales. |
| Contratos compartidos | Tipos TypeScript basicos; todavia no contiene esquemas Zod. |
| Configuracion compartida | Presets de TypeScript y ESLint. |
| Persistencia | PostgreSQL 17 en Docker Compose, Prisma y migraciones versionadas bajo `apps/api/prisma/migrations/`. |
| Pruebas | Vitest, pruebas shell del bootstrap, pytest y validacion estricta de OpenSpec integrados en `pnpm verify`. |

Autenticacion, organizaciones, permisos, auditoria, outbox, jobs persistentes y el resto del dominio forman parte de los incrementos definidos en `CONTEXT.md`.

## Estructura

```text
koty-app/
├── apps/
│   ├── web/               # Next.js
│   ├── api/               # NestJS
│   └── worker/            # Worker TypeScript
├── packages/
│   ├── contracts/         # Tipos compartidos
│   └── config/            # TypeScript y ESLint
├── crewai/                # Automatizacion con agentes
├── openspec/              # Especificaciones y cambios
├── docs/                  # Documentacion adicional
├── CONTEXT.md             # Especificacion integral del producto
├── CONTRIBUTING.md        # Guia de contribucion
├── package.json
├── pnpm-lock.yaml
└── pnpm-workspace.yaml
```

El workspace se administra directamente con pnpm; no utiliza Turborepo.

## Requisitos

- Node.js `>=20.19.0`
- pnpm `>=8.15.0`
- Python `>=3.10` y `<3.14`, solo para CrewAI
- [uv](https://docs.astral.sh/uv/), solo para CrewAI
- `mise`, instalado por el bootstrap si no esta disponible

Las versiones de dependencias del proyecto quedan fijadas en `pnpm-lock.yaml` y `crewai/uv.lock`.

## Instalacion

Desde la raiz del repositorio, elige el flujo de tu shell.

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

`bootstrap.sh` instala `mise` cuando hace falta, instala las versiones fijadas en `.mise.toml`, sincroniza las dependencias pnpm y uv con sus lockfiles y crea `crewai/.env` desde el ejemplo solo si no existe. Al final ejecuta `doctor.sh`; por eso puede devolver un codigo distinto de cero hasta que se completen las credenciales y modelos requeridos en `crewai/.env`. Despues de completarlos, vuelve a ejecutar `./scripts/doctor.sh`.

En Windows, `bootstrap.ps1` realiza el mismo flujo y usa `winget` para instalar `mise` si es necesario. El script funciona en Windows PowerShell 5.1 y PowerShell 7; la primera ejecucion puede requerir abrir una nueva sesion para que `winget` actualice `PATH`.

El bootstrap no puede modificar el shell padre. En un resultado exitoso imprime instrucciones idempotentes para agregar `~/.local/bin` y activar `mise` en Bash o Zsh. Ejecuta ese bloque antes de usar los comandos bare `pnpm` y `uv` mostrados en el resto de este documento.

Si prefieres no modificar la configuracion del shell, usa la ruta de `mise` que imprime el bootstrap:

```bash
"$HOME/.local/bin/mise" exec -- pnpm verify
"$HOME/.local/bin/mise" exec -- uv run --project crewai run_crew DEV-123
```

En PowerShell, la alternativa sin modificar el perfil es:

```powershell
& (Get-Command mise).Source exec -- pnpm verify
& (Get-Command mise).Source exec -- uv run --project crewai run_crew DEV-123
```

Si `mise` ya estaba instalado en otra ruta, sustituye `"$HOME/.local/bin/mise"` por la ruta resuelta que aparece en la salida. La forma general de la alternativa es `mise exec -- <comando>`.

No se activa manualmente `crewai/.venv`: `uv run` selecciona el entorno sincronizado. OpenSpec es una dependencia local del workspace y se invoca con `OPENSPEC_TELEMETRY=0 pnpm exec openspec`; no se instala globalmente.

Reemplaza `DEV-123` por un ticket activo antes de ejecutar el CrewAI. `DEV-5` esta archivado en OpenSpec y no debe usarse para crear, modificar o archivar artefactos.

El desarrollo de API y worker carga explícitamente el `.env` raíz mediante `node --env-file`; los comandos compilados `start` requieren que las variables ya estén exportadas. La API valida `DATABASE_URL` antes de arrancar.

## Desarrollo Local

### Web

```bash
pnpm --filter @koty-app/web dev
```

Disponible por defecto en `http://localhost:3000`.

### API

```bash
PORT=3001 pnpm --filter @koty-app/api dev
```

Disponible en:

- `http://localhost:3001/`
- `http://localhost:3001/health`

### Worker

El worker no expone HTTP. `pnpm --filter @koty-app/worker dev` ejecuta `src/main.ts`; el comando `start` ejecuta `dist/main.js` despues del build.

### Todos los paquetes

El script raiz existe:

```bash
pnpm dev
```

Ejecuta en paralelo todos los scripts `dev` del workspace. La web usa el puerto 3000 y la API usa 3001 por defecto; define `PORT` explícitamente si el entorno ya tiene servicios ocupando esos puertos.

## Scripts Node

Los siguientes scripts existen en el `package.json` raiz:

| Comando | Descripcion |
| --- | --- |
| `pnpm dev` | Ejecuta los scripts `dev` del workspace en paralelo. |
| `pnpm build` | Compila recursivamente los paquetes que definen `build`. |
| `pnpm lint` | Ejecuta lint recursivamente en modo de solo lectura. |
| `pnpm test` | Ejecuta la suite Vitest. |
| `pnpm test:shell` | Ejecuta las pruebas de bootstrap, runner supervisado y Ralph: Bash en Unix y PowerShell en Windows. |
| `pnpm crew:check` | Ejecuta pytest y la validacion estricta de OpenSpec. |
| `pnpm verify` | Ejecuta lint, todas las pruebas, builds y verificaciones de CrewAI/OpenSpec. |
| `pnpm clean` | Elimina artefactos generados mediante los scripts de cada paquete. |
| `pnpm start:web` | Inicia un build previo de Next.js. |
| `pnpm start:api` | Inicia el artefacto compilado de la API. |
| `pnpm start:worker` | Inicia el artefacto compilado del worker. |
| `pnpm db:start` / `pnpm db:stop` | Inicia o detiene PostgreSQL mediante Docker Compose. |
| `pnpm db:migrate:dev --name <nombre>` | Crea y aplica una migración Prisma de desarrollo. |
| `pnpm db:migrate:deploy` / `pnpm db:migrate:status` | Aplica o inspecciona migraciones versionadas. |
| `pnpm db:verify` | Comprueba que el schema coincide con el historial de migraciones. |

No existe un script `format` en la raíz.

## Paquetes Compartidos

### `@koty-app/contracts`

Contiene por ahora tipos TypeScript basicos para respuestas API, paginacion y estado de salud. Los esquemas Zod compartidos se incorporaran cuando los limites de API los necesiten.

### `@koty-app/config`

Exporta configuraciones compartidas de TypeScript y ESLint. Tailwind CSS permanece configurado dentro de `apps/web`.

## Ralph

`ralph.sh` es el supervisor local del flujo Linear -> CrewAI. El modo normal (`./ralph.sh`, `--once` o `--max-iterations N`) ejecuta OpenCode con el agente `.opencode/agents/ralph-linear.md` y registra logs en `.agent/history/`.

`./ralph.sh --until-finalized` usa `scripts/coordinate-crew-ticket.sh` y no invoca OpenCode: selecciona un ticket con `crew_queue next`, asegura su branch, inicia el ticket, supervisa `run-crew-ticket.sh` y llama a `finalize_ticket` hasta obtener un estado terminal. `--resume` solo continua una fase persistida no terminal y sus contratos validos; no reinicia ni desbloquea una ejecucion en `blocked`. Un cambio en el hash del ticket es la invalidacion automatica separada que vuelve a `planning`. `--replan` es la unica invalidacion manual de planificacion: reinicia en `planning` incluso desde `blocked`, conserva la evidencia de intentos anteriores y vuelve a ejecutar el flujo; no garantiza que la causa subyacente del bloqueo desaparezca.

Configura en `crewai/.env` `LINEAR_QUEUE_ASSIGNEE_EMAIL` y `LINEAR_QUEUE_MILESTONE` para que Ralph pueda seleccionar tickets. El coordinador espera 30 segundos entre sondeos por defecto (`CREW_TICKET_WAIT_SECONDS`) y reintenta después de 5 segundos (`CREW_RETRY_DELAY_SECONDS`); el worker tiene un timeout de 1800 segundos (`CREW_TICKET_TIMEOUT_SECONDS`).

Prueba el supervisor con `bash scripts/tests/ralph.test.sh`; `pnpm test:shell` también ejecuta esa prueba. El estado y los logs del worker se guardan bajo `.agent/crew/<ticket>/`, que no debe versionarse.

## CrewAI

El subproyecto `crewai/` automatiza analisis, planificacion, implementacion y revision de cambios mediante agentes. Sus dependencias se administran exclusivamente con `uv` y las sincroniza el bootstrap correspondiente a la plataforma: `./scripts/bootstrap.sh` en Unix o `scripts/bootstrap.ps1` en Windows.

La ejecucion supervisada es una maquina de fases persistente: `planning` (Analyst, Architect y preflight OpenSpec), `implementing` (Programmer), `verifying` (puertas base), `browser_testing` cuando el perfil lo requiere, `reviewing` (Reviewer), `approved` o `blocked`. Cada rol se ejecuta aislado y recibe rutas a contratos persistidos, no conversaciones de otros roles.

Los perfiles cerrados son `standard`, `browser`, `operational` y `browser_operational`. Todos conservan, sin sustituciones ni eliminaciones, las puertas base `python`, `lint`, `test`, `build`, `integration` y validacion estricta de OpenSpec. `standard` no agrega evidencia; `browser` requiere evidencia Browser E2E aprobada de Tester; `operational` exige que ReviewPack relacione cada criterio operacional con un documento, prueba o artefacto fuente versionado y su hash; `browser_operational` exige ambas evidencias. Solo `browser` y `browser_operational` ejecutan Tester; los demas guardan un resultado de navegador `skipped`.

El estado operativo se guarda sin versionar en `.agent/crew/<ticket>/execution.json`. Los contratos, evidencia, RepairPack, ReviewPack y metricas de uso de cada invocacion de rol se conservan en `openspec/changes/<change-id>/attempts/<attempt>/` para acompanar el cambio. Tras cada invocacion de un rol, las metricas registran fase, rol, modelo, limites configurados, intento y la carga de uso de CrewAI cuando esta disponible.

Configura en `crewai/.env` las claves y modelos requeridos por el archivo de ejemplo:

- `LINEAR_API_KEY`
- `OPENCODE_API_KEY`
- `ZEN_BASE_URL`
- `ZEN_ANALYST_MODEL`
- `ZEN_ARCHITECT_MODEL`
- `ZEN_CODER_MODEL`
- `ZEN_TESTER_MODEL`
- `ZEN_REVIEWER_MODEL`

Despues de activar `mise` con el bloque impreso por bootstrap y de que el doctor correspondiente (`./scripts/doctor.sh` o `scripts/doctor.ps1`) y `pnpm verify` finalicen correctamente, ejecutar un ticket activo:

```bash
export TICKET_ACTIVO=DEV-123 # reemplazar por un ticket activo real
cd crewai
uv run run_crew "$TICKET_ACTIVO"
```

En PowerShell:

```powershell
$env:TICKET_ACTIVO = 'DEV-123' # reemplazar por un ticket activo real
Set-Location crewai
uv run run_crew $env:TICKET_ACTIVO
```

No es necesario activar manualmente `crewai/.venv`. Para agregar o eliminar dependencias:

```bash
uv add <paquete>
uv remove <paquete>
```

Consulta [`crewai/README.md`](./crewai/README.md) para detalles del flujo.

## OpenSpec

OpenSpec mantiene las especificaciones actuales en `openspec/specs/` y el historial de cambios en `openspec/changes/`. El repositorio ya esta inicializado; no ejecutes `openspec init` nuevamente.

Comandos utiles desde la raiz:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec list
OPENSPEC_TELEMETRY=0 pnpm exec openspec list --specs
OPENSPEC_TELEMETRY=0 pnpm exec openspec show my-change
OPENSPEC_TELEMETRY=0 pnpm exec openspec status --change my-change
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate --all --strict
```

Los identificadores de cambios activos usan kebab-case en minusculas. `DEV-5` ya esta archivado en `openspec/changes/archive/2026-08-18-dev-5/`, por lo que no aparece como cambio activo.

## Limitaciones Conocidas

- El codigo presente es scaffolding y no implementa todavia el dominio funcional completo del incremento 0.
- PostgreSQL local, Prisma, migraciones y Docker Compose existen para la infraestructura actual; las pruebas de integracion requieren Docker y `DATABASE_URL`.
- `pnpm format` no existe en la raiz.
- La estrategia de variables de entorno Node aun no esta unificada.
- Los comandos `start` de produccion requieren revision antes de usarse para despliegue.

## Contribucion

Antes de abrir un cambio, consulta [`CONTRIBUTING.md`](./CONTRIBUTING.md), `CONTEXT.md` y las especificaciones OpenSpec aplicables. No declares pruebas ejecutadas si el comando correspondiente no existe o no ejecuto una suite real.

## Licencia

Privado - PLAN-DEPTO.
