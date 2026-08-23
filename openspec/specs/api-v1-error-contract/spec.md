# api-v1-error-contract Specification

## Purpose
TBD - created by archiving change dev-7. Update Purpose after archive.
## Requirements
### Requirement: Estructura de error estandarizada

El sistema SHALL return errors in a standardized JSON structure with code, message, fieldErrors, and correlationId.

#### Scenario: Error de validación de entrada
- GIVEN una solicitud con body inválido
- WHEN la validación Zod falla
- THEN se retorna HTTP 400 Bad Request
- AND el cuerpo de respuesta es:
```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation failed",
  "fieldErrors": [
    { "field": "email", "message": "Invalid email format" }
  ],
  "correlationId": "uuid-v4-value"
}
```

#### Scenario: Error de recurso no encontrado
- GIVEN una solicitud a `/api/v1/resources/non-existent-id`
- WHEN el recurso no existe
- THEN se retorna HTTP 404 Not Found
- AND el cuerpo de respuesta es:
```json
{
  "code": "NOT_FOUND",
  "message": "Resource not found",
  "fieldErrors": [],
  "correlationId": "uuid-v4-value"
}
```

#### Scenario: Error interno del servidor
- GIVEN una solicitud válida
- WHEN ocurre una excepción no manejada
- THEN se retorna HTTP 500 Internal Server Error
- AND el cuerpo de respuesta es:
```json
{
  "code": "INTERNAL_ERROR",
  "message": "An unexpected error occurred",
  "fieldErrors": [],
  "correlationId": "uuid-v4-value"
}
```

### Requirement: Códigos de error predefinidos

El sistema SHALL define a set of predefined error codes for consistent error handling.

#### Scenario: Códigos de error disponibles
- GIVEN la especificación de códigos de error
- THEN los siguientes códigos están disponibles:
  - `VALIDATION_ERROR` - Para errores de validación de entrada
  - `NOT_FOUND` - Para recursos no encontrados
  - `INTERNAL_ERROR` - Para errores inesperados
  - `BAD_REQUEST` - Para solicitudes mal formadas
  - `UNAUTHORIZED` - Para solicitudes sin autenticación válida

### Requirement: fieldErrors contiene errores de campo específicos

El sistema SHALL include field-specific errors in the fieldErrors array for validation failures.

#### Scenario: Error con múltiples campos inválidos
- GIVEN una solicitud con múltiples campos inválidos
- WHEN la validación Zod falla
- THEN `fieldErrors` contiene una entrada por cada campo fallido
- AND cada entrada tiene `field` con la ruta del campo y `message` con la descripción del error

### Requirement: CorrelationId en errores

El sistema SHALL include correlationId in all error responses for traceability.

#### Scenario: CorrelationId en respuesta de error
- GIVEN una solicitud que causa un error
- THEN la respuesta de error incluye el `correlationId` generado para esa solicitud
- AND el valor es consistente con el header `x-correlation-id` de la respuesta

