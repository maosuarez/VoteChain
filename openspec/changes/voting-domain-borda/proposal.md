## Why

Es el núcleo del cambio de rumbo: reemplazar "2 votos por persona" por una papeleta estilo Balón de Oro (3 picks ordenados, 3/2/1 puntos) con reglas aplicadas de forma determinista sobre la cadena.

## What Changes

- Transacciones: `CREATE_ELECTION`, `ADD_CATEGORY`, `ADD_CANDIDATE`, `OPEN_ELECTION`, `CAST_BALLOT`, `CLOSE_ELECTION`.
- Papeleta: 3 candidatos distintos y ordenados por categoría; puntos 3/2/1.
- Reglas: una papeleta por credencial por categoría, ventana de tiempo, candidatos válidos, elección abierta.
- Conteo derivado de la cadena con desempate (más 1.os lugares, luego 2.os).
- En este change la credencial es una clave pseudónima por votante; el anonimato real llega en `anonymous-credentials`.

## Capabilities

### New Capabilities
- `election-lifecycle`: creación, categorías, candidatos, apertura y cierre.
- `ballot-casting`: validación de papeleta 3/2/1 y rechazo de doble voto, votos fuera de ventana o inválidos.
- `tally`: conteo determinista, ranking y desempate recalculable por cualquier nodo.

### Modified Capabilities
<!-- Ninguna -->

## Impact

- Código: `voting/` (máquina de estados sobre la cadena).
- Depende de: `signed-transactions` (y `p2p-poa-consensus` para el piloto). Habilita: `voter-email-auth`, `master-admin-api`.
- Decisión abierta: votar en blanco / menos de 3 picks; visibilidad del ranking antes del cierre.
