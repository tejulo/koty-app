# Proposal: DEV-31 — Procesar comandos sensibles con idempotencia

## Problema

`koty-app` está compuesto por varios clientes (web, worker, integraciones externas) que pueden
reenviar accidentalmente la misma orden sensible más de una vez (creación de organizaciones,
envío de invitaciones, asignación de membresías, aceptación de invitaciones, etc.). Sin un
mecanismo de idempotencia, cada reintento produce efectos duplicados (organizaciones duplicadas,
invitaciones duplicadas, eventos publicados más de una vez) y compromete la integridad del
modelo de dominio.

El ticket DEV-31 introduce la necesidad de que la API reconozca comandos sensibles repetidos y
devuelva la misma respuesta original sin volver a ejecutar efectos, manteniendo al mismo tiempo
la capacidad de detectar reenvíos con contenido distinto (que deben rechazarse de forma explícita).

## Objetivo

Definir un contrato HTTP uniforme para procesar **comandos sensibles con idempotencia** dentro
de la API de `koty-app`, de manera que:

1. Cada comando sensible pueda acompañarse de una **clave de idempotencia** limitada por
   organización, actor y tipo de comando.
2. La API pueda **reutilizar el resultado confirmado** cuando la misma clave llegue con la misma
   huella canónica de contenido, sin repetir efectos.
3. La API pueda **detectar conflictos** cuando la misma clave llegue con una huella canónica
   distinta y responder con `409 IDEMPOTENCY_KEY_REUSED`.
4. La API **no consuma** la clave cuando el comando es rechazado por validaciones o por
   restricciones naturales del dominio **antes del commit**, de modo que un reintento válido con
   una clave nueva no quede bloqueado.
5. La API exponga el código de error `IDEMPOTENCY_KEY_REUSED` dentro del contrato de errores
   estandarizado ya definido por DEV-7.

## Alcance

1. **Cabecera HTTP `Idempotency-Key`**
   - El sistema acepta una clave opcional `Idempotency-Key` en los endpoints de comandos
     sensibles.
   - El contrato define la clave como una cadena opaca (string) generada por el cliente, con
     longitud razonable (mín. 8 caracteres, máx. 128). Las claves se truncan o se rechazan fuera
     de ese rango según se defina en el diseño.
   - Las claves vacías se tratan como "sin clave" y se procesan normalmente.

2. **Alcance de la clave (scope)**
   - Toda clave se acota por la tripleta `(organizationId, actorId, commandType)`:
     - `organizationId` proviene del contexto autenticado (la organización sobre la que se opera).
     - `actorId` es el identificador del sujeto autenticado que ejecuta el comando.
     - `commandType` es el nombre lógico del comando (`create-organization`,
       `create-invitation`, `accept-invitation`, etc.).
   - Esto evita colisiones entre clientes que usan la misma clave en contextos distintos.

3. **Huella canónica del contenido (request fingerprint)**
   - Se calcula sobre la representación estable del cuerpo de la solicitud tras la validación
     Zod estricta (modo `strict`, campos desconocidos rechazados según DEV-7/DEV-6) y la
     normalización de claves (orden determinista) y valores (representación canónica de tipos).
   - El algoritmo de huella es **SHA-256** sobre la serialización JSON canónica (claves
     ordenadas, sin espacios), codificado en hexadecimal en minúsculas.
   - El resultado se almacena junto con la respuesta confirmada para detectar conflictos.

4. **Persistencia del resultado confirmado**
   - Se introduce un nuevo modelo Prisma `IdempotencyRecord` con la siguiente forma mínima:
     - `id` (UUID v4, PK)
     - `organizationId` (string, parte del scope)
     - `actorId` (string, parte del scope)
     - `commandType` (string, parte del scope)
     - `idempotencyKey` (string)
     - `requestFingerprint` (string, SHA-256 hex)
     - `responseStatus` (int, HTTP status original confirmado)
     - `responseBody` (JSON, respuesta original confirmada)
     - `createdAt` / `updatedAt` (timestamps)
   - La unicidad se garantiza por la tripleta `(organizationId, actorId, commandType)` +
     `idempotencyKey`. No se almacena el contenido crudo del request, solo la huella.

5. **Semántica de procesamiento**
   - Cuando llega un comando sensible con `Idempotency-Key`:
     1. Si no existe un `IdempotencyRecord` para el scope y la clave:
        - Se ejecuta el comando bajo una transacción.
        - Si la transacción hace **commit** con éxito, se persiste un `IdempotencyRecord` con la
          huella, el status y el body resultantes.
        - Si la transacción **no llega a commit** (validación de dominio, error de negocio,
          restricción natural violada), **no se persiste** la clave. El cliente puede reintentar
          con una clave nueva sin que la API rechace por conflicto.
        - Si la transacción falla con un error 5xx **después del commit**, se considera un caso
          excepcional fuera del contrato de idempotencia y se documenta como "no cubierto" por
          este cambio.
     2. Si ya existe un `IdempotencyRecord` con la **misma huella canónica**, se devuelve la
        respuesta almacenada con el mismo status y el mismo body, sin volver a ejecutar el
        comando.
     3. Si ya existe un `IdempotencyRecord` con una **huella canónica distinta**, se responde
        con `409 Conflict`, código `IDEMPOTENCY_KEY_REUSED`, sin ejecutar el comando.

6. **Contrato de error `IDEMPOTENCY_KEY_REUSED`**
   - Se añade `IDEMPOTENCY_KEY_REUSED = 'IDEMPOTENCY_KEY_REUSED'` al enum `ErrorCode`.
   - Se traduce a HTTP `409 Conflict` en `ApiExceptionFilter`.
   - La respuesta sigue la estructura `ErrorResponse` existente: `code`, `message`,
     `fieldErrors`, `correlationId`.

7. **Comandos sensibles cubiertos inicialmente**
   - `create-organization` (creación de organización).
   - `create-invitation` (envío de invitación).
   - `accept-invitation` (aceptación de invitación).
   - El diseño contempla la posibilidad de añadir nuevos `commandType` sin modificar el
     mecanismo de almacenamiento, simplemente declarando el nuevo tipo en una lista de comandos
     sensibles.

## Fuera de Alcance

- Reemplazar los endpoints actuales por versiones `v2`. El contrato se añade como una cabecera
  opcional sobre los endpoints existentes.
- Persistir el cuerpo crudo del request (solo se persiste la huella canónica).
- Definir un TTL de claves de idempotencia. El contrato actual no requiere expiración; queda
  documentado como mejora futura si surge la necesidad.
- Cambios al frontend (`apps/web`) más allá de la documentación del contrato en OpenAPI.
- Cambios al worker (`apps/worker`).
- Cualquier flujo de rollback manual sobre registros de idempotencia.

## Impacto Esperado

- Los clientes (web y externos) pueden reintentar comandos sensibles con seguridad sin
  generar duplicados.
- La API distingue entre reintento válido (misma huella → mismo resultado) y reenvío
  malicioso o accidentado con contenido distinto (huella distinta → `409`).
- Las reglas de dominio siguen siendo la fuente de verdad para rechazar comandos inválidos:
  la idempotencia nunca "salta" validaciones ni restricciones naturales.
- El modelo `IdempotencyRecord` permite auditar qué comandos se procesaron bajo una clave
  concreta y cuáles fueron sus resultados.

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| Huella canónica distinta para requests semánticamente iguales | Serialización JSON canónica con claves ordenadas y misma representación numérica/booleana; especificación cubierta por tests unitarios. |
| Consumir la clave en un rechazo anterior al commit | El registro solo se persiste tras un commit exitoso; los rechazos previos al commit no escriben en `IdempotencyRecord`. |
| Una clave nueva sortea restricciones del dominio | Las restricciones de dominio se ejecutan **antes** de la fase de idempotencia; ningún cambio en este ticket modifica la lógica de negocio. |
| Saturación de la tabla `IdempotencyRecord` | Sin TTL definido por ahora; el contrato queda abierto a una política de expiración posterior. Se documenta como mejora futura. |
| Filtración de datos sensibles en `responseBody` | El contrato solo persiste respuestas ya emitidas por la API. La API no incluye secretos en sus respuestas. |

## Trazabilidad con `CONTEXT.md`

- **Incremento 0 — Plataforma segura**: la idempotencia es un pilar del manejo seguro de
  comandos en sistemas distribuidos que expone operaciones sensibles de organización e
  invitación a través de la API pública. Este mecanismo sostiene la promesa de "ningún
  usuario puede consultar o modificar datos de otra organización" sin sacrificar
  reintentos seguros.
- **Contrato de errores (`api-v1-error-contract`)**: este cambio añade un nuevo código
  predefinido y mantiene la estructura `ErrorResponse` ya especificada por DEV-7.
- **Validación (`api-v1-validation`)**: la huella canónica se calcula **tras** la validación
  Zod estricta, garantizando que solo se consideran cuerpos válidos.
- **Rutas (`api-v1-routes`)**: la cabecera `Idempotency-Key` es compatible con el prefijo
  `/api/v1` y no introduce rutas nuevas.
- **Prisma (`infra-prisma-migrations`)**: el nuevo modelo `IdempotencyRecord` se versiona
  mediante una migración reproducible siguiendo el flujo definido por DEV-6.
- **BND-IAM / BND-OPS**: la idempotencia aplica a los comandos sensibles del Incremento 0
  (organización, invitación, aceptación de invitación) y se alinea con la postura de "duplicación
  de cargos o mensajes" mitigada por claves únicas de idempotencia.

## Ambigüedades Reconocidas

El ticket original deja abiertas las siguientes cuestiones; este OpenSpec las resuelve con
posiciones explícitas y verificables:

1. **"Acción sensible"**: se limita a una lista inicial (`create-organization`,
   `create-invitation`, `accept-invitation`) extensible sin migración. El diseño documenta
   cómo añadir nuevas entradas.
2. **Algoritmo de huella**: SHA-256 sobre serialización JSON canónica (claves ordenadas).
3. **TTL**: no definido en este cambio; se documenta como mejora futura.
4. **"Anterior al commit"**: se interpreta como "antes de que la transacción de base de datos
   confirme los efectos". Se traduce en el requisito de no persistir `IdempotencyRecord`
   cuando el comando falla antes del commit.
5. **"Restricciones naturales del dominio"**: se mantienen tal y como están definidas por los
   servicios de dominio. La idempotencia no las altera ni las evita.
6. **Almacenamiento**: PostgreSQL mediante Prisma, tabla `IdempotencyRecord`, con unicidad
   compuesta `(organizationId, actorId, commandType, idempotencyKey)`.
7. **Formato de la clave**: cabecera HTTP `Idempotency-Key` (string opaca).
