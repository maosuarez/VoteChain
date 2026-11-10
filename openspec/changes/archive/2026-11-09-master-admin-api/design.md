## Context

Ver proposal.md. Las capas inferiores ya existen: `Blockchain`/`Mempool`, `Transaction`, `voting.py` (`build_state`, `VotingState.apply`, `tally`), `VoterAuth` (censo, códigos, `redeem_credential`, `set_issuer_key`). Este change solo las expone vía FastAPI en `src/votechain/api/`.

## Goals / Non-Goals

**Goals:**
- API del master, del votante y pública de lectura, con pruebas vía `TestClient`.
- Respuestas públicas que no permitan enumerar el censo ni vincular voto e identidad.

**Non-Goals:**
- SMTP real, persistencia de cadena/claves, P2P/PoA, rate limiting, TLS, usuarios master múltiples, frontend.
- Cambios en reglas de `voting.py` o `blind.py`.

## Decisions

- **Autenticación del master = token estático configurable** (`Authorization: Bearer`), comparado con `hmac.compare_digest`; se lee de `VOTECHAIN_MASTER_TOKEN` en `create_app_from_env` o se pasa a `create_app`. Alternativas (JWT, usuarios, OAuth) descartadas: un solo rol y piloto; amplían alcance. Token vacío = error de arranque.
- **Clave del master separada del token**: el token autoriza llamadas HTTP; la clave Ed25519 (`VOTECHAIN_MASTER_KEY`) firma las transacciones y su pública es el `admin` de las elecciones. El servidor firma en nombre del master; la clave nunca sale.
- **Acciones on-chain**: crear elección, categoría, candidato, abrir y cerrar. Flujo: construir tx firmada -> validar con `build_state(chain).apply` (pre-filtro que `voting-domain-borda` dejó para esta capa) -> `Mempool.add` -> `add_block_from_mempool`, un bloque por acción. Censo y reenvío de códigos NO van a la cadena: no hay tipo de transacción para ellos y los datos son personales; su rastro queda en la tabla `audit` off-chain. Desviación consciente de "cada acción relevante" del proposal, sin ampliar el dominio.
- **Clave de emisión generada por la API** al crear la elección: la pública va en `CREATE_ELECTION`, la privada a `VoterAuth.set_issuer_key` (memoria, como definió `anonymous-credentials`). Se inyecta `issuer_key_factory` para tests. Se pierde al reiniciar: límite heredado.
- **Rechazos públicos unificados**: canje -> siempre 400 `invalid_request`; papeleta -> siempre 400 `ballot_rejected`. El motivo real queda solo en el `audit` off-chain del servicio de códigos. El master recibe motivos de dominio (409) porque no revelan censo; el reenvío devuelve solo `sent: bool`.
- **Ruta de papeleta solo acepta `CAST_BALLOT`**: sin ello cualquiera podría crear elecciones o cerrarlas siendo su propio admin.
- **Sin rastro de vínculo**: las rutas del votante no persisten valor ciego, firma, IP ni correo junto a la papeleta; no hay ruta de master que devuelva papeletas o credenciales. Límite conocido: correlación por tiempo (un bloque por papeleta, timestamp del bloque) e IP a nivel de red.
- **Visibilidad del conteo**: solo con elección cerrada (403 antes). Resuelve la decisión abierta de la forma más restrictiva; reversible.
- **Concurrencia**: endpoints síncronos con un `threading.Lock` global alrededor de leer/mutar cadena y servicio, y `check_same_thread=False` en la conexión SQLite de `VoterAuth` (único cambio fuera de `api/`; sin cambio de comportamiento). Suficiente para piloto.
- **Estado en memoria**: la cadena vive en memoria del proceso; la persistencia pertenece a `pilot-deployment`.
- **Dependencias**: `fastapi` (runtime) y `httpx` (dev, requerido por `TestClient`).

## Risks / Trade-offs

- [Token estático filtrable, sin rate limit ni rotación] -> aceptable en piloto; TLS y rotación quedan para despliegue.
- [Servidor firma como master: quien robe el servidor controla la elección] -> inherente a la decisión de un solo master; la cadena lo hace auditable, no imposible.
- [Pre-validación con replay O(n) por petición] -> escala de piloto; sin optimización prematura.
- [Cadena y claves de emisión en memoria] -> reinicio pierde estado; mitigado en `pilot-deployment`.
- [Correlación tiempo/IP entre canje y voto] -> documentado en `anonymous-credentials`; no se resuelve aquí.
