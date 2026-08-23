# API v1 — Documentación OpenAPI

## ADDED Requirements

### Requirement: Documentación OpenAPI accesible

El sistema SHALL expose OpenAPI documentation via Swagger UI at `/api/docs`.

#### Scenario: Swagger UI accesible
- GIVEN la aplicación NestJS configurada con Swagger
- WHEN se accede a `GET /api/docs`
- THEN se muestra la interfaz Swagger UI
- AND se puede explorar y probar los endpoints documentados

#### Scenario: Endpoint de salud documentado
- GIVEN el endpoint `GET /api/v1/health`
- AND la documentación OpenAPI configurada
- THEN la especificación OpenAPI incluye:
  - Método: GET
  - Ruta: `/api/v1/health`
  - Respuestas:
    - 200: `{ "status": "ok", "timestamp": "string", "correlationId": "string" }`
    - 500: Error contract con `code`, `message`, `fieldErrors`, `correlationId`

### Requirement: Esquema de error en OpenAPI

El sistema SHALL define ErrorResponse schema in OpenAPI components for consistent documentation.

#### Scenario: Componente de esquema de error disponible
- GIVEN la configuración de Swagger en NestJS
- THEN existe un componente `$ref: '#/components/schemas/ErrorResponse'`
- AND su estructura es:
```yaml
ErrorResponse:
  type: object
  required:
    - code
    - message
    - fieldErrors
    - correlationId
  properties:
    code:
      type: string
      description: Código de error predefinido
    message:
      type: string
      description: Mensaje legible del error
    fieldErrors:
      type: array
      items:
        $ref: '#/components/schemas/FieldError'
    correlationId:
      type: string
      format: uuid
      description: Identificador de correlación de la solicitud
```

### Requirement: Health Check endpoint

El sistema SHALL provide a health check endpoint at `/api/v1/health` as demonstration of the base contract.

#### Scenario: Health check exitoso
- GIVEN una solicitud a `GET /api/v1/health`
- WHEN no hay errores internos
- THEN se retorna HTTP 200
- AND el cuerpo es:
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "correlationId": "generated-uuid"
}
```

### Requirement: OpenAPI JSON endpoint

El sistema SHALL expose OpenAPI specification in JSON format at `/api/docs-json`.

#### Scenario: especificación JSON accesible
- GIVEN la aplicación configurada
- WHEN se accede a `GET /api/docs-json`
- THEN se retorna la especificación OpenAPI en formato JSON
- AND puede ser consumida por herramientas de generación de código cliente
