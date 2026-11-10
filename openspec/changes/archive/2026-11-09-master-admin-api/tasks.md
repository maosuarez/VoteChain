# Tasks

## 1. Base de la API

- [x] 1.1 Agregar `fastapi` (runtime) y `httpx` (dev) a `pyproject.toml`, `check_same_thread=False` en `VoterAuth`, y crear `src/votechain/api/app.py` con `create_app` / `create_app_from_env`, autenticación Bearer del master y envío de transacciones firmadas (validar, mempool, minar); `tests/test_api_master.py` con los escenarios de autenticación.

## 2. Master

- [x] 2.1 Rutas administrativas (crear elección con clave de emisión, categorías, candidatos, abrir, cerrar, cargar censo, reenviar código) con tests de los escenarios de master-admin.

## 3. Votante

- [x] 3.1 Rutas de canje de credencial y de papeleta con rechazos unificados, y `tests/test_api_voter.py` con los escenarios de voter-api (incluido flujo completo canje -> papeleta).

## 4. Lectura pública

- [x] 4.1 Rutas de cadena, bloque, elección y conteo (solo cerrada), con `tests/test_api_public.py`.

## 5. Cierre

- [x] 5.1 Suite completa, `openspec validate master-admin-api --strict`, revisión con code-review-graph y archivar.
