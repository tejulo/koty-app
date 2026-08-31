# DEV-6 — Diseño Técnico

## Decisiones de Diseño

### 1. Prisma como ORM y herramienta de migraciones

Se adopta **Prisma** como ORM y gestor de migraciones. La elección se justifica porque:

- El stack del monorepo ya está estandarizado en TypeScript / Node.js.
- Prisma ofrece migraciones **versionadas y reproducibles** mediante `prisma migrate`.
- El cliente generado ofrece tipado fuerte, lo que reduce errores en tiempo de ejecución.
- Permite definir el esquema en un único archivo declarativo (`schema.prisma`) y generar la migración inicial de forma automática.

**Alternativas consideradas:**

- **TypeORM**: descartado por requerir configuración manual de migraciones y sincronización adicional.
- **Drizzle ORM**: descartado por menor madurez en migraciones reproducibles al momento de esta decisión.
- **Knex.js puro**: descartado por carecer de cliente tipado y por desplazar la responsabilidad de tipado al proyecto.

### 2. Ubicación y estructura del `schema.prisma`

`apps/api/prisma/schema.prisma` siguiendo la convención estándar de Prisma. Razones:

- Concentra la persistencia dentro del paquete que la consume (`apps/api`).
- Permite a Prisma CLI inferir la raíz mediante `prisma/schema.prisma` al ejecutar `pnpm --filter @koty-app/api exec prisma ...`.
- Evita acoplar el resto de paquetes (`apps/web`, `apps/worker`) al ORM.

Estructura:

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}
```

El esquema inicial puede estar vacío (sin modelos) y contener únicamente el `generator` y el `datasource`. La primera migración versionada (`migration_lock.toml`) se crea mediante `prisma migrate dev --name init --create-only` para dejar preparado el directorio de migraciones.

### 3. Scripts de migraciones explícitos

Los scripts se definen en el `package.json` raíz para que el equipo invoque `pnpm db:*` independientemente del paquete, y delegan en `apps/api` mediante `pnpm --filter @koty-app/api exec ...`.

| Script (raíz) | Script (apps/api) | Comando | Propósito |
|---|---|---|---|
| `db:migrate:dev` | `db:migrate:dev` | `prisma migrate dev` | Crear y aplicar una migración con nombre explícito en desarrollo. |
| `db:migrate:deploy` | `db:migrate:deploy` | `prisma migrate deploy` | Aplicar migraciones pendientes en modo `deploy` (CI y pruebas). |
| `db:migrate:reset` | `db:migrate:reset` | `prisma migrate reset --force` | Recrear la base y reaplicar todas las migraciones. |
| `db:migrate:status` | `db:migrate:status` | `prisma migrate status` | Listar migraciones aplicadas y pendientes. |
| `db:verify` | `db:verify` | `prisma migrate diff` con `SHADOW_DATABASE_URL` | Confirmar que el esquema coincide con el historial. |
| — | `test:integration` | `vitest run --config vitest.config.integration.ts` | Ejecutar las pruebas de integración con base aislada. |

### 4. Prohibición de migraciones automáticas

`apps/api/src/main.ts` y `apps/worker/src/main.ts` **no llaman** a la CLI de Prisma ni ejecutan código de migración. La verificación se hace por dos vías:

1. **Revisión de código**: en cada PR se inspecciona `main.ts` y los entrypoints para descartar cualquier invocación a `migrate`.
2. **Búsqueda automatizada**: una tarea de CI ejecuta `grep` sobre `apps/{api,worker}/src` buscando `migrate dev`, `migrate deploy`, `migrate reset` y `db push`. Cualquier coincidencia falla la verificación.

### 5. Validación de `DATABASE_URL` al arrancar

`DATABASE_URL` se valida al inicio en ambos procesos:

- En `apps/api/src/main.ts`, antes de `NestFactory.create`, se verifica que `process.env.DATABASE_URL` existe y se construye un `PrismaClient` para validar que la URL es parseable. Si la validación falla, se imprime un mensaje claro y se sale con `process.exit(1)`.
- En `apps/worker/src/main.ts` se mantiene la validación existente de `DATABASE_URL` y se añade la construcción de un `PrismaClient` para verificar que la URL es parseable. No se invoca ningún comando `migrate`.

La regla ya está parcialmente cubierta por la spec `config-envvars` archivada por DEV-9; este cambio la complementa con el escenario "Prisma puede inicializar el cliente" y la prohíbe explícitamente ejecutar migraciones.

### 6. Pruebas de integración con base aislada

Se añade un `apps/api/vitest.config.integration.ts` con la siguiente configuración:

```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['test/integration/**/*.integration.spec.ts'],
    globalSetup: [
      'test/setup/global-setup.ts',
      'test/setup/global-teardown.ts',
    ],
    testTimeout: 60_000,
    hookTimeout: 120_000,
  },
});
```

**`globalSetup`**:

1. Lee `DATABASE_URL` y deriva una URL única con base `plandepo_test_<runId>`.
2. Se conecta a la base de datos `postgres` con un rol con `CREATEDB`.
3. Crea la base aislada.
4. Establece `DATABASE_URL_TEST` (variable local al proceso) y la exporta para los tests.
5. Ejecuta `prisma migrate deploy` contra `DATABASE_URL_TEST`.

**`globalTeardown`**:

1. Desconecta el cliente Prisma (`$disconnect()`).
2. Ejecuta `DROP DATABASE` sobre la base aislada.
3. Termina las conexiones pendientes.

El `vitest.config.ts` raíz excluye `apps/api/src/**/*.integration.spec.ts` y `apps/api/test/**` para que `pnpm test` no los ejecute y solo se ejecuten bajo `pnpm --filter @koty-app/api test:integration`.

Las pruebas de integración **no** mockean el cliente Prisma. Cualquier intento de hacerlo se considera violación del requisito de "Pruebas de integración contra PostgreSQL real con base aislada" y se rechaza en revisión.

### 7. Health check con Prisma

El `HealthService` se extiende para inyectar opcionalmente un `PrismaService` (o un cliente Prisma equivalente). Si la inyección existe, ejecuta `prisma.$queryRaw\`SELECT 1\`` dentro de un `try/catch` y reporta el resultado. La respuesta del endpoint `GET /api/v1/health` añade un campo `database` con `status: 'up' | 'down'` y un mensaje genérico opcional.

Importante: el cuerpo de la respuesta **no debe** incluir la URL de conexión, credenciales ni la cadena completa. Solo el estado y, opcionalmente, un mensaje genérico de error. Esto se refuerza actualizando el DTO `HealthResponseDto` para que solo declare el campo `database` con `status` y un `message` opcional, y actualizando el schema OpenAPI correspondiente.

### 8. Documentación del flujo

`CONTRIBUTING.md` se amplía con una sección "Prisma migrations" que documenta:

- Cómo crear una nueva migración (`pnpm db:migrate:dev --name ...`).
- Cómo aplicarla en CI o en entorno de pruebas (`pnpm db:migrate:deploy`).
- Cómo verificar drift (`pnpm db:verify`).
- Cómo resetear la base de desarrollo (`pnpm db:migrate:reset`).
- Cómo correr las pruebas de integración (`pnpm --filter @koty-app/api test:integration`).

`.env.example` se amplía con la variable `DATABASE_URL_TEST`, documentada como opcional y derivada de `DATABASE_URL` por el `globalSetup`.
`SHADOW_DATABASE_URL` identifica una base vacía separada que `db:verify` usa para reconstruir el historial de migraciones sin alterar la base de desarrollo.

## Verification Strategy - Browser E2E: not_required

La verificación del flujo de migraciones de Prisma se realiza enteramente mediante comandos de línea (`pnpm db:migrate:deploy`, `pnpm db:verify`, `pnpm db:migrate:status`) y mediante pruebas de integración de Vitest que conectan a una base PostgreSQL real con base aislada. No existe un comportamiento verificable mediante navegador que aporte evidencia adicional: la superficie HTTP expuesta (health check) es trivial y se cubre con pruebas de integración, y los scripts de migración no son interactivos.

## Resumen de Archivos a Crear/Modificar

| Archivo | Cambio |
|---|---|
| `apps/api/package.json` | Agregar `@prisma/client`, `prisma`, scripts `db:*` y `test:integration` |
| `apps/api/prisma/schema.prisma` | Crear con `datasource` y `generator` |
| `apps/api/prisma/migrations/migration_lock.toml` | Crear para versionar migraciones |
| `apps/api/src/prisma/prisma.service.ts` | Crear `PrismaService` (NestJS provider) |
| `apps/api/src/prisma/prisma.service.spec.ts` | Crear tests unitarios del `PrismaService` |
| `apps/api/src/prisma/prisma.module.ts` | Crear módulo que expone `PrismaService` |
| `apps/api/src/prisma/prisma.constants.ts` | Constantes (DI token) para el cliente Prisma |
| `apps/api/src/health/health.service.ts` | Extender con verificación de Prisma |
| `apps/api/src/health/dto/health-response.dto.ts` | Añadir campo `database` |
| `apps/api/src/health/health.controller.ts` | Documentar nuevo campo en OpenAPI |
| `apps/api/src/common/openapi/schemas/health.schema.ts` | Documentar nuevo campo |
| `apps/api/src/main.ts` | Validar `DATABASE_URL` y cliente Prisma inicializable |
| `apps/api/src/app.module.ts` | Registrar `PrismaModule` |
| `apps/api/vitest.config.integration.ts` | Crear config con `globalSetup`/`globalTeardown` |
| `apps/api/test/setup/global-setup.ts` | Crear base aislada y aplicar migraciones |
| `apps/api/test/setup/global-teardown.ts` | Destruir base aislada |
| `apps/api/test/integration/prisma-connection.integration.spec.ts` | Test de smoke de la conexión real |
| `apps/worker/src/main.ts` | Verificar inicialización de Prisma (sin migrar) |
| `package.json` (raíz) | Agregar scripts `db:migrate:*` y `db:verify` |
| `.env.example` | Documentar `DATABASE_URL_TEST` |
| `vitest.config.ts` (raíz) | Excluir `*.integration.spec.ts` y `apps/api/test/**` |
| `CONTRIBUTING.md` | Sección "Prisma migrations" |
| `openspec/changes/dev-6/specs/infra-prisma-migrations/spec.md` | Crear spec con `## ADDED Requirements` |
| `openspec/changes/dev-6/design.md` | Este archivo |
| `openspec/changes/dev-6/tasks.md` | Checklist de implementación |
