# Workspace Monorepo Configuration

## ADDED Requirements

### Requirement: Estructura de workspaces con pnpm

The workspace SHALL use pnpm as the package manager and have the correct directory structure.

#### Scenario: Archivo pnpm-workspace.yaml existe
- GIVEN El proyecto no tiene configuración de workspace
- WHEN Se ejecuta la configuración inicial del monorepo
- THEN Existe un archivo `pnpm-workspace.yaml` en la raíz
- AND Define los directorios `apps/*` y `packages/*`

#### Scenario: Package.json raíz configurado
- GIVEN El workspace está configurado
- WHEN Se verifica la configuración
- THEN Existe un `package.json` en la raíz
- AND Incluye scripts de build, dev y lint para el workspace
- AND Especifica engines para node y pnpm

#### Scenario: Lockfile versionable
- GIVEN El monorepo está configurado con pnpm
- WHEN Se genera el lockfile
- THEN El archivo `pnpm-lock.yaml` existe en la raíz
- AND El `.gitignore` permite versionar el lockfile

#### Scenario: Estructura de directorios de aplicaciones y paquetes
- GIVEN El workspace está configurado
- WHEN Se verifica la estructura
- THEN Existe `apps/web` como directorio de la aplicación web
- AND Existe `apps/api` como directorio de la API
- AND Existe `apps/worker` como directorio del worker
- AND Existe `packages/contracts` como directorio de contratos compartidos
- AND Existe `packages/config` como directorio de configuraciones compartidas
