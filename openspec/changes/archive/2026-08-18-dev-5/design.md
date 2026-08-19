# DEV-5: Diseño Técnico - Inicialización del Monorepo

## Decisiones Técnicas

### 1. Gestor de Paquetes: pnpm

**Decisión**: Usar `pnpm` como gestor de paquetes del workspace.

**Justificación**:
- Performance superior por uso de content-addressable storage.
- Mejor manejo de dependencias en monorepos.
- Estricto control de dependencias entre paquetes.
- Soporte nativo para workspaces.

**Implementación**:
- Archivo `pnpm-workspace.yaml` en raíz con glob `apps/*` y `packages/*`.
- Configuración de `.npmrc` con `shamefully-hoist=false` para evitar conflictos.

---

### 2. Estructura de Directorios

```
/
├── apps/
│   ├── web/          # Next.js App Router
│   ├── api/          # NestJS
│   └── worker/       # Worker de procesos
├── packages/
│   ├── contracts/    # Tipos y esquemas compartidos
│   └── config/       # Configuraciones compartidas (ESLint, TS)
├── pnpm-workspace.yaml
├── package.json
└── pnpm-lock.yaml
```

---

### 3. Aplicación Web (`apps/web`)

**Stack**:
- Next.js 14+ con App Router
- TypeScript
- Tailwind CSS
- shadcn/ui (CLI)
- ESLint + Prettier

**Configuración**:
- `package.json` con scripts: `dev`, `build`, `start`, `lint`.
- TypeScript con referencias a `packages/config`.
- Configuración de Tailwind con diseño base de shadcn/ui.
- shadcn/ui inicializado con componentes base (Button, Card, etc.).

---

### 4. API (`apps/api`)

**Stack**:
- NestJS
- TypeScript
- ESLint + Prettier

**Configuración**:
- `package.json` con scripts: `start`, `start:dev`, `build`, `lint`.
- TypeScript con `tsconfig.json` propio y referencias a `packages/config`.
- Módulo raíz con controlador health check básico.

---

### 5. Worker (`apps/worker`)

**Stack**:
- Node.js con TypeScript
- Soporte para ejecución como script standalone

**Configuración**:
- `package.json` con scripts: `start`, `start:dev`, `build`, `lint`.
- Punto de entrada independiente (`src/index.ts`).
- Sin dependencias de otros apps en tiempo de ejecución.

---

### 6. Paquetes Compartidos

**`packages/contracts`**:
- Tipos y esquemas Zod compartidos.
- Exports públicos en `src/index.ts`.

**`packages/config`**:
- Configuraciones compartidas de ESLint.
- Configuraciones compartidas de TypeScript (`tsconfig.base.json`).

---

### 7. Scripts del Workspace (Raíz)

```json
{
  "scripts": {
    "dev": "pnpm -r --parallel dev",
    "build": "pnpm -r build",
    "lint": "pnpm -r lint",
    "clean": "pnpm -r --filter=./** clean"
  }
}
```

---

### 8. TypeScript en Monorepo

- Cada app/package tiene su propio `tsconfig.json` que extiende `../../tsconfig.base.json` o configuración propia.
- Referencias de TypeScript entre paquetes cuando sea necesario.
- Compilación independiente por app.

---

### 9. Versionado de Archivos

**Decisión**: Versionar `pnpm-lock.yaml`.

**Justificación**: Garantiza instalaciones reproducibles en todos los entornos.

**Implementación**:
- `.gitignore` excluye node_modules pero incluye `pnpm-lock.yaml`.
- engines en `package.json` especifica versiones de node y pnpm.

---

### 10. Convenciones de Nombres

- Apps: `apps/<nombre-app>`
- Paquetes: `packages/<nombre-paquete>`
- Scripts de build: `pnpm build` en cada app.
- Scripts de dev: `pnpm dev` para desarrollo con hot reload.
