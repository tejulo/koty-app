# DEV-5: Tareas de Implementación

## Monorepo Base

- [x] **Crear `package.json` raíz** con nombre `koty-app`, scripts workspace (`dev`, `build`, `lint`, `clean`), y engines (node, pnpm)
- [x] **Crear `pnpm-workspace.yaml`** definiendo los directorios `apps/*` y `packages/*`
- [x] **Crear `.npmrc`** con configuración `shamefully-hoist=false`
- [x] **Crear `.gitignore`** base excluyendo `node_modules` pero incluyendo `pnpm-lock.yaml`
- [x] **Crear archivo `pnpm-lock.yaml`** ejecutando `pnpm install`
- [x] **Verificar** que el workspace está configurado correctamente

## packages/contracts

- [x] **Crear directorio `packages/contracts/`**
- [x] **Crear `packages/contracts/package.json`** con nombre `@koty-app/contracts`, tipo `module`, y scripts básicos
- [x] **Crear `packages/contracts/tsconfig.json`** extendiendo configuración base
- [x] **Crear `packages/contracts/src/index.ts`** exportando tipos/schemas base (vacío inicialmente)
- [x] **Compilar** `packages/contracts` con `pnpm build`

## packages/config

- [x] **Crear directorio `packages/config/`**
- [x] **Crear `packages/config/package.json`** con nombre `@koty-app/config`, tipo `module`
- [x] **Crear `packages/config/eslint/index.js`** configuración ESLint base compartida
- [x] **Crear `packages/config/tsconfig/base.json`** configuración TypeScript base
- [x] **Exportar configuraciones** desde `packages/config`

## apps/web (Next.js)

- [x] **Crear directorio `apps/web/`**
- [x] **Inicializar Next.js** con `npx create-next-app@latest apps/web --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`
- [x] **Actualizar `apps/web/package.json`** con scripts pnpm y referencia al monorepo
- [x] **Configurar `tsconfig.json`** de web para extender `packages/config/tsconfig/base.json`
- [x] **Instalar shadcn/ui** con `pnpm dlx shadcn-ui@latest init`
- [x] **Agregar componentes base** shadcn/ui (Button, Card, Input)
- [x] **Verificar compilación** con `pnpm build` en `apps/web`
- [x] **Verificar desarrollo** con `pnpm dev` en `apps/web`

## apps/api (NestJS)

- [x] **Crear directorio `apps/api/`**
- [x] **Inicializar NestJS** con CLI o manualmente
- [x] **Crear `apps/api/package.json`** con dependencias NestJS y scripts pnpm
- [x] **Crear `apps/api/tsconfig.json`** extendiendo configuración base
- [x] **Crear módulo raíz `AppModule`** con health check endpoint
- [x] **Configurar `main.ts`** con bootstrap básico
- [x] **Agregar `.eslintrc.js`** o configuración ESLint
- [x] **Verificar compilación** con `pnpm build` en `apps/api`
- [x] **Verificar desarrollo** con `pnpm start:dev` en `apps/api`

## apps/worker

- [x] **Crear directorio `apps/worker/`**
- [x] **Crear `apps/worker/package.json`** con scripts pnpm
- [x] **Crear `apps/worker/tsconfig.json`** extendiendo configuración base
- [x] **Crear `apps/worker/src/index.ts`** punto de entrada independiente
- [x] **Crear módulo/funcionalidad básica** del worker
- [x] **Agregar `.eslintrc.js`** o configuración ESLint
- [x] **Verificar compilación** con `pnpm build` en `apps/worker`
- [x] **Verificar arranque** ejecutando worker como proceso independiente

## Verificación del Workspace

- [x] **Compilar todas las apps** ejecutando `pnpm -r build` desde raíz
- [x] **Verificar desarrollo paralelo** ejecutando `pnpm dev` (debe arrancar todas las apps)
- [x] **Verificar lockfile** que `pnpm-lock.yaml` está versionado correctamente
- [x] **Verificar que cada app funciona de forma independiente**

## Tests

- [x] **Agregar configuración de tests** para cada app (opcional en este paso) - FUERA DE ALCANCE según proposal.md
- [x] **Verificar que los builds generan los artefactos esperados** (`.next/`, `dist/`, etc.)
