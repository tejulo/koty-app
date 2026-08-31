# infra-prisma-migrations Specification

## Purpose
TBD - created by archiving change dev-6. Update Purpose after archive.
## Requirements
### Requirement: Configuración de Prisma con PostgreSQL local

The Prisma client SHALL be configured against the local PostgreSQL instance through a versioned `schema.prisma` that points to the `DATABASE_URL` environment variable.

#### Scenario: schema.prisma existe y declara datasource PostgreSQL
- GIVEN El proyecto `apps/api`
- WHEN Se verifica la configuración de Prisma
- THEN Existe el archivo `apps/api/prisma/schema.prisma`
- AND Declara un `datasource db` con `provider = "postgresql"`
- AND El datasource usa la variable de entorno `DATABASE_URL`

#### Scenario: Generator de cliente Prisma declarado
- GIVEN El archivo `apps/api/prisma/schema.prisma` está presente
- WHEN Se inspecciona su contenido
- THEN Existe un bloque `generator client` con `provider = "prisma-client-js"`
- AND El cliente generado queda disponible para los módulos de NestJS

#### Scenario: Dependencias de Prisma instaladas en apps/api
- GIVEN El proyecto `apps/api`
- WHEN Se inspecciona su `package.json`
- THEN `@prisma/client` aparece como dependencia de producción
- AND `prisma` aparece como dependencia de desarrollo

#### Scenario: prisma validate finaliza correctamente
- GIVEN El archivo `apps/api/prisma/schema.prisma` está presente
- WHEN Se ejecuta `pnpm --filter @koty-app/api exec prisma validate`
- THEN El comando finaliza con código 0
- AND No se reportan errores de sintaxis del esquema

### Requirement: Migraciones ejecutadas únicamente por comandos explícitos

The application bootstrap (API and worker) SHALL NOT execute Prisma migrations at any point in the startup or request lifecycle.

#### Scenario: API no aplica migraciones al iniciar
- GIVEN La API NestJS está configurada
- WHEN Se ejecuta el bootstrap (`apps/api/src/main.ts`)
- THEN Ningún comando `migrate dev`, `migrate deploy` o `migrate reset` se invoca
- AND El servidor arranca sin aplicar migraciones

#### Scenario: Worker no aplica migraciones al iniciar
- GIVEN El worker está configurado
- WHEN Se ejecuta el bootstrap (`apps/worker/src/main.ts`)
- THEN Ningún comando `migrate dev`, `migrate deploy` o `migrate reset` se invoca
- AND El proceso arranca sin aplicar migraciones

#### Scenario: El código fuente no contiene invocaciones a la CLI de Prisma
- GIVEN El árbol de código fuente de `apps/api` y `apps/worker`
- WHEN Se busca cualquier referencia a `migrate dev`, `migrate deploy`, `migrate reset` o `db push`
- THEN No existen tales invocaciones dentro de `src/`

### Requirement: Flujo automatizado de migraciones

The repository SHALL provide explicit, scripted commands to create, apply, and verify Prisma migrations in development and test environments.

#### Scenario: Scripts npm de migraciones en la raíz
- GIVEN El `package.json` raíz
- WHEN Se listan los scripts
- THEN Existen los scripts `db:migrate:dev`, `db:migrate:deploy`, `db:migrate:reset`, `db:migrate:status` y `db:verify`
- AND Cada uno delega explícitamente en la CLI de Prisma a través de `apps/api`

#### Scenario: Scripts npm de migraciones en apps/api
- GIVEN El `package.json` de `apps/api`
- WHEN Se listan los scripts
- THEN Existen los scripts `db:migrate:dev`, `db:migrate:deploy`, `db:migrate:reset`, `db:migrate:status` y `db:verify`
- AND Existe el script `test:integration` que invoca `vitest run --config vitest.config.integration.ts`

#### Scenario: Verificación de esquema sin drift
- GIVEN El `schema.prisma` y el historial de migraciones versionadas
- WHEN Se ejecuta `pnpm db:verify`
- THEN `prisma migrate diff` finaliza con código 0
- AND No existe drift entre el esquema y el historial aplicado

#### Scenario: Listado de migraciones pendientes
- GIVEN Una base de datos PostgreSQL disponible
- WHEN Se ejecuta `pnpm db:migrate:status`
- THEN Se listan las migraciones aplicadas y las pendientes
- AND El comando finaliza con código 0 cuando no hay drift

### Requirement: Reproducción del esquema desde una base vacía

The full database schema SHALL be reproducible from an empty database without any manual steps.

#### Scenario: Aplicación de migraciones sobre base vacía
- GIVEN Una base de datos PostgreSQL sin tablas
- WHEN Se ejecuta `pnpm db:migrate:deploy`
- THEN Todas las migraciones versionadas se aplican en orden
- AND El esquema resultante coincide con el definido en `schema.prisma`

#### Scenario: Migraciones versionadas en el repositorio
- GIVEN El proyecto `apps/api`
- WHEN Se verifica el árbol del repositorio
- THEN Existe el directorio `apps/api/prisma/migrations/`
- AND Contiene al menos una migración inicial versionada
- AND Está incluido en el control de versiones (no ignorado por `.gitignore`)

#### Scenario: Documentación del flujo de migraciones
- GIVEN El archivo `CONTRIBUTING.md`
- WHEN Se inspecciona la documentación
- THEN Existe una sección "Prisma migrations" que describe cómo crear, aplicar, resetear y verificar migraciones
- AND Documenta el uso de `DATABASE_URL_TEST` para las pruebas de integración

### Requirement: Pruebas de integración contra PostgreSQL real con base aislada

The integration tests SHALL run against a real PostgreSQL instance using a dedicated, per-run database that is created on `globalSetup` and destroyed on `globalTeardown`.

#### Scenario: Base aislada creada al iniciar pruebas
- GIVEN Una ejecución de pruebas de integración de `apps/api`
- WHEN Se ejecuta el `globalSetup` de Vitest
- THEN Se crea una base de datos con nombre único por ejecución
- AND Se le aplican todas las migraciones versionadas con `prisma migrate deploy`
- AND La URL queda disponible para los tests vía `DATABASE_URL_TEST`

#### Scenario: Base aislada destruida al finalizar pruebas
- GIVEN Pruebas de integración completadas
- WHEN Se ejecuta el `globalTeardown` de Vitest
- THEN La base de datos dedicada se elimina
- AND Ninguna otra base del mismo servidor PostgreSQL se ve afectada

#### Scenario: Las pruebas usan el cliente Prisma real
- GIVEN Un test de integración de `apps/api`
- WHEN Se ejecuta
- THEN Se conecta al PostgreSQL real usando el cliente Prisma
- AND No se sustituye el cliente por mocks, emuladores en memoria ni dobles de prueba

#### Scenario: Aislamiento entre ejecuciones concurrentes
- GIVEN Dos ejecuciones simultáneas de pruebas de integración
- WHEN Cada una crea su base aislada
- THEN Las bases tienen nombres distintos
- AND No comparten datos ni colisionan entre sí

#### Scenario: Los tests de integración se excluyen de la suite por defecto
- GIVEN El archivo `vitest.config.ts` raíz
- WHEN Se ejecuta `pnpm test`
- THEN Los archivos `apps/api/src/**/*.integration.spec.ts` no se ejecutan
- AND Los archivos dentro de `apps/api/test/**` no se ejecutan

### Requirement: Health check reporta el estado de la conexión Prisma

The `GET /api/v1/health` endpoint SHALL report the status of the Prisma connection to PostgreSQL without leaking credentials.

#### Scenario: Health check exitoso con Prisma conectado
- GIVEN La API en ejecución y PostgreSQL disponible
- WHEN Se solicita `GET /api/v1/health`
- THEN La respuesta incluye un campo `database` con `status: "up"`
- AND El código HTTP es 200

#### Scenario: Health check reporta fallo de Prisma
- GIVEN La API en ejecución sin conexión a PostgreSQL
- WHEN Se solicita `GET /api/v1/health`
- THEN La respuesta indica estado no saludable para `database`
- AND El código HTTP refleja el fallo

#### Scenario: Health check no expone credenciales
- GIVEN La respuesta del health check
- WHEN Se inspecciona su cuerpo
- THEN No aparece la cadena de conexión completa
- AND No aparece ninguna contraseña ni token
- AND El DTO `HealthResponseDto` no incluye la URL de la base de datos

### Requirement: Validación de DATABASE_URL al arrancar

The application SHALL validate that `DATABASE_URL` is present and parseable by Prisma before the server starts listening for traffic.

#### Scenario: API rechaza arranque sin DATABASE_URL
- GIVEN La variable de entorno `DATABASE_URL` no está definida
- WHEN Se inicia la API
- THEN El proceso falla con un mensaje de error claro
- AND El proceso sale con código de error no cero

#### Scenario: API arranca con DATABASE_URL válida
- GIVEN La variable `DATABASE_URL` está definida y es parseable por Prisma
- WHEN Se inicia la API
- THEN La API arranca sin errores
- AND El cliente Prisma puede abrir conexiones contra PostgreSQL

#### Scenario: Worker valida DATABASE_URL
- GIVEN La variable de entorno `DATABASE_URL` no está definida
- WHEN Se inicia el worker
- THEN El proceso falla con un mensaje de error claro
- AND El proceso sale con código de error no cero

