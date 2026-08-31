# Tasks: DEV-6 — Preparar migraciones reproducibles con Prisma

## 1. Dependencias y configuración base

- [x] **1.1 Agregar dependencias de Prisma a `apps/api`**
  - Archivo a modificar: `apps/api/package.json`
  - Agregar `@prisma/client` a `dependencies`
  - Agregar `prisma` a `devDependencies`
  - Tests: `pnpm install` finaliza correctamente y `pnpm --filter @koty-app/api exec prisma --version` responde

- [x] **1.2 Crear `apps/api/prisma/schema.prisma`**
  - Archivo a crear: `apps/api/prisma/schema.prisma`
  - Declarar `generator client` con `provider = "prisma-client-js"`
  - Declarar `datasource db` con `provider = "postgresql"` y `url = env("DATABASE_URL")`
  - Tests: `pnpm --filter @koty-app/api exec prisma validate` finaliza con código 0

- [x] **1.3 Crear `apps/api/prisma/migrations/migration_lock.toml`**
  - Archivo a crear: `apps/api/prisma/migrations/migration_lock.toml`
  - Contenido: `provider = "postgresql"` para fijar el proveedor
  - Tests: el archivo existe y Prisma lo reconoce

## 2. Scripts de migraciones

- [x] **2.1 Agregar scripts `db:*` y `test:integration` al `package.json` raíz**
  - Archivo a modificar: `package.json`
  - Scripts: `db:migrate:dev`, `db:migrate:deploy`, `db:migrate:reset`, `db:migrate:status`, `db:verify`
  - Cada script delega en `apps/api` mediante `pnpm --filter @koty-app/api exec prisma ...`
  - Tests: `pnpm db:migrate:status` finaliza con código 0

- [x] **2.2 Agregar scripts `db:*` y `test:integration` a `apps/api/package.json`**
  - Archivo a modificar: `apps/api/package.json`
  - Scripts: `db:migrate:dev`, `db:migrate:deploy`, `db:migrate:reset`, `db:migrate:status`, `db:verify`, `test:integration`
  - Tests: los scripts existen y son invocables

## 3. PrismaService y módulo

- [x] **3.1 Crear `apps/api/src/prisma/prisma.constants.ts`**
  - Archivo a crear
  - Exporta `PRISMA_CLIENT` como símbolo/constante para inyección
  - Tests: el archivo exporta la constante

- [x] **3.2 Crear `apps/api/src/prisma/prisma.service.ts`**
  - Archivo a crear
  - Inyectable NestJS que envuelve el cliente Prisma
  - Expone `$queryRaw`, `$executeRaw`, `$transaction` y `$connect`/`$disconnect` como delegación
  - Implementa `OnModuleInit` (invoca `$connect` cuando no es `INTEGRATION_TEST`) y `OnModuleDestroy` (invoca `$disconnect`)
  - Tests: `prisma.service.spec.ts` verifica que `onModuleInit` invoca `$connect` cuando `process.env.INTEGRATION_TEST !== 'true'` y que `onModuleDestroy` siempre invoca `$disconnect`

- [x] **3.3 Crear `apps/api/src/prisma/prisma.service.spec.ts`**
  - Archivo a crear
  - Verifica la delegación de métodos al cliente Prisma
  - Tests: el spec pasa

- [x] **3.4 Crear `apps/api/src/prisma/prisma.module.ts`**
  - Archivo a crear
  - Provee `PrismaService` usando el provider `PRISMA_CLIENT`
  - Exporta `PrismaService` para otros módulos
  - Tests: el módulo se importa correctamente en `AppModule`

- [x] **3.5 Registrar `PrismaModule` en `AppModule`**
  - Archivo a modificar: `apps/api/src/app.module.ts`
  - Importar `PrismaModule` para que el health check pueda inyectar `PrismaService`
  - Tests: `pnpm --filter @koty-app/api build` finaliza sin errores

## 4. Validación al arrancar

- [x] **4.1 Validar `DATABASE_URL` e inicialización de Prisma en `apps/api/src/main.ts`**
  - Archivo a modificar: `apps/api/src/main.ts`
  - Antes de `NestFactory.create`, verificar que `process.env.DATABASE_URL` existe y que `new PrismaClient()` no lanza
  - Si falla, imprimir mensaje claro y `process.exit(1)`
  - Tests: `grep -E "migrate (dev|deploy|reset)|db push" apps/api/src` no devuelve resultados

- [x] **4.2 Validar `DATABASE_URL` en `apps/worker/src/main.ts`**
  - Archivo a modificar: `apps/worker/src/main.ts`
  - Mantener la validación existente de `DATABASE_URL` y añadir verificación de que `new PrismaClient()` no lanza
  - No invocar migraciones
  - Tests: `grep -E "migrate (dev|deploy|reset)|db push" apps/worker/src` no devuelve resultados

## 5. Health check con Prisma

- [x] **5.1 Extender `HealthService` con verificación de Prisma**
  - Archivo a modificar: `apps/api/src/health/health.service.ts`
  - Inyectar opcionalmente `PrismaService` y ejecutar `prisma.$queryRaw\`SELECT 1\`` dentro de un `try/catch`
  - Retornar `status: 'ok' | 'degraded'` y un campo `database: { status: 'up' | 'down', message?: string }`
  - Si Prisma no está disponible, devolver `database: { status: 'unknown' }`
  - Tests: el spec existente sigue pasando con el nuevo campo

- [x] **5.2 Actualizar `HealthResponseDto` con el campo `database`**
  - Archivo a modificar: `apps/api/src/health/dto/health-response.dto.ts`
  - Añadir propiedad `database` con su `ApiProperty`
  - Tests: snapshot del DTO

- [x] **5.3 Actualizar `health.schema.ts` con el campo `database`**
  - Archivo a modificar: `apps/api/src/common/openapi/schemas/health.schema.ts`
  - Añadir `database` con `status` (up/down/unknown) y `message` opcional
  - Tests: el JSON en `/api/docs-json` contiene el esquema actualizado

- [x] **5.4 Actualizar `HealthController` y documentación OpenAPI**
  - Archivo a modificar: `apps/api/src/health/health.controller.ts`
  - Documentar el nuevo campo `database` en Swagger
  - Tests: el spec del controlador sigue pasando

## 6. Pruebas de integración

- [x] **6.1 Crear `apps/api/vitest.config.integration.ts`**
  - Archivo a crear
  - `include`: `apps/api/src/**/*.integration.spec.ts`
  - `globalSetup`: `apps/api/test/setup/global-setup.ts`
  - `globalTeardown`: `apps/api/test/setup/global-teardown.ts`
  - Tests: `pnpm --filter @koty-app/api test:integration --help` reconoce la configuración

- [x] **6.2 Crear `apps/api/test/setup/global-setup.ts`**
  - Archivo a crear
  - Genera `runId`, deriva `DATABASE_URL_TEST` con base `plandepo_test_<runId>`
  - Se conecta a la base `postgres` con rol con `CREATEDB`
  - Crea la base aislada y aplica `prisma migrate deploy`
  - Marca `process.env.INTEGRATION_TEST = 'true'` para que `PrismaService` no intente conectar antes de tiempo
  - Tests: ejecución manual contra una base de prueba crea la base

- [x] **6.3 Crear `apps/api/test/setup/global-teardown.ts`**
  - Archivo a crear
  - Desconecta el cliente Prisma y ejecuta `DROP DATABASE` sobre la base aislada
  - Tests: tras la ejecución, la base ya no existe

- [x] **6.4 Crear test de smoke de integración con Prisma**
- Archivo a crear: `apps/api/test/integration/prisma-connection.integration.spec.ts`
  - Conecta contra `DATABASE_URL_TEST`, ejecuta `SELECT 1` y verifica el resultado
  - No mockear el cliente Prisma
  - Tests: el test pasa al ejecutar `pnpm --filter @koty-app/api test:integration`

- [x] **6.5 Actualizar `vitest.config.ts` raíz para excluir los `.integration.spec.ts`**
  - Archivo a modificar: `vitest.config.ts`
  - Excluir `apps/api/src/**/*.integration.spec.ts` y `apps/api/test/**`
  - Tests: `pnpm test` no ejecuta los tests de integración

## 7. Reproducción y verificación de esquema

- [x] **7.1 Actualizar `.env.example` con `DATABASE_URL_TEST`**
  - Archivo a modificar: `.env.example`
  - Añadir `DATABASE_URL_TEST=postgresql://postgres:postgres@localhost:5432/plandepo_test`
  - Comentario indicando que `globalSetup` añade un sufijo único por ejecución
  - Tests: el archivo no contiene secretos reales y la nueva variable está documentada

- [x] **7.2 Documentar flujo de Prisma migrations en `CONTRIBUTING.md`**
  - Archivo a modificar: `CONTRIBUTING.md`
  - Sección "Prisma migrations": comandos para crear, aplicar, resetear y verificar migraciones
  - Sección "Integration tests": cómo correrlos y qué variables requieren
  - Tests: la documentación es legible y los comandos funcionan paso a paso

## 8. Verificación final

- [x] **8.1 Ejecutar `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate dev-6 --strict --no-interactive`**
  - Validar propuesta, specs, diseño y tareas
  - Tests: la salida finaliza con código 0 y sin errores

- [x] **8.2 Ejecutar `pnpm lint`**
  - Verificar que ESLint pasa en todos los paquetes
  - Tests: código de salida 0

- [x] **8.3 Ejecutar `pnpm test`**
  - Verificar que los tests unitarios pasan (los de integración quedan excluidos)
  - Tests: código de salida 0

- [x] **8.4 Ejecutar `pnpm build`**
  - Verificar que el build de todos los paquetes finaliza correctamente
  - Tests: código de salida 0

- [x] **8.5 Verificar ausencia de migraciones automáticas**
  - Ejecutar `grep -rE "migrate (dev|deploy|reset)|db push" apps/api/src apps/worker/src`
  - Tests: ninguna coincidencia
