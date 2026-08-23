# Config-EnvVars Specification

## Purpose

Definir la estrategia de variables de entorno del proyecto, incluyendo validación al arranque, plantilla segura y separación entre variables de servidor y cliente.

## ADDED Requirements

### Requirement: Plantilla de variables de entorno

El repositorio SHALL provide a `.env.example` template that documents all expected environment variables without including real secrets.

#### Scenario: Archivo .env.example existe

- GIVEN El repositorio está configurado
- WHEN Se verifica la estructura
- THEN Existe un archivo `.env.example` en la raíz
- AND Contiene todas las variables usadas por los componentes del workspace

#### Scenario: Variables sensibles no exponen secretos

- GIVEN El archivo `.env.example` está presente
- WHEN Se inspecciona su contenido
- THEN Las contraseñas y claves usan valores placeholder o genéricos
- AND No contiene credenciales reales ni tokens de producción

#### Scenario: Variables del navegador libres de credenciales

- GIVEN El archivo `.env.example` está presente
- WHEN Se listan las variables con prefijo `NEXT_PUBLIC_`
- THEN Todas las variables `NEXT_PUBLIC_*` contienen solo URLs públicas o valores no sensibles
- AND Ninguna expone用户名, contraseñas o claves de API

### Requirement: Validación de variables de entorno al arrancar

Cada proceso del workspace SHALL validate its mandatory environment variables at startup and fail with a clear message if any are missing.

#### Scenario: API valida variables obligatorias al iniciar

- GIVEN La API de NestJS se inicia sin `DATABASE_URL`
- WHEN Se ejecuta el comando de inicio
- THEN El proceso falla con un mensaje de error claro
- AND El mensaje indica que `DATABASE_URL` es obligatoria

#### Scenario: API inicia exitosamente con todas las variables

- GIVEN `DATABASE_URL` y las demás variables obligatorias están definidas
- WHEN Se inicia la API
- THEN El servidor arranca normalmente
- AND Responde en los endpoints `/` y `/health`

#### Scenario: Worker valida variables obligatorias al iniciar

- GIVEN El Worker se inicia sin `DATABASE_URL`
- WHEN Se ejecuta el comando de inicio
- THEN El proceso falla con un mensaje de error claro
- AND El mensaje indica que `DATABASE_URL` es obligatoria

#### Scenario: Worker inicia exitosamente con todas las variables

- GIVEN `DATABASE_URL` y las demás variables obligatorias están definidas
- WHEN Se inicia el Worker
- THEN El proceso arranca y permanece activo hasta recibir una señal de terminación
