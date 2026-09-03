# Instrucciones para agentes

## Estructura y alcance

- Es un workspace pnpm sin Turborepo: `apps/web` es Next.js, `apps/api` es NestJS, `apps/worker` es el worker TypeScript, `packages/contracts` contiene contratos compartidos y `packages/config` contiene presets.
- El repositorio sigue siendo scaffolding; no asumas que el dominio del Incremento 0 ya esta implementado. Consulta `CONTEXT.md` y el OpenSpec aplicable antes de cambiar comportamiento.
- `crewai/` es un subproyecto Python independiente. Antes de modificarlo lee `crewai/AGENTS.md`; usa `uv`, no actives manualmente `crewai/.venv`.

## Toolchain y entorno

- Las versiones fijadas en `.mise.toml` son Node `20.20.2`, pnpm `11.3.0`, Python `3.12.13` y uv `0.11.16`; ejecuta `./scripts/bootstrap.sh` o `scripts/bootstrap.ps1` para sincronizar lockfiles.
- El bootstrap no modifica el shell padre. Si `mise` no esta activado, usa `mise exec -- <comando>`; no ejecutes comandos con versiones globales distintas a las fijadas.
- Copia `.env.example` a `.env` y completa `crewai/.env` desde `crewai/.env.example`; nunca versiona secretos, `.env`, `crewai/.env`, `node_modules`, `dist` o `.next`.
- La API requiere `DATABASE_URL` antes de arrancar y usa `api/v1` como prefijo por defecto; Swagger esta en `/api/docs` y el JSON en `/api/docs-json`.
- La web usa el puerto `3000`; la API usa `3001` por defecto. Si ejecutas varios servicios, define `PORT` explícitamente para evitar colisiones.

## Comandos de desarrollo

- Instala dependencias con `pnpm install --frozen-lockfile`.
- Ejecuta todo en desarrollo con `pnpm dev`; para un servicio aislado usa `pnpm --filter @koty-app/web dev`, `PORT=3001 pnpm --filter @koty-app/api dev` o `pnpm --filter @koty-app/worker dev`.
- La puerta canonica es `pnpm verify`, en este orden: lint, typecheck, Vitest, pruebas shell, builds y `crew:check`; la fase typecheck solo ejecuta scripts de paquetes que lo declaran (`--if-present`).
- Para una prueba Vitest concreta usa `pnpm exec vitest run <ruta>`; para integracion usa `pnpm test:integration`, que necesita Docker/PostgreSQL y crea una base aislada por ejecucion.
- Las pruebas de integracion de `apps/api` usan PostgreSQL real, migraciones y `DATABASE_URL`; no sustituyas Prisma por mocks en esa suite.
- PostgreSQL local se administra con `pnpm db:start`, `pnpm db:status` y `pnpm db:stop`; el contenedor expone `localhost:5432`.

## Prisma y OpenSpec

- Las migraciones son explicitas: usa `pnpm db:migrate:dev --name <nombre>`, `pnpm db:migrate:deploy`, `pnpm db:migrate:status` y `pnpm db:verify`. La aplicacion no migra la base al arrancar.
- Un cambio de esquema debe incluir su migracion bajo `apps/api/prisma/migrations/`; `postinstall` ejecuta `prisma generate`.
- OpenSpec ya esta inicializado: no ejecutes `openspec init`. Los cambios activos usan IDs kebab-case en minusculas; valida con `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate <change-id> --strict --no-interactive`.
- No uses el ticket archivado `DEV-5` para ejecuciones que creen o modifiquen artefactos; reemplazalo por un ticket activo.

## Flujo de cambios

- Trabaja desde una branch por ticket, nunca directamente sobre `main`; actualiza `main` antes de crearla.
- Usa nombres como `feat/dev-123-descripcion-corta` y manten un ticket principal por branch, cambio OpenSpec y Pull Request.
- Usa commits Conventional Commits, por ejemplo `feat(api): agregar endpoint`; los titulos de PR usan `[DEV-123] Descripcion`.
- Antes de commit o PR revisa `git status` y `git diff`; agrega archivos selectivamente y confirma que no haya secretos ni artefactos generados.
- Consulta `CONTRIBUTING.md` para el flujo completo de branch, OpenSpec, CrewAI, validacion y PR.
