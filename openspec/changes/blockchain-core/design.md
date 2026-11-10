## Context

Repo vacío salvo el paquete `votechain` (uv, Python >=3.11). Ver proposal.md para la motivación. Este change es la base de todo lo demás: las siguientes capas (transacciones, consenso, dominio de votación) dependen de la interfaz de bloque y cadena definida aquí.

## Goals / Non-Goals

**Goals:**
- Bloque y cadena mínimos, deterministas y testeados.
- Interfaz estable para que `signed-transactions` solo extienda el bloque (Merkle root, nonce).

**Non-Goals:**
- Persistencia en disco, red, firmas, PoW/PoA, reglas de votación.

## Decisions

- **Dataclass inmutable (`frozen=True`) para `Block`.** Un bloque no se modifica; "alterarlo" en la demo se hace construyendo/reemplazando. Alternativa: clase mutable; descartada porque oculta bugs de mutación accidental. La demo manipula la lista interna de la cadena a propósito.
- **`data` como `dict` serializable en JSON** en vez de bytes. Facilita inspección y es compatible con la futura lista de transacciones. Alternativa: bytes opacos; descartada por poca legibilidad didáctica.
- **Serialización canónica** con `json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. Se hashea con `hashlib.sha256` (stdlib, sin dependencia nueva en este change; `cryptography` llega con las firmas).
- **Campos hasheados:** `index`, `timestamp`, `prev_hash`, `data`. El hash se guarda aparte y se recalcula en validación (`compute_hash()`), nunca se confía en el almacenado.
- **Génesis** como constante de módulo (timestamp 0, `data={"genesis": true}`, `prev_hash="0"*64`), no generada con la hora actual, para que todas las instancias coincidan.
- **`is_valid()` retorna resultado con índice del primer fallo** (p. ej. `ValidationResult(valid, bad_index, reason)`), no solo bool, para que la demo y futuros nodos puedan explicar el fallo. Alternativa: lanzar excepción; descartada porque la invalidez es un resultado esperado, no un error.
- **Timestamp** inyectable en `add_block` (parámetro opcional, por defecto `int(time.time())`) para tests deterministas.
- Módulos: `src/votechain/block.py`, `src/votechain/blockchain.py`; tests en `tests/test_blockchain.py`; `demo_tamper.py` en la raíz.

## Risks / Trade-offs

- [Cambiar el formato de serialización invalida todos los hashes] → Congelarlo ahora con test de vector fijo (hash conocido de un bloque de ejemplo).
- [Desacople entre `Block` y el futuro bloque con Merkle/nonce] → Mantener `compute_hash()` como único punto que decide qué campos entran al hash.
- [Un bloque sin fecha válida o con `data` no serializable] → Fallar al construir (TypeError de json) en vez de aceptar silenciosamente.
