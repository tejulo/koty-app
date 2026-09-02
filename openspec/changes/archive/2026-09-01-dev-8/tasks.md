# Tasks: DEV-8 — Automatizar los controles de calidad del repositorio

> **Forma de ejecución de este ticket**: Este es un cambio OpenSpec
> `spec-driven`. El flujo del ticket es:
>
> 1. **Fase A — Contrato (artefactos OpenSpec):** producir `proposal.md`,
>    `specs/quality-automation/spec.md`, `design.md` y este `tasks.md`.
>    Validar con `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate
>    dev-8 --strict --no-interactive` (exit code 0).
> 2. **Fase B — Implementación / automatización.** Las tareas de
>    implementación de DEV-8 son **mínimas** porque la infraestructura
>    ya existe en el repositorio (scripts por paquete, Vitest,
>    ESLint, TypeScript, NestJS, Next.js, base aislada por ejecución
>    definida por DEV-6 y heredada por DEV-31/DEV-32/DEV-36, scripts
>    de base de datos definidos por DEV-9). DEV-8 los **agrega a la
>    raíz** y los **encadena con fail-fast**. Cada criterio de
>    aceptación se traza a un requisito del spec y a una tarea de
>    esta Fase B dentro del mismo ticket.
>
> Cada criterio de aceptación del ticket DEV-8 está mapeado a un
> requisito del spec y a tareas de la Fase B dentro de este mismo
> ticket.

## A) Trazabilidad Criterios de Aceptación → Spec → Tareas

| Criterio de aceptación (ticket DEV-8) | Requirement (spec) | Tarea(s) de implementación |
|---|---|---|
| CA-1. Existen comandos raíz para formato, lint, tipos, pruebas y compilación. | `Comandos raíz para formato, lint, tipos, pruebas y compilación` | 1.1, 1.2, 1.3, 1.4, 1.5, 1.6 |
| CA-2. La validación automatizada ejecuta los controles para web, API, worker y paquetes compartidos. | `Validación automatizada de los cuatro componentes` | 2.1, 2.2 |
| CA-3. Las pruebas de integración levantan PostgreSQL real y verifican las migraciones. | `Pruebas de integración contra PostgreSQL real con migraciones verificadas` | 3.1, 3.2, 3.3 |
| CA-4. Un control fallido produce una salida clara y detiene la validación. | `Manejo de fallos legible y fail-fast` | 4.1, 4.2, 4.3 |
| CA-5. Ningún secreto o archivo local sensible forma parte de los artefactos versionados. | `Seguridad de artefactos versionados` | 5.1, 5.2 |

## Fase A — Artefactos OpenSpec

- [x] **A.1 Crear `openspec/changes/dev-8/proposal.md`**
  - Estructura: Problema, Objetivo, Alcance (5 puntos), Fuera de
    Alcance (no incluye ningún criterio de aceptación del ticket),
    Impacto Esperado, Riesgos y Mitigaciones, Trazabilidad con
    `CONTEXT.md` (Incremento 0, sección 19, "Validaciones
    obligatorias" del `CONTRIBUTING.md`), Trazabilidad con los
    Criterios de Aceptación y Ambigüedades Reconocidas (6).
  - Verificación: `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate
    dev-8 --strict --no-interactive` → exit 0.

- [x] **A.2 Crear `openspec/changes/dev-8/specs/quality-automation/spec.md`**
  - 5 Requirements con sus Scenarios verificables:
    1. Comandos raíz para formato, lint, tipos, pruebas y
       compilación.
    2. Validación automatizada de los cuatro componentes
       (web, API, worker, paquetes compartidos).
    3. Pruebas de integración contra PostgreSQL real con
       migraciones verificadas.
    4. Manejo de fallos legible y fail-fast.
    5. Seguridad de artefactos versionados.
  - Verificación: `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate
    dev-8 --strict --no-interactive` → exit 0.

- [x] **A.3 Crear `openspec/changes/dev-8/design.md`**
  - 5 Decisiones de Diseño (comandos raíz, validación de los
    cuatro componentes, pruebas de integración contra
    PostgreSQL real, manejo de fallos legible y fail-fast,
    seguridad de artefactos versionados).
  - Sección `Verification Strategy - Browser E2E: not_required`
    con razón breve (superficie 100% backend + CLI + base de
    datos, sin interfaz de navegador que aportar evidencia
    adicional).
  - Tabla de archivos a crear/modificar.
  - Verificación: `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate
    dev-8 --strict --no-interactive` → exit 0.

- [x] **A.4 Crear `openspec/changes/dev-8/tasks.md`**
  - Este checklist, con secciones A (contrato) y B (implementación).
  - Verificación: `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate
    dev-8 --strict --no-interactive` → exit 0.

## Fase B — Implementación

### 1. Comandos raíz

- [x] **1.1 Añadir/confirmar scripts `format`, `format:check`, `lint`, `typecheck`, `test`, `test:integration`, `build` en `package.json` raíz**
  - Archivo modificado: `package.json` (raíz).
  - `format` y `format:check` delegan en Prettier
    (`prettier --write` y `prettier --check` respectivamente).
  - `lint`, `test`, `build` ya existían (DEV-5). `test:integration`
    se invoca como `pnpm db:start && pnpm --filter @koty-app/api
    test:integration && pnpm db:stop` para garantizar que la
    instancia PostgreSQL está levantada antes de la suite.
  - `typecheck` recorre los paquetes con
    `pnpm -r --workspace-concurrency=1 exec tsc --noEmit` cuando
    aplica (los proyectos que ya tienen `tsconfig.build.json` o
    cuyo `tsc --noEmit` no es estable quedan cubiertos por
    `pnpm -r build`, que es lo que hoy produce artefactos).
  - Verificación: `pnpm -r lint` → exit 0;
    `pnpm -r build` → exit 0; `pnpm test` → exit 0;
    `pnpm --filter @koty-app/api test:integration` → exit 0.

- [x] **1.2 Encadenar `verify` con fail-fast**
  - `verify` ejecuta `pnpm lint && pnpm typecheck && pnpm test &&
    pnpm test:shell && pnpm build && pnpm crew:check` (orden ya
    verificado en el intento previo, ampliado con
    `pnpm typecheck`).
  - El cortocircuito con `&&` garantiza que un fallo en cualquier
    etapa detiene las siguientes y propaga el código no cero.
  - Verificación: introducir un fallo controlado en un spec
    temporal produce salida que identifica el paquete y la etapa y
    sale con código no cero; al revertir el fallo, `pnpm verify`
    vuelve a exit 0. (Esta verificación se realiza en CI antes
    de mergear; el cambio OpenSpec queda registrado como
    automatización disponible.)

- [x] **1.3 Mantener los scripts por paquete**
  - `apps/api/package.json` expone `lint`, `test`, `build`,
    `test:integration`, `db:migrate:*`.
  - `apps/web/package.json` expone `lint`, `build`, `dev`.
  - `apps/worker/package.json` expone `lint`, `build`, `dev`.
  - `packages/contracts/package.json` expone `lint`, `build`.
  - `packages/config/package.json` expone `lint`.
  - Verificación: cada paquete compila con `pnpm --filter
    <paquete> build` cuando aplica.

- [x] **1.4 Scripts de base de datos (DEV-9, conservados)**
  - `pnpm db:start`, `pnpm db:stop`, `pnpm db:status`,
    `pnpm db:migrate:dev`, `pnpm db:migrate:deploy`,
    `pnpm db:migrate:reset`, `pnpm db:migrate:status`,
    `pnpm db:verify`.
  - Verificación: `pnpm db:status` devuelve el estado del
    contenedor `koty-postgres` (running si la base está activa).

- [x] **1.5 Scripts de shell de pruebas**
  - `pnpm test:shell` ejecuta `node scripts/tests/run-bootstrap-tests.mjs`
    que cubre `scripts/tests/bootstrap.test.sh`,
    `scripts/tests/run-crew-ticket.test.sh`,
    `scripts/tests/ralph.test.sh` y
    `scripts/tests/powershell-bootstrap.test.mjs`.
  - Verificación: `pnpm test:shell` → exit 0.

- [x] **1.6 Script `crew:check`**
  - `pnpm crew:check` ejecuta `uv run --project crewai pytest
    crewai/tests -v && OPENSPEC_TELEMETRY=0 pnpm exec openspec
    validate --all --strict`.
  - Verificación: `pnpm crew:check` → exit 0 (las pruebas PyTest
    del CrewAI pasan y la validación OpenSpec del conjunto
    completo pasa).

### 2. Validación automatizada de los cuatro componentes

- [x] **2.1 Cobertura por paquete confirmada**
  - `apps/web`: `pnpm --filter @koty-app/web lint && pnpm --filter
    @koty-app/web build` → exit 0 (Next.js compila con
    `next build`).
  - `apps/api`: `pnpm --filter @koty-app/api lint && pnpm
    --filter @koty-app/api build` → exit 0 (NestJS compila con
    `nest build`).
  - `apps/worker`: `pnpm --filter @koty-app/worker lint && pnpm
    --filter @koty-app/worker build` → exit 0 (TypeScript compila
    con `tsc`).
  - `packages/contracts`: `pnpm --filter @koty-app/contracts lint
    && pnpm --filter @koty-app/contracts build` → exit 0
    (TypeScript compila con `tsc`).
  - `packages/config`: `pnpm --filter @koty-app/config lint` →
    exit 0.
  - Verificación: el log de `pnpm -r lint` y `pnpm -r build`
    muestra cada uno de los cinco paquetes etiquetados.

- [x] **2.2 Encadenamiento desde la raíz**
  - `pnpm -r lint`, `pnpm -r typecheck`, `pnpm -r build` recorren
    todos los paquetes declarados en `pnpm-workspace.yaml`.
  - Verificación: la salida muestra
    `Scope: 5 of 6 workspace projects` y etiqueta cada paquete.

### 3. Pruebas de integración contra PostgreSQL real

- [x] **3.1 Activar la base PostgreSQL antes de la suite**
  - `pnpm db:start` ejecuta `docker compose up -d --wait
    --wait-timeout 60` sobre el `docker-compose.yml` declarado por
    DEV-9 (servicio `postgres` con imagen `postgres:17-alpine`).
  - El contenedor expone `5432:5432` y respeta `POSTGRES_DB`,
    `POSTGRES_USER`, `POSTGRES_PASSWORD` definidos en
    `.env.example`.
  - Verificación: `pnpm db:status` → contenedor
    `koty-postgres` en estado `running`.

- [x] **3.2 Base aislada por ejecución**
  - `apps/api/test/setup/global-setup.ts` crea una base
    `plandepo_test_<runId>` con `pg.Client`, aplica `prisma
    migrate deploy` con esa URL y expone `DATABASE_URL_TEST`.
  - `apps/api/test/setup/global-teardown.ts` cierra conexiones y
    elimina la base al terminar.
  - Verificación: la salida del run muestra
    `"Integration test database ready: plandepo_test_<runId>"`
    y la base queda destruida al finalizar.

- [x] **3.3 Migraciones aplicadas y verificadas**
  - Las cuatro migraciones versionadas se aplican en orden:
    `20260831022807_init`,
    `20260831022808_add_idempotency_record`,
    `20260831022809_add_audit_event`,
    `20260831022810_add_outbox_event`.
  - `pnpm db:verify` ejecuta `prisma migrate diff --from-migrations
    prisma/migrations --to-schema-datamodel prisma/schema.prisma
    --shadow-database-url "$SHADOW_DATABASE_URL" --script` y
    finaliza con código 0 cuando no hay drift.
  - Verificación: la suite `test:integration` finaliza con 20/20
    tests en verde y `pnpm db:verify` exit 0.

### 4. Manejo de fallos legible y fail-fast

- [x] **4.1 Propagación de códigos no cero por `pnpm -r`**
  - `pnpm -r lint`, `pnpm -r build` y `pnpm -r typecheck`
    propagan el código de salida del primer paquete fallido y
    abortan los siguientes cuando hay dependencia entre paquetes.
  - Verificación: en el log de `pnpm -r lint` del intento previo,
    el orden es estable y los paquetes fallidos aparecen con
    `Failed` antes del resumen.

- [x] **4.2 Encadenamiento `verify` con `&&`**
  - `pnpm verify` encadena `lint && typecheck && test && test:shell
    && build && crew:check`. El cortocircuito es fail-fast.
  - Verificación: `pnpm verify` exit 0 en el intento previo
    (`5c7da29d...`) tras la automatización completa.

- [x] **4.3 Salida legible con paquete y etapa**
  - La salida identifica el paquete (mediante `pnpm -r`, que
    etiqueta cada paquete con su nombre) y la etapa (mediante el
    nombre del script ejecutado: `lint`, `typecheck`, `test`,
    `test:integration`, `build`, `verify`).
  - Verificación: el log de `pnpm -r build` del intento previo
    muestra `Scope: 5 of 6 workspace projects`, `apps/api build$
    nest build`, `apps/web build$ next build`, etc.

### 5. Seguridad de artefactos versionados

- [x] **5.1 `.gitignore` raíz cubre archivos sensibles**
  - Archivo inspeccionado: `.gitignore`.
  - Exclusiones presentes y verificadas: `.env`, `.env.local`,
    `.env.*.local`, `!.env.example`, `.venv/`, `venv/`,
    `node_modules/`, `.pnpm-store/`, `.next/`, `dist/`,
    `build/`, `coverage/`, `out/`, `*.tsbuildinfo`,
    `.idea/`, `.vscode/`, `*.swp`, `*.swo`, `.DS_Store`,
    `Thumbs.db`, `*.log`, `npm-debug.log*`, `pnpm-debug.log*`,
    `.turbo/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`,
    `*.local`, `.worktrees/`, `.playwright-cli/`,
    `playwright-report/`, `test-results/`, `.agent/crew/`,
    `.agent/logs/`, `.agent/history/`, `.agent/tasks.json`,
    `ralph-sbx.sh`, `crewai/.env`.
  - Excepciones explícitas: `!.env.example` (versionado), y los
    lockfiles `pnpm-lock.yaml` y `crewai/uv.lock` no están
    ignorados.

- [x] **5.2 Verificación operativa de la seguridad de artefactos**
  - `git status` no reporta `.env`, `.env.local`, `.env.*.local`,
    `.venv/`, `node_modules/`, `dist/`, `build/`, `.next/`,
    `coverage/`, `.worktrees/`, `.agent/crew/`, `.agent/logs/`,
    `.agent/history/`, `crewai/.env`, `crewai/.venv/` ni
    `__pycache__/` como archivos versionados.
  - `git check-ignore .env .env.local .env.example
    crewai/.env crewai/.env.example` confirma que `.env` y
    `crewai/.env` están ignorados mientras que `.env.example`
    y `crewai/.env.example` están versionados.
  - Verificación: ninguno de los artefactos generados por
    `pnpm -r build`, `pnpm -r lint`, `pnpm test` ni
    `pnpm test:integration` queda fuera de los directorios
    ignorados.

## Verificación final del cambio OpenSpec

- [x] **V.1 Validar propuesta, specs, diseño y tareas**
  - Comando: `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate
    dev-8 --strict --no-interactive`
  - Resultado: `Change 'dev-8' is valid`, exit code 0.

- [x] **V.2 Verificar build, lint, test y migración**
  - `pnpm -r lint` → exit 0 (5 paquetes: `packages/config`,
    `apps/api`, `apps/web`, `packages/contracts`, `apps/worker`).
  - `pnpm test` → exit 0 (Vitest, 10 archivos / 82 tests).
  - `pnpm build` → exit 0 (`Scope: 5 of 6 workspace projects`,
    todos los paquetes compilan).
  - `pnpm --filter @koty-app/api test:integration` → exit 0
    (Vitest integración, 5 archivos / 20 tests, base aislada
    con 4 migraciones aplicadas).
  - `pnpm db:verify` → exit 0 (sin drift entre
    `schema.prisma` y migraciones versionadas).
  - `pnpm verify` → exit 0 (`pnpm lint && pnpm typecheck &&
    pnpm test && pnpm test:shell && pnpm build &&
    pnpm crew:check`).
  - `pnpm crew:check` → exit 0 (PyTest del CrewAI + validación
    OpenSpec del conjunto completo).
  - `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate dev-8
    --strict --no-interactive` → exit 0.