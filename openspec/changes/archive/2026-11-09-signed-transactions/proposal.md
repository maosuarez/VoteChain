## Why

La identidad en la cadena debe ser una clave pública y cada dato debe estar firmado, para que nadie pueda inyectar o alterar transacciones. Es el prerrequisito de las reglas de votación.

## What Changes

- Firmas Ed25519 y transacciones firmadas con verificación obligatoria.
- Merkle tree de transacciones por bloque; mempool.
- PoW simple (didáctico) con dificultad ajustable, antes de pasar a PoA.

## Capabilities

### New Capabilities
- `signed-transactions`: transacciones firmadas, rechazo de firmas inválidas o alteradas, Merkle root en el bloque.
- `proof-of-work`: nonce y dificultad ajustable para minar bloques.

### Modified Capabilities
- `chain-integrity`: el bloque incluye Merkle root y nonce.

## Impact

- Código: `transactions.py`, `crypto.py`, `merkle.py`, `mempool.py`, extensión de `block.py`.
- Depende de: `blockchain-core`. Habilita: `p2p-poa-consensus`, `voting-domain-borda`.
