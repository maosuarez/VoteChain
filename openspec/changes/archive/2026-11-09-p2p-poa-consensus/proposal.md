## Why

Una sola copia de la cadena no da transparencia: debe existir en varios nodos operados por partes distintas que converjan al mismo estado. Al ser red permisionada, Proof of Authority es más simple y eficiente que PoW.

## What Changes

- Red P2P: propagación de transacciones y bloques, sincronización inicial.
- Resolución de forks (cadena válida más larga).
- Conjunto de validadores conocidos, bloques firmados por el validador en turno (round-robin); PoA reemplaza a PoW.
- Rechazo de bloques de no validadores.

## Capabilities

### New Capabilities
- `p2p-network`: descubrimiento, propagación, sincronización y resolución de forks.
- `poa-consensus`: validadores autorizados y rotación round-robin.

### Modified Capabilities
- `proof-of-work`: **BREAKING** queda reemplazado por PoA como consenso de producción (PoW solo didáctico, sin validadores).
- `chain-integrity`: el bloque añade `proposer` y `signature`; la validación comprueba el consenso configurado (PoW o PoA).

## Impact

- Código: `network.py`, `consensus.py` (módulos planos), `block.py`, `blockchain.py`.
- Criterio: 3 nodos convergen tras partición y reconexión; un nodo no autorizado no produce bloques válidos.
- Depende de: `signed-transactions`.
