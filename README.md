# PLAN-DEPTO

Sistema de administración de alquileres desarrollado como monorepo.

El proyecto incluye:

* Frontend con Next.js
* API REST con NestJS
* Worker para tareas en segundo plano
* Paquetes compartidos
* PostgreSQL
* CrewAI para automatización mediante agentes
* OpenSpec para planificación y especificación de cambios

---

## Requisitos

Antes de comenzar, asegúrate de tener instalados:

* Node.js 20.11.0 o superior
* pnpm 8.15.0 o superior
* Docker
* Python >= 3.10 y < 3.14
* uv
* OpenSpec CLI

### Instalar pnpm

```bash
npm install -g pnpm@8.15.0
```

### Instalar uv

Linux/macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verificar:

```bash
uv --version
```

### Instalar OpenSpec

```bash
npm install -g @fission-ai/openspec@latest
```

Verificar:

```bash
openspec --version
```

---

# Setup del proyecto

## 1. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd koty-app
```

---

## 2. Instalar dependencias Node.js

```bash
pnpm install
```

Esto instala las dependencias de las aplicaciones y paquetes del monorepo.

---

## 3. Iniciar PostgreSQL

```bash
pnpm db:start
```

Para detener PostgreSQL:

```bash
pnpm db:stop
```

---

## 4. Configurar variables de entorno del monorepo

Desde la raíz:

```bash
cp .env.example .env.local
```

Completa las variables requeridas antes de iniciar los servicios.

---

## 5. Arrancar los servicios

### Todos los servicios

```bash
pnpm dev
```

### Servicios individuales

Frontend:

```bash
pnpm --filter @plandepo/web dev
```

Disponible en:

```text
http://localhost:3000
```

API:

```bash
pnpm --filter @plandepo/api dev
```

Disponible en:

```text
http://localhost:3001
```

Worker:

```bash
pnpm --filter @plandepo/worker dev
```

El worker ejecuta tareas en segundo plano y no expone un servidor HTTP.

---

# CrewAI

El proyecto incluye un subproyecto Python con CrewAI:

```text
crewai/
├── pyproject.toml
├── uv.lock
└── src/
    └── crew/
```

Las dependencias Python son administradas con `uv`.

No se utiliza `pip install` manualmente ni se versiona el entorno virtual.

---

## 1. Entrar al proyecto CrewAI

Desde la raíz del repositorio:

```bash
cd crewai
```

---

## 2. Instalar las dependencias

```bash
uv sync --frozen
```

Esto:

* crea automáticamente `crewai/.venv`
* instala las dependencias definidas en `pyproject.toml`
* utiliza las versiones fijadas en `uv.lock`
* instala el proyecto Python en el entorno virtual

Durante desarrollo también puede utilizarse:

```bash
uv sync
```

---

## 3. Configurar variables de entorno de CrewAI

Si existe un archivo de ejemplo:

```bash
cp .env.example .env
```

Completa las claves necesarias según el proveedor de LLM utilizado.

Por ejemplo:

```env
LLM_PROVIDER=opencode
OPENCODE_API_KEY=
```

o, si se utiliza Ollama local:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
```

El archivo `.env` no debe subirse al repositorio.

---

## 4. Ejecutar CrewAI

No es necesario activar manualmente el entorno virtual.

Con `uv` se recomienda ejecutar:

```bash
uv run run_crew DEV-5
```

También puede ejecutarse directamente el archivo principal:

```bash
uv run python src/crew/main.py DEV-5
```

Donde:

```text
DEV-5
```

es el identificador del cambio o tarea que procesará el Crew.

---

## Activar manualmente el entorno virtual

Normalmente no es necesario, pero puede hacerse con:

```bash
source .venv/bin/activate
```

Para salir:

```bash
deactivate
```

---

## Agregar una dependencia Python

No usar:

```bash
pip install <paquete>
```

Usar:

```bash
uv add <paquete>
```

Ejemplo:

```bash
uv add python-dotenv
```

Esto actualiza:

```text
pyproject.toml
uv.lock
```

---

# OpenSpec

OpenSpec se utiliza para mantener las especificaciones y planes técnicos de los cambios del proyecto.

La estructura se encuentra en la raíz:

```text
openspec/
├── specs/
└── changes/
```

El repositorio ya contiene la configuración de OpenSpec, por lo que después de clonar el proyecto **no debe ejecutarse nuevamente**:

```bash
openspec init
```

Para comprobar que OpenSpec reconoce correctamente el proyecto:

```bash
cd koty-app
openspec list
```

OpenSpec debe ejecutarse desde la raíz del repositorio, donde se encuentra:

```text
openspec/
```

---

## Flujo básico de OpenSpec

Consultar cambios:

```bash
openspec list
```

Consultar un cambio:

```bash
openspec show DEV-5
```

Validar un cambio:

```bash
openspec validate DEV-5
```

Consultar su estado:

```bash
openspec status --change DEV-5
```

El CrewAI también puede ejecutar comandos de OpenSpec automáticamente durante sus procesos de planificación, implementación y revisión.

---

# Scripts disponibles

| Comando         | Descripción                        |
| --------------- | ---------------------------------- |
| `pnpm dev`      | Arrancar todos los servicios       |
| `pnpm build`    | Compilar todas las apps y paquetes |
| `pnpm lint`     | Ejecutar lint en todo el monorepo  |
| `pnpm test`     | Ejecutar tests                     |
| `pnpm clean`    | Limpiar artefactos de compilación  |
| `pnpm format`   | Formatear archivos con Prettier    |
| `pnpm db:start` | Iniciar PostgreSQL con Docker      |
| `pnpm db:stop`  | Detener PostgreSQL                 |

### CrewAI

| Comando                                | Descripción                            |
| -------------------------------------- | -------------------------------------- |
| `uv sync --frozen`                     | Instalar dependencias usando `uv.lock` |
| `uv sync`                              | Sincronizar el entorno Python          |
| `uv add <paquete>`                     | Agregar una dependencia Python         |
| `uv remove <paquete>`                  | Eliminar una dependencia Python        |
| `uv run run_crew DEV-5`                | Ejecutar el Crew                       |
| `uv run python src/crew/main.py DEV-5` | Ejecutar directamente el entrypoint    |

---

# Estructura del proyecto

```text
koty-app/
├── apps/
│   ├── web/                  # Next.js - Frontend
│   ├── api/                  # NestJS - REST API
│   └── worker/               # NestJS - Background Jobs
│
├── packages/
│   ├── contracts/            # Esquemas Zod compartidos
│   └── config/               # Configuración compartida
│
├── crewai/
│   ├── pyproject.toml        # Configuración y dependencias Python
│   ├── uv.lock               # Versiones exactas de dependencias
│   └── src/
│       └── crew/
│           ├── main.py
│           ├── crew.py
│           ├── config/
│           └── tools/
│
├── openspec/
│   ├── specs/                # Especificaciones actuales
│   └── changes/              # Cambios en planificación/desarrollo
│
├── docker-compose.yml
├── pnpm-workspace.yaml
├── package.json
├── turbo.json
└── README.md
```

---

# Paquetes compartidos

## @plandepo/contracts

Contiene esquemas Zod compartidos entre frontend y backend.

Ejemplo:

```typescript
import {
  CreateUserSchema,
  LoginSchema,
} from '@plandepo/contracts';
```

---

## @plandepo/config

Contiene configuraciones compartidas para:

* TypeScript
* ESLint
* Prettier
* Tailwind CSS

---

# Archivos que no deben versionarse

No deben subirse al repositorio:

```text
.env
.env.local
.venv/
__pycache__/
*.pyc
node_modules/
.next/
dist/
```

En particular, el entorno virtual de Python:

```text
crewai/.venv/
```

se genera localmente mediante:

```bash
uv sync
```

y nunca debe ser agregado a Git.

Por el contrario, sí deben versionarse:

```text
crewai/pyproject.toml
crewai/uv.lock
crewai/.python-version
```

si `.python-version` forma parte del proyecto.

---

# Setup rápido para nuevos desarrolladores

Después de tener instalados Node.js, pnpm, Docker, Python, uv y OpenSpec:

```bash
git clone <URL_DEL_REPOSITORIO>
cd koty-app

pnpm install

cp .env.example .env.local

pnpm db:start

cd crewai

uv sync --frozen

cp .env.example .env
```

Configura las variables correspondientes y vuelve a la raíz:

```bash
cd ..
```

Arranca el monorepo:

```bash
pnpm dev
```

Para ejecutar CrewAI:

```bash
cd crewai
uv run run_crew DEV-5
```

---

# Contribuir

Crear una rama:

```bash
git checkout -b feature/mi-feature
```

Realizar los cambios y revisar:

```bash
git status
```

Agregar los archivos:

```bash
git add .
```

Crear el commit:

```bash
git commit -m "feat: agregar nueva feature"
```

Subir la rama:

```bash
git push origin feature/mi-feature
```

Finalmente, crear un Pull Request.

---

# Licencia

Privado - PLAN-DEPTO

