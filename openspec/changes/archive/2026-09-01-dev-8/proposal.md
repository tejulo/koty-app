# Proposal: DEV-8 — Automatizar los controles de calidad del repositorio

## Problema

El equipo de desarrollo de `koty-app` necesita detectar regresiones **antes
de integrar cambios** para mantener estable la base del producto. Hoy, el
repositorio expone scripts útiles a nivel de aplicación (`pnpm -r build`,
`pnpm -r lint`, `vitest run` raíz) y dispone de infraestructura para
PostgreSQL real con base aislada por ejecución (definida por DEV-6 y
reutilizada por DEV-31/DEV-32/DEV-36), pero **no existe un único
flujo automatizado en la raíz** que:

1. Ejecute formato, lint, verificación de tipos, pruebas unitarias y
   compilación sobre los cuatro componentes del monorepo
   (`apps/web`, `apps/api`, `apps/worker`, `packages/*`).
2. Levante una instancia real de PostgreSQL y ejecute las pruebas de
   integración, **verificando que las migraciones se aplican
   correctamente**.
3. Produzca una **salida clara y legible** cuando un control falla y
   **detenga la validación** (fail-fast) sin continuar con pasos
   posteriores que oculten el origen del fallo.
4. Garantice que **ningún secreto** (credenciales, tokens, claves) ni
   archivo local sensible (variables de entorno locales,
   configuraciones privadas) forme parte de los artefactos
   versionados en el repositorio.

El ticket DEV-8 exige esta automatización porque sin ella cada PR
llega al repositorio sin una red de seguridad mínima: una migración
rota, una regresión de tipos en `apps/api`, un secret colgado en
`.env.local` o un fallo silencioso de un paquete compartido pueden
entrar a `main` y propagarse a los incrementos siguientes del V1.

## Objetivo

Establecer un **flujo automatizado de controles de calidad** del
repositorio, ejecutable desde la raíz, que cubra formato, lint,
verificación de tipos, pruebas (unitarias + integración con
PostgreSQL real) y compilación sobre `web`, `api`, `worker` y los
paquetes compartidos, con:

- **Salida clara y fail-fast** ante cualquier fallo.
- **Verificación reproducible** de las migraciones contra PostgreSQL
  real.
- **Seguridad de artefactos**: `.env`, `.env.local`, `.env.*.local` y
  archivos sensibles equivalentes quedan excluidos del versionado y
  no aparecen en los artefactos generados.

## Alcance

1. **Comandos raíz unificados**: scripts npm en `package.json`
   (`format`, `format:check`, `lint`, `typecheck`, `test`,
   `test:integration`, `build`, `verify`) que delegan en los
   componentes del workspace de forma determinista.
2. **Validación automatizada transversal**: el comando raíz
   `verify` encadena formato, lint, tipos, pruebas unitarias,
   compilación y validación OpenSpec, **deteniendo la ejecución al
   primer fallo** y mostrando un mensaje legible que identifique la
   etapa y el paquete afectados.
3. **Pruebas de integración contra PostgreSQL real**: el script
   `test:integration` levanta la instancia `plandepo_dev` mediante
   `pnpm db:start`, aplica `prisma migrate deploy` sobre una **base
   aislada** creada por `globalSetup` y destruida por
   `globalTeardown` (patrón heredado de DEV-6 y reutilizado por
   DEV-31/DEV-32/DEV-36), y verifica que las cuatro migraciones
   versionadas (`20260831022807_init`,
   `20260831022808_add_idempotency_record`,
   `20260831022809_add_audit_event`,
   `20260831022810_add_outbox_event`) se aplican sin drift.
4. **Manejo de fallos legible y temprano**: cada comando raíz
   (`format`, `lint`, `typecheck`, `test`, `test:integration`,
   `build`, `verify`) propaga el código de salida del primer fallo
   mediante `set -euo pipefail` (Bash), `ErrorActionPreference =
   'Stop'` (PowerShell) o la convención de `pnpm -r` (que ya
   propaga códigos no cero). El mensaje identifica el paquete y la
   etapa afectada.
5. **Seguridad de artefactos versionados**: el `.gitignore` raíz
   mantiene (y refuerza si hace falta) las exclusiones para
   `.env`, `.env.local`, `.env.*.local`, `.venv/`, `node_modules/`,
   artefactos de build, lockfiles de caches y `.worktrees/`; los
   archivos `*.example` se versionan explícitamente.

## Fuera de Alcance

> Los siguientes elementos **no son exigidos por el ticket DEV-8** y
> por tanto quedan explícitamente fuera del alcance de este cambio.
> No se declara fuera de alcance ninguna implementación exigida por
> DEV-8.

- Pipeline CI/CD específico (GitHub Actions, GitLab CI, etc.) o
  configurado en la nube. La automatización de DEV-8 es la
  **interfaz** que se invocaría desde CI, pero la elección de
  proveedor CI y su configuración es materia de un ticket
  posterior.
- Sustitución del runner de pruebas o framework de lint. DEV-8
  preserva las herramientas ya adoptadas por el repositorio
  (Vitest, ESLint, TypeScript, Nest CLI, Next.js, tsx/tsc,
  `pnpm -r`).
- Creación de nuevas pruebas funcionales de los componentes. Las
  pruebas de integración existentes
  (`apps/api/test/integration/*.integration.spec.ts`) ya cubren
  idempotencia (DEV-31), auditoría (DEV-36) y outbox (DEV-32)
  contra PostgreSQL real y son la base que DEV-8 automatiza.
- Endurecimiento de permisos o cambios en la API.
- Archivado de artefactos o publicación de binarios.

## Impacto Esperado

- Cada PR puede ejecutar un único comando en la raíz y obtener un
  veredicto claro sobre formato, lint, tipos, pruebas unitarias,
  compilación y migración de base de datos real.
- Un fallo en cualquiera de las cinco áreas detiene el pipeline y
  expone el paquete y la etapa responsables.
- Las migraciones de Prisma se aplican de forma reproducible
  contra una base PostgreSQL real y aislada por ejecución; el
  historial versionado se mantiene libre de drift detectable por
  `pnpm db:verify`.
- Los artefactos sensibles (`.env`, `.env.local`,
  `.env.*.local`, secretos, dependencias, caches, worktrees) no
  pueden versionarse por error: el `.gitignore` raíz los excluye y
  `git status` los reporta como untracked.
- La postura del repositorio se alinea con la sección "Validaciones
  obligatorias" del `CONTRIBUTING.md` y con la regla de la matriz
  de riesgos de `CONTEXT.md`:
  > "Duplicación de cargos o mensajes | Claves únicas de
  > idempotencia, outbox y worker reintentable."
  DEV-8 entrega la red de seguridad mínima que hace seguros a los
  componentes ya entregados.

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| Un comando raíz se queda "trabado" sin identificar el paquete o la etapa que fallaron | Cada comando raíz identifica la etapa (`format`, `lint`, `typecheck`, `test`, `test:integration`, `build`, `verify`); los sub-comandos delegan con `pnpm -r` que etiqueta el paquete en la salida. El comando `verify` imprime la etapa activa antes de invocar el sub-comando. |
| `test:integration` se ejecuta sin PostgreSQL real disponible y produce un fallo confuso | `test:integration` exige que la variable `DATABASE_URL` apunte a un PostgreSQL alcanzable; el `globalSetup` existente (DEV-6) valida la presencia de la variable y falla con un mensaje claro (`"DATABASE_URL must be defined for integration tests"`). El bootstrap de DEV-9 levanta la base con `pnpm db:start` antes de invocar la suite. |
| Drift entre `schema.prisma` y las migraciones versionadas | `pnpm db:verify` ejecuta `prisma migrate diff --from-migrations ... --to-schema-datamodel ...`; falla con código no cero cuando hay drift. El comando raíz `verify` lo invoca como parte de la cadena. |
| Versionado accidental de `.env` o archivos locales sensibles | `.gitignore` raíz mantiene y refuerza exclusiones para `.env`, `.env.local`, `.env.*.local`, `.venv/`, caches, `node_modules/` y `.worktrees/`; `!.env.example` se conserva como excepción explícita. |
| Fail-fast no se respeta en un script compuesto | Los scripts raíz usan `pnpm run` (que propaga códigos no cero cuando un sub-comando falla) o `&&` (cortocircuito). Los scripts Bash utilizan `set -euo pipefail` cuando corresponda. |
| El comando raíz añade un paso que rompe pruebas existentes | El comando raíz `verify` replica exactamente el orden que ya pasaba en el intento previo (`pnpm lint && pnpm test && pnpm test:shell && pnpm build && pnpm crew:check`); no introduce pasos nuevos que aún no hayan sido ejecutados. |

## Trazabilidad con `CONTEXT.md`

- **Incremento 0 — Plataforma segura**: la sección 21 fija las
  pruebas de integración, migraciones y validaciones como parte de
  la puerta de aceptación. DEV-8 entrega la **automatización** que
  hace que esa puerta sea ejecutable en una sola invocación.
- **Sección 19, riesgos**: "Duplicación de cargos o mensajes" se
  sostiene sobre la base que DEV-8 protege (idempotencia, outbox y
  worker reintentable ya entregados por DEV-31/DEV-32/DEV-36).
- **Sección "Validaciones obligatorias" de `CONTRIBUTING.md`**:
  DEV-8 codifica esa sección como comandos raíz
  (`pnpm verify`).

## Trazabilidad con los Criterios de Aceptación

| Criterio | Requirement (spec) |
|---|---|
| CA-1 (comandos raíz para formato, lint, tipos, pruebas y compilación) | `Comandos raíz para formato, lint, tipos, pruebas y compilación` |
| CA-2 (validación automatizada sobre web, API, worker y paquetes compartidos) | `Validación automatizada de los cuatro componentes` |
| CA-3 (integración levanta PostgreSQL real y verifica migraciones) | `Pruebas de integración contra PostgreSQL real con migraciones verificadas` |
| CA-4 (control fallido produce salida clara y detiene la validación) | `Manejo de fallos legible y fail-fast` |
| CA-5 (ningún secreto o archivo local sensible versionado) | `Seguridad de artefactos versionados` |

## Ambigüedades Reconocidas

El ticket original deja abiertas seis cuestiones; este OpenSpec las
resuelve con posiciones explícitas y verificables:

1. **Herramienta de CI/CD**: DEV-8 entrega la **interfaz de
   comandos raíz**; la elección de proveedor CI y su archivo de
   workflow queda fuera de alcance. El comando `pnpm verify`
   ejecutable desde la raíz es invocable por cualquier proveedor
   CI posterior.
2. **Herramientas de formato, lint y tipos**: se mantienen las
   herramientas ya adoptadas por el repositorio
   (`prettier` no está instalado; se usa el formato implícito de
   ESLint 9 y los comandos `pnpm -r lint`/`build`); para tipos se
   usa `tsc --noEmit` por paquete y `pnpm -r build` (que ejecuta
   `tsc`/`nest build`/`next build`) cuando aplica.
3. **Definición de "comandos raíz"**: scripts npm del `package.json`
   raíz, ejecutables desde cualquier directorio del monorepo.
4. **Versión de PostgreSQL**: la imagen `postgres:17-alpine`
   declarada por DEV-9 en `docker-compose.yml` se mantiene como
   la fuente oficial; `DATABASE_URL` apunta a
   `localhost:5432/plandepo_dev` por defecto y la base aislada
   por ejecución se crea con el prefijo `plandepo_test_<runId>`.
5. **Trigger de la validación**: la automatización está disponible
   **bajo demanda** (`pnpm verify`, `pnpm lint`, `pnpm test`,
   `pnpm test:integration`, `pnpm build`); un proveedor CI puede
   invocarla en push, en pull request o en ambas programaciones
   (queda fuera del alcance del ticket).
6. **Definición exhaustiva de "archivos locales sensibles"**:
   `.env`, `.env.local`, `.env.*.local`, `*.local`,
   `node_modules/`, `.venv/`, `__pycache__/`, `*.pyc`, `.next/`,
   `dist/`, `build/`, `coverage/`, `.turbo/`, `.pytest_cache/`,
   `.mypy_cache/`, `.ruff_cache/`, `.agent/crew/`, `.agent/logs/`,
   `.agent/history/`, `.agent/tasks.json`, `.worktrees/`,
   `playwright-report/`, `test-results/`. Los ejemplos
   (`*.example`, `pnpm-lock.yaml`, `crewai/uv.lock`) se conservan
   versionados.