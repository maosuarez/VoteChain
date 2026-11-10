# Tasks

## 1. Verificación de fuentes

- [x] 1.1 Revisar `openspec/specs/`, `openspec/changes/archive/` y `docs/` contra el estado real. Verificación: lista de changes archivados (10) y capacidades (20) coincide con el disco.
- [x] 1.2 Verificar comandos de la CLI (`votechain --help`, `election --help`, `audit --help`, `init --help`) con `.venv/bin/votechain`. Verificación: salida de ayuda muestra los subcomandos documentados.
- [x] 1.3 Verificar `docker-compose.yml` con un `.env` temporal fuera del repositorio. Verificación: `docker compose config --services` lista v1, v2, v3, api, frontend.
- [x] 1.4 Verificar demos `demo_tamper.py` y `demo_unlinkability.py` con el venv. Verificación: ambos terminan con los resultados descritos en el README.

## 2. README

- [x] 2.1 Escribir `README.md` en español: propuesta de valor, problema de los 2 votos, voto 3/2/1, garantías, arquitectura resumida. Verificación: revisión manual contra `openspec/specs/ballot-casting`, `tally` y `blind-credentials`.
- [x] 2.2 Añadir diagrama de flujo en Mermaid (código por correo → credencial anónima → papeleta → cadena → auditoría). Verificación: bloque `mermaid` con sintaxis `flowchart` válida.
- [x] 2.3 Añadir instalación y uso rápido con comandos verificados en 1.2 y 1.3. Verificación: cada comando aparece en la verificación de 1.2 o 1.3, o se marca como no ejecutado.
- [x] 2.4 Añadir sección de limitaciones tomada de `docs/guia-master.md`, `docs/guia-auditoria.md` y `docs/checklist-seguridad.md`. Verificación: cada limitación de esas guías aparece en el README.
- [x] 2.5 Añadir roadmap por changes (10 archivados) y pendientes conocidos. Verificación: nombres coinciden con `openspec/changes/archive/`.
- [x] 2.6 Añadir sección de licencia con la nota "licencia por definir" y sin crear archivo `LICENSE`. Verificación: `ls LICENSE*` no devuelve nada.

## 3. Cierre del change

- [x] 3.1 Validar el change. Verificación: `openspec validate commercial-readme --strict` sin errores.
- [x] 3.2 Revisar que no hay emojis, insignias ni capturas en el README. Verificación: búsqueda de `![` e `img` sin resultados.

## Workflow follow-up

- Archivar con `openspec archive commercial-readme --yes` (usar `--skip-specs` si el CLI lo exige; el change declara `skip_specs`).
- Sin commit: el usuario decide cuándo confirmar.
