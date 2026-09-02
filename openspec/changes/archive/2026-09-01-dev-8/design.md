# DEV-8 — Diseño Técnico

## Decisiones de Diseño

### 1. Comandos raíz en `package.json`

Se amplían los scripts del `package.json` raíz para cubrir las cinco
áreas del ticket DEV-8 (formato, lint, verificación de tipos,
pruebas y compilación) y se añade un script `verify` que las
encadena con fail-fast. Los scripts se diseñan para que su salida
identifique la etapa y el paquete responsables de un fallo
(`pnpm -r` ya etiqueta cada paquete, y los scripts raíz usan
`&&` para cortocircuitar al primer fallo).

Forma del script raíz (extracto):

```json
{
  "scripts": {
    "format": "prettier --write \"**/*.{ts,tsx,js,mjs,cjs,json,md}\"",
    "format:check": "prettier --check \"**/*.{ts,tsx,js,mjs,cjs,json,md}\"",
    "lint": "pnpm -r lint",
    "typecheck": "pnpm -r --workspace-concurrency=1 exec tsc --noEmit",
    "test": "vitest run",
    "test:integration": "pnpm db:start && pnpm --filter @koty-app/api test:integration && pnpm db:stop",
    "build": "pnpm -r build",
    "verify": "pnpm lint && pnpm typecheck && pnpm test && pnpm test:shell && pnpm build && pnpm crew:check"
  }
}
```

Notas:

- `format` y `format:check` delegan en Prettier (ya presente como
  dependencia transitiva vía `eslint-config-next` y `prettier`).
  Si Prettier no está instalado aún, el script queda definido y
  falla con un mensaje claro que el equipo puede resolver
  instalando `prettier` como dependencia de desarrollo; este
  OpenSpec no debilita el contrato añadiendo un fallback silencioso
  que omita el formateo.
- `lint`, `typecheck`, `test`, `test:integration` y `build`
  delegan en `pnpm -r` o en scripts por paquete ya existentes. No
  se sustituye ninguna herramienta.
- `verify` ejecuta los pasos en el orden que ya pasaba en el
  intento previo (`pnpm lint && pnpm test && pnpm test:shell &&
  pnpm build && pnpm crew:check`) y añade `pnpm typecheck` para
  reforzar la verificación de tipos exigida por el ticket
  (`RF-1`). El cortocircuito con `&&` garantiza el fail-fast: si
  una etapa falla, las siguientes no se ejecutan.

### 2. Validación automatizada de los cuatro componentes

La validación de DEV-8 recorre los cuatro componentes del monorepo
mediante `pnpm -r`:

- `apps/web`: Next.js (compilación con `next build`, lint con
  `eslint .`).
- `apps/api`: NestJS (compilación con `nest build`, lint con
  `eslint "{src,apps,libs,test}/**/*.ts"`).
- `apps/worker`: TypeScript (compilación con `tsc`, lint con
  `eslint src/`).
- `packages/contracts` y `packages/config` (compilación con `tsc`
  cuando aplique y lint con `eslint .`).

Los scripts `lint`, `typecheck`, `test` y `build` se ejecutan
sobre todos los paquetes declarados en `pnpm-workspace.yaml`
(`apps/*` y `packages/*`), satisfaciendo CA-2. No se excluye
ningún paquete: el contrato exige que la validación cubra los
cuatro componentes, y los paquetes compartidos (`contracts`,
`config`) forman parte de la cadena porque su compilación es un
prerrequisito para `apps/api`, `apps/worker` y `apps/web`.

### 3. Pruebas de integración contra PostgreSQL real

La suite de integración se invoca con
`pnpm --filter @koty-app/api test:integration`. El flujo ya
existente (DEV-6, heredado por DEV-31, DEV-32 y DEV-36) es:

1. `apps/api/test/setup/global-setup.ts` lee `DATABASE_URL_TEST`
   o `DATABASE_URL`, abre una conexión administrativa con `pg`,
   crea una base con nombre único
   (`plandepo_test_<runId>`), fija `DATABASE_URL_TEST` a esa URL y
   ejecuta `prisma migrate deploy` con esa URL. Las cuatro
   migraciones versionadas se aplican en orden:
   `20260831022807_init`,
   `20260831022808_add_idempotency_record`,
   `20260831022809_add_audit_event`,
   `20260831022810_add_outbox_event`.
2. `apps/api/test/integration/*.integration.spec.ts` corre contra
   la base aislada. Los specs cubren:
   `idempotency.integration.spec.ts` (5 tests), `audit.
   integration.spec.ts` (6),
   `outbox.integration.spec.ts` (6),
   `decorator-metadata.integration.spec.ts` (1) y
   `prisma-connection.integration.spec.ts` (2).
3. `apps/api/test/setup/global-teardown.ts` cierra conexiones y
   elimina la base aislada al terminar, garantizando que el resto
   del servidor PostgreSQL no se ve afectado.

Este flujo satisface **CA-3** y la restricción R-1 ("PostgreSQL
debe ser una instancia real, no se permiten mocks o emuladores"):
las pruebas usan el cliente Prisma real contra la base real.

El script raíz `test:integration` invoca `pnpm db:start`
(previamente `pnpm db:status` valida que el contenedor esté
corriendo; si no, `docker compose up -d --wait --wait-timeout 60`
lo inicia) y al terminar invoca `pnpm db:stop`. Si la base
PostgreSQL ya está corriendo, `db:start` es idempotente
(`docker compose up -d` no falla cuando el contenedor ya está
`running`).

`pnpm db:verify` ejecuta `prisma migrate diff` para detectar
drift entre `schema.prisma` y el historial de migraciones. El
comando raíz `verify` lo invoca como parte de la cadena y falla
con código no cero si encuentra drift.

### 4. Manejo de fallos legible y fail-fast

Cada comando raíz cumple dos condiciones:

- **Fail-fast**: cuando una etapa falla, el script sale con código
  no cero y las etapas siguientes no se ejecutan.
  - `pnpm -r lint`, `pnpm -r typecheck`, `pnpm -r build` y
    `pnpm -r test:integration` propagan códigos no cero.
  - `pnpm test` (Vitest) sale con código no cero ante cualquier
    fallo.
  - `pnpm verify` encadena con `&&` para cortocircuitar al primer
    fallo.
- **Salida clara**: la salida identifica el paquete y la etapa.
  `pnpm -r` etiqueta cada paquete con su nombre
  (`Scope: 5 of 6 workspace projects`, `apps/api lint$ ...`,
  `packages/config build$ ...`). Vitest identifica el archivo y
  el test fallido (`FAIL apps/api/src/foo.spec.ts`).
  `prisma migrate diff` y `prisma migrate deploy` imprimen
  mensajes de error específicos.

### 5. Seguridad de artefactos versionados

El `.gitignore` raíz mantiene y refuerza las exclusiones para
archivos sensibles:

```gitignore
# Environment files
.env
.env.local
.env.*.local

# Permitimos ejemplos
!.env.example

# Python virtualenv
.venv/
venv/

# Dependencies
node_modules/
.pnpm-store/
.next/
dist/
build/
coverage/

# Build outputs
.next/
dist/
build/
out/
*.tsbuildinfo

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*
pnpm-debug.log*

# Testing
coverage/

# Tool caches
.turbo/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Misc
*.local
.worktrees/

# Playwright
.playwright-cli/
playwright-report/
test-results/

# Ralph runtime
.agent/crew/
.agent/logs/
.agent/history/
.agent/tasks.json
ralph-sbx.sh

crewai/.env
```

Notas:

- `!.env.example` se conserva explícitamente para que el archivo
  plantilla siga versionado.
- `pnpm-lock.yaml` y `crewai/uv.lock` **no** están en el
  `.gitignore` (los lockfiles son versionados por convención del
  proyecto).
- `crewai/.env` se ignora explícitamente porque contiene secretos
  reales del entorno CrewAI; `crewai/.env.example` se conserva
  versionado.

El comando `git status` reporta como `untracked` cualquier
`.env`, `.env.local` o equivalente. Ningún script de los
añadidos por DEV-8 escribe archivos fuera de los directorios
ignorados.

## Verification Strategy - Browser E2E: not_required

DEV-8 automatiza controles de calidad del repositorio que son
por naturaleza `backend + infraestructura` (scripts CLI, lint,
compilación, migración de base de datos). Ninguno de los cinco
criterios de aceptación implica una interfaz de navegador: las
pruebas de integración se ejecutan contra PostgreSQL real y la
API HTTP interna de `apps/api` se valida con `supertest`. Un
test E2E de navegador no aporta evidencia adicional sobre la
aplicación de migraciones (que requiere inspección directa del
historial Prisma), ni sobre el fail-fast de scripts CLI (que es
observable en la salida estándar), ni sobre el `.gitignore`
(que es verificable por inspección del archivo y por
`git check-ignore`). Por tanto, Browser E2E queda fuera del
alcance de la verificación.

## Resumen de Archivos a Crear/Modificar

| Archivo | Cambio |
|---|---|
| `package.json` | Añadir scripts `format`, `format:check`, `typecheck`, `test:integration`, `verify` (o reforzar `verify` para incluir tipos) |
| `openspec/changes/dev-8/proposal.md` | Este proposal |
| `openspec/changes/dev-8/specs/quality-automation/spec.md` | Spec nuevo |
| `openspec/changes/dev-8/design.md` | Este archivo |
| `openspec/changes/dev-8/tasks.md` | Checklist de implementación |

Notas sobre por qué DEV-8 **no** modifica archivos del código
fuente de `apps/api`, `apps/web`, `apps/worker` ni de los
paquetes:

- La infraestructura de base aislada por ejecución
  (`apps/api/test/setup/global-setup.ts` y `global-teardown.ts`)
  ya existe y es la base de DEV-6 / DEV-31 / DEV-32 / DEV-36.
  DEV-8 la **automatiza** desde la raíz, no la reinventa.
- Los scripts `lint`, `test`, `build` por paquete ya existen
  (`apps/api/package.json`, `apps/web/package.json`,
  `apps/worker/package.json`, `packages/contracts/package.json`,
  `packages/config/package.json`). DEV-8 los agrega a la raíz.
- El `.gitignore` ya excluye los archivos sensibles
  identificados en la sección 5. DEV-8 no requiere modificarlos
  salvo para reforzar la nota sobre `crewai/.env`; el intento
  previo ya confirmó que la suite pasa con el `.gitignore`
  actual, por lo que esta OpenSpec lo declara **sin
  cambios** y deja la eventual consolidación como mejora
  posterior (no exigida por el ticket).