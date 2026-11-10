# Design

## Context

El repositorio no tiene `README.md` (archivo vacío). El estado real del sistema está en `openspec/specs/` (20 capacidades), `openspec/changes/archive/` (10 changes archivados) y `docs/` (guías del master, auditoría y checklist de seguridad). Ver proposal.md - Why para la motivación.

El README debe describir solo lo implementado. Cualquier afirmación que no tenga respaldo en un spec, en el código o en `docs/` queda fuera.

## Goals / Non-Goals

**Goals:**
- Un único `README.md` en español que sirva de punto de entrada para público no técnico (valor, garantías, límites) y para desarrolladores (arquitectura, instalación, comandos).
- Comandos verificados contra el repositorio (`votechain --help`, `docker compose config`, demos).
- Límites declarados en el mismo documento, no solo en `docs/`.

**Non-Goals:**
- No crear otros archivos de documentación (`LICENSE`, `CONTRIBUTING.md`, `docs/*.md` nuevos). La licencia queda como nota "por definir".
- No añadir insignias (no hay CI ni registro público que las respalde) ni capturas de pantalla (no existen capturas reales).
- No duplicar las guías de `docs/`: el README enlaza a ellas.
- No cambiar código, specs ni reglas de dominio.

## Decisions

- **Un solo archivo, sin subdirectorios de docs nuevos.** Alternativa: README corto + `docs/` extenso. Descartada: el proposal pide propuesta de valor, garantías y arquitectura en el primer vistazo; las guías ya existen en `docs/` y se enlazan.
- **Diagrama en Mermaid (`flowchart`)**. Renderiza en GitHub sin assets binarios. Alternativa: imagen PNG/SVG en `docs/`; descartada porque obliga a mantener un archivo externo que no se regenera con el código.
- **Comandos con `uv run` y con el binario del venv como equivalente.** `uv.lock` y `Dockerfile` usan uv; `[project.scripts]` expone `votechain`.
- **Sección de limitaciones tomada de `docs/guia-master.md`, `docs/guia-auditoria.md` y `docs/checklist-seguridad.md`**, reformulada y con las mismas palabras clave (correlación tiempo/IP, sin view-change, token estático, claves en un solo host, claves de emisión sin cifrar, sin protección contra coerción ni compra de votos, auditoría humana pendiente). Mantener ambas fuentes alineadas es responsabilidad de quien cambie esas guías.
- **Roadmap = lista de changes archivados en orden cronológico, más pendientes conocidos.** Los pendientes salen de decisiones abiertas de `docs/context.md` y de limitaciones; no se inventan changes futuros.
- **Licencia: nota "por definir".** Decisión del titular del repositorio. Sin archivo LICENSE, el código queda sin permiso explícito de uso o distribución; el README lo dice sin tomar partido.
- **Datos personales fuera del README.** El `pyproject.toml` contiene autor y correo; el README no los repite.

## Risks / Trade-offs

- [El README envejece al cambiar specs o guías] → Mitigación: la sección de roadmap y limitaciones se revisa al archivar cada change; el README indica que `openspec/specs/` es la fuente de verdad del comportamiento.
- [Afirmaciones de privacidad malinterpretadas como anonimato total] → Mitigación: la sección de garantías separa lo que se garantiza (un voto por credencial, emisor no vincula credencial con persona) de lo que no (correlación tiempo/IP, el master sabe qué correos canjearon código, coerción).
- [Comandos que cambian con la versión de dependencias] → Mitigación: se verificaron con `votechain --help`, `election --help`, `audit --help`, `init --help` y `docker compose config` sobre el repositorio actual. `uv` no está instalado en el entorno de verificación; los comandos `uv run` quedan sin ejecutar y se indica en el reporte.

## Migration Plan

No aplica: solo se crea `README.md` (hoy vacío) y los artefactos del change. Rollback: restaurar el archivo vacío.

## Open Questions

- Ninguna que cambie el alcance. La licencia queda marcada como pendiente en el propio README (decisión del usuario, fuera del change).
