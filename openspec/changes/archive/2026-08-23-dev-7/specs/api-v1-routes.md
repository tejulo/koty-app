# API v1 — Rutas Base

## ADDED Requirements

### Requirement: Prefijo de rutas /api/v1

El sistema SHALL publish all API v1 endpoints under the `/api/v1` prefix.

#### Scenario: Endpoint responde bajo /api/v1
- GIVEN una aplicación NestJS configurada
- WHEN se define un endpoint `health` en el controlador
- THEN la ruta accesible es `GET /api/v1/health`
- AND la respuesta es `{ status: "ok", timestamp: "<ISO-8601>" }`

#### Scenario: Prefijo global aplicado a todos los endpoints
- GIVEN una solicitud a `GET /api/v1/health`
- AND una solicitud a `POST /api/v1/otro`
- THEN ambos endpoints comparten el prefijo `/api/v1`
- AND no existen endpoints fuera de `/api/v1` en la API v1

### Requirement: Configuración del prefijo de versión

El sistema SHALL allow configuration of the version prefix via environment variables.

#### Scenario: Configuración mediante variable de entorno
- GIVEN la variable de entorno `API_VERSION_PREFIX` configurada como `api/v1`
- WHEN se inicia la aplicación
- THEN todos los endpoints se publican bajo `/api/v1`
- AND si `API_VERSION_PREFIX` no está definida, se usa el valor por defecto `/api/v1`

### Requirement: Rechazo de solicitudes fuera del prefijo /api/v1

El sistema SHALL reject requests to endpoints outside /api/v1 prefix.

#### Scenario: Requests outside /api/v1 return 404
- GIVEN una solicitud a `GET /health` (sin prefijo)
- WHEN la solicitud llega al servidor
- THEN se retorna HTTP 404 Not Found
- OR el endpoint no está expuesto sin el prefijo de versión
