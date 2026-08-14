# Diseno de dificultad y prioridad del Incremento 0

## Objetivo

Asignar prioridad y dificultad a los 35 tickets del proyecto Linear `koty-app`
sin cambiar responsables, estado, proyecto ni dependencias.

## Criterios

- La dificultad usa estimaciones Fibonacci `1`, `2`, `3`, `5` y `8`.
- Ningun ticket recibe `1` porque todos representan capacidades verticales no
  triviales.
- `2` identifica un alcance pequeno y acotado.
- `3` identifica complejidad moderada.
- `5` identifica seguridad, integracion o trabajo en varias capas.
- `8` identifica concurrencia, alcance transversal, recuperacion o validacion
  amplia.
- La prioridad combina riesgo tecnico y posicion en el grafo de dependencias.
- `Low` expresa menor prioridad inmediata dentro del incremento; no convierte
  el ticket en opcional.

## Clasificacion aprobada

| Ticket | Prioridad | Dificultad |
| --- | --- | ---: |
| `DEV-5` | Urgent | 5 |
| `DEV-6` | Urgent | 3 |
| `DEV-7` | Urgent | 3 |
| `DEV-8` | High | 5 |
| `DEV-9` | Urgent | 2 |
| `DEV-10` | High | 5 |
| `DEV-11` | Medium | 5 |
| `DEV-12` | Medium | 3 |
| `DEV-13` | Urgent | 5 |
| `DEV-14` | High | 5 |
| `DEV-15` | Low | 5 |
| `DEV-16` | Medium | 5 |
| `DEV-17` | High | 3 |
| `DEV-18` | High | 5 |
| `DEV-19` | High | 8 |
| `DEV-20` | High | 8 |
| `DEV-21` | High | 5 |
| `DEV-22` | High | 5 |
| `DEV-23` | Medium | 5 |
| `DEV-24` | Medium | 5 |
| `DEV-25` | Medium | 5 |
| `DEV-26` | Urgent | 5 |
| `DEV-27` | High | 8 |
| `DEV-28` | Low | 5 |
| `DEV-29` | High | 3 |
| `DEV-30` | High | 8 |
| `DEV-31` | Urgent | 5 |
| `DEV-32` | Urgent | 5 |
| `DEV-33` | High | 8 |
| `DEV-34` | Medium | 5 |
| `DEV-35` | Medium | 5 |
| `DEV-36` | Urgent | 5 |
| `DEV-37` | High | 8 |
| `DEV-38` | High | 8 |
| `DEV-39` | Low | 8 |

## Distribucion

- Prioridad Urgent: 9 tickets.
- Prioridad High: 15 tickets.
- Prioridad Medium: 8 tickets.
- Prioridad Low: 3 tickets.
- Dificultad 2: 1 ticket.
- Dificultad 3: 5 tickets.
- Dificultad 5: 21 tickets.
- Dificultad 8: 8 tickets.

## Verificacion

- Los tickets `DEV-5` a `DEV-39` aparecen exactamente una vez.
- Linear conserva los 35 tickets en el team `dev`, proyecto `koty-app` y estado
  `Backlog`.
- Cada ticket conserva su responsable actual.
- Cada ticket recibe la prioridad y estimacion indicadas en la tabla.
