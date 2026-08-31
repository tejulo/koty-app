# Proposal: DEV-36 — Registrar una auditoría append-only

## Problema

El Incremento 0 de `koty-app` (ver `CONTEXT.md`, sección 21, "Incremento 0 — Plataforma
segura") establece como puerta de aceptación que la **auditoría base** forme parte de
la Plataforma segura. Hasta ahora:

- `apps/api/prisma/schema.prisma` solo declara `SchemaMigrationMarker` e
  `IdempotencyRecord`. No existe un modelo `AuditEvent` que persista quién hizo qué.
- `apps/api/src/common/idempotency/idempotency.service.ts` define `IdempotencyService`
  para deduplicar comandos sensibles por `(organizationId, actorId, commandType,
  idempotencyKey)`, pero ese mecanismo no produce un registro auditable del efecto:
  solo guarda la respuesta confirmada.
- No existe ningún servicio, controlador ni endpoint que permita a un administrador
  autorizado consultar el historial de acciones sensibles (creación de
  organizaciones, invitaciones, asignación de membresías, etc.).
- No existe ninguna restricción de base de datos que impida modificar o borrar un
  evento desde la propia aplicación. La única "inmutabilidad" disponible es la
  convención de no invocar `UPDATE`/`DELETE`, que es trivialmente eludible.
- No hay una lista permitida de campos auditables ni una exclusión obligatoria de
  datos sensibles (`password`, `token`, `session`, contenido completo), por lo que
  es posible registrar accidentalmente secretos en el cuerpo `before`/`after`.

En consecuencia, un actor no autorizado podría borrar evidencia, y un programador
descuidado podría persistir contraseñas o tokens en el log. El ticket DEV-36 exige
un sistema de auditoría append-only verificable que cubra estructura mínima,
registro de cambios antes/después, inmutabilidad, búsqueda e idempotencia,
alineado con los casos `BND-IAM-*` y la regla "ningún usuario puede consultar o
modificar datos de otra organización" del Incremento 0.

## Objetivo

Introducir en `apps/api` un sistema de **auditoría append-only** que permita a un
administrador autorizado consultar quién realizó cada acción sensible sin exponer
secretos ni permitir alterar el historial, de manera que:

1. Cada acción sensible quede registrada como un evento inmutable con alcance
   (plataforma u organización), actor tipado, acción, entidad, instante y
   correlación.
2. Los cambios antes/después se limiten a una **lista permitida** explícita por tipo
   de entidad y excluyan de forma obligatoria contraseñas, tokens, sesiones y
   contenido completo.
3. Los eventos no puedan ser editados ni eliminados desde la aplicación, ni por la
   propia API ni por un `UPDATE`/`DELETE` accidental ejecutado contra la base de
   datos de aplicación.
4. Un administrador autorizado pueda buscar eventos por actor, acción, entidad y
   rango de fechas, con aislamiento obligatorio por organización (un administrador
   de la organización `A` nunca debe poder descubrir identificadores válidos de la
   organización `B`).
5. Un reintento idempotente de la misma transición no produzca un segundo evento.

## Alcance

1. **Modelo Prisma `AuditEvent`**
   - Añadir a `apps/api/prisma/schema.prisma` un modelo `AuditEvent` con los campos:
     `id`, `scope` (`PLATFORM` | `ORGANIZATION`), `organizationId` (nullable para
     `PLATFORM`), `actorType` (`USER` | `SYSTEM` | `API_KEY` | `WORKER`), `actorId`,
     `action` (string), `entityType` (string), `entityId` (string), `occurredAt`
     (`DateTime`), `correlationId` (string), `transitionKey` (string, hash),
     `before` (`Json`), `after` (`Json`), `createdAt`.
   - Enums `AuditScope` y `AuditActorType` declarados en el mismo `schema.prisma`.
   - Constraints: `@@unique([scope, transitionKey])` para idempotencia por
     `(scope, transitionKey)`; índices secundarios para búsqueda eficiente.
   - `transitionKey` **no** se expone en respuestas HTTP; solo se persiste para
     arbitraje interno.

2. **Migración reproducible**
   - Crear `apps/api/prisma/migrations/<timestamp>_add_audit_event/migration.sql`
     siguiendo el flujo de DEV-6: `pnpm db:migrate:dev --name add_audit_event`
     aplicada con `pnpm db:migrate:deploy` y verificada con `pnpm db:verify`.
   - La migración añade:
     - Tabla `AuditEvent` con sus columnas y restricciones.
     - Función `audit_event_block_mutations()` y trigger
       `audit_event_append_only` (`BEFORE UPDATE OR DELETE`) que lanza `EXCEPTION`
       con el mensaje "AuditEvent is append-only".
     - `REVOKE UPDATE, DELETE ON TABLE "AuditEvent" FROM PUBLIC` para reforzar la
       inmutabilidad a nivel de permisos PostgreSQL.

3. **Lista permitida y exclusión de secretos**
   - Definir un mapa `AUDIT_CHANGE_FIELDS: Readonly<Record<EntityType, readonly
     string[]>>` en `apps/api/src/audit/audit.constants.ts`, que liste los únicos
     campos que pueden aparecer en `before`/`after` para cada `entityType`.
   - Definir `EXCLUDED_CHANGE_FIELDS: readonly string[]` con valores literales
     (`password`, `token`, `session`, `content`, `secret`, `apiKey`, `accessToken`,
     `refreshToken`, `cookies`, `body`, `payload`) y un predicado
     `isExcludedChangeField(name)` que detecta coincidencias por nombre
     case-insensitive y por sufijo (`*password`, `*token`, `*secret`).
   - `AuditService.record` debe:
     1. Validar que cada clave de `before`/`after` pertenece a
        `AUDIT_CHANGE_FIELDS[entityType]`. Si no, lanzar
        `AuditInvalidFieldException` mapeada a `400 VALIDATION_ERROR`.
     2. Eliminar cualquier clave que case con `EXCLUDED_CHANGE_FIELDS` **antes** de
        la validación de allowlist. Si tras el filtrado `before` o `after` queda
        vacío, se persiste el valor como `null`.

4. **Idempotencia por `(scope, transitionKey)`**
   - `transitionKey` se calcula como
     `sha256("${scope}|${action}|${entityType}|${entityId}|${correlationId}")`
     (delegando en `canonicalStringify` de DEV-31).
   - El constraint único en base de datos es el mecanismo de arbitraje entre
     instancias de la API y reintentos del cliente.
   - `AuditService.record` inserta el evento; si la inserción viola el
     `@@unique([scope, transitionKey])` y la huella coincide, se considera idempotente
     y se devuelve el evento existente con `created: false`. Si la huella difiere
     (caso patológico por `correlationId` mutado manualmente), se lanza
     `AuditTransitionConflictException` mapeada a `409 AUDIT_TRANSITION_CONFLICT`.
   - El servicio **nunca** actualiza ni borra filas de `AuditEvent`.

5. **Servicio `AuditService`**
   - `record(input: AuditEventInput): Promise<AuditEventRecord>` registra un evento
     aplicando allowlist + exclusión de secretos + idempotencia + propagación de
     `correlationId`.
   - `search(query: AuditSearchQuery): Promise<AuditSearchPage>` devuelve una página
     con `items`, `total`, `limit`, `offset`. Soporta filtros por `actorType`,
     `actorId`, `action`, `entityType`, `entityId`, `from`, `to`. Aísla por
     `organizationId` (los administradores solo ven su organización; el
     superadministrador de plataforma ve `scope = PLATFORM` y, opcionalmente,
     cualquier organización mediante flag explícito).
   - Ningún método expone `transitionKey` en la respuesta.

6. **Controlador HTTP `AuditController`**
   - `GET /api/v1/audit-events` con query params validados por Zod (`actorType`,
     `actorId`, `action`, `entityType`, `entityId`, `from`, `to`, `limit`, `offset`).
     Requiere permiso `audit:read` y, salvo para superadministrador con flag
     explícito, restringe a `organizationId` del actor autenticado.
   - `POST /api/v1/audit-events` con cuerpo validado por Zod para filtros complejos
     (alternativa opcional al GET cuando los filtros excedan la longitud razonable
     de query string).
   - Respuesta JSON sigue el contrato `ErrorResponse` para fallos y nunca incluye
     `transitionKey`.

7. **Endpoint de smoke `AuditEchoController`**
   - `POST /api/v1/_audit/echo` montado únicamente cuando
     `process.env.ENABLE_AUDIT_ECHO === 'true'`. Permite a las pruebas de
     integración validar el contrato end-to-end sin depender de un servicio de
     dominio real. Crea un `AuditEvent` con `entityType = "audit-echo"`,
     `action = "audit-echo.create"`, `actorType = "USER"` y `before`/`after`
     opcionales, y devuelve el evento persistido (sin `transitionKey`).

8. **Propagación de `correlationId`**
   - `AuditService.record` lee `correlationId` desde el header de la request
     (`x-correlation-id`) o, en su defecto, genera un UUID v4. El valor se persiste
     en `AuditEvent.correlationId` y se devuelve al llamador para trazabilidad.

9. **Permisos y aislamiento**
   - El cambio documenta el permiso lógico `audit:read` (la integración con el
     módulo de membresías queda fuera de este ticket).
   - El aislamiento se aplica a nivel de servicio (`search` filtra por
     `organizationId` del contexto autenticado).

10. **Pruebas**
    - **Unitarias**:
      - `audit-allowlist.spec.ts`: verifica `isExcludedChangeField`, filtrado de
        claves no listadas y dedup de `before`/`after` antes de persistir.
      - `audit.service.spec.ts`: cubre `record` (allowlist, exclusión,
        idempotencia, conflicto) y `search` (filtros y aislamiento).
      - `canonical-transition-key.spec.ts`: SHA-256 estable frente a orden y a
        cambios menores.
    - **Integración** (`apps/api/test/integration/audit.integration.spec.ts`):
      sigue el patrón de `idempotency.integration.spec.ts`, usa base aislada y
      valida:
      - Inserción inicial exitosa vía `POST /api/v1/_audit/echo`.
      - Reintento con mismo `correlationId` no crea un segundo `AuditEvent`.
      - `UPDATE`/`DELETE` directos por la API Prisma fallan con error SQL
        "AuditEvent is append-only".
      - Búsqueda por actor/acción/entidad/rango con aislamiento por organización.
      - La respuesta JSON de búsqueda y del endpoint echo no contiene
        `transitionKey`.

## Fuera de Alcance

- Auditoría de cambios a nivel de base de datos fuera de la propia tabla
  `AuditEvent` (CDC / WAL / Debezium).
- Retención, archivado o purga de eventos. La tabla crece monótonamente; el TTL se
  documenta como mejora futura.
- Exportación de eventos (CSV, JSONL, PDF) — queda cubierta por incrementos
  posteriores.
- Cambios al frontend (`apps/web`) más allá de la documentación del contrato en
  OpenAPI.
- Cambios al worker (`apps/worker`) más allá del consumo opcional del servicio para
  registrar eventos `WORKER`.
- Autenticación o autorización reales: el permiso `audit:read` queda declarado
  lógicamente; la integración con el módulo de membresías corresponde a
  incrementos posteriores.
- Replicación o mirroring de auditoría a un servicio externo.

## Impacto Esperado

- Toda acción sensible ejecutada por la API produce un `AuditEvent` inmutable con
  actor tipado, correlación y before/after restringido a una allowlist.
- Los administradores autorizados pueden consultar el historial por actor, acción,
  entidad y rango de fechas sin exponer secretos.
- La inmutabilidad se garantiza por dos vías independientes: trigger SQL
  `BEFORE UPDATE OR DELETE` que lanza excepción y `REVOKE UPDATE, DELETE` sobre
  la tabla.
- Reintentos idempotentes de la misma transición no duplican eventos, alineado con
  el contrato de `IdempotencyService` (DEV-31).
- La superficie HTTP queda documentada en Swagger y cubierta por pruebas de
  integración contra PostgreSQL real con base aislada (DEV-6).

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| Registrar accidentalmente contraseñas, tokens o contenido | `EXCLUDED_CHANGE_FIELDS` + verificación de allowlist en `AuditService.record` antes de persistir; tests unitarios cubren la exclusión. |
| `UPDATE`/`DELETE` accidental desde la propia aplicación | Trigger SQL `BEFORE UPDATE OR DELETE` lanza excepción + `REVOKE UPDATE, DELETE` sobre `"AuditEvent"`; `AuditService` no expone métodos de mutación distintos a `record`. |
| Fuga entre organizaciones en la búsqueda | `AuditService.search` aplica filtro obligatorio por `organizationId` del contexto autenticado, salvo para superadministrador con flag explícito; cubierto por test de integración. |
| Reintento no idempotente produce duplicados | `@@unique([scope, transitionKey])` + cálculo canónico del `transitionKey`; test de integración valida que dos inserciones con la misma transición producen un solo registro. |
| Exposición accidental de `transitionKey` en respuestas | `AuditController` y DTOs excluyen explícitamente `transitionKey`; tests unitarios verifican que el campo no aparece en JSON. |
| `correlationId` ausente o manipulado | El middleware `CorrelationIdMiddleware` (DEV-7) ya asigna un UUID v4 cuando el header falta; `AuditService.record` lo lee de headers validados y nunca del cuerpo del request. |

## Trazabilidad con `CONTEXT.md`

- **Incremento 0 — Plataforma segura**: la auditoría base es parte explícita de la
  puerta de aceptación del Incremento 0 ("auditoría base" + "Dos organizaciones
  operan sin acceso cruzado").
- **Sección 3.1 (incluido)**: "Auditoría de acciones sensibles".
- **Sección 4.1 (superadministrador)**: "Para acceder a datos de negocio debe ser
  invitado como miembro de esa organización; esa incorporación queda auditada".
- **Sección 4.2 (administrador de organización)**: "Cierra y reabre periodos con
  permiso especial y motivo obligatorio" → auditable.
- **Sección 12 (Auditoría, referenciada desde Incremento 0)**: base de `AUD` que
  cubre estructura, append-only, búsqueda y aislamiento.
- **BND-IAM-01 a BND-IAM-08 / BND-IAM-10**: aplicación directa del modelo de
  auditoría en flujos de identidad y membresías.
- **Patrón DEV-31 (idempotencia) y DEV-6 (Prisma)**: la implementación reutiliza
  el flujo de migraciones versionadas, el `globalSetup`/`globalTeardown` con base
  aislada y el patrón de servicio + controlador de smoke con flag de entorno.

## Ambigüedades Reconocidas

El ticket original deja abiertas varias cuestiones; este OpenSpec las resuelve con
posiciones explícitas y verificables:

1. **"Acción sensible"**: se cubre de forma inicial con
   `entityType ∈ {"organization", "invitation", "membership", "audit-echo"}` y
   `action` libre. La allowlist por `entityType` se documenta en
   `AUDIT_CHANGE_FIELDS` y es extensible sin migración. Comandos sensibles del
   Incremento 0 ya cubiertos por DEV-31 (`create-organization`,
   `create-invitation`, `accept-invitation`) producirán eventos de auditoría en
   tickets posteriores.
2. **"Lista permitida"**: `AUDIT_CHANGE_FIELDS[entityType]` define los únicos
   campos que pueden aparecer en `before`/`after`. Cualquier clave fuera de la
   allowlist es rechazada con `400 VALIDATION_ERROR`.
3. **"Administrador autorizado"**: la búsqueda exige el permiso lógico
   `audit:read` y filtra por `organizationId`. La integración con el módulo de
   membresías queda fuera de este cambio.
4. **"Correlación"**: `x-correlation-id` (header HTTP estándar) generado o
   propagado por `CorrelationIdMiddleware` (DEV-7); se persiste en
   `AuditEvent.correlationId`.
5. **"Almacenamiento"**: PostgreSQL mediante Prisma, tabla `AuditEvent`, con
   trigger `BEFORE UPDATE OR DELETE` y `REVOKE UPDATE, DELETE` sobre la tabla.
6. **"Rendimiento"**: queda fuera de alcance; los índices secundarios definidos
   cubren los filtros del requisito de búsqueda (`actorId`, `action`,
   `entityType+entityId`, `occurredAt`, `organizationId+occurredAt`).
7. **"Detección de reintento idempotente"**: por
   `transitionKey = sha256(scope|action|entityType|entityId|correlationId)`; el
   `@@unique([scope, transitionKey])` es el árbitro en presencia de concurrencia.
