# PLAN-DEPTO

PLAN-DEPTO es un sistema SaaS de administracion de alquileres para el mercado paraguayo. Este repositorio contiene el scaffolding inicial del monorepo y las herramientas auxiliares de especificacion y automatizacion.

La especificacion funcional y tecnica del producto esta en [`CONTEXT.md`](./CONTEXT.md). Ese documento describe el objetivo de V1 y sus incrementos; no representa funcionalidades ya implementadas.

## Estado Actual

El repositorio se encuentra antes de la implementacion funcional del incremento 0.

| Componente | Estado actual |
| --- | --- |
| Web | Next.js 14 con App Router, Tailwind CSS y una pagina inicial estatica. |
| API | NestJS 10 con `GET /` y `GET /health`; aun sin prefijo `/api/v1`, OpenAPI ni modulos de dominio. |
| Worker | Scaffolding TypeScript; el bootstrap existe, pero los scripts actuales no lo ejecutan. |
| Contratos compartidos | Tipos TypeScript basicos; todavia no contiene esquemas Zod. |
| Configuracion compartida | Presets de TypeScript y ESLint. |
| Persistencia | PostgreSQL, Prisma, migraciones y Docker Compose todavia no estan incorporados. |
| Pruebas | No hay suite ni script `pnpm test` configurados. |

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

- Node.js `>=20.11.0`
- pnpm `>=8.15.0`
- Python `>=3.10` y `<3.14`, solo para CrewAI
- [uv](https://docs.astral.sh/uv/), solo para CrewAI
- OpenSpec CLI, para trabajar con especificaciones

Las versiones de dependencias del proyecto quedan fijadas en `pnpm-lock.yaml` y `crewai/uv.lock`.

### pnpm

Con Node.js 20 puede habilitarse pnpm mediante Corepack:

```bash
corepack enable pnpm
pnpm --version
```

La documentacion oficial de pnpm confirma el uso de `--filter` para seleccionar paquetes del workspace. Los nombres validos de este repositorio usan el scope `@koty-app/*`.

### uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

### OpenSpec

```bash
npm install -g @fission-ai/openspec@latest
openspec --version
```

## Instalacion

Desde la raiz del repositorio:

```bash
pnpm install
```

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

El worker no expone HTTP. Sus scripts `dev` y `start` apuntan actualmente a `src/index.ts` y `dist/index.js`, que solo exportan la clase y no ejecutan el bootstrap de `src/main.ts`. Por eso no debe considerarse operativo hasta corregir sus entrypoints.

### Todos los paquetes

El script raiz existe:

```bash
pnpm dev
```

Ejecuta en paralelo todos los scripts `dev` del workspace. En el estado actual no es el flujo recomendado porque web y API intentan usar el puerto 3000 si `PORT` no se exporta, y el worker no inicia su bootstrap.

## Scripts Node

Los siguientes scripts existen en el `package.json` raiz:

| Comando | Descripcion |
| --- | --- |
| `pnpm dev` | Ejecuta los scripts `dev` del workspace en paralelo. |
| `pnpm build` | Compila recursivamente los paquetes que definen `build`. |
| `pnpm lint` | Ejecuta lint recursivamente; API y worker aplican `--fix`. |
| `pnpm clean` | Elimina artefactos generados mediante los scripts de cada paquete. |
| `pnpm start:web` | Inicia un build previo de Next.js. |
| `pnpm start:api` | Inicia el artefacto compilado de la API. |
| `pnpm start:worker` | Script presente, pero bloqueado por el entrypoint descrito arriba. |

No existen todavia los scripts `test`, `format`, `db:start` ni `db:stop`.

## Paquetes Compartidos

### `@koty-app/contracts`

Contiene por ahora tipos TypeScript basicos para respuestas API, paginacion y estado de salud. Los esquemas Zod compartidos se incorporaran cuando los limites de API los necesiten.

### `@koty-app/config`

Exporta configuraciones compartidas de TypeScript y ESLint. Tailwind CSS permanece configurado dentro de `apps/web`.

## CrewAI

El subproyecto `crewai/` automatiza analisis, planificacion, implementacion y revision de cambios mediante agentes. Sus dependencias se administran exclusivamente con `uv`.

```bash
cd crewai
uv sync --frozen
cp .env.example .env
```

Configura en `crewai/.env` las claves y modelos requeridos por el archivo de ejemplo:

- `LINEAR_API_KEY`
- `OPENCODE_API_KEY`
- `ZEN_BASE_URL`
- `ZEN_ANALYST_MODEL`
- `ZEN_ARCHITECT_MODEL`
- `ZEN_CODER_MODEL`
- `ZEN_REVIEWER_MODEL`

Ejecutar un ticket:

```bash
uv run run_crew DEV-5
```

Alternativamente:

```bash
uv run python src/crew/main.py DEV-5
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
openspec list
openspec list --specs
openspec show my-change
openspec status --change my-change
openspec validate --all --strict
```

Los identificadores de cambios activos usan kebab-case en minusculas. `DEV-5` ya esta archivado en `openspec/changes/archive/2026-08-18-dev-5/`, por lo que no aparece como cambio activo.

## Limitaciones Conocidas

- El codigo presente es scaffolding y no implementa todavia el incremento 0.
- No hay PostgreSQL local, Prisma, migraciones ni Docker Compose.
- `pnpm test`, `pnpm format`, `pnpm db:start` y `pnpm db:stop` no existen.
- El worker no ejecuta su bootstrap mediante sus scripts actuales.
- La estrategia de variables de entorno Node aun no esta unificada.
- Los comandos `start` de produccion requieren revision antes de usarse para despliegue.

## Contribucion

Antes de abrir un cambio, consulta [`CONTRIBUTING.md`](./CONTRIBUTING.md), `CONTEXT.md` y las especificaciones OpenSpec aplicables. No declares pruebas ejecutadas si el comando correspondiente no existe o no ejecuto una suite real.

## Licencia

Privado - PLAN-DEPTO.
