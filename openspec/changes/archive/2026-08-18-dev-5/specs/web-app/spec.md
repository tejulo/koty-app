# Web Application Configuration

## ADDED Requirements

### Requirement: Aplicación web inicializada con Next.js App Router

The web application SHALL be configured with Next.js App Router, Tailwind CSS, and shadcn/ui.

#### Scenario: Aplicación web configurada correctamente
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

#### Scenario: Aplicación web compilable por separado
- GIVEN La aplicación web tiene su propio package.json
- WHEN Se ejecuta el comando build en `apps/web`
- THEN La compilación termina sin errores
- AND Los artefactos se generan en `apps/web/.next`
