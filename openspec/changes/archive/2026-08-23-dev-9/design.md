# DEV-9: Diseño Técnico

## Decisiones de Diseño

### 1. Docker Compose en la raíz

Se creará `docker-compose.yml` en la raíz del repositorio para mantener la configuración de contenedores junto al código. Esto permite que cualquier desarrollador ejecute `docker compose up -d` desde la raíz sin buscar archivos en subdirectorios.

**Alternativa descartada:** Archivo en `infra/` o `docker/`. Descartada porque fragmenta la configuración y complica los comandos de un solo paso.

### 2. Variables de conexión PostgreSQL

El servicio PostgreSQL usará variables de entorno alineadas con `DATABASE_URL` en `.env.example`:

- `POSTGRES_DB=plandepo_dev`
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`

Estas credenciales son para desarrollo local únicamente. El puerto expuesto será `5432:5432` para mantener compatibilidad con `localhost:5432`.

### 3. Volumen persistente para datos

Se configurará un volumen named `postgres_data` en Docker Compose para persistir los datos de la base de datos entre sesiones. Esto evita pérdida accidental de datos de desarrollo.

### 4. Plantilla `.env.example` existente

El archivo `.env.example` ya existe en el repositorio. Se expandirá para incluir:

- Todas las variables actuales (API, Web, Worker)
- Variables específicas de la base de datos (`DATABASE_URL`)
- Comentarios indicando qué valores son placeholders

### 5. Validación de env vars en API (NestJS)

Se implementará un módulo de configuración en NestJS que:

- Use `@nestjs/config` con validación de esquema
- Aplique `class-validator` para verificar variables obligatorias
- Lance `Error` con mensaje descriptivo si falta una variable
- Se ejecute en la fase de bootstrapping (antes de escuchar en puertos)

### 6. Validación de env vars en Worker (TypeScript)

Se implementará validación en el entrypoint del worker (`src/main.ts`):

- Carga de variables con `dotenv` si aplica
- Verificación de `DATABASE_URL` antes de iniciar
- Lanzamiento de `Error` con mensaje claro si falta
- Log del mensaje antes de salir con código de error

### 7. Variables `NEXT_PUBLIC_*` seguras

Se seguirá la convención de Next.js donde:

- Solo variables prefijadas con `NEXT_PUBLIC_` son accesibles en el navegador
- Valores sensibles (DB credentials, API keys de backend) nunca tendrán este prefijo
- El `.env.example` marcará claramente cuáles variables son seguras para el navegador

### 8. Scripts de base de datos

Se agregarán scripts npm en la raíz para complementar Docker Compose:

- `pnpm db:start`: Ejecuta `docker compose up -d` e imprime estado
- `pnpm db:stop`: Ejecuta `docker compose down`
- `pnpm db:status`: Verifica si el contenedor está corriendo

### 9. Documentación en CONTRIBUTING.md

Se extenderá `CONTRIBUTING.md` con una sección de "Development Environment Setup" que incluya:

- Requisitos previos (Docker, Node.js, pnpm, mise)
- Pasos para clonar e instalar
- Configuración de variables de entorno
- Inicio de PostgreSQL
- Verificación del entorno

---

## Resumen de Archivos a Crear/Modificar

| Archivo | Cambio |
|---------|--------|
| `docker-compose.yml` | Crear |
| `.env.example` | Expandir con DATABASE_URL y comentarios |
| `CONTRIBUTING.md` | Agregar sección de setup de desarrollo |
| `package.json` | Agregar scripts db:start, db:stop, db:status |
| `apps/api/src/main.ts` | Agregar validación de env vars |
| `apps/worker/src/main.ts` | Agregar validación de env vars |
