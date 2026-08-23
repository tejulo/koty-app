# Proposal: DEV-7 — Establecer el contrato base de la API v1

## Problema

La API carece de un contrato base unificado para la versión v1. Los endpoints no siguen una estructura de rutas consistente, no existe validación estricta de entradas ni una estructura de errores definida. Esto genera:

- Respuestas inconsistentes entre endpoints.
- Errores difícilmente consumibles por clientes.
- Sin trazabilidad entre solicitudes mediante identificadores de correlación.
- Ausencia de documentación OpenAPI funcional.

## Objetivo

Establecer el contrato base de la API v1 que garantice:

1. Rutas consistentes bajo `/api/v1`.
2. Validación estricta de entradas con Zod (rechazo de campos desconocidos).
3. Estructura de errores predecible con `code`, `message`, `fieldErrors`, `correlationId`.
4. Identificador de correlación (`correlationId`) generado para cada solicitud.
5. Documentación OpenAPI básica con endpoint de ejemplo.

## Alcance

- Prefijo de rutas `/api/v1` configurado globalmente.
- Middleware de correlación que genera y adjunta `correlationId` a cada solicitud.
- Interceptor global de respuestas que incluye `correlationId`.
- Middleware/Guard de validación Zod estricto para inputs.
- Filtro global de excepciones que normaliza errores al contrato definido.
- Esquema de error estandarizado.
- Endpoint de ejemplo `/api/v1/health` con documentación OpenAPI.
- Documentación OpenAPI (Swagger) accesible en `/api/docs`.

## Fuera de Alcance

- Implementación de autenticación/autorización.
- Rate limiting o throttling.
- Logging estructurado detallado.
- Versionado de esquemas de respuesta.
- Migración de endpoints existentes fuera de `/api/v1`.

## Impacto Esperado

- Base técnica sólida para todos los endpoints futuros de la API v1.
- Experiencia de desarrollo consistente con errores predecibles.
- Trazabilidad de solicitudes mediante `correlationId`.
- Documentación automática y funcional via OpenAPI/Swagger.
- Reducción de errores de validación en producción.
