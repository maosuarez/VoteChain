## 1. Setup

- [x] 1.1 Agregar `pytest` como dependencia de desarrollo y verificar que `uv run pytest` corre (sin tests aún) sin errores de configuración
- [x] 1.2 Crear `src/votechain/block.py`, `src/votechain/blockchain.py` y `tests/__init__.py`/`tests/test_blockchain.py` vacíos y verificar que `import votechain.block, votechain.blockchain` funciona

## 2. Block

- [x] 2.1 Implementar serialización canónica y `Block` (dataclass frozen con `compute_hash()`); verificar con tests: hash determinista, orden de claves irrelevante, el campo hash no entra al cálculo, cambio mínimo cambia el hash
- [x] 2.2 Agregar test de vector fijo (hash conocido de un bloque de ejemplo) y verificar que pasa

## 3. Blockchain

- [x] 3.1 Implementar bloque génesis constante y `Blockchain.__init__`; verificar con tests: génesis idéntico entre instancias, `prev_hash` de ceros, cadena nueva válida
- [x] 3.2 Implementar `add_block` (índice consecutivo, `prev_hash`, timestamp inyectable); verificar con test de encadenamiento
- [x] 3.3 Implementar `is_valid()` con resultado `(valid, bad_index, reason)` y los tres chequeos más validación del génesis; verificar con tests: datos alterados, alterados con hash recalculado (falla en el siguiente), índice no consecutivo, génesis alterado, bloque intermedio eliminado

## 4. Demo

- [x] 4.1 Crear `demo_tamper.py` que construye una cadena, altera un bloque intermedio y muestra válida→inválida con el índice de ruptura; verificar ejecutando `uv run python demo_tamper.py` y comprobando la salida

## 5. Cierre

- [x] 5.1 Ejecutar `uv run pytest` completo y `openspec validate blockchain-core --strict`; ambos deben pasar
- [ ] 5.2 Revisar cambios con `code-review-graph` (detect_changes) antes de archivar
