# Tasks: DEV-7 — Contrato Base API v1

## Implementación del Contrato Base

- [x] **apps/api/package.json** — Agregar dependencias: `zod`, `nestjs-zod`, `@nestjs/swagger`, `swagger-ui-express`
  - Cambios: Añadir nuevas dependencias al bloque `dependencies`
  - Tests: Verificar instalación con `pnpm install`

- [x] **apps/api/src/main.ts** — Configurar prefijos globales, Swagger y filtros globales
  - Cambios: Importar SwaggerModule, DocumentBuilder, setGlobalPrefix, aplicar ApiExceptionFilter global
  - Tests: Verificar que `/api/v1/health` responde correctamente

- [x] **apps/api/src/common/errors/error-code.enum.ts** — Crear enum de códigos de error
  - Cambios: Crear archivo con `VALIDATION_ERROR`, `NOT_FOUND`, `INTERNAL_ERROR`, `BAD_REQUEST`, `UNAUTHORIZED`
  - Tests: Unit test del enum

- [x] **apps/api/src/common/errors/error-response.interface.ts** — Crear interfaces de error
  - Cambios: Crear `FieldError`, `ErrorResponse` interfaces
  - Tests: Unit test de tipos

- [x] **apps/api/src/common/errors/api-exception.filter.ts** — Crear filtro de excepciones global
  - Cambios: Implementar `ExceptionFilter` que normaliza todos los errores al contrato `ErrorResponse`
  - Tests: Test de integración verificando formato de respuesta para errores 400, 404, 500

- [x] **apps/api/src/common/middleware/correlation-id.middleware.ts** — Crear middleware de correlación
  - Cambios: Generar UUID v4 si no existe, usar header del cliente si existe, adjuntar a headers
  - Tests: Unit test verificando generación y propagación de correlationId

- [x] **apps/api/src/common/interceptors/correlation-id-response.interceptor.ts** — Crear interceptor de respuesta
  - Cambios: Incluir `correlationId` en el cuerpo de todas las respuestas exitosas
  - Tests: Integration test verificando `correlationId` en respuestas

- [x] **apps/api/src/common/openapi/schemas/error.schema.ts** — Crear esquema OpenAPI de error
  - Cambios: Definir `ErrorResponseSchema` y `FieldErrorSchema` para Swagger
  - Tests: Verificar documentación en `/api/docs`

- [x] **apps/api/src/common/openapi/schemas/health.schema.ts** — Crear esquema OpenAPI de health
  - Cambios: Definir `HealthResponseSchema` con status, timestamp, correlationId
  - Tests: Verificar documentación en `/api/docs`

- [x] **apps/api/src/common/openapi/swagger.config.ts** — Crear configuración centralizada de Swagger
  - Cambios: Configurar título, descripción, versión, tags, esquemas globales
  - Tests: Verificar que Swagger UI carga correctamente

- [x] **apps/api/src/common/validation/create-zod-dto.ts** — Crear helper para DTOs Zod estrictos
  - Cambios: Exportar función helper o documentación de uso
  - Tests: Unit test del helper

- [x] **apps/api/src/common/validation/zod-validation.interceptor.ts** — Crear interceptor de validación Zod
  - Cambios: Implementar interceptor que valida request contra esquema Zod y lanza errores de validación
  - Tests: Test verificando rechazo de campos desconocidos

- [x] **apps/api/src/health/dto/health-response.dto.ts** — Crear DTO de respuesta de health
  - Cambios: Definir respuesta con status, timestamp, correlationId
  - Tests: Unit test del DTO

- [x] **apps/api/src/health/health.controller.ts** — Crear controlador de health
  - Cambios: Definir `GET /api/v1/health` con documentación OpenAPI
  - Tests: Test del endpoint verificando respuesta y documentación

- [x] **apps/api/src/health/health.service.ts** — Crear servicio de health
  - Cambios: Implementar lógica de health check
  - Tests: Unit test del servicio

- [x] **apps/api/src/health/health.module.ts** — Crear módulo de health
  - Cambios: Registrar controller y servicio
  - Tests: Verificar que el módulo se carga correctamente

- [x] **apps/api/src/app.module.ts** — Registrar módulos y middleware globales
  - Cambios: Importar HealthModule, registrar CorrelationIdMiddleware globalmente
  - Tests: Verificar que la aplicación inicia correctamente

## Verificación

- [x] **apps/api/src/common/errors/api-exception.filter.spec.ts** — Tests de integración del filtro de excepciones
  - Verificar formato de error para cada código
  - Verificar que `correlationId` está presente

- [x] **apps/api/src/common/middleware/correlation-id.middleware.spec.ts** — Tests del middleware
  - Verificar generación de UUID cuando no hay header
  - Verificar uso de header del cliente cuando existe
  - Verificar que el header se adjunta a la respuesta

- [x] **apps/api/src/health/health.controller.spec.ts** — Tests del endpoint health
  - Verificar respuesta HTTP 200
  - Verificar estructura de respuesta
  - Verificar que `correlationId` está en headers y cuerpo

- [x] **apps/api/src/common/validation/zod-validation.interceptor.spec.ts** — Tests de validación
  - Verificar que campos válidos pasan
  - Verificar que campos desconocidos son rechazados
  - Verificar mensaje de error específico por campo

## Documentación

- [x] **README.md** — Actualizar documentación del API
  - Agregar sección sobre endpoints disponibles bajo `/api/v1`
  - Documentar formato de errores
  - Agregar enlace a Swagger UI en `/api/docs`

## Criterios de Aceptación Verificables

1. ✅ `GET /api/v1/health` responde con status 200 y cuerpo con `status`, `timestamp`, `correlationId`
2. ✅ Header `x-correlation-id` presente en todas las respuestas
3. ✅ Solicitud con campos desconocidos retorna 400 con `VALIDATION_ERROR`
4. ✅ Error response incluye `code`, `message`, `fieldErrors`, `correlationId`
5. ✅ Swagger UI accesible en `/api/docs`
6. ✅ Especificación JSON en `/api/docs-json`
7. ✅ Endpoint health documentado en OpenAPI con respuestas 200 y 500
