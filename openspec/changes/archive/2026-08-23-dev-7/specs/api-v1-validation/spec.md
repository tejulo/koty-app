# API v1 — Validación de Entradas con Zod

## ADDED Requirements

### Requirement: Validación Zod estricta de body

El sistema SHALL validate all request body inputs using Zod in strict mode, rejecting unknown fields.

#### Scenario: Validación de body con campos válidos
- GIVEN un esquema Zod para validación: `{ name: z.string(), email: z.string().email() }`
- AND un body de solicitud: `{ "name": "Test", "email": "test@example.com" }`
- WHEN la solicitud llega al middleware de validación
- THEN la validación pasa
- AND la solicitud continúa al handler

#### Scenario: Rechazo de campos desconocidos
- GIVEN un esquema Zod para validación: `{ name: z.string() }`
- AND un body de solicitud: `{ "name": "Test", "unknownField": "value" }`
- WHEN la solicitud llega al middleware de validación
- THEN la validación falla
- AND se retorna error con estructura de contrato

#### Scenario: Rechazo de campos faltantes requeridos
- GIVEN un esquema Zod para validación: `{ name: z.string(), email: z.string().email() }`
- AND un body de solicitud: `{ "name": "Test" }`
- WHEN la solicitud llega al middleware de validación
- THEN la validación falla
- AND se retorna error indicando campos faltantes

### Requirement: Validación de Query Parameters

El sistema SHALL validate query parameters using Zod strict mode.

#### Scenario: Query params válidos
- GIVEN un esquema Zod para query: `{ page: z.coerce.number().int().positive() }`
- AND query string: `?page=1`
- WHEN la solicitud llega al middleware de validación
- THEN la validación pasa

#### Scenario: Query params con campo desconocido
- GIVEN un esquema Zod para query: `{ page: z.coerce.number() }`
- AND query string: `?page=1&filter=all`
- WHEN la solicitud llega al middleware de validación
- THEN la validación falla
- AND se retorna error indicando campo desconocido

### Requirement: Validación de Path Parameters

El sistema SHALL validate path parameters using Zod.

#### Scenario: Path param con tipo inválido
- GIVEN un esquema Zod para params: `{ id: z.string().uuid() }`
- AND path: `/resource/invalid-uuid`
- WHEN la solicitud llega al middleware de validación
- THEN la validación falla
- AND se retorna error indicando formato inválido
