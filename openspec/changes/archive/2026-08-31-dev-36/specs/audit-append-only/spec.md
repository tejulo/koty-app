# audit-append-only Specification

## Purpose
Define el contrato de un sistema de auditoría append-only en `koty-app`:
estructura mínima de un `AuditEvent`, lista permitida de campos auditables,
exclusión obligatoria de secretos, inmutabilidad garantizada por la base de
datos, búsqueda con aislamiento por organización e idempotencia por transición.
El cambio DEV-36 introduce la base de `AUD` referenciada en el Incremento 0 de
`CONTEXT.md`.

## ADDED Requirements

### Requirement: Estructura mínima del evento de auditoría

El sistema SHALL persistir un `AuditEvent` con alcance, actor tipado, acción,
entidad, instante, correlación y, opcionalmente, los cambios antes/después
registrados como JSON.

#### Scenario: Evento declara los campos obligatorios
- GIVEN una acción sensible ejecutada en `apps/api`
- WHEN `AuditService.record` persiste el evento
- THEN el registro contiene `scope` (`PLATFORM` | `ORGANIZATION`)
- AND contiene `actorType` (`USER` | `SYSTEM` | `API_KEY` | `WORKER`)
- AND contiene `actorId` no vacío
- AND contiene `action` no vacío
- AND contiene `entityType` no vacío
- AND contiene `entityId` no vacío
- AND contiene `occurredAt` con marca de tiempo
- AND contiene `correlationId` no vacío
- AND contiene `transitionKey` igual a
  `sha256("${scope}|${action}|${entityType}|${entityId}|${correlationId}")`

#### Scenario: Actor tipado se limita a los valores permitidos
- GIVEN un `AuditEvent` registrado
- WHEN se inspecciona `actorType`
- THEN el valor es uno de `USER`, `SYSTEM`, `API_KEY`, `WORKER`
- AND cualquier otro valor es rechazado por Prisma antes de la inserción

#### Scenario: Alcance distingue plataforma de organización
- GIVEN un `AuditEvent` con `scope = "PLATFORM"`
- WHEN se persiste
- THEN `organizationId` es `NULL`
- AND el evento es consultable únicamente por un actor con permiso de plataforma

#### Scenario: Alcance de organización exige organizationId no vacío
- GIVEN un `AuditEvent` con `scope = "ORGANIZATION"`
- WHEN se persiste
- THEN `organizationId` no es `NULL`
- AND el evento solo es consultable por actores de esa organización

### Requirement: Cambios antes/después usan una lista permitida y excluyen secretos

El sistema SHALL persistir los campos `before` y `after` solo para los campos
explícitamente listados en `AUDIT_CHANGE_FIELDS[entityType]` y SHALL omitir
cualquier campo cuyo nombre coincida con `EXCLUDED_CHANGE_FIELDS`
(case-insensitive y por sufijo `*password`, `*token`, `*secret`).

#### Scenario: Campo no listado en la allowlist se rechaza
- GIVEN un `entityType` con `AUDIT_CHANGE_FIELDS = ["status", "name"]`
- WHEN `AuditService.record` recibe `before = { "password": "x", "status": "active" }`
- THEN el servicio lanza `AuditInvalidFieldException`
- AND la API responde con `400 VALIDATION_ERROR`
- AND el cuerpo incluye `fieldErrors` con `field = "before.password"`

#### Scenario: Campos sensibles se omiten silenciosamente
- GIVEN un evento con `before = { "name": "Acme", "password": "x", "accessToken": "y" }`
- WHEN `AuditService.record` aplica la allowlist
- THEN el JSON persistido para `before` solo contiene `name`
- AND `password` y `accessToken` no aparecen en ninguna columna ni respuesta

#### Scenario: Contenido completo nunca se registra
- GIVEN un `entityType` que tiene `content` como atributo
- WHEN `AuditService.record` recibe `after = { "content": "..." }`
- THEN el campo `content` es omitido por `EXCLUDED_CHANGE_FIELDS`
- AND el JSON persistido para `after` no contiene `content`

#### Scenario: Evento de creación persiste before nulo y after allowlisted
- GIVEN un evento de creación (`action = "create"`)
- WHEN `AuditService.record` recibe `before = null` y `after = { "name": "Acme" }`
- THEN el evento se persiste con `before = NULL` y `after = { "name": "Acme" }`
- AND `before` puede ser `null` para representar ausencia de estado previo

#### Scenario: When before/after would be empty after sanitization, null is persisted
- GIVEN un `AuditEvent` cuyo `before` y `after` contienen únicamente campos excluidos
- WHEN `AuditService.record` aplica la allowlist y la exclusión
- THEN el evento se persiste con `before = NULL` y `after = NULL`
- AND el evento queda registrado sin exponer secretos

### Requirement: Inmutabilidad append-only en base de datos

El sistema SHALL garantizar que un `AuditEvent` no puede ser actualizado ni
eliminado por la API ni por SQL directo ejecutado contra la tabla.

#### Scenario: UPDATE sobre AuditEvent falla por trigger SQL
- GIVEN un `AuditEvent` existente
- WHEN se ejecuta `UPDATE "AuditEvent" SET "action" = '...' WHERE "id" = ...`
- THEN PostgreSQL lanza una excepción con el mensaje "AuditEvent is append-only"
- AND ninguna fila es modificada

#### Scenario: DELETE sobre AuditEvent falla por trigger SQL
- GIVEN un `AuditEvent` existente
- WHEN se ejecuta `DELETE FROM "AuditEvent" WHERE "id" = ...`
- THEN PostgreSQL lanza una excepción con el mensaje "AuditEvent is append-only"
- AND ninguna fila es eliminada

#### Scenario: El rol PUBLIC no tiene permisos de UPDATE/DELETE
- GIVEN la tabla `AuditEvent`
- WHEN se consulta `information_schema.role_table_grants` para `grantee = 'PUBLIC'`
- THEN no existen grants `UPDATE` ni `DELETE` sobre la tabla

#### Scenario: AuditService no expone métodos de mutación distintos a record
- GIVEN `AuditService`
- WHEN se inspecciona su API pública
- THEN solo expone `record(input)` y `search(query)`
- AND no expone métodos `update`, `delete`, `patch`, `truncate` ni equivalentes

### Requirement: Búsqueda por actor, acción, entidad y rango de fechas con aislamiento por organización

El sistema SHALL permitir a un actor autorizado buscar `AuditEvent` filtrando
por `actorType`, `actorId`, `action`, `entityType`, `entityId`, `from` y `to`,
y SHALL aplicar aislamiento obligatorio por `organizationId`.

#### Scenario: Filtro por actor
- GIVEN eventos con `actorId = "u-1"` y `actorId = "u-2"`
- WHEN un administrador autorizado consulta
  `GET /api/v1/audit-events?actorId=u-1`
- THEN la respuesta contiene únicamente eventos con `actorId = "u-1"`

#### Scenario: Filtro por acción
- GIVEN eventos con `action = "create"` y `action = "delete"`
- WHEN se consulta `GET /api/v1/audit-events?action=create`
- THEN la respuesta contiene únicamente eventos con `action = "create"`

#### Scenario: Filtro por entidad
- GIVEN eventos con `entityType = "organization"` y
  `entityType = "invitation"`
- WHEN se consulta `GET /api/v1/audit-events?entityType=invitation`
- THEN la respuesta contiene únicamente eventos con
  `entityType = "invitation"`

#### Scenario: Filtro por rango de fechas
- GIVEN eventos con `occurredAt` entre el 1 y el 31 de enero de 2026
- WHEN se consulta
  `GET /api/v1/audit-events?from=2026-01-01&to=2026-01-31`
- THEN la respuesta contiene únicamente eventos cuyo `occurredAt` está dentro
  del rango (inclusive)

#### Scenario: Aislamiento por organización
- GIVEN un administrador autenticado en la organización `O1`
- WHEN consulta `GET /api/v1/audit-events`
- THEN la respuesta contiene únicamente eventos con
  `organizationId = "O1"`
- AND no contiene eventos de la organización `O2`
- AND no contiene identificadores válidos de `O2`

#### Scenario: Paginación con limit y offset
- GIVEN más de `limit` eventos coincidentes
- WHEN se consulta `GET /api/v1/audit-events?limit=50&offset=100`
- THEN la respuesta contiene como máximo `50` eventos
- AND la respuesta incluye `total`, `limit`, `offset`

#### Scenario: Búsqueda requiere permiso audit:read
- GIVEN un actor autenticado sin el permiso `audit:read`
- WHEN consulta `GET /api/v1/audit-events`
- THEN la API responde con `401 UNAUTHORIZED`
- AND no se ejecuta la consulta

### Requirement: Idempotencia por (scope, transitionKey)

El sistema SHALL tratar dos `AuditEvent` con el mismo `(scope, transitionKey)`
como una única transición y SHALL persistir un único registro.

#### Scenario: Misma transición no crea duplicados
- GIVEN un evento registrado con `transitionKey = T1`
- WHEN `AuditService.record` recibe una segunda invocación con los mismos
  `scope`, `action`, `entityType`, `entityId` y `correlationId`
- THEN `transitionKey` calculado es `T1`
- AND la base de datos rechaza la inserción por la restricción `@@unique`
- AND el servicio resuelve el conflicto leyendo el registro existente
- AND devuelve el evento original marcado como idempotente (`created: false`)

#### Scenario: Diferente correlación produce diferente transitionKey
- GIVEN una transición con `correlationId = "c-1"` que registra el evento `E1`
- WHEN `AuditService.record` recibe la misma transición con
  `correlationId = "c-2"`
- THEN `transitionKey` calculado es distinto
- AND se crea un nuevo `AuditEvent` con `id` distinto

#### Scenario: Diferente entityId produce diferente transitionKey
- GIVEN una transición sobre `entityId = "x"` que registra `E1`
- WHEN `AuditService.record` recibe la misma transición sobre `entityId = "y"`
- THEN `transitionKey` calculado es distinto
- AND se crea un nuevo `AuditEvent`

### Requirement: Propagación de correlationId en eventos de auditoría

El sistema SHALL persistir el `correlationId` recibido en `x-correlation-id` (o
uno generado por el middleware si falta) en cada `AuditEvent` registrado por la
API.

#### Scenario: correlationId presente en headers se persiste tal cual
- GIVEN una solicitud con
  `x-correlation-id: 11111111-1111-4111-8111-111111111111`
- WHEN `AuditService.record` registra el evento
- THEN `AuditEvent.correlationId` es
  `11111111-1111-4111-8111-111111111111`

#### Scenario: correlationId ausente es generado por el middleware
- GIVEN una solicitud sin `x-correlation-id`
- WHEN `AuditService.record` registra el evento
- THEN `AuditEvent.correlationId` es un UUID v4 válido
- AND ese mismo UUID aparece en la cabecera de respuesta `x-correlation-id`

#### Scenario: transitionKey nunca se devuelve en respuestas HTTP
- GIVEN una respuesta de `GET /api/v1/audit-events` o de
  `POST /api/v1/_audit/echo`
- WHEN se inspecciona el JSON del cuerpo
- THEN el campo `transitionKey` no aparece en ningún objeto
- AND los DTOs de respuesta no declaran esa propiedad

### Requirement: Código de error para conflictos de transición de auditoría

El sistema SHALL definir el código `AUDIT_TRANSITION_CONFLICT` mapeado a HTTP
`409 Conflict`, siguiendo el contrato `ErrorResponse` ya especificado por DEV-7,
**sin debilitar** el mapeo del código `IDEMPOTENCY_KEY_REUSED` definido por
DEV-31.

#### Scenario: Conflicto de transición responde con 409
- GIVEN un `AuditEvent` ya registrado con `transitionKey = T1` y un
  `correlationId` distinto
- WHEN `AuditService.record` recibe una transición que colisiona con `T1` por
  una mutación manual del `correlationId`
- THEN la API responde con `409 Conflict`
- AND el cuerpo tiene `code = "AUDIT_TRANSITION_CONFLICT"`
- AND la estructura cumple `ErrorResponse` con `fieldErrors` y `correlationId`

#### Scenario: Mapeo del código IDEMPOTENCY_KEY_REUSED no se debilita
- GIVEN el `ApiExceptionFilter`
- WHEN llega una `HttpException` con status `409` y
  `code = "IDEMPOTENCY_KEY_REUSED"` (DEV-31)
- THEN la respuesta HTTP tiene `code = "IDEMPOTENCY_KEY_REUSED"`
- AND NO se sustituye por `AUDIT_TRANSITION_CONFLICT`