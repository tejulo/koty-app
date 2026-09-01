# transactional-outbox Specification

## Purpose
TBD - created by archiving change dev-32. Update Purpose after archive.
## Requirements
### Requirement: Estructura mínima del evento del outbox

El sistema SHALL persistir cada evento de dominio con los metadatos `organizationId`, `aggregateType`, `aggregateId`, `version`, `semanticKey`, `eventType`, `correlationId`, `causationId` (opcional) y `payload`.

#### Scenario: Evento persistido con todos los metadatos obligatorios
- GIVEN un servicio de dominio que invoca `OutboxService.record({ organizationId, aggregateType, aggregateId, version, semanticKey, eventType, correlationId, causationId: null, payload })`
- WHEN la transacción de negocio hace commit
- THEN la tabla `OutboxEvent` contiene una fila con esos valores
- AND `createdAt` se asigna en el momento del insert

#### Scenario: Causación opcional
- GIVEN un evento de dominio cuyo `causationId` es `null`
- WHEN se persiste
- THEN la columna `causationId` queda `NULL`
- AND una segunda invocación con `causationId = "<id del primer evento>"` lo persiste como string no nulo

#### Scenario: Payload poblado como JSON
- GIVEN un `payload` con campos arbitrarios
- WHEN el evento se persiste
- THEN la columna `payload` se almacena como `JSONB` con el contenido íntegro
- AND se recupera íntegro en una lectura posterior

### Requirement: Inmutabilidad append-only del outbox

El sistema SHALL tratar la tabla `OutboxEvent` como append-only: no se permite `UPDATE` ni `DELETE` desde la aplicación, y la base de datos rechaza esas operaciones mediante un trigger y `REVOKE`.

#### Scenario: La aplicación no expone métodos de mutación distintos a record
- GIVEN el módulo `OutboxModule`
- WHEN se enumeran los métodos públicos de `OutboxService`
- THEN sólo `record` está disponible
- AND no existen `update`, `delete`, `patch` ni `truncate`

#### Scenario: UPDATE directo por SQL raw es rechazado
- GIVEN un `OutboxEvent` persistido
- WHEN se ejecuta `UPDATE "OutboxEvent" SET "version" = $1 WHERE "id" = $2`
- THEN PostgreSQL lanza `EXCEPTION 'OutboxEvent is append-only'`
- AND la fila original queda intacta

#### Scenario: DELETE directo por SQL raw es rechazado
- GIVEN un `OutboxEvent` persistido
- WHEN se ejecuta `DELETE FROM "OutboxEvent" WHERE "id" = $1`
- THEN PostgreSQL lanza `EXCEPTION 'OutboxEvent is append-only'`
- AND el registro no se elimina

### Requirement: Atomicidad con la transacción de negocio

El sistema SHALL permitir que un handler persista la mutación de dominio, el `IdempotencyRecord` (DEV-31), el `AuditEvent` (DEV-36) y el `OutboxEvent` dentro de una sola transacción de base de datos, de forma que todo se confirme o todo se revierta.

#### Scenario: Commit confirma dominio, idempotencia, auditoría y outbox a la vez
- GIVEN un handler que invoca la mutación de dominio, la inserción del `IdempotencyRecord`, la inserción del `AuditEvent` y la llamada a `OutboxService.record` dentro del mismo `prisma.$transaction`
- WHEN la transacción hace commit
- THEN las cuatro escrituras quedan persistidas
- AND ningún observador externo ve un estado parcial

#### Scenario: Rollback deja todas las escrituras sin efecto
- GIVEN un handler con la misma composición
- WHEN la mutación de dominio falla (o el handler fuerza un error) **después** de invocar `OutboxService.record`
- THEN ninguna fila queda en `OutboxEvent`, `IdempotencyRecord` ni `AuditEvent`
- AND la transacción de base de datos se revierte como un todo

### Requirement: Cero llamadas externas dentro de la transacción de negocio

El sistema SHALL garantizar que la persistencia de un evento en el outbox no realiza ninguna llamada externa (HTTP, RPC, cola, broker, etc.) y se limita a una escritura SQL local.

#### Scenario: OutboxService sólo escribe en PostgreSQL
- GIVEN una invocación a `OutboxService.record`
- WHEN la operación se ejecuta
- THEN la única escritura observada es `INSERT` contra la tabla `OutboxEvent`
- AND no se emite ninguna petición HTTP, RPC, ni publicación a colas

#### Scenario: OutboxService no expone API de envío
- GIVEN la superficie pública de `OutboxService`
- WHEN se enumeran los métodos
- THEN no existe `publish`, `send`, `dispatch`, `emit`, `enqueue` ni equivalentes
- AND la única operación de escritura es `record`

### Requirement: Idempotencia por (organizationId, aggregateType, aggregateId, semanticKey)

El sistema SHALL tratar como idempotente la persistencia de un evento cuya clave `(organizationId, aggregateType, aggregateId, semanticKey)` ya exista en la tabla, devolviendo el evento original sin crear un duplicado.

#### Scenario: Misma clave semántica en el mismo agregado no crea un duplicado
- GIVEN un `OutboxEvent` persistido con `semanticKey = "k1"` para `(org-1, organization, org-123)`
- WHEN el handler invoca de nuevo `OutboxService.record` con la misma `semanticKey` y el mismo `payload`
- THEN la base de datos no crea una segunda fila
- AND el servicio devuelve el evento original con `created: false`

#### Scenario: Misma clave semántica con payload distinto se detecta como conflicto
- GIVEN un `OutboxEvent` persistido con `semanticKey = "k1"` y `payload = P1`
- WHEN el handler invoca `OutboxService.record` con la misma `semanticKey` y un `payload` distinto `P2`
- THEN el servicio lanza `OutboxSemanticConflictException` mapeada a `409 OUTBOX_SEMANTIC_CONFLICT`
- AND el evento original queda intacto

#### Scenario: Misma clave semántica en otra organización es independiente
- GIVEN un `OutboxEvent` con `semanticKey = "k1"` para `(org-1, organization, org-123)`
- WHEN el handler invoca `OutboxService.record` con la misma `semanticKey` pero `organizationId = "org-2"`
- THEN la inserción es exitosa
- AND coexisten dos eventos con la misma `semanticKey` en organizaciones distintas

### Requirement: Causación y correlación propagadas

El sistema SHALL propagar el `correlationId` desde el header de la request y persistir el `causationId` cuando el caller lo proporciona, manteniendo la trazabilidad extremo a extremo.

#### Scenario: correlationId del header se persiste
- GIVEN una request con `x-correlation-id: <uuid>`
- WHEN el handler invoca `OutboxService.record` sin override de `correlationId`
- THEN la fila persistida contiene ese mismo `correlationId`

#### Scenario: correlationId generado cuando el header está ausente
- GIVEN una request sin `x-correlation-id`
- WHEN el handler invoca `OutboxService.record` sin override
- THEN la fila persistida contiene un UUID v4 generado por el servicio
- AND ese UUID se devuelve en la respuesta del endpoint

#### Scenario: causationId se persiste cuando el caller lo pasa
- GIVEN un evento origen con `id = "ev-1"`
- WHEN el handler invoca `OutboxService.record({ ..., causationId: "ev-1" })`
- THEN la fila persistida contiene `causationId = "ev-1"`

### Requirement: Rechazo de payload que excede el límite

El sistema SHALL rechazar con `400 OUTBOX_PAYLOAD_TOO_LARGE` cualquier intento de persistir un `payload` cuyo tamaño serializado exceda el límite máximo configurado.

#### Scenario: Payload dentro del límite se persiste
- GIVEN un `payload` serializado de 1 KB
- WHEN el handler invoca `OutboxService.record`
- THEN la fila se persiste sin error

#### Scenario: Payload que excede el límite se rechaza antes de tocar la base de datos
- GIVEN un `payload` serializado mayor que `OUTBOX_MAX_PAYLOAD_BYTES`
- WHEN el handler invoca `OutboxService.record`
- THEN el servicio lanza `OutboxPayloadTooLargeException` mapeada a `400 OUTBOX_PAYLOAD_TOO_LARGE`
- AND no se ejecuta ningún `INSERT` contra `OutboxEvent`

### Requirement: Código de error OUTBOX_SEMANTIC_CONFLICT

El sistema SHALL definir `OUTBOX_SEMANTIC_CONFLICT` como código predefinido mapeado a HTTP `409 Conflict`, siguiendo el contrato `ErrorResponse` existente (DEV-7), sin debilitar `IDEMPOTENCY_KEY_REUSED`.

#### Scenario: Conflicto de clave semántica devuelve 409 con código OUTBOX_SEMANTIC_CONFLICT
- GIVEN un `OutboxEvent` existente con `semanticKey = "k1"` y `payload = P1`
- WHEN el handler invoca `OutboxService.record` con la misma `semanticKey` y un `payload` distinto `P2`
- THEN la API responde con HTTP `409`
- AND el cuerpo es:
```json
{
  "code": "OUTBOX_SEMANTIC_CONFLICT",
  "message": "Outbox semantic key reused with a different payload",
  "fieldErrors": [],
  "correlationId": "uuid-v4-value"
}
```

#### Scenario: Lista de códigos de error disponibles
- GIVEN la especificación de códigos de error
- THEN `OUTBOX_SEMANTIC_CONFLICT` y `OUTBOX_PAYLOAD_TOO_LARGE` forman parte del conjunto
- AND coexisten con `IDEMPOTENCY_KEY_REUSED`, `AUDIT_TRANSITION_CONFLICT`, `AUDIT_INVALID_FIELD` y los demás códigos predefinidos

### Requirement: Huella canónica del payload

El sistema SHALL calcular una huella SHA-256 sobre la serialización canónica (claves ordenadas recursivamente) de los metadatos del evento más el `payload` para detectar diferencias semánticas en presencia de reintentos.

#### Scenario: Mismo payload con distinto orden de claves produce la misma huella
- GIVEN un `payload` `{ "name": "Acme", "status": "active" }`
- AND el mismo `payload` con claves reordenadas `{ "status": "active", "name": "Acme" }`
- WHEN se calcula la huella canónica
- THEN ambas huellas son idénticas

#### Scenario: Cambio en cualquier metadato produce una huella distinta
- GIVEN un evento con `organizationId = "org-1"` y `version = 1`
- WHEN se calcula la huella tras cambiar `version` a `2`
- THEN la huella cambia

