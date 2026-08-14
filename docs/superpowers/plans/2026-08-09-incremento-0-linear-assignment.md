# Incremento 0 Linear Assignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Asignar los 35 tickets del Incremento 0 a Juan y Avi segun el reparto aprobado y verificar el equilibrio y las dependencias cruzadas.

**Architecture:** `docs/superpowers/specs/2026-08-09-incremento-0-ticket-assignment-design.md` es la fuente unica del reparto. Las actualizaciones se hacen en dos lotes disjuntos por usuario y se verifican mediante una lectura completa del proyecto, sin cambiar titulos, descripciones, estados, prioridades ni relaciones.

**Tech Stack:** Linear MCP, workspace `tejulo`, team `dev`, proyecto `koty-app`.

## Global Constraints

- Juan usa el usuario Linear `33eaeaa0-6af8-4f15-9ea2-ba840b189dd1`.
- Avi usa el usuario Linear `d6da7e04-28f6-4d0d-89bf-7277e52ee6e4`.
- Solo se modifica el campo `assignee`.
- El resultado debe contener 18 tickets de Juan y 17 de Avi.
- Los 35 tickets deben conservar team `dev`, proyecto `koty-app`, estado y relaciones existentes.
- Si una actualización falla, se vuelve a listar antes de reintentar para no sobrescribir cambios concurrentes.

---

### Task 1: Revalidar usuarios y asignaciones actuales

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-ticket-assignment-design.md`
- Modify: ninguno

**Interfaces:**
- Consumes: usuarios `juanmb86`, `avi.alvarenga5` y los 35 issues del proyecto.
- Produces: estado actual reconciliado antes de escribir.

- [ ] Consultar ambos usuarios y confirmar que siguen activos en el team `dev`.
- [ ] Listar los 35 tickets y comprobar que ninguno fue reasignado desde la aprobacion.
- [ ] Detener la operacion si aparece un tercer assignee o cambia el conjunto de tickets.

### Task 2: Asignar los 18 tickets de Juan

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-ticket-assignment-design.md:20-39`
- Modify: ninguno

**Interfaces:**
- Consumes: usuario de Juan y tickets `DEV-5`, `DEV-9`, `DEV-6`, `DEV-7`, `DEV-8`, `DEV-17`, `DEV-11`, `DEV-16`, `DEV-15`, `DEV-18`, `DEV-31`, `DEV-36`, `DEV-32`, `DEV-34`, `DEV-33`, `DEV-35`, `DEV-39`, `DEV-37`.
- Produces: 18 issues asignados a Juan.

- [ ] Actualizar solo `assignee` en los 18 issues.
- [ ] Confirmar que cada respuesta conserva titulo, proyecto, team y estado.
- [ ] Reconciliar por identificador antes de reintentar cualquier fallo parcial.

### Task 3: Asignar los 17 tickets de Avi

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-ticket-assignment-design.md:41-59`
- Modify: ninguno

**Interfaces:**
- Consumes: usuario de Avi y tickets `DEV-13`, `DEV-10`, `DEV-12`, `DEV-14`, `DEV-21`, `DEV-19`, `DEV-23`, `DEV-24`, `DEV-28`, `DEV-25`, `DEV-29`, `DEV-22`, `DEV-27`, `DEV-26`, `DEV-20`, `DEV-30`, `DEV-38`.
- Produces: 17 issues asignados a Avi.

- [ ] Actualizar solo `assignee` en los 17 issues.
- [ ] Confirmar que cada respuesta conserva titulo, proyecto, team y estado.
- [ ] Reconciliar por identificador antes de reintentar cualquier fallo parcial.

### Task 4: Verificar el reparto final

**Files:**
- Read: `docs/superpowers/specs/2026-08-09-incremento-0-ticket-assignment-design.md`
- Modify: ninguno

**Interfaces:**
- Consumes: lista final de issues con assignee y relaciones.
- Produces: evidencia de reparto `18/17`, cobertura completa y 16 dependencias cruzadas.

- [ ] Listar los 35 tickets con identificador, titulo, assignee, team, proyecto y estado.
- [ ] Confirmar que Juan tiene exactamente los 18 identificadores aprobados.
- [ ] Confirmar que Avi tiene exactamente los 17 identificadores aprobados.
- [ ] Confirmar que no existe un ticket sin asignar o con una tercera persona.
- [ ] Revisar las 81 relaciones y confirmar 65 internas, 16 cruzadas y solo tres cruces de Avi hacia Juan.
