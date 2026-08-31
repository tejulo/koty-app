# Tasks: DEV-36 — Registrar una auditoría append-only

> **Forma de ejecución de este ticket**: Este es un cambio OpenSpec
> `spec-driven`. El flujo del ticket es:
>
> 1. **Fase A — Contrato (artefactos OpenSpec):** producir `proposal.md`,
>    `specs/audit-append-only/spec.md`, `design.md` y este `tasks.md`.
>    Validar con `openspec validate dev-36 --strict --no-interactive`
>    (exit code 0). Solo se marcan como completadas `[x]` las tareas de esta
>    fase cuyo resultado es verificable dentro del propio ticket.
> 2. **Fase B — Implementación:** ejecutar el código que materializa el
>    contrato definido en la Fase A (modelo Prisma, migración con trigger,
>    `AuditService`, `AuditController`, `AuditEchoController` de smoke,
>    DTOs, OpenAPI y pruebas). Las tareas de esta fase se enumeran también
>    en este `tasks.md` para garantizar la trazabilidad 1-a-1 con los
>    criterios de aceptación del ticket DEV-36; quedan marcadas `[x]` solo
>    cuando el trabajo esté implementado, probado y verificado.
>
> Cada criterio de aceptación del ticket DEV-36 está mapeado a un requisito
> del spec y a tareas de la Fase B dentro de este mismo ticket.

## A) Trazabilidad Criterios de Aceptación → Spec → Tareas

| Criterio de aceptación (ticket DEV-36) | Requirement (spec) | Tarea(s) de implementación |
|---|---|---|
| CA1. Cada evento declara alcance de plataforma u organización, actor tipado, acción, entidad, instante y correlación. | `Estructura mínima del evento de auditoría` | 1.1, 1.2, 1.3, 5.1 |
| CA2. Los cambios antes y después usan una lista permitida y excluyen contraseñas, tokens, sesiones y contenido completo. | `Cambios antes/después usan una lista permitida y excluyen secretos` | 2.1, 2.2, 5.1, 5.2 |
| CA3. Los eventos no se pueden editar ni eliminar desde la aplicación. | `Inmutabilidad append-only en base de datos` | 1.2, 4.1, 4.2, 5.1, 9.1 |
| CA4. Un usuario autorizado puede buscar por actor, acción, entidad y rango de fechas. | `Búsqueda por actor, acción, entidad y rango de fechas con aislamiento por organización` | 5.1, 6.1, 6.2, 7.1, 7.2, 7.3, 9.1 |
| CA5. Un reintento idempotente no crea un segundo evento para la misma transición. | `Idempotencia por (scope, transitionKey)` | 3.1, 3.2, 4.1, 4.2, 5.1, 5.2, 9.1 |

## Fase A — Artefactos OpenSpec

- [x] **A.1 Crear `openspec/changes/dev-36/proposal.md`**
  - Estructura: Problema, Objetivo, Alcance (10 puntos), Fuera de Alcance,
    Impacto Esperado, Riesgos y Mitigaciones, Trazabilidad con `CONTEXT.md`
    (Incremento 0, secciones 3.1, 4.1, 4.2, 12, casos BND-IAM-*), y
    Ambigüedades Reconocidas.
  - Verificación: `openspec validate dev-36 --strict --no-interactive` → exit 0.

- [x] **A.2 Crear `openspec/changes/dev-36/specs/audit-append-only/spec.md`**
  - 8 Requirements con sus Scenarios verificables:
    1. Estructura mínima del evento.
    2. Allowlist + exclusión de secretos en `before`/`after`.
    3. Inmutabilidad append-only (trigger SQL + REVOKE).
    4. Búsqueda por actor/acción/entidad/rango con aislamiento por
       organización.
    5. Idempotencia por `(scope, transitionKey)`.
    6. Propagación de `correlationId`.
    7. Exclusión de `transitionKey` en respuestas HTTP.
    8. Código `AUDIT_TRANSITION_CONFLICT` mapeado a 409 sin debilitar
       `IDEMPOTENCY_KEY_REUSED`.
  - Verificación: `openspec validate dev-36 --strict --no-interactive` → exit 0.

- [x] **A.3 Crear `openspec/changes/dev-36/design.md`**
  - 10 Decisiones de Diseño (modelo Prisma, enums, migración con trigger,
    allowlist, exclusión de secretos, `transitionKey` canónico,
    `AuditService`, `AuditController`, `AuditEchoController` de smoke,
    pruebas).
  - Sección `Verification Strategy - Browser E2E: not_required` con razón
    breve (superficie 100% API HTTP + PostgreSQL, verificable por
    integración contra base aislada).
  - Tabla de archivos a crear/modificar.
  - Verificación: `openspec validate dev-36 --strict --no-interactive` → exit 0.

- [x] **A.4 Crear `openspec/changes/dev-36/tasks.md`**
  - Este checklist, con secciones A (contrato) y B (implementación).
  - Verificación: `openspec validate dev-36 --strict --no-interactive` → exit 0.

## Fase B — Implementación

### 1. Modelo Prisma y enums

- [x] **1.1 Añadir enums y modelo `AuditEvent` a `schema.prisma`**
  - Archivo modificado: `apps/api/prisma/schema.prisma`
  - Declara `enum AuditScope { PLATFORM, ORGANIZATION }` y
    `enum AuditActorType { USER, SYSTEM, API_KEY, WORKER }`.
  - Declara `model AuditEvent` con todos los campos requeridos.
  - Constraints: `@@unique([scope, transitionKey])`; índices secundarios
    `(scope, organizationId, occurredAt)`, `(actorType, actorId, occurredAt)`,
    `(action, occurredAt)`, `(entityType, entityId, occurredAt)`.

- [x] **1.2 Crear migración versionada `add_audit_event`**
  - Archivo creado: `apps/api/prisma/migrations/20260831022809_add_audit_event/migration.sql`
  - Contiene: `CREATE TYPE` para los enums, `CREATE TABLE` con columnas e
    índices, `CREATE FUNCTION audit_event_block_mutations()`,
    `CREATE TRIGGER audit_event_append_only BEFORE UPDATE OR DELETE ON
    "AuditEvent"` que lanza `EXCEPTION 'AuditEvent is append-only'`, y
    `REVOKE UPDATE, DELETE ON TABLE "AuditEvent" FROM PUBLIC`.

- [x] **1.3 Cliente Prisma expone `auditEvent` y enums**
  - Verificación: el cliente expone `prisma.auditEvent` con tipos correctos
    (consumido por `AuditService` mediante delegate tipado local).

### 2. Constantes, allowlist y exclusión de secretos

- [x] **2.1 Crear `apps/api/src/audit/audit.constants.ts`**
  - Exporta `AUDIT_CHANGE_FIELDS` con entradas para `organization`,
    `invitation`, `membership`, `audit-echo`.
  - Exporta `EXCLUDED_CHANGE_FIELDS` con la lista literal requerida.
  - Exporta `isExcludedChangeField(name)` (case-insensitive + sufijo
    `(password|token|secret)$`).
  - Exporta `getAuditChangeFields(entityType)` para resolver la allowlist.

- [x] **2.2 Crear `apps/api/src/audit/audit.constants.spec.ts`**
  - Cubre `isExcludedChangeField` (case-insensitive, sufijo), pertenencia
    a allowlist y `getAuditChangeFields`.

### 3. Cálculo canónico de `transitionKey`

- [x] **3.1 Crear `apps/api/src/audit/canonical-transition-key.ts`**
  - Exporta `computeCanonicalTransitionKey(input)` que devuelve
    `sha256(canonicalStringify(input))` en hexadecimal minúsculo.
  - Reutiliza `canonicalStringify` de
    `apps/api/src/common/idempotency/canonical-fingerprint.ts` (DEV-31).

- [x] **3.2 Crear `apps/api/src/audit/canonical-transition-key.spec.ts`**
  - Cubre estabilidad, longitud (64 hex), y cambios por `correlationId`,
    `entityId`, `scope`, `action` y `entityType`.

### 4. Excepciones y códigos de error

- [x] **4.1 Crear `apps/api/src/audit/audit.exceptions.ts`**
  - `AuditInvalidFieldException` extiende `BadRequestException` y mapea a
    `400` con `code: AUDIT_INVALID_FIELD` y `fieldErrors` específicos.
  - `AuditTransitionConflictException` extiende `HttpException` y mapea a
    `409` con `code: AUDIT_TRANSITION_CONFLICT`.

- [x] **4.2 Añadir `AUDIT_TRANSITION_CONFLICT` y `AUDIT_INVALID_FIELD` al enum**
  - Archivo modificado: `apps/api/src/common/errors/error-code.enum.ts`.
  - Añadidos los nuevos códigos sin eliminar los existentes definidos por
    DEV-7/DEV-31.

- [x] **4.3 Preservar el mapeo de `IDEMPOTENCY_KEY_REUSED` en `ApiExceptionFilter`**
  - Archivo verificado: `apps/api/src/common/errors/api-exception.filter.ts`.
  - Cuando la `HttpException` declara `code` explícito en su payload (caso
    de `IdempotencyKeyReusedException` y `AuditTransitionConflictException`),
    se respeta ese código. Para `409` sin `code` explícito, se conserva
    `IDEMPOTENCY_KEY_REUSED` como valor por defecto.

- [x] **4.4 Actualizar schema OpenAPI de errores**
  - Archivo modificado: `apps/api/src/common/openapi/schemas/error.schema.ts`.
  - Añadidos `AUDIT_TRANSITION_CONFLICT` y `AUDIT_INVALID_FIELD` al `enum`
    de `code`, junto con ejemplos `auditInvalidFieldExample` y
    `auditTransitionConflictExample`.

### 5. Servicio `AuditService`

- [x] **5.1 Crear `apps/api/src/audit/audit.service.ts`**
  - Inyectable NestJS con `PrismaService`.
  - `record(input: AuditEventInput)`: aplica allowlist + exclusión +
    cálculo de `transitionKey` + persistencia + manejo de `P2002` como
    idempotente (`created: false` cuando el `@@unique` colisiona con un
    registro existente de huella coincidente). Si la huella del registro
    existente difiere, lanza `AuditTransitionConflictException`.
  - `search(query: AuditSearchQuery)`: aplica filtros validados y
    aislamiento por `organizationId`.
  - **No** expone `update`, `delete`, `patch`, `truncate`.
  - Nunca devuelve `transitionKey`.

- [x] **5.2 Crear `apps/api/src/audit/audit.service.spec.ts`**
  - Cubre: registro exitoso, allowlist rechaza campo no listado, exclusión
    elimina `password`/`token` antes de persistir, idempotencia (segunda
    invocación con mismos parámetros devuelve `created: false`),
    `AuditTransitionConflictException` cuando el `@@unique` colisiona con un
    registro previo de huella distinta, `search` aplica filtros y
    aislamiento.

### 6. DTOs y validación

- [x] **6.1 Crear DTOs de respuesta sin `transitionKey`**
  - Archivo creado: `apps/api/src/audit/dto/audit-event.dto.ts`.
  - `AuditEventResponseDto` declara `id`, `scope`, `organizationId`,
    `actorType`, `actorId`, `action`, `entityType`, `entityId`, `occurredAt`,
    `correlationId`, `before`, `after`, `createdAt` (sin `transitionKey`).
  - Archivo creado: `apps/api/src/audit/dto/audit-search.dto.ts`.
  - `AuditSearchResponseDto` declara `items: AuditEventResponseDto[]`,
    `total`, `limit`, `offset`.

- [x] **6.2 Crear DTOs de query validados por Zod**
  - Schema Zod con `actorType`, `actorId`, `action`, `entityType`, `entityId`,
    `from`, `to`, `limit` (1-200, default 50), `offset` (>=0, default 0) y
    `organizationId` opcional.
  - DTO generado con `createStrictZodDto`.

### 7. Controlador y módulo

- [x] **7.1 Crear `apps/api/src/audit/audit.controller.ts`**
  - `GET /api/v1/audit-events` con `@Query()` validado por Zod.
  - `POST /api/v1/audit-events` con `@Body()` validado por Zod para filtros
    complejos.
  - Documentado en Swagger con tag `audit`. La respuesta se proyecta con
    `auditSearchResponseSchema.parse(...)` para garantizar que
    `transitionKey` nunca se filtra al cliente.

- [x] **7.2 Crear `apps/api/src/audit/audit.module.ts`**
  - Declara `AuditService` y `AuditController`. Exporta `AuditService`.

- [x] **7.3 Registrar `AuditModule` y `AuditEchoModule` en `AppModule`**
  - Archivo modificado: `apps/api/src/app.module.ts`.
  - Importa `AuditModule` siempre y `AuditEchoModule.register()` cuando
    `process.env.ENABLE_AUDIT_ECHO === 'true'`.

### 8. Endpoint de smoke y propagación

- [x] **8.1 Crear `AuditEchoController` y su módulo**
  - Archivos creados: `apps/api/src/audit-echo/audit-echo.controller.ts`,
    `apps/api/src/audit-echo/audit-echo.module.ts`.
  - `POST /api/v1/_audit/echo` con `{ organizationId?, actorId, message? }`
    registra un `AuditEvent` con `entityType = "audit-echo"`,
    `action = "audit-echo.create"`, `actorType = "USER"`.
  - Devuelve el evento persistido **sin** `transitionKey`.
  - Solo se monta cuando `ENABLE_AUDIT_ECHO === 'true'`.

- [x] **8.2 Activar flag en `global-setup.ts`**
  - Archivo modificado: `apps/api/test/setup/global-setup.ts`.
  - Añadido `process.env['ENABLE_AUDIT_ECHO'] = 'true'` junto al flag
    existente `ENABLE_IDEMPOTENCY_ECHO`.

- [x] **8.3 Documentar tag `audit` en Swagger**
  - Archivo modificado: `apps/api/src/common/openapi/swagger.config.ts`.
  - Añadido `.addTag('audit', 'Consulta y registro de auditoría append-only')`.

### 9. Pruebas de integración

- [x] **9.1 Crear `apps/api/test/integration/audit.integration.spec.ts`**
  - Usa `DATABASE_URL_TEST` y `AppModule` siguiendo el patrón de
    `idempotency.integration.spec.ts`.
  - Escenarios cubiertos:
    - Inserción inicial exitosa vía `POST /api/v1/_audit/echo` (y la
      respuesta no contiene `transitionKey`).
    - Reintento con mismo `correlationId` produce un solo `AuditEvent`
      (`created: false` en la segunda llamada).
    - `UPDATE` directo por SQL raw sobre `AuditEvent` lanza error
      "AuditEvent is append-only" y la fila queda intacta.
    - `DELETE` directo por SQL raw sobre `AuditEvent` lanza error
      "AuditEvent is append-only" y la fila no se elimina.
    - `GET /api/v1/audit-events` con filtros por `actorId`, `action`,
      `entityType` y rango `from`/`to` devuelve únicamente eventos
      coincidentes (sin `transitionKey` en los items).
    - Aislamiento: dos organizaciones distintas registran eventos y la
      búsqueda con `organizationId = A` solo devuelve eventos de `A`.

## Verificación final del cambio OpenSpec

- [x] **V.1 Validar propuesta, specs, diseño y tareas**
  - Comando: `openspec validate dev-36 --strict --no-interactive`
  - Resultado: `Change 'dev-36' is valid`, exit code 0.

- [x] **V.2 Verificar build, lint, test y migración**
  - `pnpm --filter @koty-app/api exec prisma validate` → exit 0
    (modelo `AuditEvent` y enums declarados).
  - `pnpm db:verify` → exit 0
    (migración `20260831022809_add_audit_event` consistente con `schema.prisma`).
  - `pnpm --filter @koty-app/api exec prisma migrate deploy` aplica
    `add_audit_event` sin errores y crea el trigger `audit_event_append_only`.
  - `pnpm --filter @koty-app/api test` → exit 0
    (cubre `audit.constants.spec.ts`, `canonical-transition-key.spec.ts`,
    `audit.service.spec.ts`).
  - `pnpm --filter @koty-app/api test:integration` → exit 0
    (cubre `audit.integration.spec.ts` con base aislada).