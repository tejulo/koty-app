# DEV-36 — Diseño Técnico

## Decisiones de Diseño

### 1. Modelo Prisma `AuditEvent`

Se introduce el modelo `AuditEvent` en `apps/api/prisma/schema.prisma` con la
siguiente forma:

```prisma
enum AuditScope {
  PLATFORM
  ORGANIZATION
}

enum AuditActorType {
  USER
  SYSTEM
  API_KEY
  WORKER
}

model AuditEvent {
  id             String         @id @default(uuid())
  scope          AuditScope
  organizationId String?
  actorType      AuditActorType
  actorId        String
  action         String
  entityType     String
  entityId       String
  occurredAt     DateTime       @default(now())
  correlationId  String
  transitionKey  String
  before         Json?
  after          Json?
  createdAt      DateTime       @default(now())

  @@unique([scope, transitionKey])
  @@index([scope, organizationId, occurredAt])
  @@index([actorType, actorId, occurredAt])
  @@index([action, occurredAt])
  @@index([entityType, entityId, occurredAt])
}
```

Notas:

- `transitionKey` se persiste **solo** para arbitraje interno; no se expone en JSON
  ni en respuestas HTTP (ver requisito "transitionKey nunca se devuelve en
  respuestas HTTP").
- `before` y `after` son `Json?`. `null` indica ausencia del dato; `{}` indica
  objeto vacío tras la aplicación de la allowlist.
- Los índices secundarios cubren los filtros del requisito de búsqueda: por
  organización+fecha, por actor+fecha, por acción+fecha y por entidad+fecha.

### 2. Enums `AuditScope` y `AuditActorType`

Los enums se declaran en el mismo `schema.prisma` para que Prisma genere tipos
fuertes y para que la base de datos PostgreSQL aplique el constraint `CHECK` en la
columna. El enum `AuditActorType` se limita explícitamente a `USER`, `SYSTEM`,
`API_KEY` y `WORKER`. Cualquier valor fuera de este conjunto es rechazado por
Prisma antes de llegar a PostgreSQL.

### 3. Migración reproducible con trigger de inmutabilidad

Se crea la migración
`apps/api/prisma/migrations/<timestamp>_add_audit_event/migration.sql` siguiendo
el flujo definido por DEV-6 (`pnpm db:migrate:dev --name add_audit_event`). El
contenido de la migración incluye:

1. `CREATE TYPE "AuditScope" AS ENUM ('PLATFORM', 'ORGANIZATION')`.
2. `CREATE TYPE "AuditActorType" AS ENUM ('USER', 'SYSTEM', 'API_KEY', 'WORKER')`.
3. `CREATE TABLE "AuditEvent"` con sus columnas, PK, índices y `@@unique`.
4. Función `audit_event_block_mutations()` y trigger `audit_event_append_only`
   que se dispara `BEFORE UPDATE OR DELETE` sobre `"AuditEvent"` y lanza
   `EXCEPTION 'AuditEvent is append-only'`.
5. `REVOKE UPDATE, DELETE ON TABLE "AuditEvent" FROM PUBLIC` para reforzar la
   inmutabilidad por permisos.

La migración se aplica con `pnpm db:migrate:deploy` y se verifica con
`pnpm db:verify` (de DEV-6).

### 4. Lista permitida de campos auditables

`apps/api/src/audit/audit.constants.ts` define:

```ts
export const AUDIT_CHANGE_FIELDS: Readonly<Record<string, readonly string[]>> = {
  organization: ['name', 'slug', 'status'],
  invitation: ['email', 'role', 'status', 'expiresAt'],
  membership: ['role', 'status', 'permissions'],
  'audit-echo': ['message'],
};
```

`AuditService.record` exige que cada clave presente en `before` o `after`
pertenezca a la allowlist del `entityType` correspondiente. Si no, lanza
`AuditInvalidFieldException`, mapeada a `400 VALIDATION_ERROR` con `fieldErrors`
indicando la clave problemática (por ejemplo `before.password`).

### 5. Exclusión obligatoria de secretos

`apps/api/src/audit/audit.constants.ts` también exporta:

```ts
export const EXCLUDED_CHANGE_FIELDS = [
  'password',
  'token',
  'session',
  'content',
  'secret',
  'apiKey',
  'accessToken',
  'refreshToken',
  'cookies',
  'body',
  'payload',
] as const;

export function isExcludedChangeField(name: string): boolean {
  const lower = name.toLowerCase();
  if (EXCLUDED_CHANGE_FIELDS.some((e) => e.toLowerCase() === lower)) return true;
  return /(password|token|secret)$/.test(lower);
}
```

`AuditService.record` aplica `isExcludedChangeField` a cada clave y elimina las
coincidencias **antes** de validar contra `AUDIT_CHANGE_FIELDS`. Esto garantiza
que un cambio que intente registrar `password` sea silenciosamente omitido y no
genere error de allowlist. Si tras la exclusión `before`/`after` quedan vacíos,
se persiste el valor como `null` (evento sin cuerpo de cambios).

### 6. Cálculo canónico de `transitionKey`

`apps/api/src/audit/canonical-transition-key.ts` reutiliza `canonicalStringify`
de `apps/api/src/common/idempotency/canonical-fingerprint.ts` (DEV-31):

```ts
import { createHash } from 'node:crypto';
import { canonicalStringify } from '../common/idempotency/canonical-fingerprint';

export function computeCanonicalTransitionKey(input: {
  scope: 'PLATFORM' | 'ORGANIZATION';
  action: string;
  entityType: string;
  entityId: string;
  correlationId: string;
}): string {
  const serialized = canonicalStringify(input);
  return createHash('sha256').update(serialized).digest('hex');
}
```

El resultado es un digest SHA-256 hexadecimal minúsculo de 64 caracteres, estable
frente al orden de las claves (que ya están fijas en `input`).

### 7. Servicio `AuditService`

`apps/api/src/audit/audit.service.ts` define dos métodos públicos:

#### `record(input: AuditEventInput): Promise<AuditEventRecord>`

Pasos:

1. Lee `correlationId` desde el header de request (`x-correlation-id`) o genera
   un UUID v4 si falta. Acepta un override explícito desde el handler.
2. Calcula `transitionKey` con `computeCanonicalTransitionKey`.
3. Aplica la allowlist y la exclusión de secretos a `before`/`after`.
4. Intenta `prisma.auditEvent.create({ data: { ... } })`.
5. Si la inserción viola el `@@unique([scope, transitionKey])`:
   - Lee el registro existente.
   - Si existe y la huella coincide, devuelve el evento con
     `created: false` (idempotente).
   - Si existe con una huella distinta (caso patológico, p.ej. `correlationId`
     mutado manualmente), lanza `AuditTransitionConflictException` mapeada a
     `409 AUDIT_TRANSITION_CONFLICT`.
6. Devuelve el evento persistido sin el campo `transitionKey`.

#### `search(query: AuditSearchQuery): Promise<AuditSearchPage>`

Aplica los filtros validados por Zod:

- `actorType`, `actorId`
- `action`
- `entityType`, `entityId`
- `from`, `to` (rango sobre `occurredAt`)
- `limit` (default 50, máximo 200), `offset` (default 0)
- Aislamiento obligatorio por `organizationId` del actor autenticado. Para
  `scope = 'PLATFORM'`, se omiten los eventos de organización. Para
  `scope = 'ORGANIZATION'`, se fuerza `organizationId` al del actor (salvo
  superadministrador con flag explícito).

Devuelve `{ items, total, limit, offset }`. Nunca expone `transitionKey` ni los
campos excluidos.

### 8. Controlador `AuditController`

`apps/api/src/audit/audit.controller.ts` define:

- `GET /api/v1/audit-events`: query params validados por Zod (entrada de búsqueda
  misma que `search()`). Devuelve `AuditSearchResponseDto`.
- `POST /api/v1/audit-events`: alternativa para filtros complejos. Cuerpo
  validado por Zod con la misma forma. Devuelve el mismo
  `AuditSearchResponseDto`.

Los DTOs (`audit-event.dto.ts`, `audit-search.dto.ts`) usan
`createStrictZodDto` para mantener consistencia con DEV-7. **Ningún DTO declara
`transitionKey`**; los servicios lo filtran explícitamente en la respuesta.

### 9. Endpoint de smoke `AuditEchoController`

`apps/api/src/audit-echo/audit-echo.controller.ts` se monta únicamente cuando
`process.env.ENABLE_AUDIT_ECHO === 'true'`. Patrón equivalente a
`IdempotencyEchoController` (DEV-31):

- `POST /api/v1/_audit/echo` recibe `{ organizationId?, actorId, message? }`.
- Registra un `AuditEvent` con `entityType = "audit-echo"`,
  `action = "audit-echo.create"`, `actorType = "USER"`,
  `before = null`, `after = { message }` cuando hay `message`.
- Devuelve el evento persistido (sin `transitionKey`).
- Permite a las pruebas de integración validar el contrato end-to-end sin
  depender de un servicio de dominio real.

`global-setup.ts` añade `process.env.ENABLE_AUDIT_ECHO = 'true'` antes de
ejecutar las pruebas de integración.

### 10. Pruebas y validación

- **Unitarias** (`apps/api/src/audit/*.spec.ts`):
  - `audit.constants.spec.ts`: `isExcludedChangeField` (case-insensitive,
    sufijo), pertenencia a allowlist.
  - `canonical-transition-key.spec.ts`: SHA-256 estable frente al orden y a
    cambios menores.
  - `audit.service.spec.ts`: cubre `record` (allowlist, exclusión,
    idempotencia, conflicto) y `search` (filtros y aislamiento) con un fake
    Prisma tipado contra el delegate `auditEvent`.
- **Integración** (`apps/api/test/integration/audit.integration.spec.ts`):
  - Usa `DATABASE_URL_TEST` (base aislada de DEV-6).
  - Valida: creación inicial exitosa; reintento con mismo `correlationId` no
    crea un segundo `AuditEvent`; `UPDATE`/`DELETE` directos por la API Prisma
    fallan con error SQL "AuditEvent is append-only"; búsqueda con filtros y
    aislamiento.
- **Validación de migraciones**: `pnpm db:verify` finaliza con código 0.
- **OpenSpec**: `openspec validate dev-36 --strict --no-interactive` finaliza con
  código 0.

## Verification Strategy - Browser E2E: not_required

La superficie del cambio es 100% API HTTP y persistencia PostgreSQL. El endpoint
de búsqueda (`GET /api/v1/audit-events`) se valida con pruebas de integración
contra una base PostgreSQL real con base aislada (patrón DEV-6/DEV-31), lo que
proporciona evidencia más rigurosa que un test E2E de navegador. No existe UI
que aporte evidencia adicional sobre la inmutabilidad (que se valida mediante el
trigger SQL directamente desde SQL raw en la prueba de integración) ni sobre la
idempotencia (que es lógica de servicio). Por tanto, Browser E2E no aporta
valor y queda fuera del alcance de la verificación.

## Resumen de Archivos a Crear/Modificar

| Archivo | Cambio |
|---|---|
| `apps/api/prisma/schema.prisma` | Añadir enums `AuditScope`, `AuditActorType` y modelo `AuditEvent` |
| `apps/api/prisma/migrations/<timestamp>_add_audit_event/migration.sql` | Crear migración versionada con tabla, enums, índices, `@@unique`, trigger `BEFORE UPDATE OR DELETE` y `REVOKE UPDATE, DELETE` |
| `apps/api/src/audit/audit.constants.ts` | Crear: `AUDIT_CHANGE_FIELDS`, `EXCLUDED_CHANGE_FIELDS`, `isExcludedChangeField` |
| `apps/api/src/audit/canonical-transition-key.ts` | Crear utilidad SHA-256 canónica |
| `apps/api/src/audit/canonical-transition-key.spec.ts` | Crear tests unitarios |
| `apps/api/src/audit/audit.constants.spec.ts` | Crear tests unitarios de allowlist y exclusión |
| `apps/api/src/audit/audit.exceptions.ts` | Crear `AuditInvalidFieldException`, `AuditTransitionConflictException` |
| `apps/api/src/audit/dto/audit-event.dto.ts` | Crear DTO de respuesta (sin `transitionKey`) |
| `apps/api/src/audit/dto/audit-search.dto.ts` | Crear DTOs de query y de respuesta paginada |
| `apps/api/src/audit/audit.service.ts` | Crear `AuditService` con `record` y `search` |
| `apps/api/src/audit/audit.service.spec.ts` | Crear tests unitarios del servicio |
| `apps/api/src/audit/audit.controller.ts` | Crear `AuditController` (`GET`, `POST`) |
| `apps/api/src/audit/audit.module.ts` | Crear módulo NestJS |
| `apps/api/src/audit-echo/audit-echo.controller.ts` | Crear controlador de smoke (gated por `ENABLE_AUDIT_ECHO`) |
| `apps/api/src/audit-echo/audit-echo.module.ts` | Crear módulo dinámico |
| `apps/api/src/app.module.ts` | Registrar `AuditModule` y, en test, `AuditEchoModule.register()` |
| `apps/api/src/common/errors/error-code.enum.ts` | Añadir `AUDIT_TRANSITION_CONFLICT` y `AUDIT_INVALID_FIELD` |
| `apps/api/src/common/errors/api-exception.filter.ts` | Asegurar mapeo del código 409 al nuevo `ErrorCode` (sin debilitar el mapeo de `IDEMPOTENCY_KEY_REUSED`) |
| `apps/api/src/common/openapi/schemas/error.schema.ts` | Añadir ejemplos `AUDIT_INVALID_FIELD` y `AUDIT_TRANSITION_CONFLICT` |
| `apps/api/src/common/openapi/swagger.config.ts` | Añadir tag `audit` y parámetros de búsqueda |
| `apps/api/test/setup/global-setup.ts` | Activar `ENABLE_AUDIT_ECHO` |
| `apps/api/test/integration/audit.integration.spec.ts` | Crear test de integración con base aislada |
| `apps/api/src/main.ts` | Mantener la validación de `DATABASE_URL` (sin tocar lo existente) |
| `openspec/changes/dev-36/proposal.md` | Este proposal |
| `openspec/changes/dev-36/specs/audit-append-only/spec.md` | Spec nuevo |
| `openspec/changes/dev-36/design.md` | Este archivo |
| `openspec/changes/dev-36/tasks.md` | Checklist de implementación |
