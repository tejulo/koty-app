# Transiciones Linear desde CrewAI

## Objetivo

Permitir que el agente `analyst` mueva el ticket procesado a `In Progress` al
inicio del flujo y que `reviewer` lo mueva a `Done` solamente al finalizar con
implementacion, verificaciones y OpenSpec correctos.

## Flujo

El crew conserva su proceso secuencial:

1. `analysis_task` busca el ticket real y solicita `In Progress` antes de
   analizarlo.
2. `architecture_task` crea y valida los artefactos OpenSpec.
3. `coding_task` implementa, completa `tasks.md` y ejecuta verificaciones.
4. `review_task` revisa, valida, archiva, repite verificaciones y solicita
   `Done` como ultima accion.

## Autoridad De Las Tools

Se agregan dos tools distintas; no existe una tool generica para elegir estados:

- `Marcar Tarea en Progreso`, disponible solo para `analyst`.
- `Completar Tarea en Linear`, disponible solo para `reviewer`.

Ambas usan `LINEAR_API_KEY`, restringen el ticket al team `dev` y proyecto
`koty-app`, comprueban el estado anterior, ejecutan `issueUpdate` con unicamente
`stateId` y releen el ticket para confirmar la transicion.

`In Progress` requiere:

- El mismo ticket fue recuperado antes mediante `Buscar Tarea en Linear`.
- Su estado actual es `Backlog` o `Todo`.

`Done` requiere:

- El mismo ticket fue iniciado por este proceso y sigue en `In Progress`.
- `python`, `lint`, `test` y `build` terminaron correctamente despues del
  archive, que tambien modifica archivos del repositorio.
- El cambio tuvo `openspec validate` exitoso despues de la ultima escritura de
  sus artefactos.
- `openspec archive` termino correctamente.
- El cambio activo ya no existe y existe su directorio archivado.

La evidencia vive solamente durante una ejecucion del proceso. Escribir un
archivo o archivar un cambio invalida las verificaciones previas; escribir dentro
del cambio invalida ademas su validacion y archive.

## Fallos

Las nuevas tools devuelven `ToolFailure` ante configuracion faltante, alcance o
estado incorrectos, rechazo GraphQL, evidencia incompleta o postcondicion no
confirmada. `analyst` y `reviewer` usan `ToolFailurePolicy.RAISE`, por lo que el
crew se detiene y no permite que el error se narre como un resultado exitoso.

No se revierte automaticamente `In Progress` cuando falla una etapa posterior.
No se marca `Done` confiando solamente en el texto final del LLM.

## Archivos

- `src/crew/config/agents.yaml`: responsabilidades de las transiciones.
- `src/crew/config/tasks.yaml`: orden obligatorio de las llamadas.
- `src/crew/crew.py`: tools exclusivas y politica de fallos.
- `src/crew/tools/custom_tool.py`: cliente Linear compartido, evidencia y gates.
- `tests/test_custom_tool.py`: transiciones permitidas y rechazadas.

## Verificacion

- Tests unitarios sin llamadas reales a Linear ni subprocess reales.
- Carga de la configuracion YAML y construccion del crew con variables ficticias.
- `uv run pytest` y compilacion del paquete.

CrewAI instalado permanece en `1.15.16`. La actualizacion disponible a
`1.15.17` queda fuera de este cambio.
