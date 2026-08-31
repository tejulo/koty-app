# Proposal: DEV-6 — Preparar migraciones reproducibles con Prisma

## Problema

El proyecto `koty-app` ya cuenta con una instancia local de PostgreSQL levantada con Docker Compose (entregable DEV-9) y la variable `DATABASE_URL` documentada en `.env.example`. Sin embargo:

- La aplicación `apps/api` aún no carga Prisma ni expone un cliente para acceder a PostgreSQL.
- No existe un `schema.prisma` versionado ni una carpeta `migrations/` reproducible.
- No hay comandos explícitos para crear, aplicar ni verificar migraciones.
- No hay un flujo que permita reconstruir el esquema completo partiendo de una base vacía sin intervención manual.
- Las pruebas de integración de `apps/api` no existen o no están configuradas contra una base de datos PostgreSQL aislada.

Sin esta base, los incrementos posteriores del milestone "Incremento 0 - Plataforma segura" (organizaciones, membresías, auditoría, outbox, jobs) no pueden definir modelos de datos ni ejecutar pruebas contra una base real.

## Objetivo

Establecer la base de **migraciones reproducibles con Prisma sobre PostgreSQL local**, de manera que:

1. El esquema de la base de datos sea versionado, repetible y reconstruible desde una base vacía con un solo comando.
2. Las migraciones solo se ejecuten mediante **comandos explícitos**, nunca al iniciar la aplicación.
3. Exista un flujo automatizado para **crear**, **aplicar** y **verificar** migraciones en desarrollo y pruebas.
4. Las pruebas de integración operen contra una instancia **real de PostgreSQL** con una **base de datos aislada** que se crea y se destruye por ejecución.

## Alcance

1. **Prisma como ORM y herramienta de migraciones**
   - Añadir `@prisma/client` y `prisma` como dependencias de `apps/api`.
   - Crear `apps/api/prisma/schema.prisma` con datasource PostgreSQL apuntando a `DATABASE_URL` y `output` para el cliente generado.
   - Generar una migración inicial versionada en `apps/api/prisma/migrations/`.
   - Exponer un `PrismaService` (o equivalente) reutilizable para los módulos de NestJS.

2. **Flujo automatizado de migraciones explícitas**
   - Scripts npm en `apps/api/package.json`:
     - `db:migrate:dev` — crea y aplica una migración con nombre explícito en desarrollo.
     - `db:migrate:deploy` — aplica migraciones pendientes en modo `deploy` (uso en pruebas y CI).
     - `db:migrate:reset` — recrea la base y reaplica todas las migraciones desde cero.
     - `db:migrate:status` — lista migraciones pendientes y aplicadas.
     - `db:verify` — ejecuta `prisma migrate diff` para confirmar que el esquema actual coincide con el historial versionado.
   - Scripts envoltorio en el `package.json` raíz para invocar los anteriores desde el workspace.
   - **Prohibido** invocar migraciones dentro de `apps/api/src/main.ts`, `apps/worker/src/main.ts` o cualquier ciclo de vida de bootstrap de NestJS.

3. **Validación de la configuración de Prisma**
   - `DATABASE_URL` permanece como variable obligatoria para `apps/api` y `apps/worker`.
   - `apps/api/src/main.ts` debe rechazar el arranque si `DATABASE_URL` falta o no es parseable por Prisma.
   - El health check `GET /api/v1/health` reporta el estado de la conexión Prisma a PostgreSQL (sin filtrar credenciales).

4. **Reproducción del esquema desde base vacía**
   - Documentar y verificar que, partiendo de una base de datos sin tablas, ejecutar `pnpm db:migrate:deploy` deja el esquema completo aplicado, sin pasos manuales adicionales.
   - Versionar `apps/api/prisma/migrations/` junto al código fuente.

5. **Pruebas de integración contra PostgreSQL real con base aislada**
   - Configurar Vitest (ya presente en la raíz) con `globalSetup` y `globalTeardown` específicos para `apps/api`.
   - `globalSetup` debe:
     - Crear una base de datos dedicada (por ejemplo `plandepo_test_<runId>`) usando un rol con permisos de `CREATEDB`.
     - Aplicar todas las migraciones sobre esa base usando `prisma migrate deploy`.
   - `globalTeardown` debe:
     - Desconectar el cliente Prisma.
     - Eliminar la base de datos creada, sin afectar otras bases del mismo servidor.
   - La URL de la base aislada se expone vía `DATABASE_URL_TEST`, derivada de `DATABASE_URL` o mediante una variable dedicada documentada en `.env.example`.
   - Ninguna prueba de integración puede usar mocks del cliente Prisma para simular la base de datos.

## Fuera de Alcance

- Definición del modelo de dominio (organizaciones, usuarios, membresías, auditoría, outbox, jobs): corresponde a tickets posteriores del Incremento 0.
- Sembrado de datos (`prisma db seed`) para desarrollo.
- Estrategia de rollback explícito de migraciones (`migrate resolve --rolled-back`).
- Migraciones para producción o pipelines de despliegue.
- Cambios al frontend (`apps/web`).
- Autenticación, autorización o cualquier regla de negocio.

## Impacto Esperado

- El equipo podrá reconstruir el esquema de la base de datos desde una base vacía con un único comando (`pnpm db:migrate:deploy`).
- Las migraciones quedarán versionadas en el repositorio y sujetas a revisión de código.
- La aplicación nunca aplicará migraciones al arrancar, eliminando el riesgo de migraciones accidentales en entornos compartidos.
- Las pruebas de integración de `apps/api` operarán sobre una base de datos PostgreSQL real, dedicada por ejecución, garantizando reproducibilidad y aislamiento.
- Los incrementos siguientes del milestone podrán añadir modelos y migraciones reutilizando el flujo definido aquí.

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| Migración ejecutada por accidente al iniciar la app | Prohibido en código (`main.ts` y `bootstrap`) y verificado por revisión; ninguna llamada a `migrate dev`/`migrate deploy` dentro del ciclo de vida de la app. |
| Pruebas contaminando la base de desarrollo | Uso obligatorio de `DATABASE_URL_TEST` con base de datos de nombre único por ejecución, creada y destruida por `globalSetup`/`globalTeardown`. |
| Drift entre `schema.prisma` y migraciones aplicadas | Script `db:verify` ejecuta `prisma migrate diff` y debe finalizar con código 0. |
| Credenciales filtradas en health check | El health endpoint expone solo `status` y `timestamp` del estado Prisma, nunca la URL. |

## Trazabilidad con `CONTEXT.md`

- **Incremento 0 — Plataforma segura**: este ticket es el prerrequisito de infraestructura de persistencia para organizaciones, membresías, auditoría, outbox y jobs con lease.
- **R-1 (Prisma como herramienta de migraciones)**: cumplido mediante `@prisma/client` + `prisma migrate`.
- **R-2 (PostgreSQL local)**: cumplido usando la instancia ya provista por DEV-9.
- **R-3 (sin migraciones automáticas al iniciar)**: cumplido por construcción (no se llama `migrate` en `main.ts`).
- **R-4 (pruebas contra PostgreSQL real)**: cumplido con Vitest + base aislada.
- **R-5 (reproducción automática desde base vacía)**: cumplido con `db:migrate:deploy` y migración inicial versionada.
