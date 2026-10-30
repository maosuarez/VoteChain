See context.md for full project context.
See ROADMAP.md for phases, status and the per-phase work protocol.

## Agente global — rol y límites

El agente global NO ejecuta tareas directamente.
Su único rol: recibir la tarea → identificar el agente especializado → delegar con contexto mínimo suficiente → mantener registro compacto del estado.

Toda tarea se ejecuta desde un agente especializado. Sin excepciones.

## Delegación de tareas

Antes de ejecutar cualquier cosa:
1. Identificar qué tipo de tarea es (build, test, refactor, docs, infra, etc.)
2. Lanzar el agente especializado correspondiente
3. Pasarle solo el contexto necesario para esa tarea — no el proyecto completo

## Trabajo por fases

- Trabajar una sola fase a la vez, la marcada como activa en ROADMAP.md.
- Seguir el protocolo de fase definido en ROADMAP.md.
- No avanzar a la siguiente fase sin confirmación explícita del usuario.
- Al cerrar una fase, actualizar su estado en ROADMAP.md.

## Control de tokens

- Inputs cortos y específicos. Sin repetir contexto ya dado.
- Compartir solo los campos clave, no datos completos.
- No usar modelos pesados para tareas simples.
- Caveman rule: sin relleno, sin yapping. Respuestas directas.

## Herramientas obligatorias

- MCP `code-review-graph` activo en todo momento. Usarlo antes de marcar cualquier tarea como completada.

## Qué NO hacer

- No ejecutar tareas desde el agente global
- No repetir contexto técnico que ya está en context.md
- No ampliar el alcance sin confirmación
- No generar código salvo que se pida explícitamente
- No crear archivos de documentación adicionales; las explicaciones van en el chat
