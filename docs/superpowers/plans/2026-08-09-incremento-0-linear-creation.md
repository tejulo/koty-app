# Incremento 0 Linear Ticket Creation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear en Linear los 35 tickets aprobados del Incremento 0 y verificar que cada uno conserve su titulo, descripcion, criterios y destino correctos.

**Architecture:** `docs/superpowers/specs/2026-08-09-incremento-0-linear-tickets-design.md` es la fuente unica. Los issues se crean por bloques tematicos, se conserva un mapa entre numero de diseno e identificador Linear, y las dependencias criticas se agregan despues para no depender del orden de asignacion de identificadores.

**Tech Stack:** Linear MCP, workspace `tejulo`, team `dev`, proyecto `koty-app`.

## Global Constraints

- Crear exactamente 35 issues y no crear epics, milestones, labels, prioridades o asignaciones no solicitadas.
- Usar el campo `title` de Linear para `Titulo` y guardar en la descripcion solamente `Descripcion` y `Criterios de Aceptacion`.
- Mantener entre tres y cinco criterios por issue, sin resumir ni reinterpretar el texto aprobado.
- No duplicar un issue si una llamada falla: volver a listar y comparar por titulo antes de reintentar.
- Mantener todos los issues en el team `dev` y proyecto `koty-app`.

---

### Task 1: Revalidar el destino y los duplicados

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-linear-tickets-design.md`
- Modify: ninguno

**Interfaces:**
- Consumes: proyecto `koty-app`, team `dev`, lista actual de issues del proyecto.
- Produces: identificadores confirmados de team y proyecto, y una lista de titulos que no deben recrearse.

- [ ] Consultar el proyecto `koty-app` y confirmar que pertenece al team `dev`.
- [ ] Listar todos los issues actuales del proyecto, incluidos los archivados.
- [ ] Comparar los titulos existentes con los 35 titulos de la especificacion.
- [ ] Si existe un titulo identico, reutilizar ese issue solo si su cuerpo coincide; de lo contrario, detener la carga para evitar sobrescribir trabajo ajeno.

### Task 2: Crear los tickets de plataforma local

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-linear-tickets-design.md:14-82`
- Modify: ninguno

**Interfaces:**
- Consumes: tickets de diseno 1 a 5 y los identificadores de team/proyecto.
- Produces: mapa de tickets 1 a 5 hacia sus identificadores y URLs Linear.

- [ ] Crear los cinco issues con `linear_save_issue`, sin asignado, prioridad, labels ni ciclo.
- [ ] Confirmar en cada respuesta el team `dev` y proyecto `koty-app`.
- [ ] Registrar identificador, titulo y URL de cada issue creado.
- [ ] Si una llamada falla, listar el proyecto y reintentar solo el titulo ausente.

### Task 3: Crear los tickets de identidad, sesiones y email

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-linear-tickets-design.md:83-194`
- Modify: ninguno

**Interfaces:**
- Consumes: tickets de diseno 6 a 13 y los identificadores de team/proyecto.
- Produces: mapa de tickets 6 a 13 hacia sus identificadores y URLs Linear.

- [ ] Crear los ocho issues con el texto aprobado completo.
- [ ] Confirmar que cada cuerpo contiene una descripcion y entre tres y cinco criterios.
- [ ] Registrar identificador, titulo y URL de cada issue creado.
- [ ] Ante un resultado parcial, reconciliar por titulo antes de continuar.

### Task 4: Crear los tickets de organizaciones y autorizacion

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-linear-tickets-design.md:195-362`
- Modify: ninguno

**Interfaces:**
- Consumes: tickets de diseno 14 a 25 y los identificadores de team/proyecto.
- Produces: mapa de tickets 14 a 25 hacia sus identificadores y URLs Linear.

- [ ] Crear los doce issues con el texto aprobado completo.
- [ ] Mantener separados los tickets de membresias, roles, elevacion, planos y aislamiento.
- [ ] Registrar identificador, titulo y URL de cada issue creado.
- [ ] Ante un resultado parcial, reconciliar por titulo antes de continuar.

### Task 5: Crear los tickets de auditoria, outbox y jobs

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-linear-tickets-design.md:363-460`
- Modify: ninguno

**Interfaces:**
- Consumes: tickets de diseno 26 a 32 y los identificadores de team/proyecto.
- Produces: mapa de tickets 26 a 32 hacia sus identificadores y URLs Linear.

- [ ] Crear los siete issues con el texto aprobado completo.
- [ ] Confirmar que outbox, dispatcher, lease y reejecucion permanecen como capacidades distintas.
- [ ] Registrar identificador, titulo y URL de cada issue creado.
- [ ] Ante un resultado parcial, reconciliar por titulo antes de continuar.

### Task 6: Crear los tickets de operacion y aceptacion

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-linear-tickets-design.md:461-502`
- Modify: ninguno

**Interfaces:**
- Consumes: tickets de diseno 33 a 35 y los identificadores de team/proyecto.
- Produces: mapa completo de los 35 tickets hacia sus identificadores y URLs Linear.

- [ ] Crear los tres issues con el texto aprobado completo.
- [ ] Registrar identificador, titulo y URL de cada issue creado.
- [ ] Confirmar que el mapa contiene exactamente 35 entradas unicas.

### Task 7: Agregar dependencias criticas

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-linear-tickets-design.md:503-512`
- Modify: ninguno

**Interfaces:**
- Consumes: mapa completo entre numero de diseno e identificador Linear.
- Produces: relaciones `blockedBy` que expresan solo prerequisitos tecnicos obligatorios.

- [ ] Relacionar plataforma: 2 por 1; 3 por 2; 4 por 1; 5 por 1, 2, 3 y 4.
- [ ] Relacionar sustrato: 26 por 3 y 4; 27 por 26; 28 por 3 y 4; 29 por 3, 4 y 28; 30 por 29.
- [ ] Relacionar identidad: 6 por 4, 26 y 29; 7 por 6; 8 por 7; 9 y 11 por 8; 10 por 7 y 12; 12 por 30, 31 y 32; 13 por 12.
- [ ] Relacionar organizaciones: 14 por 28 y 29; 15 por 7 y 14; 16 por 7, 26, 28 y 29; 17 por 12, 15, 16 y 22; 18 por 8, 15 y 16; 19 y 20 por 15 y 16; 21 por 15, 16 y 22; 22 por 15 y 16; 23 por 21, 22 y 27; 24 por 8, 21 y 22; 25 por 3 y 24.
- [ ] Relacionar worker y cierre: 31 por 20, 24 y 30; 32 por 31; 33 y 34 por 13 y 32; 35 por 5, 11, 13, 17, 18, 20, 23, 25, 27, 32, 33 y 34.

### Task 8: Verificar la carga final

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-linear-tickets-design.md`
- Modify: ninguno

**Interfaces:**
- Consumes: issues creados y relaciones agregadas.
- Produces: evidencia final y lista copiable con identificador, titulo y URL.

- [ ] Listar todos los issues del proyecto con titulo, descripcion, team, proyecto y relaciones.
- [ ] Confirmar exactamente 35 titulos unicos y comparar cada cuerpo con la especificacion.
- [ ] Confirmar que ningun issue quedo fuera del team `dev` o proyecto `koty-app`.
- [ ] Revisar las dependencias para detectar ciclos.
- [ ] Entregar al usuario la lista completa en el formato solicitado y resumir cualquier desviacion real.
