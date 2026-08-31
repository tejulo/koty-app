# Contribuir a Koty App

Este documento define las convenciones y el flujo de trabajo para contribuir al monorepo de Koty App.

El objetivo es mantener un proceso consistente entre:

```text
Linear
  ↓
Git Branch
  ↓
OpenSpec
  ↓
CrewAI / Desarrollo
  ↓
Validaciones
  ↓
Pull Request
  ↓
main
```

---

# 1. Requisitos previos

Antes de comenzar a trabajar en el proyecto, asegúrate de tener instalados:

* Git
* Node.js
* pnpm
* Docker
* Python
* uv

Las versiones de Node.js, pnpm, Python y uv estan fijadas en `.mise.toml`. Desde la raiz, prepara y verifica el entorno con el flujo correspondiente.

### Bash (Linux, macOS y WSL)

```bash
./scripts/bootstrap.sh
# ejecutar las instrucciones que imprime para activar mise en este shell
# completar crewai/.env
./scripts/doctor.sh
pnpm verify
cd crewai
uv run run_crew DEV-5
```

### PowerShell 5.1 o 7 (Windows)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
# ejecutar las instrucciones que imprime para activar mise en este shell
# completar crewai\.env
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
pnpm verify
Set-Location crewai
uv run run_crew DEV-5
```

En PowerShell 7, sustituye `powershell.exe` por `pwsh` en ambos comandos.

`bootstrap.sh` instala `mise` cuando hace falta, instala las versiones fijadas, sincroniza las dependencias pnpm y uv con sus lockfiles y crea `crewai/.env` desde el ejemplo solo si no existe. Ejecuta `doctor.sh` al final, por lo que puede devolver un codigo distinto de cero hasta que se completen las credenciales y modelos requeridos; despues debe repetirse `./scripts/doctor.sh`.

El bootstrap no puede modificar el shell padre. Cuando termina correctamente imprime instrucciones idempotentes para agregar `~/.local/bin` y activar `mise` en Bash o Zsh. Ejecuta ese bloque antes de usar cualquier comando bare `pnpm` o `uv` de esta guia.

En Windows, `bootstrap.ps1` instala `mise` mediante `winget` si es necesario e imprime el bloque idempotente para activar `mise` en PowerShell 5.1 o 7. Si `winget` acaba de instalar `mise` y no aparece en `PATH`, abre una nueva sesion y ejecuta nuevamente el bootstrap.

Si no quieres modificar la configuracion del shell, usa la ruta resuelta que muestra el bootstrap:

```bash
"$HOME/.local/bin/mise" exec -- pnpm verify
"$HOME/.local/bin/mise" exec -- uv run --project crewai run_crew DEV-5
```

Si `mise` ya estaba instalado en otra ruta, reemplaza `"$HOME/.local/bin/mise"` por la ruta impresa. La forma general es `mise exec -- <comando>`.

No requiere activacion manual de `crewai/.venv`: usa `uv run`. OpenSpec es local al workspace y todos sus comandos se ejecutan desde la raiz mediante `OPENSPEC_TELEMETRY=0 pnpm exec openspec`; no requiere instalacion global.

`DEV-5` esta archivado. El comando del flujo documenta el formato del entrypoint; si la ejecucion puede crear, modificar o archivar artefactos, sustituye `DEV-5` por un ticket activo.

Los ejemplos operativos usan `TICKET_ACTIVO` y `CHANGE_ID_ACTIVO`. En Bash, asigna los identificadores reales con `export TICKET_ACTIVO=DEV-123` y `export CHANGE_ID_ACTIVO=dev-123`; en PowerShell usa `$env:TICKET_ACTIVO = 'DEV-123'` y `$env:CHANGE_ID_ACTIVO = 'dev-123'`.

Consulta el `README.md` principal para las instrucciones completas de instalación.

---

# 2. Development Environment Setup

Esta sección documenta el procedimiento para dejar un entorno limpio completamente operativo.

## 2.1 Requisitos previos del entorno

Asegúrate de tener instalado:

* Docker Desktop (o Docker Engine en Linux)
* Node.js >= 20.19.0
* pnpm >= 8.15.0
* Python >= 3.11
* uv

## 2.2 Configurar variables de entorno

1. Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

2. Abre `.env` y verifica que `DATABASE_URL` tenga el valor correcto para desarrollo local:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/plandepo_dev
```

3. Las variables con prefijo `NEXT_PUBLIC_` son seguras para el navegador y no contienen credenciales.

## 2.3 Iniciar PostgreSQL

Desde la raíz del proyecto:

```bash
# Iniciar el contenedor
pnpm db:start

# Verificar que está corriendo
pnpm db:status
```

El contenedor PostgreSQL estará disponible en `localhost:5432`.

## 2.4 Detener PostgreSQL

```bash
pnpm db:stop
```

## 2.5 Verificar el entorno

1. Asegúrate de que Docker está corriendo
2. Ejecuta el bootstrap:

```bash
# Bash
./scripts/bootstrap.sh

# PowerShell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

3. Verifica el entorno completo:

```bash
pnpm verify
```

4. Inicia la API:

```bash
pnpm start:api
```

La API debe responder en `http://localhost:3001` y validar que `DATABASE_URL` está configurada. Si falta, mostrará un mensaje de error claro.

## 2.6 Comandos de base de datos

| Comando | Descripción |
|---------|-------------|
| `pnpm db:start` | Inicia PostgreSQL con Docker Compose |
| `pnpm db:stop` | Detiene y elimina el contenedor |
| `pnpm db:status` | Muestra el estado del contenedor |

---

# 2.7 Prisma migrations

Las migraciones de Prisma se ejecutan **únicamente** mediante comandos explícitos. La aplicación nunca aplica migraciones al arrancar.

| Comando | Descripción |
|---|---|
| `pnpm db:migrate:dev --name <nombre>` | Crea una nueva migración versionada y la aplica sobre la base de desarrollo. |
| `pnpm db:migrate:deploy` | Aplica las migraciones pendientes en modo `deploy` (CI, pruebas). |
| `pnpm db:migrate:reset` | Recrea la base de desarrollo y reaplica todas las migraciones desde cero. |
| `pnpm db:migrate:status` | Lista las migraciones aplicadas y las pendientes. |
| `pnpm db:verify` | Ejecuta `prisma migrate diff` para confirmar que el esquema coincide con el historial. |

Buenas prácticas:

- Cada cambio de esquema se commitea junto con su migración SQL bajo `apps/api/prisma/migrations/`.
- Antes de mergear, ejecuta `pnpm db:verify` para detectar drift entre `schema.prisma` y el historial.
- Si necesitas descartar cambios locales en la base, usa `pnpm db:migrate:reset`.
- Ningún `main.ts` ni ciclo de vida de Nest invoca `prisma migrate` directamente; si lo necesitas, crea un script en `package.json` y consúltalo con el equipo.

### Reproducir el esquema desde una base vacía

Con el contenedor PostgreSQL arriba y `DATABASE_URL` definido en `.env`:

```bash
pnpm db:migrate:deploy
```

El comando aplica todas las migraciones versionadas y deja el esquema listo, sin pasos manuales.

---

# 2.8 Integration tests (apps/api)

Las pruebas de integración de `apps/api` se ejecutan contra una base PostgreSQL real aislada por ejecución. La configuración se encuentra en `apps/api/vitest.config.integration.ts`.

Requisitos:

- PostgreSQL local accesible (el mismo usado para desarrollo).
- `DATABASE_URL` definida y con permisos para crear bases de datos.
- (Opcional) `DATABASE_URL_TEST` definida en `.env` con la URL base; si no se define, el `globalSetup` deriva una base `plandepo_test_<runId>` usando `DATABASE_URL`.

Ejecución:

```bash
pnpm --filter @koty-app/api test:integration
```

El flujo:

1. `globalSetup` crea la base aislada y aplica `prisma migrate deploy` sobre ella.
2. Los tests de integración se ejecutan contra esa base.
3. `globalTeardown` cierra las conexiones y destruye la base.

Los tests de integración **no** mockean el cliente Prisma; cualquier sustitución queda prohibida por el requisito de "Pruebas de integración contra PostgreSQL real con base aislada".

---

# 3. Rama principal

La rama principal del proyecto es:

```text
main
```

`main` debe mantenerse siempre en un estado estable.

No se deben desarrollar funcionalidades directamente sobre `main`.

Evita:

```bash
git switch main

# modificar código
git add .
git commit -m "..."
```

En su lugar, todo cambio debe realizarse en una branch específica.

---

# 4. Flujo general de desarrollo

Para cada ticket de Linear se crea una branch independiente.

Ejemplo:

```text
Linear:
DEV-5

OpenSpec:
dev-5

Branch:
feat/dev-5-inicializar-monorepo

Pull Request:
[DEV-5] Inicializar monorepo
```

El flujo completo es:

```text
Linear DEV-5
      ↓
actualizar main
      ↓
crear branch
      ↓
crear / actualizar OpenSpec
      ↓
implementar
      ↓
lint + test + build
      ↓
commit
      ↓
push
      ↓
Pull Request
      ↓
Code Review / CI
      ↓
merge a main
      ↓
eliminar branch
```

---

# 5. Antes de comenzar un ticket

Siempre comienza desde una versión actualizada de `main`.

```bash
git switch main
git pull origin main
```

Comprueba:

```bash
git status
```

Idealmente debe mostrar:

```text
nothing to commit, working tree clean
```

Luego crea la branch correspondiente al ticket.

---

# 6. Convención de nombres de branches

Formato:

```text
<tipo>/<ticket>-<descripcion>
```

Reglas:

* usar minúsculas;
* usar `-` para separar palabras;
* incluir siempre el ticket de Linear;
* utilizar una descripción corta;
* no utilizar espacios;
* no utilizar `_`;
* evitar nombres genéricos.

Ejemplo:

```text
feat/dev-5-inicializar-monorepo
```

---

## Tipos de branches

### feat

Nueva funcionalidad.

```text
feat/

...[TRUNCADO]...

ambios relacionados con herramientas de compilación o packaging.

```text
build/dev-40-configurar-turbo
```

### ci

Cambios de integración continua.

```text
ci/dev-45-agregar-github-actions
```

### hotfix

Corrección urgente de producción.

```text
hotfix/dev-50-corregir-error-produccion
```

---

# 7. Crear una branch

Ejemplo para el ticket `DEV-5`:

```bash
git switch main
git pull origin main

git switch -c feat/dev-5-inicializar-monorepo
```

Verifica:

```bash
git branch --show-current
```

Debe mostrar:

```text
feat/dev-5-inicializar-monorepo
```

---

# 8. Relación entre Linear, OpenSpec y Git

Los identificadores deben mantenerse relacionados.

Ejemplo:

```text
Linear:
DEV-5

OpenSpec:
dev-5

Branch:
feat/dev-5-inicializar-monorepo

Pull Request:
[DEV-5] Inicializar monorepo
```

Linear utiliza normalmente el identificador:

```text
DEV-5
```

OpenSpec utiliza:

```text
dev-5
```

Las branches también utilizan el ticket en minúsculas:

```text
dev-5
```

Esto permite rastrear fácilmente un cambio entre las distintas herramientas.

---

# 9. Flujo con CrewAI

El proyecto incluye un CrewAI para automatizar:

```text
Linear
  ↓
Requirements Analyst
  ↓
Software Architect
  ↓
OpenSpec
  ↓
Senior Software Developer
  ↓
Quality Reviewer
```

El Crew debe ejecutarse desde la branch correspondiente a un ticket activo.

Ejemplo:

```bash
git switch -c feat/dev-6-agregar-autenticacion

cd crewai

uv run run_crew DEV-6
```

No ejecutes el Crew para desarrollar una feature directamente sobre:

```text
main
```

---

# 10. OpenSpec

Los cambios OpenSpec se encuentran en:

```text
openspec/changes/
```

Ejemplo:

```text
openspec/
└── changes/
    └── dev-5/
        ├── proposal.md
        ├── design.md
        ├── tasks.md
        └── specs/
```

Los artifacts representan:

```text
proposal.md
→ objetivo y alcance

specs/
→ contrato funcional

design.md
→ decisiones técnicas

tasks.md
→ checklist de implementación
```

---

# 11. Validar OpenSpec

Antes de considerar terminado un cambio:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate "$CHANGE_ID_ACTIVO" --strict --no-interactive
```

También puedes revisar tareas pendientes:

```bash
grep -n '\[ \]' "openspec/changes/$CHANGE_ID_ACTIVO/tasks.md"
```

Si no devuelve resultados, todas las tareas están marcadas como completadas.

---

# 12. Reintentar un cambio rechazado

Si el Reviewer rechaza un cambio, no elimines automáticamente:

```text
openspec/changes/$CHANGE_ID_ACTIVO/
```

Corrige los problemas indicados y vuelve a ejecutar:

```bash
cd crewai

uv run run_crew "$TICKET_ACTIVO"
```

Conserva:

```text
proposal.md
design.md
specs/
tasks.md
```

Solo elimina el change si se decidió explícitamente rehacer toda la planificación desde cero.

---

# 13. Validaciones obligatorias

Antes de crear un Pull Request, deben ejecutarse las validaciones del monorepo.

Desde la raíz:

```bash
pnpm verify
```

La puerta incluye lint, Vitest, pruebas shell, builds, pytest y validacion estricta de OpenSpec. Debe finalizar correctamente.

---

## Python / CrewAI

También puede verificarse:

```bash
cd crewai

uv run python -m compileall -q src/crew
```

---

## OpenSpec

Desde la raíz:

```bash
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate "$CHANGE_ID_ACTIVO" --strict --no-interactive
```

---

# 14. Checklist antes del commit

Antes de crear un commit:

```bash
git status
git diff
```

Comprueba que:

* no haya archivos temporales;
* no haya secretos;
* no se esté versionando `.env`;
* no se esté versionando `.venv`;
* no haya `node_modules`;
* no haya `__pycache__`;
* no haya artefactos de build innecesarios;
* los cambios pertenezcan al ticket actual.

---

# 15. Archivos que no deben subirse

Entre otros:

```text
.env
.env.local

.venv/
venv/

node_modules/

__pycache__/
*.pyc

.next/
dist/
build/
coverage/

.turbo/
.pytest_cache/
.mypy_cache/
.ruff_cache/
```

Los archivos de ejemplo sí deben versionarse:

```text
.env.example
crewai/.env.example
```

---

# 16. Lockfiles

Los lockfiles deben versionarse.

Node / pnpm:

```text
pnpm-lock.yaml
```

Python / uv:

```text
crewai/uv.lock
```

No deben agregarse al `.gitignore`.

---

# 17. Convención de commits

Utilizamos una convención basada en Conventional Commits.

Formato:

```text
<tipo>(<scope opcional>): <descripcion>
```

Ejemplos:

```text
feat: configurar estructura inicial del monorepo
```

```text
feat(api): agregar endpoint de health check
```

```text
fix(web): corregir configuración TypeScript
```

```text
fix(worker): corregir configuración ESLint
```

```text
docs: documentar flujo de CrewAI
```

---

# 18. Tipos de commits

### feat

Nueva funcionalidad.

```text
feat: agregar autenticación
```

### fix

Corrección.

```text
fix: corregir validación de usuario
```

### refactor

Refactorización.

```text
refactor: reorganizar servicio de autenticación
```

### docs

Documentación.

```text
docs: actualizar contributing
```

### test

Tests.

```text
test: agregar tests de autenticación
```

### chore

Mantenimiento.

```text
chore: actualizar dependencias
```

### build

Build o tooling.

```text
build: configurar turbo
```

### ci

CI/CD.

```text
ci: agregar workflow de pull requests
```

---

# 19. Scope de commits

Cuando sea útil, agrega el módulo afectado:

```text
feat(web): agregar pantalla de login
fix(api): corregir health check
feat(worker): agregar job de notificaciones
feat(contracts): agregar schema de usuario
docs(crewai): actualizar instrucciones
```

No es obligatorio cuando el cambio afecta todo el proyecto.

---

# 20. Crear commits

Revisa primero:

```bash
git status
git diff
```

Agrega los archivos:

```bash
git add .
```

O preferentemente, agrega de forma selectiva:

```bash
git add apps/api
git add packages/contracts
git add openspec/changes/dev-5
```

Luego:

```bash
git commit -m "feat: inicializar estructura del monorepo"
```

---

# 21. Commits pequeños

Se prefieren commits pequeños y coherentes.

Por ejemplo:

```text
feat: configurar workspace pnpm
feat(web): inicializar Next.js
feat(api): inicializar NestJS
feat(worker): inicializar worker
fix: corregir configuración ESLint
fix: corregir configuración TypeScript
```

Evita commits como:

```text
cambios
fix
update
final
final2
cosas
test
```

---

# 22. Subir la branch

La primera vez:

```bash
git push -u origin feat/dev-5-inicializar-monorepo
```

Después:

```bash
git push
```

---

# 23. Pull Requests

Cada branch debe integrarse a `main` mediante Pull Request.

Flujo:

```text
feat/dev-5-inicializar-monorepo
              ↓
         Pull Request
              ↓
             main
```

---

# 24. Convención de títulos de Pull Request

Formato:

```text
[TICKET] Descripción
```

Ejemplo:

```text
[DEV-5] Inicializar monorepo
```

Otros ejemplos:

```text
[DEV-12] Corregir autenticación
[DEV-20] Agregar recuperación de contraseña
```

---

# 25. Contenido recomendado del Pull Request

Cada Pull Request debería incluir:

```markdown
## Ticket

DEV-5

## Descripción

Resumen del cambio implementado.

## Cambios principales

- ...
- ...
- ...

## Validaciones

- [x] lint
- [x] test
- [x] build
- [x] OpenSpec validate

## OpenSpec

`dev-5`
```

---

# 26. Revisión antes del PR

Ejecuta:

```bash
pnpm verify
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate "$CHANGE_ID_ACTIVO" --strict --no-interactive
```

Y:

```bash
git status
git diff main...HEAD
```

---

# 27. Merge

Un Pull Request puede integrarse a `main` cuando:

* la implementación cumple el ticket;
* las validaciones pasan;
* OpenSpec es válido;
* la revisión de código fue aprobada;
* CI pasa si está configurado.

---

# 28. Estrategia recomendada de merge

Para branches de features normales se recomienda:

```text
Squash and merge
```

Ejemplo:

La branch contiene:

```text
feat: configurar workspace
feat(web): inicializar frontend
fix: corregir eslint
fix: corregir tsconfig
```

Al integrar puede quedar un solo commit:

```text
feat: [DEV-5] inicializar monorepo
```

Esto mantiene `main` más limpio.

---

# 29. Después del merge

Actualiza `main`:

```bash
git switch main
git pull origin main
```

Elimina la branch local:

```bash
git branch -d feat/dev-5-inicializar-monorepo
```

Si la branch remota sigue existiendo:

```bash
git push origin --delete feat/dev-5-inicializar-monorepo
```

---

# 30. Comenzar el siguiente ticket

Ejemplo:

```bash
git switch main
git pull origin main

git switch -c feat/dev-6-agregar-autenticacion
```

Y luego:

```bash
cd crewai
uv run run_crew dev-6
```

---

# 31. Mantener una branch actualizada

Si `main` cambia mientras trabajas:

```bash
git switch main
git pull origin main

git switch feat/dev-5-inicializar-monorepo
git rebase main
```

Si prefieres merge:

```bash
git merge main
```

El equipo debe utilizar consistentemente una de las estrategias.

Para branches cortas se recomienda preferentemente:

```text
rebase sobre main
```

antes de abrir o actualizar el PR.

---

# 32. Conflictos durante rebase

Si aparece un conflicto:

```bash
git status
```

Resuelve los archivos.

Luego:

```bash
git add <archivo>
git rebase --continue
```

Cancelar:

```bash
git rebase --abort
```

Si la branch ya había sido subida antes del rebase:

```bash
git push --force-with-lease
```

No utilizar:

```bash
git push --force
```

salvo un caso excepcional.

`--force-with-lease` evita sobrescribir accidentalmente cambios remotos que no tienes localmente.

---

# 33. Hotfixes

Para una corrección urgente:

```bash
git switch main
git pull origin main

git switch -c hotfix/dev-50-corregir-error-produccion
```

Se aplica el mismo proceso:

```text
hotfix branch
    ↓
validaciones
    ↓
Pull Request
    ↓
main
```

No se deben saltar las validaciones por tratarse de un hotfix.

---

# 34. Cambios sin ticket

Siempre que sea posible, todo cambio debe estar asociado a un ticket.

Para cambios administrativos pequeños que excepcionalmente no tengan ticket, puede utilizarse:

```text
chore/actualizar-documentacion
```

Sin embargo, se recomienda crear un ticket incluso para cambios técnicos importantes.

Esto mantiene la trazabilidad.

---

# 35. No mezclar tickets

Una branch debe corresponder principalmente a un ticket.

Evita:

```text
feat/dev-5-inicializar-monorepo
```

conteniendo además cambios relacionados con:

```text
DEV-8
DEV-12
DEV-20
```

Si aparece trabajo adicional, crea otro ticket y crea otra branch.

---

# 36. No desarrollar sobre branches de otros tickets

Evita:

```text
main
  ↓
feat/dev-5
  ↓
feat/dev-6
```

si `DEV-6` no depende explícitamente de `DEV-5`.

Preferir:

```text
main
 ├── feat/dev-5
 └── feat/dev-6
```

Esto reduce dependencias entre Pull Requests.

---

# 37. Branches dependientes

Si un ticket depende realmente de otro aún no mergeado, documenta claramente esa dependencia en el Pull Request.

Ejemplo:

```text
main
  ↓
feat/dev-5-base-auth
  ↓
feat/dev-6-google-login
```

Cuando `DEV-5` llegue a `main`, actualiza `DEV-6` mediante rebase.

---

# 38. Cambios generados por CrewAI

CrewAI puede modificar muchos archivos.

Después de cada ejecución revisa obligatoriamente:

```bash
git status
git diff
```

No asumas que porque el Reviewer del Crew aprobó el cambio todo debe agregarse automáticamente al commit.

La revisión humana del diff sigue siendo necesaria.

---

# 39. OpenSpec y Git

Los cambios OpenSpec forman parte del repositorio.

Versionar:

```text
openspec/
```

No ignorar:

```text
openspec/changes/
openspec/specs/
```

Los artifacts de OpenSpec permiten entender por qué existe una implementación y qué requisitos debe cumplir.

---

# 40. CrewAI y Git

Versionar:

```text
crewai/pyproject.toml
crewai/uv.lock
crewai/.env.example
crewai/README.md
crewai/src/
```

No versionar:

```text
crewai/.env
crewai/.venv/
crewai/**/__pycache__/
```

---

# 41. Definition of Done

Un ticket se considera terminado cuando:

* [ ] el ticket fue implementado;
* [ ] los requisitos de OpenSpec están cubiertos;
* [ ] todas las tasks de OpenSpec están completas;
* [ ] `pnpm verify` pasa;
* [ ] `OPENSPEC_TELEMETRY=0 pnpm exec openspec validate "$CHANGE_ID_ACTIVO" --strict --no-interactive` pasa;
* [ ] no hay secretos en Git;
* [ ] el diff fue revisado;
* [ ] la branch fue subida;
* [ ] existe Pull Request;
* [ ] el PR fue aprobado;
* [ ] CI pasa;
* [ ] el cambio fue integrado a `main`.

---

# 42. Resumen rápido

Para un ticket activo, por ejemplo:

```text
DEV-6
```

Ejecuta:

```bash
git switch main
git pull origin main

git switch -c feat/dev-6-agregar-autenticacion
```

Si corresponde usar CrewAI:

```bash
cd crewai
uv run run_crew DEV-6
cd ..
```

Valida:

```bash
pnpm verify
OPENSPEC_TELEMETRY=0 pnpm exec openspec validate dev-6 --strict --no-interactive
```

Revisa:

```bash
git status
git diff
```

Commit:

```bash
git add .
git commit -m "feat: inicializar monorepo"
```

Push:

```bash
git push -u origin feat/dev-5-inicializar-monorepo
```

Crear PR:

```text
[DEV-5] Inicializar monorepo
```

Después del merge:

```bash
git switch main
git pull origin main

git branch -d feat/dev-5-inicializar-monorepo
```

---

# Convención resumida

```text
Linear
DEV-5

OpenSpec
dev-5

Branch
feat/dev-5-descripcion

Commit
feat(scope): descripcion

Pull Request
[DEV-5] Descripción

Destino
main
```

La regla general es:

> Un ticket, una branch, un cambio OpenSpec y un Pull Request.