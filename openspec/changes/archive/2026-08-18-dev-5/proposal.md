# DEV-5: Inicializar el monorepo de la plataforma

## Problema

El equipo de desarrollo necesita una base unificada desde la cual ejecutar, desarrollar y mantener la aplicación web, la API y el worker del sistema PLAN-DEPTO. Actualmente no existe una estructura que permita trabajar de forma coordinada en los tres componentes.

## Objetivo

Establecer la estructura base y configuración inicial del repositorio monorepo que alojará y permitirá el desarrollo conjunto de los componentes de la plataforma (web, api, worker).

## Alcance

1. **Configuración del monorepo**: Workspace con `pnpm` como gestor de paquetes.
2. **Estructura de directorios**: Creación de `apps/web`, `apps/api`, `apps/worker`, `packages/contracts`, `packages/config`.
3. **Configuración de aplicaciones**:
   - Web: Next.js App Router, Tailwind CSS, shadcn/ui.
   - API: NestJS.
   - Worker: Proceso independiente arrancable.
4. **Verificación de compilación**: Cada aplicación compila por separado y el proyecto completo compila desde la raíz.
5. **Control de versiones**: `pnpm-lock.yaml` y versiones de herramientas versionados.

## Fuera de Alcance

- Configuración de linting, formateo o testing avanzado.
- Contenido específico de `packages/contracts` o `packages/config`.
- Pipeline CI/CD.
- Despliegue.
- Base de datos o migraciones.
- Autenticación o autorización.

## Impacto Esperado

- El equipo podrá ejecutar cada aplicación de forma independiente.
- El proyecto completo compila sin errores desde la raíz.
- La estructura permite agregar nuevos paquetes y aplicaciones de forma consistente.
- Se sienta la base para los incrementos subsiguientes del proyecto.
