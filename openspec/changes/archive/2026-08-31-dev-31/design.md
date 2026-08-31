# DEV-31 — Diseño Técnico

## Decisiones de Diseño

### 1. Transporte de la clave de idempotencia

Se utiliza la cabecera HTTP `Idempotency-Key` (string opaca) en los endpoints de comandos
sensibles. Razones:

- Es la convención más extendida (RFC drafts previos sobre idempotency keys, así como
  convenciones adoptadas por Stripe, PayPal, AWS, etc.).
- Permite añadir idempotencia **sin cambiar las rutas** ni romper a clientes existentes:
  los clientes que no envíen la cabecera siguen operando como hasta ahora.
- Permite limitar el alcance de la cabecera por endpoint, no de forma global, mediante el
  guard/interceptor que se describe más adelante.

**Restricciones sobre la cabecera:**

- Si la cabecera no está presente, el endpoint se procesa sin idempotencia (igual que hoy).
- Si está presente y vacía, se trata como ausente.
- Si está presente y excede 128 caracteres (o tiene menos de 8), se rechaza con
  `400 VALIDATION_ERROR` (campo `idempotencyKey`).

### 2. Cálculo del scope y de la huella canónica

**Scope** (componente de la unicidad):

```
scope = `${organizationId}:${actorId}:${commandType}`
```

Los tres valores deben estar disponibles antes de calcular la huella:

- `organizationId`: proviene del contexto de la request. Para endpoints que aún no reciben
  organización en el path, se infiere del token de autenticación (o, si no hay token, se
  rechaza con `401 UNAUTHORIZED`).
- `actorId`: identificador del sujeto autenticado. Si la request no está autenticada, se
  rechaza con `401 UNAUTHORIZED`.
- `commandType`: literal controlado por el servidor, declarado por cada endpoint que
  participa en el contrato de idempotencia.

**Huella canónica** (`requestFingerprint`):

- Se aplica sobre el `body` de la request **después** de la validación Zod estricta.
- Pasos:
  1. Tomar el objeto validado como `Record<string, unknown>`.
  2. Eliminar campos que no forman parte del efecto del comando (por ejemplo, metadatos
     puramente cosméticos definidos por una lista de claves excluidas por endpoint).
  3. Ordenar las claves de cada objeto de forma recursiva (los arrays preservan su orden).
  4. Serializar a JSON sin espacios adicionales.
  5. Calcular `sha256(serialized)` y devolver el resultado en hexadecimal minúsculas.

La función `computeCanonicalFingerprint(input: unknown): string` vive en
`apps/api/src/common/idempotency/canonical-fingerprint.ts` y se exporta para ser
reutilizada en los handlers y en los tests.

### 3. Modelo de datos: `IdempotencyRecord`

Se añade un nuevo modelo al `schema.prisma`:

```prisma
model IdempotencyRecord {
  id                 String   @id @default(uuid())
  organizationId     String
  actorId            String
  commandType        String
  idempotencyKey     String
  requestFingerprint String
  responseStatus     Int
  responseBody       Json
  createdAt          DateTime @default(now())
  updatedAt          DateTime @updatedAt

  @@unique([organizationId, actorId, commandType, idempotencyKey])
  @@index([organizationId, commandType])
}
```

Notas:

- El cliente Prisma no se sustituye en los tests de integración: el nuevo modelo se cubre
  por tests de integración que usan PostgreSQL real (DEV-6).
- No se almacena el cuerpo crudo del request, solo la huella. Esto evita filtraciones y
  reduce el tamaño de los registros.
- No se define TTL. La tabla crece de forma monótona. Se documenta como mejora futura.

### 4. Servicio de idempotencia

Se introduce `IdempotencyService` en
`apps/api/src/common/idempotency/idempotency.service.ts`. Su responsabilidad es:

1. **Resolver si la clave ya tiene un resultado confirmado:**
   - Buscar por `(organizationId, actorId, commandType, idempotencyKey)`.
   - Si existe, comparar `requestFingerprint`.
     - Iguales → devolver el resultado confirmado.
     - Distintos → lanzar `IdempotencyKeyReusedException` (mapeada a
       `409 IDEMPOTENCY_KEY_REUSED`).

2. **Ejecutar el comando bajo un "resultado provisional":**
   - El handler del comando ejecuta su lógica de negocio bajo una transacción Prisma.
   - Si la transacción **hace commit** con éxito, el handler llama a
     `IdempotencyService.commit({ scope, key, fingerprint, status, body })` que
     inserta el `IdempotencyRecord`. Si la inserción viola el constraint único y el
     `requestFingerprint` coincide, se considera idempotente (otro nodo ganó la carrera)
     y se devuelve el resultado ya almacenado.
   - Si la transacción **no llega a commit** (validación de dominio, error de negocio,
     violación de restricción natural), el handler no llama a `commit`. La clave no se
     consume y el cliente puede reintentar con una clave nueva.

3. **Manejar la concurrencia:**
   - El constraint único `(organizationId, actorId, commandType, idempotencyKey)` en la
     base de datos es el mecanismo de arbitraje entre múltiples instancias de la API.
   - En caso de carrera, el ganador inserta; el perdedor recibe el resultado del ganador
     si su huella coincide, o `409 IDEMPOTENCY_KEY_REUSED` si no coincide.

### 5. Extensión del contrato de errores

Se añade el código `IDEMPOTENCY_KEY_REUSED` al enum `ErrorCode` en
`apps/api/src/common/errors/error-code.enum.ts`.

```ts
export enum ErrorCode {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  BAD_REQUEST = 'BAD_REQUEST',
  UNAUTHORIZED = 'UNAUTHORIZED',
  IDEMPOTENCY_KEY_REUSED = 'IDEMPOTENCY_KEY_REUSED',
}
```

`ApiExceptionFilter` se actualiza para mapear el código a HTTP `409 Conflict`:

```ts
const CONFLICT = 409;
...
else if (httpStatus === CONFLICT) {
  code = ErrorCode.IDEMPOTENCY_KEY_REUSED;
}
```

El filtro mantiene la estructura `ErrorResponse` (`code`, `message`, `fieldErrors`,
`correlationId`) ya especificada por DEV-7.

### 6. Integración con handlers existentes

Para evitar acoplar `IdempotencyService` a cada caso de uso particular, se opta por un
patrón explícito en cada handler:

```ts
async createOrganization(req, body) {
  const scope = {
    organizationId: req.auth.organizationId ?? req.body.organizationId,
    actorId: req.auth.actorId,
    commandType: 'create-organization',
  };

  return this.idempotency.run({
    scope,
    key: req.headers['idempotency-key'],
    request: body,
    execute: async () => this.organizationsService.create(body),
  });
}
```

El método `IdempotencyService.run` se encarga de:

- Calcular la huella canónica del `request`.
- Buscar un `IdempotencyRecord` existente.
- Si existe con la misma huella, devolver el resultado confirmado.
- Si existe con huella distinta, lanzar `IdempotencyKeyReusedException`.
- Si no existe, ejecutar `execute()` dentro de una transacción.
- Si `execute()` hace commit, llamar a `commit()` para persistir el `IdempotencyRecord`.
- Si `execute()` lanza, propagar la excepción sin persistir nada.

Este patrón se aplica de forma manual en cada handler de comando sensible. No se introduce
un interceptor global, porque queremos conservar el control explícito sobre qué endpoints
participan y bajo qué `commandType`.

### 7. Endpoints que adoptan idempotencia en este cambio

- `POST /api/v1/organizations` → `commandType = 'create-organization'`
- `POST /api/v1/invitations` → `commandType = 'create-invitation'`
- `POST /api/v1/invitations/:id/accept` → `commandType = 'accept-invitation'`

Estos endpoints son declarativos en este cambio. La implementación concreta de los
servicios de dominio queda fuera del alcance (corresponde a tickets posteriores del
Incremento 0). Para que el contrato sea verificable, el cambio introduce:

- Un endpoint de smoke `POST /api/v1/_idempotency/echo` (solo bajo
  `process.env.ENABLE_IDEMPOTENCY_ECHO === 'true'`) que ejecuta un comando controlado
  (`commandType = 'echo'` o `commandType = 'fail'` según el payload) y devuelve el cuerpo
  recibido. Permite verificar el contrato HTTP end-to-end sin acoplarlo a
  organización/invitación, que son funcionalidades aún no implementadas.
- Tests de integración que cubren:
  - Reintento con misma clave y misma huella → mismo resultado.
  - Reintento con misma clave y huella distinta → `409 IDEMPOTENCY_KEY_REUSED`.
  - Comando rechazado antes del commit → no consume la clave.
  - Comando rechazado por restricción de dominio → no consume la clave.

### 8. Documentación OpenAPI

Se documenta en Swagger:

- La cabecera `Idempotency-Key` como parámetro opcional para los endpoints que la
  soportan.
- El nuevo código `IDEMPOTENCY_KEY_REUSED` en el schema de errores.
- Un ejemplo de respuesta `409` con la estructura `ErrorResponse`.

### 9. Migración reproducible

Se crea la migración
`apps/api/prisma/migrations/<timestamp>_add_idempotency_record/migration.sql`
siguiendo el flujo definido por DEV-6:

- `pnpm db:migrate:dev --name add_idempotency_record` para crear la migración.
- La migración queda versionada y se aplica con `pnpm db:migrate:deploy`.
- `pnpm db:verify` confirma que no hay drift entre `schema.prisma` y el historial.

### 10. Pruebas

- **Unitarias**:
  - `canonical-fingerprint.spec.ts`: verifica que dos objetos con distinto orden de claves
    producen la misma huella, y que dos objetos con un valor distinto producen huellas
    distintas.
  - `idempotency.service.spec.ts`: cubre la lógica de `run()` con un repositorio Prisma
    mockeado a nivel de servicio (no a nivel de cliente Prisma).
  - `api-exception.filter.spec.ts`: añade el escenario `409 → IDEMPOTENCY_KEY_REUSED`.

- **Integración** (`apps/api/test/integration/idempotency.integration.spec.ts`):
  - Usa `DATABASE_URL_TEST` (base aislada creada por el `globalSetup` de DEV-6).
  - Verifica el ciclo completo contra PostgreSQL real:
    - Reintento con misma clave y misma huella → mismo resultado y un solo `IdempotencyRecord`.
    - Reintento con misma clave y huella distinta → `409 IDEMPOTENCY_KEY_REUSED` y ningún
      nuevo `IdempotencyRecord`.
    - Comando rechazado antes del commit → no se crea `IdempotencyRecord`.
    - Comando rechazado por validación → no se crea `IdempotencyRecord`.

## Verification Strategy - Browser E2E: not_required

El contrato de idempotencia es un comportamiento de **API HTTP** verificable de forma
exhaustiva mediante herramientas de línea (curl, Vitest) y pruebas de integración contra
PostgreSQL real. No existe UI que aporte evidencia adicional sobre la semántica de claves,
huellas y conflictos. Por lo tanto, la verificación Browser E2E no es necesaria: el flujo
queda cubierto por las pruebas de integración y los specs unitarios.

## Resumen de Archivos a Crear/Modificar

| Archivo | Cambio |
|---|---|
| `apps/api/prisma/schema.prisma` | Añadir modelo `IdempotencyRecord` |
| `apps/api/prisma/migrations/<timestamp>_add_idempotency_record/migration.sql` | Migración versionada |
| `apps/api/src/common/errors/error-code.enum.ts` | Añadir `IDEMPOTENCY_KEY_REUSED` |
| `apps/api/src/common/errors/error-response.interface.ts` | Sin cambios estructurales |
| `apps/api/src/common/errors/api-exception.filter.ts` | Mapear `409 → IDEMPOTENCY_KEY_REUSED` |
| `apps/api/src/common/errors/api-exception.filter.spec.ts` | Añadir escenario `409` |
| `apps/api/src/common/idempotency/canonical-fingerprint.ts` | Nueva utilidad de huella |
| `apps/api/src/common/idempotency/canonical-fingerprint.spec.ts` | Tests unitarios |
| `apps/api/src/common/idempotency/idempotency.service.ts` | Nuevo servicio |
| `apps/api/src/common/idempotency/idempotency.service.spec.ts` | Tests unitarios |
| `apps/api/src/common/idempotency/idempotency.module.ts` | Módulo NestJS |
| `apps/api/src/common/idempotency/idempotency.exceptions.ts` | Excepciones específicas |
| `apps/api/src/idempotency-echo/idempotency-echo.controller.ts` | Endpoint de smoke (test) |
| `apps/api/src/idempotency-echo/idempotency-echo.module.ts` | Módulo del endpoint de smoke |
| `apps/api/src/app.module.ts` | Registrar `IdempotencyModule` y (en test) `IdempotencyEchoModule` |
| `apps/api/src/common/openapi/swagger.config.ts` | Parámetro reutilizable `Idempotency-Key` |
| `apps/api/src/common/openapi/schemas/error.schema.ts` | Ejemplo `IDEMPOTENCY_KEY_REUSED` |
| `apps/api/test/setup/global-setup.ts` | Activar `ENABLE_IDEMPOTENCY_ECHO` |
| `openspec/changes/dev-31/specs/api-v1-idempotency/spec.md` | Spec nuevo |
| `openspec/changes/dev-31/proposal.md` | Este proposal |
| `openspec/changes/dev-31/design.md` | Este archivo |
| `openspec/changes/dev-31/tasks.md` | Checklist de implementación |
