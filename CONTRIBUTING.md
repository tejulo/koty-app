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
* OpenSpec CLI

Verifica:

```bash
git --version
node --version
pnpm --version
docker --version
python --version
uv --version
openspec --version
```

Consulta el `README.md` principal para las instrucciones completas de instalación.

---

# 2. Rama principal

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

# 3. Flujo general de desarrollo

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

# 4. Antes de comenzar un ticket

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

# 5. Convención de nombres de branches

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
feat/dev-5-inicializar-monorepo
feat/dev-20-agregar-autenticacion
```

### fix

Corrección de errores.

```text
fix/dev-12-corregir-login
fix/dev-23-corregir-validacion-email
```

### refactor

Cambios internos que no agregan nuevas funcionalidades ni corrigen directamente un bug.

```text
refactor/dev-18-reorganizar-auth
```

### docs

Cambios de documentación.

```text
docs/dev-22-actualizar-readme
```

### test

Cambios relacionados principalmente con tests.

```text
test/dev-30-agregar-tests-auth
```

### chore

Mantenimiento general.

```text
chore/dev-35-actualizar-dependencias
```

### build

Cambios relacionados con herramientas de compilación o packaging.

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

# 6. Crear una branch

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

# 7. Relación entre Linear, OpenSpec y Git

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

# 8. Flujo con CrewAI

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

El Crew debe ejecutarse desde la branch correspondiente al ticket.

Ejemplo:

```bash
git switch -c feat/dev-5-inicializar-monorepo

cd crewai

uv run run_crew dev-5
```

No ejecutes el Crew para desarrollar una feature directamente sobre:

```text
main
```

---

# 9. OpenSpec

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

# 10. Validar OpenSpec

Antes de considerar terminado un cambio:

```bash
openspec validate dev-5 --strict --no-interactive
```

También puedes revisar tareas pendientes:

```bash
grep -n '\[ \]' openspec/changes/dev-5/tasks.md
```

Si no devuelve resultados, todas las tareas están marcadas como completadas.

---

# 11. Reintentar un cambio rechazado

Si el Reviewer rechaza un cambio, no elimines automáticamente:

```text
openspec/changes/dev-5/
```

Corrige los problemas indicados y vuelve a ejecutar:

```bash
cd crewai

uv run run_crew dev-5
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

# 12. Validaciones obligatorias

Antes de crear un Pull Request, deben ejecutarse las validaciones del monorepo.

Desde la raíz:

```bash
pnpm lint
pnpm test
pnpm build
```

Todas deben finalizar correctamente.

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
openspec validate dev-5 --strict --no-interactive
```

---

# 13. Checklist antes del commit

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

# 14. Archivos que no deben subirse

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

# 15. Lockfiles

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

# 16. Convención de commits

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

# 17. Tipos de commits

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

# 18. Scope de commits

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

# 19. Crear commits

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

# 20. Commits pequeños

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

# 21. Subir la branch

La primera vez:

```bash
git push -u origin feat/dev-5-inicializar-monorepo
```

Después:

```bash
git push
```

---

# 22. Pull Requests

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

# 23. Convención de títulos de Pull Request

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

# 24. Contenido recomendado del Pull Request

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

# 25. Revisión antes del PR

Ejecuta:

```bash
pnpm lint
pnpm test
pnpm build
```

Después:

```bash
openspec validate dev-5 --strict --no-interactive
```

Y:

```bash
git status
git diff main...HEAD
```

---

# 26. Merge

Un Pull Request puede integrarse a `main` cuando:

* la implementación cumple el ticket;
* las validaciones pasan;
* OpenSpec es válido;
* la revisión de código fue aprobada;
* CI pasa si está configurado.

---

# 27. Estrategia recomendada de merge

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

# 28. Después del merge

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

# 29. Comenzar el siguiente ticket

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

# 30. Mantener una branch actualizada

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

# 31. Conflictos durante rebase

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

# 32. Hotfixes

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

# 33. Cambios sin ticket

Siempre que sea posible, todo cambio debe estar asociado a un ticket.

Para cambios administrativos pequeños que excepcionalmente no tengan ticket, puede utilizarse:

```text
chore/actualizar-documentacion
```

Sin embargo, se recomienda crear un ticket incluso para cambios técnicos importantes.

Esto mantiene la trazabilidad.

---

# 34. No mezclar tickets

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

Si aparece trabajo adicional, crea otro ticket y otra branch.

---

# 35. No desarrollar sobre branches de otros tickets

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

# 36. Branches dependientes

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

# 37. Cambios generados por CrewAI

CrewAI puede modificar muchos archivos.

Después de cada ejecución revisa obligatoriamente:

```bash
git status
git diff
```

No asumas que porque el Reviewer del Crew aprobó el cambio todo debe agregarse automáticamente al commit.

La revisión humana del diff sigue siendo necesaria.

---

# 38. OpenSpec y Git

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

# 39. CrewAI y Git

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

# 40. Definition of Done

Un ticket se considera terminado cuando:

* [ ] el ticket fue implementado;
* [ ] los requisitos de OpenSpec están cubiertos;
* [ ] todas las tasks de OpenSpec están completas;
* [ ] `pnpm lint` pasa;
* [ ] `pnpm test` pasa;
* [ ] `pnpm build` pasa;
* [ ] la validación Python pasa cuando corresponda;
* [ ] `openspec validate` pasa;
* [ ] no hay secretos en Git;
* [ ] el diff fue revisado;
* [ ] la branch fue subida;
* [ ] existe Pull Request;
* [ ] el PR fue aprobado;
* [ ] CI pasa;
* [ ] el cambio fue integrado a `main`.

---

# 41. Resumen rápido

Para un ticket:

```text
DEV-5
```

Ejecuta:

```bash
git switch main
git pull origin main

git switch -c feat/dev-5-inicializar-monorepo
```

Si corresponde usar CrewAI:

```bash
cd crewai
uv run run_crew dev-5
cd ..
```

Valida:

```bash
pnpm lint
pnpm test
pnpm build

openspec validate dev-5 --strict --no-interactive
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

