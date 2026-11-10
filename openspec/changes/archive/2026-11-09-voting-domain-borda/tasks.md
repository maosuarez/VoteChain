## 1. Estado de elecciones

- [x] 1.1 Crear `src/votechain/voting.py` con estado de elección y `apply` para `CREATE_ELECTION`, `ADD_CATEGORY`, `ADD_CANDIDATE`, `OPEN_ELECTION`, `CLOSE_ELECTION`; verificar con `tests/test_voting_lifecycle.py` (escenarios de election-lifecycle) en verde.

## 2. Papeletas

- [x] 2.1 Agregar `CAST_BALLOT` a `apply` (3 picks distintos, candidatos válidos, una por credencial/categoría, estado y ventana por timestamp de bloque); verificar con `tests/test_voting_ballot.py` (escenarios de ballot-casting) en verde.

## 3. Conteo

- [x] 3.1 Implementar `build_state(chain)` (replay determinista, inválidas ignoradas) y `tally` con ranking y desempate; verificar con `tests/test_voting_tally.py` (escenarios de tally, incluyendo replay sobre `Blockchain` real) en verde.

## 4. Cierre

- [x] 4.1 Correr la suite completa y `openspec validate voting-domain-borda --strict`; verificar ambos sin errores.
