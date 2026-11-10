## Context

Existe `Block` (index, timestamp, prev_hash, data, hash) y `Blockchain.is_valid()` con `ValidationResult`. Ver proposal.md. Este change extiende el bloque y es la base del dominio de votación y del consenso PoA.

## Goals / Non-Goals

**Goals:**
- Transacciones firmadas, Merkle root, mempool y PoW con dificultad ajustable.
- Mantener `ValidationResult(valid, bad_index, reason)` como contrato de validación.

**Non-Goals:**
- Red, validadores PoA, reglas de votación, persistencia, gestión de claves (custodia/almacenamiento).
- Semántica de los tipos de transacción (llega con `voting-domain-borda`; aquí `type` y `payload` son opacos).

## Decisions

- **Ed25519 con `cryptography`** (nueva dependencia; ya prevista en context.md). Identificador = clave pública cruda en hex (64 chars). Firma en hex.
- **Transacción:** dataclass frozen `{type, payload, sender, timestamp, signature}`. `tx_id = sha256(canonical(cuerpo sin firma))`. Se reutiliza `canonical_bytes`. Alternativa: incluir un nonce de secuencia por emisor; descartada por ahora, el `tx_id` único + rechazo de duplicados basta contra replay en cadena, y las reglas de un-voto-por-credencial viven en el dominio.
- **Datos del bloque:** `data = {"transactions": [tx_dict, ...]}`. El bloque génesis usa lista vacía.
- **Merkle:** hoja = `sha256(0x00 || canonical(tx_dict_con_firma))`, nodo = `sha256(0x01 || izq || der)`. Nivel impar: el último nodo se promueve sin duplicarse (evita la colisión [A,B,C] vs [A,B,C,C] de Bitcoin, CVE-2012-2459). Raíz vacía = `sha256(b"")`.
- **Campos nuevos del bloque:** `merkle_root`, `nonce`, ambos dentro de `compute_hash()` (único punto que decide qué se hashea). **BREAKING** del formato: cambian los hashes y el génesis; aceptable porque no hay cadenas persistidas ni publicadas.
- **PoW por bits en cero** (no por dígitos hex) para granularidad fina: `hash_int >> (256 - difficulty) == 0`. La dificultad es parámetro de `Blockchain(difficulty=...)`, no campo del bloque; el génesis está exento. Alternativa: dificultad en la cabecera del bloque; descartada, PoW es transitorio hasta PoA.
- **`mine()` devuelve el bloque y el número de intentos** para hacer visible el "trabajo medible".
- **Mempool** en memoria, `OrderedDict` por `tx_id`, `add(tx) -> bool/razón`, `pop_batch(max)`. Verifica firma al admitir.
- **Validación de cadena** conserva el orden bloque a bloque; se agregan los chequeos (d)(e)(f). El conjunto de `tx_id` ya vistos se acumula durante la pasada.
- **Módulos:** `crypto.py`, `transactions.py`, `merkle.py`, `mempool.py`; extender `block.py`, `blockchain.py`.
- Verificación de firma nunca lanza al llamador: captura errores de decodificación/`InvalidSignature` y devuelve False.

## Risks / Trade-offs

- [Cambio de formato del hash rompe tests existentes] → Actualizar el test de vector fijo y el génesis en este mismo change.
- [Timestamps de transacción no verificados contra la hora del bloque] → Fuera de alcance; lo decide el dominio (ventana de elección).
- [PoW lento en tests] → Dificultad baja (≤12 bits) en tests; parametrizable.
- [Custodia de claves privadas] → No resuelta aquí; se aborda en `master-admin-api` y `anonymous-credentials`.
