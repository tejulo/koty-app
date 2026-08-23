# DEV-9: Tareas de Implementación

## Infraestructura

- [x] **Crear `docker-compose.yml`**
  - Archivo a crear: `docker-compose.yml`
  - Servicio PostgreSQL con imagen oficial `postgres:17-alpine`
  - Variables: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
  - Puerto: `5432:5432`
  - Volumen named: `postgres_data:/var/lib/postgresql/data`
  - Tests: Verificar que `docker compose up -d` levanta el contenedor y `docker compose down` lo detiene

## Configuración de Variables de Entorno

- [x] **Expandir `.env.example`**
  - Archivo a modificar: `.env.example`
  - Agregar variable `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/plandepo_dev`
  - Agregar comentarios indicating placeholders vs. valores reales
  - Verificar que `NEXT_PUBLIC_*` no contengan credenciales
  - Tests: Verificar que el archivo no contiene secretos reales

- [x] **Agregar scripts de base de datos a `package.json`**
  - Archivo a modificar: `package.json` (raíz)
  - Scripts: `db:start`, `db:stop`, `db:status`
  - Tests: Verificar que los scripts ejecutan los comandos correctos

## Validación de Entorno

- [x] **Implementar validación en API (NestJS)**
  - Archivo a modificar: `apps/api/src/main.ts`
  - Usar `@nestjs/config` con esquema de validación
  - Validar `DATABASE_URL` como obligatoria
  - Fallar con mensaje claro si falta
  - Tests: API falla con mensaje claro si `DATABASE_URL` no está definida

- [x] **Implementar validación en Worker (TypeScript)**
  - Archivo a modificar: `apps/worker/src/main.ts`
  - Verificar `DATABASE_URL` antes de iniciar
  - Fallar con mensaje claro y código de salida no cero
  - Tests: Worker falla con mensaje claro si `DATABASE_URL` no está definida

## Documentación

- [x] **Actualizar CONTRIBUTING.md**
  - Archivo a modificar: `CONTRIBUTING.md`
  - Agregar sección "Development Environment Setup"
  - Incluir: requisitos previos, Docker, variables de entorno, PostgreSQL, verificación
  - Tests: Documentación legible y completa

## Verificación

- [x] **Ejecutar validación OpenSpec**
  - Validar que todas las specs están correctamente formateadas
  - Verificar que el diseño es coherente con las specs
  - Verificar trazabilidad entre tareas y specs
