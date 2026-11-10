## 1. Persistencia y correo

- [x] 1.1 `ChainStore` (JSON atómico, validación al cargar, falla si es inválida) y `IssuerKeyStore` (0600) integrados en `VoterAuth` (carga al arrancar, guardado en `set_issuer_key`); `tests/test_persistence.py` cubre reinicio con la misma cadena, canje tras reinicio, cadena corrupta rechazada y permisos.
- [x] 1.2 `SmtpMailer`, `FileMailer` y `mailer_from_env` con fallo de envío contenido; `tests/test_mailer.py` con servidor SMTP falso local y buzón en archivo.

## 2. Red HTTP

- [x] 2.1 `HttpTransport`, cola/hilo de trabajo, bucle de producción/sync y rutas `/p2p/*` en `src/votechain/p2p_http.py`; `tests/test_p2p_http.py` con 3 servidores reales: convergencia, par caído, recuperación, bloque de no validador, persistencia al reiniciar.

## 3. API sobre PoA

- [x] 3.1 `create_app(node=...)` con espera de inclusión y 503, `VOTECHAIN_WEB_DIR`, y `create_api_from_env` / `create_node_from_env` con la configuración por entorno; `tests/test_api_node.py` (acción confirmada, 503, rechazo de dominio, reinicio de la API).

## 4. Auditoría independiente

- [x] 4.1 `audit.py` (validación con validadores de confianza, comparación de nodos, conteo recalculado) y `scripts/explorer_tally.js`; `tests/test_audit.py` cubre cadena alterada, validadores distintos, nodos divergentes y conteo contra el verificador de Node (omitido sin Node).

## 5. CLI

- [x] 5.1 `votechain/cli.py` con `init`, `status`, `check`, `election ...`, `audit`, `serve-node`, `serve-api` (Rich) y entry point en `pyproject.toml`; `tests/test_cli.py` con los escenarios de operations-cli.

## 6. Contenedores

- [x] 6.1 `Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` (3 validadores, perfil `extended`, API, frontend), `.dockerignore` y `.env` ignorado; `tests/test_compose.py` valida el YAML y `docker compose config` si Docker está disponible; se intenta `docker compose up` y el resultado real se documenta.

## 7. E2E

- [x] 7.1 `votechain/e2e.py` y `tests/test_pilot_e2e.py`: elección completa en 3 validadores + API reales, doble voto rechazado, reinicio de un validador y de la API, verificación independiente (Python + explorador JS) y detección de manipulación.

## 8. Documentación

- [x] 8.1 `docs/guia-master.md`, `docs/checklist-seguridad.md`, `docs/guia-auditoria.md` (auditoría humana pendiente explícita) y actualización de `docs/context.md`; verificable por `tests/test_docs.py` (existencia y marcador de auditoría pendiente).

## 9. Cierre

- [x] 9.1 Suite completa con `uv run pytest`, `openspec validate pilot-deployment --strict` y revisión con code-review-graph.

## Workflow follow-up

- Archivar con `openspec archive pilot-deployment --yes` solo si todas las tareas están completas. Sin commit.
