# api-app Specification

## Purpose
Define la configuración, ejecución y compilación independiente de la API con NestJS y TypeScript.
## Requirements
### Requirement: API NestJS inicializada correctamente

The API SHALL be configured with NestJS.

#### Scenario: API NestJS configurada correctamente
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

#### Scenario: API compilable por separado
- GIVEN La API tiene su propio package.json
- WHEN Se ejecuta el comando build en `apps/api`
- THEN La compilación termina sin errores
- AND Los artefactos se generan en `apps/api/dist`
