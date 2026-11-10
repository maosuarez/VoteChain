## Why

Todo el sistema de votación descansa en un registro inmutable. Sin una cadena que detecte cualquier alteración no hay trazabilidad ni transparencia verificables. Es la base de la que dependen todos los demás changes.

## What Changes

- Estructura `Block` (index, timestamp, prev_hash, data, hash) con serialización canónica.
- `Blockchain`: agregar bloques, bloque génesis fijo, validación completa de la cadena.
- `demo_tamper.py`: altera un bloque intermedio y muestra dónde se rompe la cadena.
- Tests de los tres chequeos: hash recalculado, `prev_hash`, índices consecutivos.

## Capabilities

### New Capabilities
- `chain-integrity`: bloques encadenados por hash, génesis determinista y validación que detecta cualquier alteración.

### Modified Capabilities
<!-- Ninguna -->

## Impact

- Código nuevo: `src/votechain/block.py`, `src/votechain/blockchain.py`, `tests/test_blockchain.py`, `demo_tamper.py`.
- Dependencias: `cryptography` o `hashlib` (SHA-256), `pytest`.
- Depende de: nada. Habilita: `signed-transactions`.
