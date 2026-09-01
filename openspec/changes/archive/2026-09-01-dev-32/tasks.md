# Tasks: DEV-32 — Guardar eventos en un outbox transaccional

> **Forma de ejecución de este ticket**: Este es un cambio OpenSpec
> `spec-driven`. El flujo del ticket es:
>
> 1. **Fase A — Contrato (artefactos OpenSpec):** producir `proposal.md`,
>    `specs/transactional-outbox/spec.md`, `design.md` y este `tasks.md`.
>    Validar con `openspec validate dev-32 --strict --no-interactive`
>    (exit code 0). Solo se marcan como completadas `[x]` las tareas de
>    esta fase cuyo resultado es verificable dentro del propio ticket.
> 2. **Fase B — Implementación:** ejecutar el código que materializa el
>    contrato definido en la Fase A (modelo Prisma, migración con
>    trigger, `OutboxService`, `OutboxEchoController` de smoke, DTOs,
>    OpenAPI y pruebas). Las tareas de esta fase se enumeran también en
>    este `tasks.md` para garantizar la trazabilidad 1-a-1 con los
>    criterios de aceptación del ticket DEV-32; quedan marcadas `[x]`
>    solo cuando el trabajo esté implementado, probado y verificado.
>
> Cada criterio de aceptación del ticket DEV-32 está mapeado a un
> requisito del spec y a tareas de la Fase B dentro de este mismo
> ticket.

## A) Trazabilidad Criterios de Aceptación → Spec → Tareas

| Criterio de aceptación (ticket DEV-32) | Requirement (spec) | Tarea(s) de implementación |
|---|---|---|
| CA-1. El evento incluye organización, agregado, versión, correlación, causación y clave semántica. | `Estructura mínima del evento del outbox`, `Causación y correlación propagadas` | 1.1, 1.2, 1.3, 5.1, 8.1 |
| CA-2. Dominio, idempotencia, auditoría y outbox se confirman o revierten en una sola transacción. | `Atomicidad con la transacción de negocio` | 1.2, 4.1, 4.2, 5.1, 7.1, 7.2, 9.1 |
| CA-3. Los eventos son inmutables y no se eliminan al procesarlos. | `Inmutabilidad append-only del outbox` | 1.2, 4.1, 6.1, 9.1 |
| CA-4. Ninguna llamada externa ocurre dentro de la transacción de negocio. | `Cero llamadas externas dentro de la transacción de negocio` | 4.1, 4.3, 5.1, 5.2, 9.1 |
| CA-5. Repetir el comando confirmado no crea otro evento semánticamente equivalente. | `Idempotencia por (organizationId, aggregateType, aggregateId, semanticKey)`, `Huella canónica del payload`, `Código de error OUTBOX_SEMANTIC_CONFLICT` | 1.1, 3.1, 3.2, 4.1, 5.1, 6.1, 6.2, 9.1 |

## Fase A — Artefactos OpenSpec

- [x] **A.1 Crear `openspec/changes/dev-32/proposal.md`**
  - Estructura: Problema, Objetivo, Alcance (8 puntos), Fuera de
    Alcance, Impacto Esperado, Riesgos y Mitigaciones, Trazabilidad con
    `CONTEXT.md` (Incremento 0, sección 19, casos BND-IAM-*),
    Trazabilidad con los Criterios de Aceptación y Ambigüedades
    Reconocidas.
  - Verificación: `openspec validate dev-32 --strict --no-interactive`
    → exit 0.

- [x] **A.2 Crear `openspec/changes/dev-32/specs/transactional-outbox/spec.md`**
  - 9 Requirements con sus Scenarios verificables:
    1. Estructura mínima del evento.
    2. Inmutabilidad append-only (trigger SQL + REVOKE + superficie
       reducida del servicio).
    3. Atomicidad con la transacción de negocio.
    4. Cero llamadas externas dentro de la transacción.
    5. Idempotencia por `(organizationId, aggregateType, aggregateId,
       semanticKey)`.
    6. Causación y correlación propagadas.
    7. Rechazo de payload que excede el límite.
    8. Código de error `OUTBOX_SEMANTIC_CONFLICT` (y `OUTBOX_PAYLOAD_TOO_LARGE`).
    9. Huella canónica del payload.
  - Verificación: `openspec validate dev-32 --strict --no-interactive`
    → exit 0.

- [x] **A.3 Crear `openspec/changes/dev-32/design.md`**
  - 9 Decisiones de Diseño (modelo Prisma, migración con trigger,
    huella canónica, `OutboxService` sin transacciones propias,
    superficie reducida del servicio, excepciones, endpoint de smoke,
    DTOs, pruebas).
  - Sección `Verification Strategy - Browser E2E: not_required` con
    razón breve (superficie 100% API HTTP + PostgreSQL, verificable
    por integración contra base aislada).
  - Tabla de archivos a crear/modificar.
  - Verificación: `openspec validate dev-32 --strict --no-interactive`
    → exit 0.

- [x] **A.4 Crear `openspec/changes/dev-32/tasks.md`**
  - Este checklist, con secciones A (contrato) y B (implementación).
  - Verificación: `openspec validate dev-32 --strict --no-interactive`
    → exit 0.

## Fase B — Implementación

### 1. Modelo Prisma y migración

- [x] **1.1 Añadir modelo `OutboxEvent` a `schema.prisma`**
  - Archivo modificado: `apps/api/prisma/schema.prisma`
  - Declara `model OutboxEvent` con todos los campos requeridos
    (`id`, `organizationId`, `aggregateType`, `aggregateId`, `version`,
    `semanticKey`, `eventType`, `correlationId`, `causationId?`,
    `payload` (Json), `createdAt`).
  - Constraints: `@@unique([organizationId, aggregateType, aggregateId,
    semanticKey])`; índices secundarios `(organizationId, createdAt)` y
    `(aggregateType, aggregateId, version)`.
  - Verificación: `pnpm --filter @koty-app/api exec prisma validate`
    → exit 0.

- [x] **1.2 Crear migración versionada `add_outbox_event`**
  - Archivo creado:
    `apps/api/prisma/migrations/20260831022810_add_outbox_event/migration.sql`
  - Contiene: `CREATE TABLE "OutboxEvent"` con columnas, PK, índices
    y `@@unique`; función `outbox_event_block_mutations()`; trigger
    `outbox_event_append_only` `BEFORE UPDATE OR DELETE` que lanza
    `EXCEPTION 'OutboxEvent is append-only'`; y
    `REVOKE UPDATE, DELETE ON TABLE "OutboxEvent" FROM PUBLIC`.
  - Verificación: `pnpm db:verify` → exit 0.

- [x] **1.3 Cliente Prisma expone `outboxEvent`**
  - Verificación: el cliente expone `prisma.outboxEvent` con tipos
    correctos (consumido por `OutboxService` mediante delegate tipado
    local).

### 2. Constantes

- [x] **2.1 Crear `apps/api/src/outbox/outbox.constants.ts`**
  - Exporta `OUTBOX_MAX_PAYLOAD_BYTES` (límite por defecto: 65536).
  - Exporta `MAX_SEMANTIC_KEY_LENGTH` (200 caracteres).
  - Exporta `MIN_SEMANTIC_KEY_LENGTH` (1 carácter).
  - Exporta `MIN_ORGANIZATION_ID_LENGTH` y `MAX_PAYLOAD_DEPTH`.

### 3. Huella canónica

- [x] **3.1 Crear `apps/api/src/outbox/outbox-canonical-fingerprint.ts`**
  - Exporta `computeOutboxCanonicalFingerprint(input)` que devuelve
    `sha256(canonicalStringify({...}))` en hexadecimal minúsculo.
  - Reutiliza `canonicalStringify` de
    `apps/api/src/common/idempotency/canonical-fingerprint.ts` (DEV-31).
  - La huella cubre `organizationId`, `aggregateType`, `aggregateId`,
    `version`, `semanticKey`, `eventType`, `payload` (excluye
    `correlationId` y `causationId` por diseño).

- [x] **3.2 Crear `apps/api/src/outbox/outbox-canonical-fingerprint.spec.ts`**
  - Cubre estabilidad, longitud (64 hex), insensibilidad al orden de
    claves, sensibilidad a cambios en cada metadato.

### 4. Excepciones y códigos de error

- [x] **4.1 Crear `apps/api/src/outbox/outbox.exceptions.ts`**
  - `OutboxSemanticConflictException` extiende `HttpException` y
    mapea a `409` con `code: OUTBOX_SEMANTIC_CONFLICT`.
  - `OutboxPayloadTooLargeException` extiende `BadRequestException` y
    mapea a `400` con `code: OUTBOX_PAYLOAD_TOO_LARGE`.

- [x] **4.2 Añadir `OUTBOX_SEMANTIC_CONFLICT` y `OUTBOX_PAYLOAD_TOO_LARGE` al enum**
  - Archivo modificado: `apps/api/src/common/errors/error-code.enum.ts`.
  - Añadidos los nuevos códigos sin eliminar los existentes definidos
    por DEV-7/DEV-31/DEV-36.

- [x] **4.3 Preservar el mapeo existente en `ApiExceptionFilter`**
  - Archivo verificado:
    `apps/api/src/common/errors/api-exception.filter.ts`.
  - Cuando la `HttpException` declara `code` explícito en su payload
    (caso de `OutboxSemanticConflictException`,
    `OutboxPayloadTooLargeException` y todas las excepciones
    previas), se respeta ese código. Para `409`/`400` sin `code`
    explícito, se conserva el mapeo por defecto
    (`IDEMPOTENCY_KEY_REUSED` / `VALIDATION_ERROR`).
  - Verificación: `api-exception.filter.spec.ts` sigue pasando (sin
    debilitarse).

- [x] **4.4 Actualizar schema OpenAPI de errores**
  - Archivo modificado:
    `apps/api/src/common/openapi/schemas/error.schema.ts`.
  - Añadidos `OUTBOX_SEMANTIC_CONFLICT` y `OUTBOX_PAYLOAD_TOO_LARGE`
    al `enum` de `code`, junto con ejemplos
    `outboxSemanticConflictExample` y
    `outboxPayloadTooLargeExample`.

### 5. Servicio `OutboxService`

- [x] **5.1 Crear `apps/api/src/outbox/outbox.service.ts`**
  - Inyectable NestJS con `PrismaService`.
  - `record(input: OutboxEventInput)`: valida `payload`, calcula la
    huella canónica, llama a `prisma.outboxEvent.create` y maneja
    `P2002` como idempotente (`created: false` cuando el `@@unique`
    colisiona con un registro existente de huella coincidente). Si la
    huella difiere, lanza `OutboxSemanticConflictException`. Si el
    `payload` excede `OUTBOX_MAX_PAYLOAD_BYTES`, lanza
    `OutboxPayloadTooLargeException` **antes** de tocar la base de
    datos.
  - `OutboxService` **no** expone `update`, `delete`, `patch` ni
    `truncate`. La verificación de la superficie reducida queda
    incluida en el spec unitario.
  - `OutboxService` **no** importa ni expone clientes HTTP, SDKs de
    colas ni SDKs de brokers. La superficie observable es
    exclusivamente Prisma + `OutboxService.record`.

- [x] **5.2 Crear `apps/api/src/outbox/outbox.service.spec.ts`**
  - Cubre: registro exitoso, idempotencia (segunda invocación con
    misma `semanticKey` y mismo `payload` devuelve `created: false`),
    conflicto (`OutboxSemanticConflictException` cuando el `@@unique`
    colisiona con un registro previo de huella distinta),
    `OutboxPayloadTooLargeException` cuando el `payload` serializado
    excede el límite, `correlationId` propagado, `causationId`
    opcional persistido, y verificación de que la superficie del
    servicio no expone `update`/`delete`/`patch`/`truncate`.

### 6. DTOs y validación

- [x] **6.1 Crear DTOs de respuesta y de entrada del endpoint de smoke**
  - Archivos creados:
    `apps/api/src/outbox/dto/outbox-event.dto.ts`,
    `apps/api/src/outbox/dto/outbox-echo.dto.ts`.
  - `OutboxEventResponseDto` declara los campos públicos del evento
    persistido (sin exponer detalles internos sensibles).
  - `OutboxEchoRequestDto` valida con Zod el cuerpo del endpoint de
    smoke, incluyendo `forceRollback` para validar la atomicidad.

### 7. Controlador y módulo

- [x] **7.1 Crear `apps/api/src/outbox-echo/outbox-echo.controller.ts`**
  - `POST /api/v1/_outbox/echo` con body validado por Zod.
  - Ejecuta `OutboxService.record` dentro de un
    `prisma.$transaction`. Si `forceRollback = true`, lanza un `Error`
    **después** del `record` para verificar el rollback.
  - Devuelve el evento persistido (`created: true|false`).
  - Solo se monta cuando `ENABLE_OUTBOX_ECHO === 'true'`.

- [x] **7.2 Crear `apps/api/src/outbox-echo/outbox-echo.module.ts`**
  - Declara `OutboxEchoController` y reexporta `OutboxModule`.

- [x] **7.3 Registrar `OutboxModule` y `OutboxEchoModule` en `AppModule`**
  - Archivo modificado: `apps/api/src/app.module.ts`.
  - Importa `OutboxModule` siempre y `OutboxEchoModule.register()`
    cuando `process.env.ENABLE_OUTBOX_ECHO === 'true'`.

- [x] **7.4 Documentar tag `outbox` en Swagger**
  - Archivo modificado:
    `apps/api/src/common/openapi/swagger.config.ts`.
  - Añadido `.addTag('outbox', 'Outbox transaccional append-only')`.

### 8. Propagación de correlación

- [x] **8.1 OutboxEchoController propaga `correlationId`**
  - Lee `x-correlation-id` del header (gestionado por
    `CorrelationIdMiddleware` de DEV-7) o lo deja en manos del caller
    para que `OutboxService` genere un UUID v4.
  - La respuesta del endpoint expone `correlationId` para
    trazabilidad.

### 9. Pruebas de integración

- [x] **9.1 Crear `apps/api/test/integration/outbox.integration.spec.ts`**
  - Usa `DATABASE_URL_TEST` y `AppModule` siguiendo el patrón de
    `idempotency.integration.spec.ts` y `audit.integration.spec.ts`.
  - Escenarios cubiertos:
    - Inserción inicial exitosa vía `POST /api/v1/_outbox/echo` con
      `payload` poblado.
    - Reintento con misma `semanticKey` y mismo `payload` no crea un
      segundo `OutboxEvent` (`created: false` en la segunda
      llamada).
    - Misma `semanticKey` con `payload` distinto devuelve
      `409 OUTBOX_SEMANTIC_CONFLICT`.
    - `UPDATE` directo por SQL raw sobre `OutboxEvent` lanza error
      "OutboxEvent is append-only" y la fila queda intacta.
    - `DELETE` directo por SQL raw sobre `OutboxEvent` lanza error
      "OutboxEvent is append-only" y la fila no se elimina.
    - Rollback atómico: `POST /api/v1/_outbox/echo?forceRollback=true`
      no persiste ningún `OutboxEvent` cuando el handler falla tras
      la llamada a `OutboxService.record`.
    - `correlationId` se propaga desde el header `x-correlation-id`.

### 10. Activación del flag en el global setup

- [x] **10.1 Activar `ENABLE_OUTBOX_ECHO` en `global-setup.ts`**
  - Archivo modificado: `apps/api/test/setup/global-setup.ts`.
  - Añadido `process.env['ENABLE_OUTBOX_ECHO'] = 'true'` junto al
    flag existente `ENABLE_AUDIT_ECHO` y `ENABLE_IDEMPOTENCY_ECHO`.
  - Verificación: la variable está presente durante el run de
    integración.

## Verificación final del cambio OpenSpec

- [x] **V.1 Validar propuesta, specs, diseño y tareas**
  - Comando: `openspec validate dev-32 --strict --no-interactive`
  - Resultado: `Change 'dev-32' is valid`, exit code 0.

- [x] **V.2 Verificar build, lint, test y migración**
  - `pnpm --filter @koty-app/api exec prisma validate` → exit 0
    (modelo `OutboxEvent` declarado).
  - `pnpm db:verify` → exit 0
    (migración `20260831022810_add_outbox_event` consistente con
    `schema.prisma`).
  - `pnpm --filter @koty-app/api exec prisma migrate deploy` aplica
    `add_outbox_event` sin errores y crea el trigger
    `outbox_event_append_only`.
  - `pnpm --filter @koty-app/api test` → exit 0
    (cubre `outbox.constants.spec.ts` (si aplica),
    `outbox-canonical-fingerprint.spec.ts`, `outbox.service.spec.ts`).
  - `pnpm --filter @koty-app/api test:integration` → exit 0
    (cubre `outbox.integration.spec.ts` con base aislada).