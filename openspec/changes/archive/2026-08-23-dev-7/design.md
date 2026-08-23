# Design: DEV-7 — Contrato Base API v1

## Decisiones Técnicas

### DT-1: Prefijo de rutas /api/v1

**Decisión:** Usar `setGlobalPrefix` de NestJS para aplicar `/api/v1` a todos los endpoints.

**Justificación:** Es el mecanismo nativo de NestJS, centralizado y simple. Evita duplicar el prefijo en cada controlador.

**Implementación:**
```typescript
// apps/api/src/main.ts
app.setGlobalPrefix(
  process.env.API_VERSION_PREFIX || 'api/v1',
  { exclude: ['/api/docs', '/api/docs-json'] }
);
```

**Exclusiones:** Los endpoints de documentación Swagger (`/api/docs`, `/api/docs-json`) quedan fuera del prefijo para mantener URLs canónicas de documentación.

---

### DT-2: Formato de correlationId

**Decisión:** Usar UUID v4 para el `correlationId`.

**Justificación:** 
- UUID v4 es ampliamente soportado, no requiere coordinación central.
- Formato estándar de industria para trazabilidad (AWS, Azure, Google Cloud).
- Longitud suficiente (36 caracteres) para garantizar unicidad global.
- La expresión "seguro" se interpreta como: no predecible (random) y globalmente único.

**Implementación:**
```typescript
// apps/api/src/common/middleware/correlation-id.middleware.ts
import { randomUUID } from 'crypto';
import type { NestMiddleware } from '@nestjs/common';

export class CorrelationIdMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    const correlationId = (req.headers['x-correlation-id'] as string) || randomUUID();
    res.setHeader('x-correlation-id', correlationId);
    req.headers['x-correlation-id'] = correlationId;
    next();
  }
}
```

**Propagación:** Se almacena en un `InjectionToken` (`CORRELATION_ID`) para acceso en servicios, guards e interceptors.

---

### DT-3: Validación Zod Estricta

**Decisión:** Usar Zod con `strict()` mode y `z.union` para validar body, query y params por separado.

**Justificación:**
- Zod ofrece validación de runtime con tipado estático inferido.
- El modo `strict()` rechaza claves no definidas en el esquema.
- Se integra bien con decorators de NestJS usando `createZodDto`.

**Dependencias requeridas:**
```json
{
  "zod": "^3.22.0",
  "nestjs-zod": "^3.0.0"
}
```

**Implementación del DTO:**
```typescript
// apps/api/src/common/validation/create-zod-dto.ts
import { createZodDto } from 'nestjs-zod';
import { ZodSchema, ZodError } from 'zod';

export function createStrictZodDto<T extends ZodSchema>(schema: T) {
  return createZodDto(schema.strict());
}
```

**Decorator de validación:**
```typescript
// apps/api/src/common/validation/validate-request.decorator.ts
import { applyDecorators, UseInterceptor } from '@nestjs/common';
import { ZodValidationInterceptor } from './zod-validation.interceptor';

export function ValidateRequest(schema: ZodSchema) {
  return applyDecorators(UseInterceptor(new ZodValidationInterceptor(schema)));
}
```

---

### DT-4: Contrato de Error Estandarizado

**Decisión:** Definir interfaz `ApiError` y crear `ApiExceptionFilter` global.

**Justificación:** Centraliza el manejo de errores y garantiza formato consistente.

**Esquema de error:**
```typescript
// apps/api/src/common/errors/error-response.interface.ts
export interface FieldError {
  field: string;
  message: string;
}

export interface ErrorResponse {
  code: string;
  message: string;
  fieldErrors: FieldError[];
  correlationId: string;
}

export enum ErrorCode {
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  NOT_FOUND = 'NOT_FOUND',
  INTERNAL_ERROR = 'INTERNAL_ERROR',
  BAD_REQUEST = 'BAD_REQUEST',
  UNAUTHORIZED = 'UNAUTHORIZED',
}
```

**Códigos HTTP asociados:**
| Código | HTTP Status |
|--------|-------------|
| VALIDATION_ERROR | 400 |
| BAD_REQUEST | 400 |
| NOT_FOUND | 404 |
| UNAUTHORIZED | 401 |
| INTERNAL_ERROR | 500 |

**Filtro de excepciones:**
```typescript
// apps/api/src/common/errors/api-exception.filter.ts
@Catch()
export class ApiExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse();
    const correlationId = ctx.getRequest().headers['x-correlation-id'];
    
    // Construir ErrorResponse según tipo de excepción
    response.status(httpStatus).json({
      code: errorCode,
      message: humanMessage,
      fieldErrors: fieldErrors,
      correlationId,
    });
  }
}
```

---

### DT-5: Configuración Swagger/OpenAPI

**Decisión:** Usar `@nestjs/swagger` con configuración centralizada.

**Justificación:** Es el paquete oficial de NestJS para Swagger, con soporte para decoradores y componentes reutilizables.

**Dependencias requeridas:**
```json
{
  "@nestjs/swagger": "^7.0.0",
  "swagger-ui-express": "^5.0.0"
}
```

**Configuración:**
```typescript
// apps/api/src/main.ts
const document = SwaggerModule.createDocument(app, swaggerConfig);
SwaggerModule.setup('api/docs', app, document);
```

**Esquema global de error:**
```typescript
// apps/api/src/common/openapi/schemas/error.schema.ts
export const errorResponseSchema = {
  type: 'object',
  required: ['code', 'message', 'fieldErrors', 'correlationId'],
  properties: {
    code: { type: 'string' },
    message: { type: 'string' },
    fieldErrors: { type: 'array', items: { $ref: '#/components/schemas/FieldError' } },
    correlationId: { type: 'string', format: 'uuid' },
  },
};
```

---

### DT-6: Estructura de archivos

```
apps/api/src/
├── main.ts                          # Configuración global, Swagger, prefix
├── app.module.ts
├── common/
│   ├── errors/
│   │   ├── error-response.interface.ts
│   │   ├── error-code.enum.ts
│   │   └── api-exception.filter.ts
│   ├── middleware/
│   │   └── correlation-id.middleware.ts
│   ├── interceptors/
│   │   └── correlation-id-response.interceptor.ts
│   ├── openapi/
│   │   ├── schemas/
│   │   │   ├── error.schema.ts
│   │   │   └── health.schema.ts
│   │   └── swagger.config.ts
│   └── validation/
│       ├── create-zod-dto.ts
│       └── zod-validation.interceptor.ts
└── health/
    ├── health.controller.ts
    ├── health.service.ts
    └── dto/
        └── health-response.dto.ts
```

---

### DT-7: Dependencias adicionales

```json
{
  "dependencies": {
    "zod": "^3.22.4",
    "nestjs-zod": "^3.0.0",
    "@nestjs/swagger": "^7.3.1",
    "swagger-ui-express": "^5.0.0"
  }
}
```

---

## Resumen de Decisiones

| ID | Descripción | Alternativas descartadas |
|----|-------------|-------------------------|
| DT-1 | Global prefix `/api/v1` | Prefijo manual por controlador (error-prone) |
| DT-2 | UUID v4 para correlationId | Nanoid (menos estándar), CUID (no random) |
| DT-3 | Zod strict mode | class-validator (menos flexible), Valibot (ecosistema menor) |
| DT-4 | Exception filter global | Manejo por controlador (no centralizado) |
| DT-5 | @nestjs/swagger | Manual OpenAPI JSON (tedioso) |
| DT-6 | Estructura flat con common/ | Estructura por features (premature) |
