# Tasks: DEV-31 — Procesar comandos sensibles con idempotencia

## 1. Modelo de datos y migración

- [x] **1.1 Añadir modelo `IdempotencyRecord` en `apps/api/prisma/schema.prisma`**
  - Archivo a modificar: `apps/api/prisma/schema.prisma`
  - Modelo con columnas: `id`, `organizationId`, `actorId`, `commandType`,
    `idempotencyKey`, `requestFingerprint`, `responseStatus`, `responseBody` (Json),
    `createdAt`, `updatedAt`
  - Restricción `@@unique([organizationId, actorId, commandType, idempotencyKey])`
  - Índice `@@index([organizationId, commandType])`
  - Tests: `pnpm --filter @koty-app/api exec prisma validate` finaliza con código 0

- [x] **1.2 Crear migración versionada**
  - Comando: `pnpm db:migrate:dev --name add_idempotency_record`
  - Archivo generado: `apps/api/prisma/migrations/<timestamp>_add_idempotency_record/migration.sql`
  - Tests: `pnpm db:verify` finaliza con código 0

## 2. Utilidad de huella canónica

- [x] **2.1 Crear `canonical-fingerprint.ts`**
  - Archivo a crear: `apps/api/src/common/idempotency/canonical-fingerprint.ts`
  - Exporta `computeCanonicalFingerprint(input: unknown): string`
  - Implementa serialización JSON con claves ordenadas recursivamente y SHA-256 en
    hexadecimal minúsculas
  - Tests: `canonical-fingerprint.spec.ts` cubre dos casos:
    - Mismo objeto con distinto orden de claves → misma huella
    - Mismo objeto con un valor distinto → huella distinta
    - Objetos anidados con mismo contenido → misma huella

- [x] **2.2 Crear `canonical-fingerprint.spec.ts`**
  - Archivo a crear: `apps/api/src/common/idempotency/canonical-fingerprint.spec.ts`
  - Cubre los escenarios anteriores
  - Tests: `pnpm --filter @koty-app/api test` finaliza con código 0 para este spec

## 3. Excepciones y errores

- [x] **3.1 Añadir `IDEMPOTENCY_KEY_REUSED` al enum `ErrorCode`**
  - Archivo a modificar: `apps/api/src/common/errors/error-code.enum.ts`
  - Tests: el enum compila y los specs existentes siguen pasando

- [x] **3.2 Mapear `409 Conflict` a `IDEMPOTENCY_KEY_REUSED` en `ApiExceptionFilter`**
  - Archivo a modificar: `apps/api/src/common/errors/api-exception.filter.ts`
  - Añadir constante `CONFLICT = 409` y la rama correspondiente
  - Tests: `api-exception.filter.spec.ts` añade el escenario `409 → IDEMPOTENCY_KEY_REUSED`

- [x] **3.3 Crear `idempotency.exceptions.ts`**
  - Archivo a crear: `apps/api/src/common/idempotency/idempotency.exceptions.ts`
  - Exporta `IdempotencyKeyReusedException` (extiende `HttpException` con status `409` y
    código `IDEMPOTENCY_KEY_REUSED`)
  - Tests: `idempotency.service.spec.ts` la invoca cuando hay conflicto de huella

## 4. Servicio de idempotencia

- [x] **4.1 Crear `idempotency.service.ts`**
  - Archivo a crear: `apps/api/src/common/idempotency/idempotency.service.ts`
  - Métodos públicos:
    - `run<T>({ scope, key, request, execute }): Promise<{ status: number; body: T }>`
    - `commit({ scope, key, fingerprint, status, body }): Promise<void>`
  - Inyecta `PrismaService`
  - Implementa la lógica descrita en el design (búsqueda, comparación de huella,
    inserción, manejo de carrera vía `@@unique`)
  - Tests: `idempotency.service.spec.ts` cubre:
    - Reintento con misma clave y misma huella → resultado cacheado
    - Reintento con misma clave y huella distinta → `IdempotencyKeyReusedException`
    - Comando exitoso → se crea el `IdempotencyRecord`
    - Comando que lanza antes del commit → no se crea el `IdempotencyRecord`

- [x] **4.2 Crear `idempotency.service.spec.ts`**
  - Archivo a crear: `apps/api/src/common/idempotency/idempotency.service.spec.ts`
  - Mockea el repositorio a nivel de servicio (no el cliente Prisma)
  - Cubre los escenarios anteriores
  - Tests: `pnpm --filter @koty-app/api test` finaliza con código 0

- [x] **4.3 Crear `idempotency.module.ts`**
  - Archivo a crear: `apps/api/src/common/idempotency/idempotency.module.ts`
  - Declara y exporta `IdempotencyService`
  - Tests: `AppModule` importa el módulo sin errores de DI

- [x] **4.4 Registrar `IdempotencyModule` en `AppModule`**
  - Archivo a modificar: `apps/api/src/app.module.ts`
  - Importar `IdempotencyModule`
  - Tests: `pnpm --filter @koty-app/api build` finaliza sin errores

## 5. Endpoint de smoke

- [x] **5.1 Crear `IdempotencyEchoController`**
  - Archivo a crear: `apps/api/src/idempotency-echo/idempotency-echo.controller.ts`
  - Ruta: `POST /api/v1/_idempotency/echo`
  - Acepta la cabecera `Idempotency-Key`
  - Usa `IdempotencyService.run` con `commandType = 'echo'`
  - Devuelve `{ echoed: <body>, correlationId }`
  - Solo se monta cuando `process.env.ENABLE_IDEMPOTENCY_ECHO === 'true'`
    (configurado por los tests de integración)
  - Tests: el spec del controlador cubre el flujo de éxito

- [x] **5.2 Crear `IdempotencyEchoModule`**
  - Archivo a crear: `apps/api/src/idempotency-echo/idempotency-echo.module.ts`
  - Importa `IdempotencyModule`
  - Declara `IdempotencyEchoController`
  - Tests: `AppModule` importa el módulo condicionalmente sin errores

## 6. Pruebas de integración

- [x] **6.1 Crear `idempotency.integration.spec.ts`**
  - Archivo a crear: `apps/api/test/integration/idempotency.integration.spec.ts`
  - Usa `DATABASE_URL_TEST` y el `IdempotencyEchoController` activado por
    `ENABLE_IDEMPOTENCY_ECHO=true` durante el run
  - Cubre:
    - Misma clave + misma huella → mismo status y mismo body, un solo
      `IdempotencyRecord`
    - Misma clave + huella distinta → `409 IDEMPOTENCY_KEY_REUSED`, sin nuevos
      registros
    - Comando que lanza antes del commit (controlado por `commandType = 'fail'`
      manejado en el endpoint de smoke) → no se crea `IdempotencyRecord`
  - Tests: `pnpm --filter @koty-app/api test:integration` finaliza con código 0

- [x] **6.2 Actualizar `global-setup.ts` para activar el endpoint de smoke**
  - Archivo a modificar: `apps/api/test/setup/global-setup.ts`
  - Antes de invocar `prisma migrate deploy`, exportar
    `process.env.ENABLE_IDEMPOTENCY_ECHO = 'true'`
  - Tests: la variable está presente durante el run de integración

## 7. Documentación y OpenAPI

- [x] **7.1 Documentar la cabecera `Idempotency-Key` en Swagger**
  - Archivo a modificar: `apps/api/src/common/openapi/swagger.config.ts`
  - Añadir un parámetro común reutilizable para `Idempotency-Key`
  - Tests: el JSON en `/api/docs-json` contiene el parámetro

- [x] **7.2 Documentar `IDEMPOTENCY_KEY_REUSED` en el schema de errores**
  - Archivo a modificar: `apps/api/src/common/openapi/schemas/error.schema.ts`
  - Añadir ejemplo `409 IDEMPOTENCY_KEY_REUSED`
  - Tests: el JSON en `/api/docs-json` contiene el ejemplo

## 8. Verificación final

- [x] **8.1 Ejecutar `openspec validate dev-31 --strict --no-interactive`**
  - Validar propuesta, specs, diseño y tareas
  - Tests: la salida finaliza con código 0 y sin errores

- [x] **8.2 Ejecutar `pnpm lint`**
  - Verificar que ESLint pasa en todos los paquetes
  - Tests: código de salida 0

- [x] **8.3 Ejecutar `pnpm test`**
  - Verificar que los tests unitarios pasan
  - Tests: código de salida 0

- [x] **8.4 Ejecutar `pnpm build`**
  - Verificar que el build de todos los paquetes finaliza correctamente
  - Tests: código de salida 0

- [x] **8.5 Ejecutar `pnpm --filter @koty-app/api test:integration`**
  - Ejecutar las pruebas de integración contra PostgreSQL real con base aislada
  - Tests: código de salida 0

- [x] **8.6 Ejecutar `pnpm db:verify`**
  - Confirmar que no hay drift entre `schema.prisma` y el historial de migraciones
  - Tests: código de salida 0
