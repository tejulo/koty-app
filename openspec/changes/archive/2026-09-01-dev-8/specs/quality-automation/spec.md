# quality-automation Specification

## Purpose
Automatizar los controles de calidad del repositorio mediante
comandos raíz ejecutables desde cualquier directorio del monorepo,
con validación transversal sobre web, API, worker y paquetes
compartidos, pruebas de integración contra PostgreSQL real que
verifican la aplicación de las migraciones, manejo fail-fast con
salida legible y exclusión de secretos y archivos locales sensibles
del versionado.

## ADDED Requirements

### Requirement: Comandos raíz para formato, lint, tipos, pruebas y compilación

El repositorio SHALL expose en la raíz (`package.json`) comandos
ejecutables que cubran, al menos, formato, lint, verificación de
tipos, ejecución de pruebas y compilación, sin requerir `cd` a
ningún subdirectorio.

#### Scenario: Comando de formato accesible desde la raíz
- GIVEN un repositorio clonado con `pnpm install` ejecutado
- WHEN se ejecuta `pnpm format` o `pnpm format:check` desde la
  raíz
- THEN el comando se resuelve a un script npm del `package.json`
  raíz
- AND el comando finaliza con código 0 cuando los archivos ya
  cumplen el formato, o no cero cuando hay archivos por formatear
- AND la salida identifica los archivos afectados cuando aplica

#### Scenario: Comando de lint accesible desde la raíz
- GIVEN un repositorio clonado con `pnpm install` ejecutado
- WHEN se ejecuta `pnpm lint` desde la raíz
- THEN se ejecuta el lint sobre `apps/*` y `packages/*`
- AND finaliza con código 0 cuando no hay infracciones
- AND finaliza con código no cero y salida legible que identifique
  el paquete y los archivos afectados cuando hay infracciones

#### Scenario: Comando de verificación de tipos accesible desde la raíz
- GIVEN un repositorio clonado con `pnpm install` ejecutado
- WHEN se ejecuta `pnpm typecheck` desde la raíz
- THEN se ejecuta la verificación de tipos sobre los proyectos
  TypeScript del monorepo
- AND finaliza con código 0 cuando la verificación pasa

#### Scenario: Comando de pruebas accesible desde la raíz
- GIVEN un repositorio clonado con `pnpm install` ejecutado
- WHEN se ejecuta `pnpm test` desde la raíz
- THEN Vitest ejecuta las pruebas unitarias configuradas
  (`apps/{api,web,worker}/src/**/*.spec.ts` y
  `packages/config/eslint/**/*.spec.js`)
- AND finaliza con código 0 cuando todas las pruebas pasan
- AND excluye las pruebas de integración
  (`apps/api/src/**/*.integration.spec.ts` y `apps/api/test/**`)
  del run por defecto

#### Scenario: Comando de pruebas de integración accesible desde la raíz
- GIVEN un repositorio clonado con `pnpm install` ejecutado y
  PostgreSQL disponible en `localhost:5432`
- WHEN se ejecuta `pnpm test:integration` desde la raíz
- THEN el comando garantiza que el contenedor PostgreSQL está
  corriendo (`pnpm db:start`)
- AND ejecuta la suite de integración de `apps/api` con
  `vitest run --config vitest.config.integration.ts`
- AND finaliza con código 0 cuando las pruebas pasan

#### Scenario: Comando de compilación accesible desde la raíz
- GIVEN un repositorio clonado con `pnpm install` ejecutado
- WHEN se ejecuta `pnpm build` desde la raíz
- THEN se compilan `apps/*` y `packages/*` que tengan script
  `build`
- AND finaliza con código 0 cuando todos los proyectos compilan

### Requirement: Validación automatizada de los cuatro componentes

El repositorio SHALL ejecutar los controles de calidad (lint,
verificación de tipos, pruebas unitarias y compilación) sobre los
cuatro componentes del monorepo: `apps/web`, `apps/api`,
`apps/worker` y `packages/*`.

#### Scenario: Lint sobre los cuatro componentes
- GIVEN los paquetes `apps/web`, `apps/api`, `apps/worker`,
  `packages/contracts` y `packages/config`
- WHEN se ejecuta `pnpm lint` desde la raíz
- THEN se invoca `lint` en cada uno de los cinco paquetes
- AND la salida etiqueta cada paquete por su nombre
- AND el comando finaliza con código 0 cuando todos los paquetes
  pasan lint

#### Scenario: Compilación sobre los cuatro componentes
- GIVEN los paquetes `apps/web`, `apps/api`, `apps/worker`,
  `packages/contracts` y `packages/config`
- WHEN se ejecuta `pnpm build` desde la raíz
- THEN se compilan los proyectos que tengan script `build`
  (`apps/web`, `apps/api`, `apps/worker`, `packages/contracts`)
- AND `packages/config` no falla cuando no tiene script `build`
  (`echo 'No build script needed'`)

#### Scenario: Pruebas unitarias sobre los cuatro componentes
- GIVEN las pruebas unitarias presentes en
  `apps/api/src/`, `apps/web/src/`, `apps/worker/src/` y
  `packages/config/eslint/`
- WHEN se ejecuta `pnpm test` desde la raíz
- THEN Vitest descubre y ejecuta las pruebas de los cuatro
  componentes configurados en `vitest.config.ts` raíz

#### Scenario: Verificación de tipos cubre los proyectos TypeScript
- GIVEN los proyectos TypeScript del monorepo
- WHEN se ejecuta `pnpm typecheck` desde la raíz
- THEN se ejecuta la verificación de tipos sobre cada proyecto
  TypeScript
- AND finaliza con código 0 cuando la verificación pasa

### Requirement: Pruebas de integración contra PostgreSQL real con migraciones verificadas

El repositorio SHALL ejecutar pruebas de integración que levantan
una instancia real de PostgreSQL y verifican que las migraciones
versionadas de Prisma se aplican correctamente sobre una base
aislada por ejecución.

#### Scenario: Base PostgreSQL real antes de la suite
- GIVEN el archivo `docker-compose.yml` con el servicio
  `postgres` (imagen `postgres:17-alpine`, puerto `5432:5432`)
- WHEN se ejecuta `pnpm db:start` desde la raíz
- THEN el contenedor `koty-postgres` queda en estado `running`
- AND el puerto `5432` queda accesible en `localhost`

#### Scenario: Base aislada por ejecución con migraciones aplicadas
- GIVEN una ejecución de la suite de integración
- WHEN el `globalSetup` de Vitest se ejecuta
- THEN crea una base con nombre único `plandepo_test_<runId>`
- AND aplica `prisma migrate deploy` con `DATABASE_URL` apuntando
  a esa base
- AND las cuatro migraciones versionadas
  (`20260831022807_init`,
  `20260831022808_add_idempotency_record`,
  `20260831022809_add_audit_event`,
  `20260831022810_add_outbox_event`) se aplican sin errores
- AND expone la URL como `DATABASE_URL_TEST` para los tests

#### Scenario: Base aislada destruida al finalizar
- GIVEN una ejecución de la suite de integración completada
- WHEN se ejecuta el `globalTeardown` de Vitest
- THEN la base `plandepo_test_<runId>` queda eliminada
- AND el resto del servidor PostgreSQL no se ve afectado

#### Scenario: Migraciones verificadas sin drift
- GIVEN el archivo `schema.prisma` y el historial de migraciones
  versionadas
- WHEN se ejecuta `pnpm db:verify` desde la raíz
- THEN `prisma migrate diff` finaliza con código 0
- AND no existe drift entre el esquema declarado y las
  migraciones aplicadas

#### Scenario: Aislamiento entre ejecuciones concurrentes
- GIVEN dos ejecuciones simultáneas de la suite de integración
- WHEN cada `globalSetup` crea su base aislada
- THEN las bases tienen nombres distintos
- AND no comparten datos ni colisionan entre sí

#### Scenario: Las pruebas usan el cliente Prisma real
- GIVEN un test de integración de `apps/api`
- WHEN se ejecuta
- THEN se conecta al PostgreSQL real usando el cliente Prisma
- AND no se sustituye por mocks, emuladores en memoria ni dobles
  de prueba

### Requirement: Manejo de fallos legible y fail-fast

El repositorio SHALL detener la validación ante el primer fallo y
producir una salida que identifique el paquete y la etapa
afectados.

#### Scenario: Fallo de lint detiene la validación
- GIVEN un paquete con una infracción de lint
- WHEN se ejecuta `pnpm lint` desde la raíz
- THEN el comando finaliza con código no cero
- AND la salida identifica el paquete y los archivos afectados

#### Scenario: Fallo en una etapa de `verify` detiene las siguientes
- GIVEN `pnpm verify` definido como
  `pnpm lint && pnpm typecheck && pnpm test && pnpm test:shell
  && pnpm build && pnpm crew:check`
- WHEN una etapa intermedia falla (por ejemplo, `pnpm typecheck`)
- THEN las etapas siguientes no se ejecutan
- AND el comando finaliza con el código no cero de la etapa
  fallida
- AND la salida identifica la etapa fallida

#### Scenario: Fallo de compilación detiene el pipeline
- GIVEN un paquete con un error de TypeScript
- WHEN se ejecuta `pnpm build` desde la raíz
- THEN el comando finaliza con código no cero
- AND la salida identifica el paquete con el error

#### Scenario: Fallo de pruebas de integración detiene el pipeline
- GIVEN una suite de integración con un test fallido
- WHEN se ejecuta `pnpm test:integration` desde la raíz
- THEN el comando finaliza con código no cero
- AND la salida identifica el archivo de test fallido
- AND el comando `db:stop` no se invoca si la suite falla antes
  (la base queda disponible para inspección)

### Requirement: Seguridad de artefactos versionados

El repositorio SHALL garantizar que ningún secreto ni archivo
local sensible queda versionado, mediante exclusiones explícitas
en `.gitignore` raíz y manteniendo los archivos `*.example`
versionados.

#### Scenario: Archivos `.env*` ignorados y `.env.example` versionado
- GIVEN el archivo `.gitignore` raíz
- WHEN se listan las exclusiones
- THEN `.env`, `.env.local` y `.env.*.local` están ignorados
- AND `!.env.example` se mantiene como excepción explícita para
  que el archivo plantilla siga versionado

#### Scenario: Dependencias y artefactos de build ignorados
- GIVEN el archivo `.gitignore` raíz
- WHEN se listan las exclusiones
- THEN `node_modules/`, `.pnpm-store/`, `.next/`, `dist/`,
  `build/`, `coverage/`, `out/` y `*.tsbuildinfo` están
  ignorados

#### Scenario: Entornos virtuales y caches ignorados
- GIVEN el archivo `.gitignore` raíz
- WHEN se listan las exclusiones
- THEN `.venv/`, `venv/`, `.pytest_cache/`, `.mypy_cache/` y
  `.ruff_cache/` están ignorados

#### Scenario: Estado local de la CrewAI ignorado
- GIVEN el archivo `.gitignore` raíz
- WHEN se listan las exclusiones
- THEN `crewai/.env` está ignorado
- AND `crewai/.env.example` se mantiene versionado

#### Scenario: Lockfiles versionados
- GIVEN los archivos `pnpm-lock.yaml` y `crewai/uv.lock`
- WHEN se inspecciona el `.gitignore` raíz
- THEN estos lockfiles NO están ignorados
- AND se mantienen versionados para garantizar instalaciones
  reproducibles

#### Scenario: Worktrees y artefactos locales ignorados
- GIVEN el archivo `.gitignore` raíz
- WHEN se listan las exclusiones
- THEN `.worktrees/`, `.agent/crew/`, `.agent/logs/`,
  `.agent/history/`, `.agent/tasks.json`, `ralph-sbx.sh` están
  ignorados

#### Scenario: Verificación operativa de archivos sensibles
- GIVEN un clon limpio del repositorio
- WHEN se ejecuta `git check-ignore .env .env.local
  .env.example crewai/.env crewai/.env.example pnpm-lock.yaml
  crewai/uv.lock`
- THEN `.env`, `.env.local` y `crewai/.env` son reportados como
  ignorados
- AND `.env.example`, `crewai/.env.example`, `pnpm-lock.yaml` y
  `crewai/uv.lock` son reportados como no ignorados
