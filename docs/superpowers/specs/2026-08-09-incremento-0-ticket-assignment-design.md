# Diseno de asignacion de tickets del Incremento 0

## Objetivo

Asignar los 35 tickets del proyecto Linear `koty-app` entre `juanmb86` y `avi.alvarenga5` de forma equitativa, manteniendo juntas tantas dependencias como sea posible y respetando sus especialidades.

## Identidades Linear

- Juan: `juanmb86`, usuario `33eaeaa0-6af8-4f15-9ea2-ba840b189dd1`.
- Avi: `avi.alvarenga5`, usuario `d6da7e04-28f6-4d0d-89bf-7277e52ee6e4`.

## Criterios

- El reparto por cantidad es 18 tickets para Juan y 17 para Avi.
- Juan prioriza backend, infraestructura, identidad y seguridad.
- Avi prioriza frontend y flujos web, sin restriccion para recibir capacidades relacionadas.
- Se minimizan dependencias cruzadas sin separar artificialmente un ticket vertical.
- Ningun ticket queda sin asignar o asignado a una tercera persona.

## Asignacion a Juan

1. `DEV-5` Inicializar el monorepo de la plataforma.
2. `DEV-9` Configurar el entorno local con PostgreSQL.
3. `DEV-6` Preparar migraciones reproducibles con Prisma.
4. `DEV-7` Establecer el contrato base de la API v1.
5. `DEV-8` Automatizar los controles de calidad del repositorio.
6. `DEV-17` Solicitar el registro de una cuenta.
7. `DEV-11` Recuperar una contrasena olvidada.
8. `DEV-16` Enviar emails de identidad de forma confiable.
9. `DEV-15` Registrar los eventos de entrega de Resend.
10. `DEV-18` Crear una organizacion pendiente desde plataforma.
11. `DEV-31` Procesar comandos sensibles con idempotencia.
12. `DEV-36` Registrar una auditoria append-only.
13. `DEV-32` Guardar eventos en un outbox transaccional.
14. `DEV-34` Convertir el outbox en jobs persistentes.
15. `DEV-33` Ejecutar jobs con lease y fencing token.
16. `DEV-35` Gestionar reintentos y reejecuciones de jobs.
17. `DEV-39` Exponer salud y observabilidad de la plataforma.
18. `DEV-37` Probar respaldo y restauracion sin egress.

## Asignacion a Avi

1. `DEV-13` Verificar el email y establecer la contrasena.
2. `DEV-10` Iniciar sesion con una sesion opaca.
3. `DEV-12` Administrar las sesiones activas.
4. `DEV-14` Proteger las mutaciones autenticadas.
5. `DEV-21` Activar una organizacion con la invitacion inicial.
6. `DEV-19` Autorregistrar una organizacion activa.
7. `DEV-23` Administrar invitaciones de miembros.
8. `DEV-24` Cambiar el contexto activo de organizacion.
9. `DEV-28` Configurar el perfil y la zona horaria de la organizacion.
10. `DEV-25` Suspender y reactivar una organizacion.
11. `DEV-29` Administrar membresias de la organizacion.
12. `DEV-22` Configurar roles y permisos.
13. `DEV-27` Impedir elevaciones y conservar un administrador raiz.
14. `DEV-26` Separar los planos y principales de autorizacion.
15. `DEV-20` Aplicar aislamiento estricto entre organizaciones.
16. `DEV-30` Proteger mutaciones concurrentes y revocaciones.
17. `DEV-38` Validar la puerta de aceptacion del Incremento 0.

## Dependencias cruzadas

El grafo tiene 81 relaciones directas. Esta asignacion conserva 65 dentro de la misma persona y cruza 16.

### Juan bloquea a Avi

- `DEV-31` bloquea `DEV-30`.
- `DEV-17` bloquea `DEV-13`.
- `DEV-18` bloquea `DEV-21`.
- `DEV-31` bloquea `DEV-19`.
- `DEV-36` bloquea `DEV-19`.
- `DEV-32` bloquea `DEV-19`.
- `DEV-16` bloquea `DEV-23`.
- `DEV-6` bloquea `DEV-20`.
- `DEV-8` bloquea `DEV-38`.
- `DEV-15` bloquea `DEV-38`.
- `DEV-35` bloquea `DEV-38`.
- `DEV-39` bloquea `DEV-38`.
- `DEV-37` bloquea `DEV-38`.

### Avi bloquea a Juan

- `DEV-13` bloquea `DEV-11`.
- `DEV-25` bloquea `DEV-33`.
- `DEV-26` bloquea `DEV-33`.

## Resultado esperado

- Juan recibe 18 tickets.
- Avi recibe 17 tickets.
- Los 35 tickets quedan asignados exactamente una vez.
- Las 16 dependencias cruzadas son las unicas excepciones del reparto.
- La mayor parte de los cruces va desde la plataforma de Juan hacia los flujos de Avi; solo tres cruces obligan a Juan a esperar una tarea de Avi.
