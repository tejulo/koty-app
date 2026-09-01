# DEV-32 — Diseño Técnico

## Decisiones de Diseño

### 1. Modelo Prisma `OutboxEvent`

Se introduce el modelo `OutboxEvent` en `apps/api/prisma/schema.prisma` con
la siguiente forma:

```prisma
model OutboxEvent {
  id             String   @id @default(uuid())
  organizationId String
  aggregateType  String
  aggregateId    String
  version        Int
  semanticKey    String
  eventType      String
  correlationId  String
  causationId    String?
  payload        Json
  createdAt      DateTime @default(now())

  @@unique([organizationId, aggregateType, aggregateId, semanticKey])
  @@index([organizationId, createdAt])
  @@index([aggregateType, aggregateId, version])
}
```

Notas:

- El `@@unique` opera sobre la combinación canónica de
  `organizationId + aggregateType + aggregateId + semanticKey`. Esa
  combinación es el **árbitro** de idempotencia: dos eventos con la
  misma cuádruple representan la misma intención y deben colapsar a
  una sola fila.
- `payload` es `Json` obligatorio (no nullable): un evento de dominio
  sin payload no es un evento. El servicio garantiza que el valor
  siempre es un objeto JSON serializable.
- `version` se modela como `Int` (no `BigInt`) para mantener paridad
  con la convención del resto del esquema y para simplificar la
  serialización JSON.
- `causationId` queda como `String?` para soportar el caso en el que
  un evento es la primera causa (sin `causationId`).
- El `createdAt` actúa como segundo índice secundario
  (`[organizationId, createdAt]`) para que un futuro relé pueda
  consumir los eventos en orden FIFO por organización sin escanear
  toda la tabla.
- El índice `[aggregateType, aggregateId, version]` cubre el caso de
  relectura del stream de eventos de un agregado (replay).

### 2. Migración reproducible con trigger de inmutabilidad

Se crea la migración
`apps/api/prisma/migrations/<timestamp>_add_outbox_event/migration.sql`
siguiendo el flujo definido por DEV-6
(`pnpm db:migrate:dev --name add_outbox_event`). El contenido de la
migración incluye:

1. `CREATE TABLE "OutboxEvent"` con sus columnas, PK, índices y
   `@@unique` declarado.
2. Función `outbox_event_block_mutations()` y trigger
   `outbox_event_append_only` que se dispara `BEFORE UPDATE OR DELETE`
   sobre `"OutboxEvent"` y lanza `EXCEPTION 'OutboxEvent is
   append-only'`.
3. `REVOKE UPDATE, DELETE ON TABLE "OutboxEvent" FROM PUBLIC` para
   reforzar la inmutabilidad por permisos (alineado con DEV-36).

La migración se aplica con `pnpm db:migrate:deploy` y se verifica con
`pnpm db:verify`.

### 3. Huella canónica del evento

`apps/api/src/outbox/outbox-canonical-fingerprint.ts` reutiliza
`canonicalStringify` de `apps/api/src/common/idempotency/
canonical-fingerprint.ts` (DEV-31) y produce un digest SHA-256
hexadecimal minúsculo de 64 caracteres. La huella se calcula sobre:

```ts
{
  organizationId,
  aggregateType,
  aggregateId,
  version,
  semanticKey,
  eventType,
  payload,
}
```

`correlationId` y `causationId` se excluyen deliberadamente: el
`semanticKey` ya identifica la intención y la huella detecta cambios
en el `payload` para distinguir reintentos idempotentes de
conflictos.

### 4. Servicio `OutboxService`

`apps/api/src/outbox/outbox.service.ts` define un único método público:

#### `record(input: OutboxEventInput): Promise<OutboxEventRecord>`

Pasos:

1. Valida el `payload`:
   - Debe ser un objeto JSON serializable.
   - Su serialización canónica no debe exceder
     `OUTBOX_MAX_PAYLOAD_BYTES` (límite fijo, 64 KB por defecto). Si lo
     excede, lanza `OutboxPayloadTooLargeException` (mapeada a `400`
     `OUTBOX_PAYLOAD_TOO_LARGE`).
2. Calcula la huella canónica.
3. Intenta `prisma.outboxEvent.create({ data: { ... } })` delegando
   en la transacción del caller.
4. Si la inserción viola el `@@unique([organizationId, aggregateType,
   aggregateId, semanticKey])`:
   - Lee el registro existente.
   - Si la huella coincide, devuelve el evento con `created: false`
     (idempotente).
   - Si la huella difiere, lanza
     `OutboxSemanticConflictException` mapeada a `409`
     `OUTBOX_SEMANTIC_CONFLICT`.
5. Devuelve el evento persistido.

`OutboxService` **no** expone `update`, `delete`, `patch` ni
`truncate`. Su superficie es deliberadamente mínima: una sola
operación de escritura (`record`) y la búsqueda auxiliar que necesita
para arbitrar la unicidad.

#### Atomicidad con la transacción de negocio

`OutboxService.record` se implementa como un delegate Prisma
(`prisma.outboxEvent.create`). **No abre transacciones propias**;
delega la gestión al caller. El patrón de uso es:

```ts
await prisma.$transaction(async (tx) => {
  await tx.organization.update({ where: { id }, data: { status: 'active' } });
  await tx.idempotencyRecord.create({ data: { ... } });
  await tx.auditEvent.create({ data: { ... } });
  await outboxService.record({ ... }); // opera sobre tx.outboxEvent
});
```

El handler de smoke `OutboxEchoController` materializa este patrón de
forma explícita y verificable: encola el `OutboxEvent` y luego
fuerza un error opcional para validar el rollback.

### 5. Cero llamadas externas

`OutboxService` no importa ni expone:

- Ningún cliente HTTP (`fetch`, `axios`, `HttpService`).
- Ningún cliente de colas / brokers (`amqplib`, `kafkajs`, `bull`,
  `p-queue`, etc.).
- Ningún SDK externo (AWS, GCP, Resend, Twilio, etc.).
- Ningún timer / scheduler que abra conexiones de red.

Su única operación de escritura es `INSERT` contra la tabla
`OutboxEvent` de PostgreSQL. La verificación se realiza mediante:

- Inspección del código (no hay `import` de SDKs de red en
  `apps/api/src/outbox/`).
- El spec unitario `outbox.service.spec.ts` que mockea el delegate
  Prisma y verifica que las únicas llamadas son `create` y
  `findUnique` sobre `outboxEvent`.
- El spec de integración `outbox.integration.spec.ts` que verifica
  que un rollback no produce efectos externos.

### 6. Excepciones y códigos de error

Se añaden los siguientes códigos a
`apps/api/src/common/errors/error-code.enum.ts`:

```ts
export enum ErrorCode {
  // ... existing codes
  OUTBOX_SEMANTIC_CONFLICT = 'OUTBOX_SEMANTIC_CONFLICT',
  OUTBOX_PAYLOAD_TOO_LARGE = 'OUTBOX_PAYLOAD_TOO_LARGE',
}
```

`apps/api/src/outbox/outbox.exceptions.ts` define:

- `OutboxSemanticConflictException extends HttpException` con
  `code: OUTBOX_SEMANTIC_CONFLICT` y status `409`.
- `OutboxPayloadTooLargeException extends BadRequestException` con
  `code: OUTBOX_PAYLOAD_TOO_LARGE` y status `400`.

`ApiExceptionFilter` ya respeta el `code` explícito presente en el
payload de la `HttpException` (verificado por el test del filtro).
Por tanto, el nuevo mapeo no debilita el de `IDEMPOTENCY_KEY_REUSED`
ni `AUDIT_TRANSITION_CONFLICT`.

### 7. Endpoint de smoke `OutboxEchoController`

`apps/api/src/outbox-echo/outbox-echo.controller.ts` se monta
únicamente cuando `process.env.ENABLE_OUTBOX_ECHO === 'true'`.
Patrón equivalente a `IdempotencyEchoController` (DEV-31) y
`AuditEchoController` (DEV-36):

- `POST /api/v1/_outbox/echo` recibe
  `{ organizationId, aggregateType?, aggregateId?, version?, semanticKey,
    eventType?, payload?, forceRollback? }`.
- Construye un `OutboxEventInput` con `aggregateType = "outbox-echo"`
  por defecto y `payload = { message }` cuando se provee.
- Ejecuta la mutación dentro de un `prisma.$transaction` que llama a
  `OutboxService.record`. Si `forceRollback = true`, el handler
  lanza un `Error` **después** del `record` para verificar el
  rollback.
- Devuelve el evento persistido (incluyendo `created: true|false`).
- Permite a las pruebas de integración validar el contrato
  end-to-end sin depender de un servicio de dominio real.

`global-setup.ts` añade `process.env.ENABLE_OUTBOX_ECHO = 'true'`
antes de ejecutar las pruebas de integración.

### 8. DTOs y validación

`apps/api/src/outbox/dto/outbox-event.dto.ts` declara el DTO de
respuesta sin exponer detalles internos:

- `OutboxEventResponseDto` con `id`, `organizationId`, `aggregateType`,
  `aggregateId`, `version`, `eventType`, `correlationId`,
  `causationId`, `payload`, `createdAt`, `created`.

`apps/api/src/outbox/dto/outbox-echo.dto.ts` declara el cuerpo de
entrada del endpoint de smoke, validado con Zod:

- `organizationId` (string, requerido).
- `aggregateType`, `aggregateId` (string, opcional, default
  `"outbox-echo"`).
- `version` (int, opcional, default `1`).
- `semanticKey` (string, requerido, longitud 1-200).
- `eventType` (string, opcional, default `"outbox-echo.create"`).
- `payload` (objeto JSON, opcional, default `{}`).
- `forceRollback` (boolean, opcional, default `false`).

### 9. Pruebas

- **Unitarias**:
  - `outbox-canonical-fingerprint.spec.ts`: huella canónica estable
    frente al orden de claves y sensible a cambios en cualquier
    metadato (`organizationId`, `aggregateType`, `aggregateId`,
    `version`, `semanticKey`, `eventType`, `payload`).
  - `outbox.service.spec.ts`: `record` exitoso (incluye
    `correlationId` propagado y `causationId` opcional), idempotencia
    por `semanticKey`, conflicto por payload distinto,
    `OUTBOX_PAYLOAD_TOO_LARGE` cuando el payload serializado excede el
    límite, y verificación de que la superficie del servicio no
    expone `update`/`delete`/`patch`/`truncate`.
- **Integración** (`apps/api/test/integration/outbox.integration
  .spec.ts`):
  - Usa `DATABASE_URL_TEST` (base aislada de DEV-6).
  - Cubre:
    - Inserción inicial exitosa vía `POST /api/v1/_outbox/echo` con
      `payload` poblado.
    - Reintento con misma `semanticKey` no crea un segundo
      `OutboxEvent` (`created: false` en la segunda llamada).
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
- **Validación de migraciones**: `pnpm db:verify` finaliza con
  código 0.
- **OpenSpec**: `openspec validate dev-32 --strict --no-interactive`
  finaliza con código 0.

## Verification Strategy - Browser E2E: not_required

La superficie del cambio es 100% API HTTP y persistencia PostgreSQL.
El patrón Transactional Outbox es, por definición, lógica de backend:
no existe UI que aporte evidencia adicional sobre la inmutabilidad
del outbox (que se valida mediante el trigger SQL directamente desde
SQL raw en la prueba de integración), ni sobre la idempotencia
(lógica de servicio), ni sobre la atomicidad con la transacción
(rollback verificado en la prueba de integración). Las pruebas de
integración contra una base PostgreSQL real con base aislada
(patrón DEV-6/DEV-31/DEV-36) proporcionan evidencia más rigurosa que
un test E2E de navegador. Por tanto, Browser E2E no aporta valor y
queda fuera del alcance de la verificación.

## Resumen de Archivos a Crear/Modificar

| Archivo | Cambio |
|---|---|
| `apps/api/prisma/schema.prisma` | Añadir modelo `OutboxEvent` |
| `apps/api/prisma/migrations/<timestamp>_add_outbox_event/migration.sql` | Crear migración versionada con tabla, índices, `@@unique`, trigger `BEFORE UPDATE OR DELETE` y `REVOKE UPDATE, DELETE` |
| `apps/api/src/outbox/outbox.constants.ts` | Crear: `OUTBOX_MAX_PAYLOAD_BYTES` y `MAX_SEMANTIC_KEY_LENGTH` |
| `apps/api/src/outbox/outbox-canonical-fingerprint.ts` | Crear utilidad SHA-256 canónica sobre metadatos + payload |
| `apps/api/src/outbox/outbox-canonical-fingerprint.spec.ts` | Crear tests unitarios |
| `apps/api/src/outbox/outbox.exceptions.ts` | Crear `OutboxSemanticConflictException`, `OutboxPayloadTooLargeException` |
| `apps/api/src/outbox/dto/outbox-event.dto.ts` | Crear DTO de respuesta (sin detalles internos sensibles) |
| `apps/api/src/outbox/dto/outbox-echo.dto.ts` | Crear DTO de entrada del endpoint de smoke |
| `apps/api/src/outbox/outbox.service.ts` | Crear `OutboxService` con `record` |
| `apps/api/src/outbox/outbox.service.spec.ts` | Crear tests unitarios del servicio |
| `apps/api/src/outbox/outbox.module.ts` | Crear módulo NestJS |
| `apps/api/src/outbox-echo/outbox-echo.controller.ts` | Crear controlador de smoke (gated por `ENABLE_OUTBOX_ECHO`) |
| `apps/api/src/outbox-echo/outbox-echo.module.ts` | Crear módulo dinámico |
| `apps/api/src/app.module.ts` | Registrar `OutboxModule` y, en test, `OutboxEchoModule.register()` |
| `apps/api/src/common/errors/error-code.enum.ts` | Añadir `OUTBOX_SEMANTIC_CONFLICT` y `OUTBOX_PAYLOAD_TOO_LARGE` |
| `apps/api/src/common/openapi/schemas/error.schema.ts` | Añadir ejemplos `OUTBOX_SEMANTIC_CONFLICT` y `OUTBOX_PAYLOAD_TOO_LARGE` |
| `apps/api/src/common/openapi/swagger.config.ts` | Añadir tag `outbox` |
| `apps/api/test/setup/global-setup.ts` | Activar `ENABLE_OUTBOX_ECHO` |
| `apps/api/test/integration/outbox.integration.spec.ts` | Crear test de integración con base aislada |
| `openspec/changes/dev-32/proposal.md` | Este proposal |
| `openspec/changes/dev-32/specs/transactional-outbox/spec.md` | Spec nuevo |
| `openspec/changes/dev-32/design.md` | Este archivo |
| `openspec/changes/dev-32/tasks.md` | Checklist de implementación |