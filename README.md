# PLAN-DEPTO

PLAN-DEPTO es un sistema SaaS de administracion de alquileres para el mercado paraguayo. Este repositorio contiene el scaffolding inicial del monorepo y las herramientas auxiliares de especificacion y automatizacion.

La especificacion funcional y tecnica del producto esta en [`CONTEXT.md`](./CONTEXT.md). Ese documento describe el objetivo de V1 y sus incrementos; no representa funcionalidades ya implementadas.

## Estado Actual

El repositorio se encuentra antes de la implementacion funcional del incremento 0.

| Componente | Estado actual |
| --- | --- |
| Web | Next.js 16 con App Router, Tailwind CSS y una pagina inicial estatica. |
| API | NestJS 11 con `GET /` y `GET /health`; aun sin prefijo `/api/v1`, OpenAPI ni modulos de dominio. |
| Worker | Scaffolding TypeScript con entrypoint ejecutable y cierre controlado por senales. |
| Contratos compartidos | Tipos TypeScript basicos; todavia no contiene esquemas Zod. |
| Configuracion compartida | Presets de TypeScript y ESLint. |
| Persistencia | PostgreSQL, Prisma, migraciones y Docker Compose todavia no estan incorporados. |
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

`bootstrap.sh` instala `mise` cuando hace falta, instala las versiones fijadas en `.mise.toml`, sincroniza las dependencias pnpm y uv con sus lockfiles y crea `crewai/.env` desde el ejemplo solo si no existe. Al final ejecuta `doctor.sh`; por eso puede devolver un codigo distinto de cero hasta que se completen las credenciales y modelos requeridos en `crewai/.env`. Despues de completarlos, vuelve a ejecutar `./scripts/doctor.sh`.

En Windows, `bootstrap.ps1` realiza el mismo flujo y usa `winget` para instalar `mise` si es necesario. El script funciona en Windows PowerShell 5.1 y PowerShell 7; la primera ejecucion puede requerir abrir una nueva sesion para que `winget` actualice `PATH`.

El bootstrap no puede modificar el shell padre. En un resultado exitoso imprime instrucciones idempotentes para agregar `~/.local/bin` y activar `mise` en Bash o Zsh. Ejecuta ese bloque antes de usar los comandos bare `pnpm` y `uv` mostrados en el resto de este documento.

Si prefieres no modificar la configuracion del shell, usa la ruta de `mise` que imprime el bootstrap:

```bash
"$HOME/.local/bin/mise" exec -- pnpm verify
"$HOME/.local/bin/mise" exec -- uv run --project crewai run_crew DEV-5
```

En PowerShell, la alternativa sin modificar el perfil es:

```powershell
& (Get-Command mise).Source exec -- pnpm verify
& (Get-Command mise).Source exec -- uv run --project crewai run_crew DEV-5
```

Si `mise` ya estaba instalado en otra ruta, sustituye `"$HOME/.local/bin/mise"` por la ruta resuelta que aparece en la salida. La forma general de la alternativa es `mise exec -- <comando>`.

No se activa manualmente `crewai/.venv`: `uv run` selecciona el entorno sincronizado. OpenSpec es una dependencia local del workspace y se invoca con `OPENSPEC_TELEMETRY=0 pnpm exec openspec`; no se instala globalmente.

`DEV-5` esta archivado en OpenSpec. El comando anterior documenta la forma del entrypoint; toda ejecucion que pueda crear, modificar o archivar artefactos debe sustituirlo por un ticket activo.

Actualmente el archivo `.env.example` de la raiz documenta variables previstas, pero las aplicaciones Node no cargan de forma uniforme un `.env.local` raiz. En particular, la API necesita recibir `PORT` desde el entorno para no competir con la web por el puerto 3000.

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

Ejecuta en paralelo todos los scripts `dev` del workspace. Web y API intentan usar el puerto 3000 si `PORT` no se exporta, por lo que conviene iniciar la API con un puerto explicito.

## Scripts Node

Los siguientes scripts existen en el `package.json` raiz:

| Comando | Descripcion |
| --- | --- |
| `pnpm dev` | Ejecuta los scripts `dev` del workspace en paralelo. |
| `pnpm build` | Compila recursivamente los paquetes que definen `build`. |
| `pnpm lint` | Ejecuta lint recursivamente en modo de solo lectura. |
| `pnpm test` | Ejecuta la suite Vitest. |
| `pnpm test:shell` | Ejecuta las pruebas de bootstrap y doctor: Bash en Unix y PowerShell en Windows. |
| `pnpm crew:check` | Ejecuta pytest y la validacion estricta de OpenSpec. |
| `pnpm verify` | Ejecuta lint, todas las pruebas, builds y verificaciones de CrewAI/OpenSpec. |
| `pnpm clean` | Elimina artefactos generados mediante los scripts de cada paquete. |
| `pnpm start:web` | Inicia un build previo de Next.js. |
| `pnpm start:api` | Inicia el artefacto compilado de la API. |
| `pnpm start:worker` | Inicia el artefacto compilado del worker. |

No existen todavia los scripts `format`, `db:start` ni `db:stop`.

## Paquetes Compartidos

### `@koty-app/contracts`

Contiene por ahora tipos TypeScript basicos para respuestas API, paginacion y estado de salud. Los esquemas Zod compartidos se incorporaran cuando los limites de API los necesiten.

### `@koty-app/config`

Exporta configuraciones compartidas de TypeScript y ESLint. Tailwind CSS permanece configurado dentro de `apps/web`.

## CrewAI

El subproyecto `crewai/` automatiza analisis, planificacion, implementacion y revision de cambios mediante agentes. Sus dependencias se administran exclusivamente con `uv` y las sincroniza el bootstrap correspondiente a la plataforma: `./scripts/bootstrap.sh` en Unix o `scripts/bootstrap.ps1` en Windows.

Configura en `crewai/.env` las claves y modelos requeridos por el archivo de ejemplo:

- `LINEAR_API_KEY`
- `OPENCODE_API_KEY`
- `ZEN_BASE_URL`
- `ZEN_ANALYST_MODEL`
- `ZEN_ARCHITECT_MODEL`
- `ZEN_CODER_MODEL`
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

- El codigo presente es scaffolding y no implementa todavia el incremento 0.
- No hay PostgreSQL local, Prisma, migraciones ni Docker Compose.
- `pnpm format`, `pnpm db:start` y `pnpm db:stop` no existen.
- La estrategia de variables de entorno Node aun no esta unificada.
- Los comandos `start` de produccion requieren revision antes de usarse para despliegue.

## Contribucion

Antes de abrir un cambio, consulta [`CONTRIBUTING.md`](./CONTRIBUTING.md), `CONTEXT.md` y las especificaciones OpenSpec aplicables. No declares pruebas ejecutadas si el comando correspondiente no existe o no ejecuto una suite real.

## Licencia

Privado - PLAN-DEPTO.
