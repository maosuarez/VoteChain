See docs/context.md for full project context (sistema de votación Balón de Oro 3/2/1, roles, código por correo, blockchain).
Specs y changes: OpenSpec en `openspec/` (flujo `/opsx:*`). ROADMAP.md es el plan histórico; los changes de OpenSpec lo reemplazan.

## Agente global — rol y límites

El agente global NO ejecuta tareas de implementación directamente.
Su rol: recibir la tarea → identificar el agente especializado → delegar con contexto mínimo suficiente → mantener registro compacto del estado.

Toda implementación se ejecuta desde un agente especializado. Edición de documentación de proyecto (CLAUDE.md, context.md, specs de OpenSpec) y planeación pueden hacerse desde el agente global.

## Delegación de tareas

Antes de ejecutar cualquier cosa:
1. Identificar qué tipo de tarea es (build, test, refactor, docs, infra, etc.)
2. Lanzar el agente especializado correspondiente
3. Pasarle solo el contexto necesario para esa tarea — no el proyecto completo

## Trabajo con OpenSpec

- Un change a la vez. Flujo: propose → (specs, design, tasks) → apply → archive.
- Cada change debe tener specs con escenarios verificables antes de implementar.
- No pasar al siguiente change sin confirmación explícita del usuario.
- Dependencias entre changes: respetar el orden definido al planearlos; no implementar algo que dependa de un change no archivado.
- Los specs describen comportamiento; las decisiones de diseño y trade-offs van en `design.md` del change.
- Al archivar, los specs del change se fusionan en `openspec/specs/`.

## Control de tokens

- Inputs cortos y específicos. Sin repetir contexto ya dado.
- Compartir solo los campos clave, no datos completos.
- No usar modelos pesados para tareas simples.
- Caveman rule: sin relleno, sin yapping. Respuestas directas.

## Herramientas obligatorias

- MCP `code-review-graph` activo en todo momento. Usarlo antes de marcar cualquier tarea como completada.
- `openspec` CLI para crear/validar changes (`openspec validate <change>`).

## Reglas del dominio (no negociables)

- Papeleta: 3 picks distintos y ordenados por categoría; puntos 3/2/1.
- El voto nunca debe ser vinculable a la identidad del votante; el master tampoco puede vincularlos.
- Códigos de correo: un solo uso, con expiración, almacenados solo como hash.
- Datos personales (correos, censo) fuera de la cadena.

## Qué NO hacer

- No ejecutar implementación desde el agente global
- No repetir contexto técnico que ya está en docs/context.md
- No ampliar el alcance sin confirmación
- No generar código salvo que se pida explícitamente
- No crear archivos de documentación adicionales; las explicaciones van en el chat
