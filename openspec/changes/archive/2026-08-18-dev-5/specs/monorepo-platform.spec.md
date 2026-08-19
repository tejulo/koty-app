# Monorepo Platform Specification

## ADDED Requirements

### Requirement: Configuración del monorepo con pnpm

El workspace utiliza pnpm como gestor de paquetes. Se crea la estructura de directorios para las aplicaciones y paquetes.

#### Scenario: Estructura de workspaces con pnpm
- GIVEN El proyecto no tiene configuración de workspace
- WHEN Se ejecuta la configuración inicial del monorepo
- THEN Existe un archivo `pnpm-workspace.yaml` en la raíz
- AND Existe un `package.json` en la raíz con scripts de build, dev y lint para el workspace
- AND El archivo `pnpm-lock.yaml` es versionable

#### Scenario: Directorios de aplicaciones y paquetes
- GIVEN El workspace está configurado
- WHEN Se verifica la estructura
- THEN Existe `apps/web` como directorio de la aplicación web
- AND Existe `apps/api` como directorio de la API
- AND Existe `apps/worker` como directorio del worker
- AND Existe `packages/contracts` como directorio de contratos compartidos
- AND Existe `packages/config` como directorio de configuraciones compartidas

---

### Requirement: Aplicación web con Next.js App Router

La aplicación web está configurada con Next.js App Router, Tailwind CSS y shadcn/ui.

#### Scenario: Aplicación web inicializada correctamente
- GIVEN El directorio `apps/web` existe
- WHEN Se verifica la configuración
- THEN El proyecto usa Next.js con App Router (directorio `app/`)
- AND Tailwind CSS está configurado
- AND shadcn/ui está configurado e inicializado
- AND El proyecto compila sin errores con `pnpm build` dentro de `apps/web`

#### Scenario: Aplicación web arrancable en desarrollo
- GIVEN La aplicación web está configurada
- WHEN Se ejecuta `pnpm dev` en `apps/web` o desde la raíz
- THEN La aplicación arranca en el puerto configurado
- AND El servidor de desarrollo está disponible

---

### Requirement: API con NestJS

La API está configurada con NestJS.

#### Scenario: API NestJS inicializada correctamente
- GIVEN El directorio `apps/api` existe
- WHEN Se verifica la configuración
- THEN El proyecto usa NestJS como framework
- AND TypeScript está configurado
- AND El proyecto compila sin errores con `pnpm build` dentro de `apps/api`

#### Scenario: API arrancable en desarrollo
- GIVEN La API está configurada
- WHEN Se ejecuta `pnpm start:dev` en `apps/api` o desde la raíz
- THEN La aplicación NestJS arranca
- AND El servidor está disponible en el puerto configurado

---

### Requirement: Worker como proceso independiente

El worker puede arrancar como proceso independiente.

#### Scenario: Worker inicializado correctamente
- GIVEN El directorio `apps/worker` existe
- WHEN Se verifica la configuración
- THEN El proyecto compila sin errores con `pnpm build` dentro de `apps/worker`

#### Scenario: Worker arrancable en desarrollo
- GIVEN El worker está configurado
- WHEN Se ejecuta el comando de arranque en `apps/worker` o desde la raíz
- THEN El worker arranca como proceso independiente
- AND El proceso no depende de la API o web para funcionar

---

### Requirement: Compilación desde la raíz del repositorio

El proyecto completo compila desde la raíz del repositorio.

#### Scenario: Compilación del workspace completo
- GIVEN El monorepo está configurado
- WHEN Se ejecuta `pnpm -r build` o `pnpm build` en la raíz
- THEN Todas las aplicaciones y paquetes compilan sin errores
- AND Cada aplicación genera sus artefactos de build en su directorio correspondiente

#### Scenario: Cada aplicación compila por separado
- GIVEN Cada aplicación tiene su propio package.json
- WHEN Se ejecuta el comando build en `apps/web`
- THEN La compilación de web termina sin errores
- AND Los artefactos se generan en `apps/web/.next` o equivalente
- WHEN Se ejecuta el comando build en `apps/api`
- THEN La compilación de api termina sin errores
- AND Los artefactos se generan en `apps/api/dist`
- WHEN Se ejecuta el comando build en `apps/worker`
- THEN La compilación de worker termina sin errores
- AND Los artefactos se generan en `apps/worker/dist`

---

### Requirement: Control de versiones de lockfile y herramientas

El archivo de bloqueo y las versiones de herramientas quedan versionados.

#### Scenario: Lockfile versionado
- GIVEN El monorepo está configurado con pnpm
- WHEN Se genera el lockfile
- THEN El archivo `pnpm-lock.yaml` existe en la raíz
- AND El `.gitignore` permite commitear el lockfile

#### Scenario: Versiones de herramientas especificadas
- GIVEN El workspace está configurado
- WHEN Se verifica el package.json raíz
- THEN Las versiones de Node.js y pnpm están especificadas (engines)
- AND El lockfile está registrado en el repositorio
