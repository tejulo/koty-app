# api-v1-idempotency Specification

## Purpose
TBD - created by archiving change dev-31. Update Purpose after archive.
## Requirements
### Requirement: Cabecera Idempotency-Key opcional

El sistema SHALL accept an optional `Idempotency-Key` header on sensitive command endpoints.

#### Scenario: Endpoint acepta la cabecera cuando está presente
- GIVEN un endpoint de comando sensible (por ejemplo `POST /api/v1/_idempotency/echo`)
- WHEN la solicitud llega con la cabecera `Idempotency-Key: <opaque-string>`
- THEN la cabecera se considera parte del scope de idempotencia
- AND el comando se procesa bajo esa clave

#### Scenario: Endpoint procesa la solicitud sin clave
- GIVEN un endpoint de comando sensible
- WHEN la solicitud llega sin la cabecera `Idempotency-Key`
- THEN el endpoint se procesa sin idempotencia
- AND la respuesta es equivalente a una invocación sin clave

#### Scenario: Cabecera con longitud excesiva se rechaza
- GIVEN un endpoint de comando sensible
- WHEN la solicitud llega con `Idempotency-Key` de más de 128 caracteres
- THEN la API responde con `400 VALIDATION_ERROR`
- AND el cuerpo del error incluye `fieldErrors` con `field: "idempotencyKey"`

### Requirement: Alcance de la clave por organización, actor y comando

El sistema SHALL limit each idempotency key to the triple `(organizationId, actorId, commandType)`.

#### Scenario: Misma clave usada por dos actores distintos no colisiona
- GIVEN una clave `k1` usada por el actor `A` en la organización `O1`
- AND la misma clave `k1` usada por el actor `B` en la organización `O1`
- WHEN ambas solicitudes llegan al endpoint
- THEN cada solicitud se procesa de forma independiente
- AND no se devuelve el resultado de la otra

#### Scenario: Misma clave usada para dos comandos distintos no colisiona
- GIVEN una clave `k1` usada para `commandType = create-organization`
- AND la misma clave `k1` usada para `commandType = create-invitation`
- WHEN ambas solicitudes llegan al endpoint correspondiente
- THEN cada solicitud se procesa de forma independiente
- AND no se devuelve el resultado de la otra

#### Scenario: Falta de actor autenticado se rechaza
- GIVEN un endpoint de comando sensible con idempotencia
- WHEN la solicitud llega sin actor autenticado
- THEN la API responde con `401 UNAUTHORIZED`
- AND no se almacena ningún `IdempotencyRecord`

### Requirement: Huella canónica del contenido

El sistema SHALL compute a canonical fingerprint of the validated request body using SHA-256 over a stable JSON serialization.

#### Scenario: Mismo cuerpo con distinto orden de claves produce la misma huella
- GIVEN un cuerpo `{ "name": "Acme", "email": "a@b.co" }`
- AND otro cuerpo `{ "email": "a@b.co", "name": "Acme" }`
- WHEN se calcula la huella canónica de ambos cuerpos
- THEN ambas huellas son idénticas

#### Scenario: Cuerpos con un valor distinto producen huellas distintas
- GIVEN un cuerpo `{ "name": "Acme" }`
- AND otro cuerpo `{ "name": "Beta" }`
- WHEN se calcula la huella canónica de ambos cuerpos
- THEN las huellas son distintas

#### Scenario: La huella se calcula después de la validación Zod
- GIVEN un endpoint protegido por `ZodValidationInterceptor` en modo strict
- WHEN llega una solicitud con un campo desconocido
- THEN la validación falla con `400 VALIDATION_ERROR`
- AND no se calcula ni se almacena ninguna huella canónica

### Requirement: Reutilización del resultado confirmado

El sistema SHALL return the previously confirmed response when a request arrives with the same `(organizationId, actorId, commandType, idempotencyKey)` and the same canonical fingerprint, without re-executing the command.

#### Scenario: Reintento con misma clave y misma huella devuelve el resultado original
- GIVEN un comando confirmado con clave `k1` y huella `h1` que devolvió `{ status: 201, body: { id: "x" } }`
- WHEN llega una nueva solicitud con clave `k1` y huella `h1`
- THEN la API responde con `201` y `{ id: "x" }`
- AND el comando no se vuelve a ejecutar
- AND no se crea un nuevo `IdempotencyRecord`

#### Scenario: La respuesta cacheada mantiene el status y el body originales
- GIVEN un comando confirmado con status original `201` y body `{ id: "x", name: "Acme" }`
- WHEN se reintenta con la misma clave y huella
- THEN la respuesta tiene exactamente `status: 201` y `body: { id: "x", name: "Acme" }`

### Requirement: Detección de conflictos por huella distinta

El sistema SHALL respond with `409 IDEMPOTENCY_KEY_REUSED` when a request arrives with the same `(organizationId, actorId, commandType, idempotencyKey)` but a different canonical fingerprint.

#### Scenario: Misma clave con huella distinta devuelve 409
- GIVEN un comando confirmado con clave `k1` y huella `h1`
- WHEN llega una nueva solicitud con clave `k1` y huella `h2` (`h2 !== h1`)
- THEN la API responde con `409 Conflict`
- AND el cuerpo de respuesta tiene `code: "IDEMPOTENCY_KEY_REUSED"`
- AND la estructura del error cumple el contrato `ErrorResponse` (incluye `correlationId`)

#### Scenario: El conflicto no ejecuta el comando
- GIVEN un comando confirmado con clave `k1` y huella `h1`
- WHEN llega una nueva solicitud con clave `k1` y huella `h2`
- THEN el comando no se ejecuta
- AND no se modifica el `IdempotencyRecord` original

### Requirement: Rechazos previos al commit no consumen la clave

El sistema SHALL NOT persist an `IdempotencyRecord` when the command fails before the underlying transaction commits, and SHALL NOT prevent the client from retrying with a new key.

#### Scenario: Comando rechazado por validación no consume la clave
- GIVEN una solicitud con clave `k1` que falla la validación Zod
- WHEN la API rechaza la solicitud con `400 VALIDATION_ERROR`
- THEN no se crea ningún `IdempotencyRecord` para `(organizationId, actorId, commandType, "k1")`
- AND una solicitud posterior con una clave distinta `k2` y contenido válido se procesa normalmente

#### Scenario: Comando rechazado por restricción de dominio no consume la clave
- GIVEN una solicitud con clave `k1` que viola una restricción natural del dominio (por ejemplo, nombre duplicado)
- WHEN la API rechaza la solicitud con un error de dominio (no 5xx)
- THEN no se crea ningún `IdempotencyRecord` para `(organizationId, actorId, commandType, "k1")`
- AND una solicitud posterior con una clave distinta `k2` y contenido válido se procesa normalmente

#### Scenario: Comando exitoso consume la clave
- GIVEN una solicitud con clave `k1` que se procesa con éxito
- WHEN la transacción subyacente hace commit
- THEN se crea un `IdempotencyRecord` para `(organizationId, actorId, commandType, "k1")`
- AND la huella canónica, el status y el body confirmados quedan almacenados

### Requirement: Código de error IDEMPOTENCY_KEY_REUSED

El sistema SHALL define `IDEMPOTENCY_KEY_REUSED` as a predefined error code mapped to HTTP `409 Conflict`, siguiendo el contrato `ErrorResponse`.

#### Scenario: Error 409 con código IDEMPOTENCY_KEY_REUSED
- GIVEN un conflicto de huella bajo la misma clave
- WHEN la API construye la respuesta de error
- THEN el HTTP status es `409`
- AND el cuerpo es:
```json
{
  "code": "IDEMPOTENCY_KEY_REUSED",
  "message": "Idempotency key reused with a different request payload",
  "fieldErrors": [],
  "correlationId": "uuid-v4-value"
}
```

#### Scenario: Lista de códigos de error disponibles
- GIVEN la especificación de códigos de error
- THEN `IDEMPOTENCY_KEY_REUSED` forma parte del conjunto de códigos predefinidos
- AND coexiste con `VALIDATION_ERROR`, `NOT_FOUND`, `INTERNAL_ERROR`, `BAD_REQUEST`, `UNAUTHORIZED`

