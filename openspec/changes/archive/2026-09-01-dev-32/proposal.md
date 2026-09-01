# Proposal: DEV-32 — Guardar eventos en un outbox transaccional

## Problema

`koty-app` ejecuta acciones de negocio que producen efectos secundarios
(creación de organizaciones, invitaciones, aceptaciones, asignaciones de
membresía, etc.). Hasta ahora, los contratos disponibles en la API (DEV-31
para idempotencia, DEV-36 para auditoría) cubren dos aristas del mismo flujo,
pero **no** resuelven el problema de la **persistencia atómica de los
eventos de dominio** que esos comandos generan:

- `IdempotencyService` (DEV-31) guarda la respuesta HTTP confirmada y
  deduplica comandos repetidos, pero no produce un evento de dominio
  reusable por un worker o por otros consumidores.
- `AuditService` (DEV-36) registra un evento inmutable con alcance,
  actor y `before`/`after`, pero se centra en **quién hizo qué** (auditoría
  humana), no en **qué evento de dominio** se publicó (eventos de máquina).
- No existe ningún modelo Prisma ni servicio que persista un evento de
  dominio dentro de la misma transacción de base de datos que modifica el
  estado de negocio, lo que abre la puerta a:
  - **Pérdida de eventos** si la transacción hace commit pero el envío a
    un broker / cola / API externa falla después.
  - **Publicación anticipada** si el código intenta emitir el evento antes
    de confirmar la transacción principal.
  - **Eventos duplicados** cuando un comando se reintenta con la misma
    clave semántica.
  - **Eventos huérfanos** (estado mutado, evento no persistido) cuando se
    intercalan I/O externos en mitad de la transacción.

El ticket DEV-32 exige el **patrón Transactional Outbox** dentro del
Incremento 0 de `koty-app` ("Incremento 0 — Plataforma segura"), alineado con
la regla explícita de la matriz de riesgos de `CONTEXT.md`:
> "Duplicación de cargos o mensajes | Claves únicas de idempotencia,
> outbox y worker reintentable."

Y con la mención del Incremento 0: "API, outbox, jobs con lease y
restauración en hold". El outbox es la base que hace seguros al resto de
los mecanismos de V1.

## Objetivo

Introducir en `apps/api` un **outbox transaccional** que permita a un
servicio de dominio persistir cada evento de dominio en la **misma
transacción ACID** que modifica el estado de negocio, de forma que:

1. Cada evento de dominio se persista con metadatos obligatorios
   (`organizationId`, `aggregateType`, `aggregateId`, `version`,
   `correlationId`, `causationId`, `semanticKey`, `eventType`, `payload`).
2. La escritura del estado de negocio, la validación de idempotencia, la
   auditoría (DEV-36) y el outbox se confirmen o se reviertan en una sola
   transacción.
3. Los eventos del outbox sean **inmutables y append-only**: no se
   modifican ni se eliminan desde la aplicación ni por SQL directo.
4. **Ninguna llamada externa** (HTTP, RPC, colas, brokers) se ejecute
   dentro de la transacción de negocio.
5. Repetir un comando confirmado con la misma clave semántica **no**
   cree un segundo evento semánticamente equivalente.

## Alcance

1. **Modelo Prisma `OutboxEvent`**
   - Añadir a `apps/api/prisma/schema.prisma` un modelo `OutboxEvent` con
     las columnas: `id`, `organizationId`, `aggregateType`, `aggregateId`,
     `version` (int), `semanticKey` (string), `eventType` (string),
     `correlationId` (string), `causationId` (string, nullable),
     `payload` (`Json`), `createdAt` (`DateTime`).
   - Restricción `@@unique([organizationId, aggregateType, aggregateId,
     semanticKey])` para idempotencia por agregación y clave semántica.
   - Índices secundarios para reenvío futuro: `(organizationId,
     createdAt)`, `(aggregateType, aggregateId, version)`.

2. **Migración reproducible con inmutabilidad**
   - Crear `apps/api/prisma/migrations/<timestamp>_add_outbox_event/
     migration.sql` con:
     - `CREATE TABLE "OutboxEvent"` con columnas, PK, índices y
       `@@unique` declarado.
     - Función `outbox_event_block_mutations()` y trigger
       `outbox_event_append_only` (`BEFORE UPDATE OR DELETE`) que lance
       `EXCEPTION 'OutboxEvent is append-only'`.
     - `REVOKE UPDATE, DELETE ON TABLE "OutboxEvent" FROM PUBLIC`.

3. **Servicio `OutboxService`**
   - `record(input: OutboxEventInput): Promise<OutboxEventRecord>`
     inserta un evento aplicando la misma huella canónica (SHA-256 sobre
     serialización JSON estable) y deja al `@@unique` arbitrar
     concurrencia. Si la inserción viola el constraint y la huella
     coincide, devuelve el evento existente con `created: false`
     (idempotente). Si la huella difiere, lanza
     `OutboxSemanticConflictException` mapeada a `409`
     `OUTBOX_SEMANTIC_CONFLICT`.
   - `OutboxService` **no** expone `update`, `delete`, `patch` ni
     `truncate`. Su única operación de escritura es `record`.
   - El servicio **nunca** realiza llamadas externas: su API sólo
     recibe valores ya materializados y los delega a Prisma dentro de
     la transacción del caller.

4. **Excepciones y códigos de error**
   - `OUTBOX_SEMANTIC_CONFLICT` añadido a `ErrorCode` (mapeo a HTTP
     `409`).
   - `OUTBOX_PAYLOAD_TOO_LARGE` añadido a `ErrorCode` (mapeo a HTTP
     `400`), lanzado cuando el `payload` excede el límite máximo
     permitido por la API (regla de calidad, no de seguridad).

5. **Endpoint de smoke `OutboxEchoController`**
   - `POST /api/v1/_outbox/echo` montado únicamente cuando
     `process.env.ENABLE_OUTBOX_ECHO === 'true'`. Acepta un cuerpo
     validado por Zod y registra un `OutboxEvent` con `aggregateType =
     "outbox-echo"`, `eventType = "outbox-echo.create"`. Devuelve el evento
     persistido (sin revelar claves internas adicionales) para que las
     pruebas de integración cubran el contrato end-to-end.

6. **Propagación de `correlationId` y `causationId`**
   - `OutboxService.record` lee `correlationId` del header HTTP
     (`x-correlation-id`) o genera un UUID v4 cuando falta. Acepta
     override explícito desde el handler.
   - `causationId` se acepta desde el caller (es el id del evento que
     originó este nuevo evento) y queda persistido en la columna
     correspondiente.

7. **Atomicidad con la transacción de negocio**
   - `OutboxService.record` se ejecuta como un delegate Prisma normal
     (`prisma.outboxEvent.create`) y **delega la gestión de la
     transacción al caller**: los handlers deben invocarlo dentro de un
     `prisma.$transaction([...])` o tras un `tx.outboxEvent.create(...)`.
   - La regla de atomicidad la cumplen los handlers de comando, que
     gestionan un único `prisma.$transaction` que incluye (a) la
     mutación de dominio, (b) la inserción del `OutboxEvent`, (c) la
     inserción del `AuditEvent` y (d) la inserción del
     `IdempotencyRecord`. El handler de smoke `OutboxEchoController`
     materializa este patrón de forma explícita y verificable.
   - El diseño no añade "transacciones anidadas": el caller es dueño de
     la transacción; el servicio sólo opera sobre el delegate.

8. **Pruebas**
   - **Unitarias**:
     - `outbox-canonical-fingerprint.spec.ts`: huella canónica estable
       y sensible al cambio de cualquier campo de metadatos.
     - `outbox.service.spec.ts`: `record` exitoso, idempotencia por
       `semanticKey`, conflicto por huella distinta, `payload` vacío
       rechazado, `causationId` opcional persistido.
   - **Integración** (`apps/api/test/integration/outbox.integration
     .spec.ts`):
     - Inserción inicial exitosa vía `POST /api/v1/_outbox/echo` con
       `payload` poblado.
     - Reintento con misma `semanticKey` no crea un segundo
       `OutboxEvent`.
     - `UPDATE`/`DELETE` directos por SQL raw sobre `OutboxEvent`
       fallan con error SQL "OutboxEvent is append-only".
     - Rollback atómico: si el handler de smoke fuerza un fallo tras
       encolar un evento, **ningún** `OutboxEvent` queda persistido
       (cubre CA-2: dominio + outbox en una sola transacción).
     - `correlationId` se propaga desde el header `x-correlation-id`.

## Fuera de Alcance

> Los siguientes elementos **no son exigidos por el ticket DEV-32** y por
> tanto quedan explícitamente fuera del alcance de este cambio. No se
> declara fuera de alcance ninguna implementación exigida por DEV-32.

- Lectura, envío o publicación posterior de los eventos hacia
  sistemas externos o colas de mensajes (la contraparte del patrón outbox
  es materia de tickets posteriores del Incremento 0 / Incremento 5,
  alineado con la sección "Fuera de alcance" del propio ticket).
- Relé, polling, lease de jobs o `OutboxRelay` (lo define el worker de
  otro ticket posterior del Incremento 0).
- Replicación o mirroring del outbox a un servicio externo.
- Retención, archivado o purga de eventos. La tabla crece
  monótonamente; el TTL queda documentado como mejora futura.
- Cambios al frontend (`apps/web`).
- Cambios al worker (`apps/worker`) más allá del consumo opcional del
  servicio para producir eventos `WORKER` en el futuro.
- Autenticación o autorización reales: el endpoint de smoke sólo se
  monta bajo un flag de entorno y queda documentado como instrumento
  de verificación.

## Impacto Esperado

- Toda acción de negocio puede encolar sus eventos de dominio dentro
  de la misma transacción que muta el estado, sin riesgo de "efecto
  sin evento" ni de "evento sin efecto".
- Los reintentos idempotentes de un comando confirmado no duplican
  eventos: la combinación `(organizationId, aggregateType, aggregateId,
  semanticKey)` es el árbitro.
- La inmutabilidad del outbox está reforzada por dos vías
  independientes: trigger SQL `BEFORE UPDATE OR DELETE` que lanza
  excepción y `REVOKE UPDATE, DELETE` sobre la tabla.
- Cero llamadas externas dentro de la transacción de negocio: el
  `OutboxService` no expone ninguna API de I/O y queda libre de
  clientes HTTP, SDKs de brokers o SDKs de colas.
- El patrón queda alineado con la matriz de riesgos de `CONTEXT.md`
  y con la postura BND-IAM / BND-OPS del Incremento 0.

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| `payload` sensible (contraseña, token) persistido accidentalmente | El `OutboxService` exige que `payload` sea un objeto JSON arbitrario y no impone allowlist, pero el contrato define la responsabilidad en el caller; el spec fija que `payload` no se expone fuera del relay. La tabla es append-only, por lo que el riesgo es equivalente al de cualquier log de eventos. |
| Publicación del evento antes del commit | `OutboxService` no expone ninguna API de envío. La única operación de escritura es `record`, que delega en Prisma dentro de la transacción del caller. |
| Reintento que duplica eventos semánticamente equivalentes | `@@unique([organizationId, aggregateType, aggregateId, semanticKey])` + huella canónica SHA-256; `record` trata la colisión como idempotente y nunca crea una segunda fila. |
| `UPDATE`/`DELETE` accidental desde la propia aplicación | Trigger SQL `BEFORE UPDATE OR DELETE` lanza excepción + `REVOKE UPDATE, DELETE` sobre `"OutboxEvent"`; `OutboxService` no expone métodos de mutación distintos a `record`. |
| Transacción "medio confirmada" (commit parcial) | El handler es dueño de la transacción; el contrato obliga a que dominio + outbox vivan en el mismo `prisma.$transaction`. La prueba de integración valida rollback. |
| `payload` demasiado grande | Límite `OUTBOX_MAX_PAYLOAD_BYTES` aplicado por `OutboxService.record` antes de la inserción; excederlo lanza `OutboxPayloadTooLargeException` (mapeada a `400 OUTBOX_PAYLOAD_TOO_LARGE`). |

## Trazabilidad con `CONTEXT.md`

- **Incremento 0 — Plataforma segura**: la sección 21 fija la
  auditoría base, API, **outbox**, jobs con lease y restauración en
  hold como parte de la puerta de aceptación. DEV-32 entrega el
  outbox que sostiene la promesa "ningún evento se pierde en caso de
  fallo y ninguno se publica antes del commit".
- **Sección 3.1**: la persistencia de eventos derivados de acciones
  sensibles es parte de la entrega V1.
- **Sección 19, riesgos**: la fila "Duplicación de cargos o mensajes"
  exige "claves únicas de idempotencia, outbox y worker reintentable";
  este OpenSpec entrega el outbox, alineado con DEV-31 (idempotencia)
  y DEV-36 (auditoría).
- **BND-IAM-01 a BND-IAM-08**: las acciones de organización,
  invitación y membresía deben persistir sus eventos de dominio
  dentro de la misma transacción que muta el estado, condición
  habilitada por este cambio.
- **Patrón DEV-31 (idempotencia) y DEV-36 (auditoría)**: la
  implementación reutiliza `canonicalStringify` (DEV-31), la
  estructura de trigger + REVOKE (DEV-36), el patrón de servicio +
  controlador de smoke con flag de entorno, el `globalSetup` con base
  aislada y el `ApiExceptionFilter` (DEV-7) para mapear el nuevo
  código de error.

## Trazabilidad con los Criterios de Aceptación

| Criterio | Requisito(s) del spec que lo cubren |
|---|---|
| CA-1 (estructura mínima del evento) | `Estructura mínima del evento del outbox`, `Causación y correlación propagadas` |
| CA-2 (atomicidad) | `Atomicidad con la transacción de negocio` |
| CA-3 (inmutabilidad) | `Inmutabilidad append-only del outbox` |
| CA-4 (cero llamadas externas) | `Cero llamadas externas dentro de la transacción de negocio` |
| CA-5 (idempotencia semántica) | `Idempotencia por (organizationId, aggregateType, aggregateId, semanticKey)`, `Huella canónica del payload`, `Código de error OUTBOX_SEMANTIC_CONFLICT` |

## Ambigüedades Reconocidas

El ticket original deja abiertas varias cuestiones; este OpenSpec las
resuelve con posiciones explícitas y verificables:

1. **"Acción de negocio"**: se cubre de forma inicial con
   `aggregateType ∈ {"organization", "invitation", "membership",
   "outbox-echo"}` y `eventType` libre. La lista es extensible sin
   migración (el `@@unique` actúa sobre cualquier `aggregateType`).
2. **"Clave semántica"**: literal controlado por el caller, libre pero
   obligatorio. La idempotencia opera sobre
   `(organizationId, aggregateType, aggregateId, semanticKey)`.
3. **"Causación"**: string nullable; cuando un evento es consecuencia
   directa de otro, el handler pasa el `id` del evento original como
   `causationId`.
4. **"Almacenamiento"**: PostgreSQL mediante Prisma, tabla
   `OutboxEvent`, con trigger `BEFORE UPDATE OR DELETE` y
   `REVOKE UPDATE, DELETE` sobre la tabla.
5. **"Transacción"**: el caller es dueño de la transacción Prisma;
   `OutboxService.record` se invoca dentro de esa transacción y no
   abre transacciones propias. La atomicidad con el dominio la
   garantiza el handler, no el servicio.
6. **"Sin llamadas externas"**: el servicio sólo expone `record` (sin
   red) y la única escritura es `INSERT` contra PostgreSQL. No
   importa ni expone clientes HTTP, SDKs de colas ni SDKs de
   brokers.
7. **"Versionado"**: `version` es un entero controlado por el caller
   (típicamente la versión del agregado tras la mutación). El
   contrato no impone monotonicidad: sólo exige que esté presente.
8. **"Detección de reintento idempotente"**: por
   `semanticKey` (literal) más una huella canónica SHA-256 sobre
   `{organizationId, aggregateType, aggregateId, eventType, payload}`;
   el `@@unique` es el árbitro en presencia de concurrencia.