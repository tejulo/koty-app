# Infra-Database Specification

## Purpose

Definir la configuración y uso de PostgreSQL local mediante Docker Compose para el entorno de desarrollo.

## ADDED Requirements

### Requirement: Docker Compose para PostgreSQL

El proyecto SHALL provide a Docker Compose configuration that allows starting and stopping a local PostgreSQL instance in a reproducible way.

#### Scenario: Archivo docker-compose.yml existe en la raíz

- GIVEN El repositorio no tiene configuración de contenedores
- WHEN Se implementa la configuración de infraestructura
- THEN Existe un archivo `docker-compose.yml` en la raíz
- AND Define un servicio `postgres` con imagen oficial PostgreSQL
- AND Expone el puerto `5432` del contenedor

#### Scenario: Variables de conexión configurables

- GIVEN El archivo `docker-compose.yml` está presente
- WHEN Se configura el servicio postgres
- THEN Las variables de entorno `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD` se definen
- AND Coinciden con los valores esperados por `DATABASE_URL` en `.env.example`

#### Scenario: PostgreSQL inicia correctamente

- GIVEN `docker compose up -d` se ejecuta desde la raíz
- WHEN El comando finaliza sin errores
- THEN El contenedor `postgres` está en estado `running`
- AND El puerto `5432` está accesible en `localhost`

#### Scenario: PostgreSQL se detiene correctamente

- GIVEN Un contenedor PostgreSQL está en ejecución
- WHEN `docker compose down` se ejecuta desde la raíz
- THEN El contenedor se detiene y elimina
- AND El puerto `5432` queda libre

#### Scenario: Datos persistentes entre reinicios

- GIVEN Un volumen named está configurado en Docker Compose
- WHEN Los contenedores se reinician
- THEN Los datos de la base de datos persisten en el volumen
- AND No se pierden datos de desarrollo entre sesiones
