# api-v1-correlation Specification

## Purpose
TBD - created by archiving change dev-7. Update Purpose after archive.
## Requirements
### Requirement: Generación de correlationId

El sistema SHALL generate a unique correlationId for each request using UUID v4 format.

#### Scenario: CorrelationId generado automáticamente
- GIVEN una solicitud HTTP entrante sin `correlationId` en headers
- WHEN la solicitud llega al middleware
- THEN se genera un nuevo `correlationId` con formato UUID v4
- AND se adjunta al header de respuesta `x-correlation-id`
- AND se inyecta en el contexto de la solicitud para uso en logs y respuestas

#### Scenario: CorrelationId proporcionado por el cliente
- GIVEN una solicitud HTTP con header `x-correlation-id: client-provided-id`
- WHEN la solicitud llega al middleware
- THEN se usa el valor proporcionado por el cliente
- AND se adjunta al header de respuesta `x-correlation-id`
- AND se inyecta en el contexto de la solicitud

#### Scenario: CorrelationId presente en respuesta
- GIVEN una solicitud válida a `GET /api/v1/health`
- WHEN la respuesta es retornada
- THEN el header `x-correlation-id` contiene el correlationId de la solicitud
- AND el cuerpo de respuesta incluye `correlationId` al mismo nivel que otros campos

### Requirement: Propagation de correlationId

El sistema SHALL expose the correlationId throughout the request lifecycle for logging and diagnostics.

#### Scenario: CorrelationId accesible en servicios
- GIVEN una solicitud con `correlationId` generado
- WHEN un servicio procesa la lógica de negocio
- THEN el `correlationId` es inyectable o accesible via InjectionToken
- AND puede incluirse en logs de diagnóstico

#### Scenario: CorrelationId propagado en respuestas de error
- GIVEN una solicitud que causa un error
- WHEN se construye la respuesta de error
- THEN el `correlationId` se incluye en el cuerpo del error
- AND el header `x-correlation-id` contiene el mismo valor

