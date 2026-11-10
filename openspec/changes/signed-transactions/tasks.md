## 1. Dependencias y cripto

- [ ] 1.1 Agregar `cryptography` y verificar que `uv run python -c "import cryptography"` funciona
- [ ] 1.2 Implementar `crypto.py` (generar clave, firmar, verificar sin lanzar); verificar con tests: identidades distintas, firma válida, firma malformada devuelve False

## 2. Transacciones

- [ ] 2.1 Implementar `Transaction` (cuerpo canónico, `tx_id`, firma, `verify()`); verificar con tests: válida, payload alterado, firma de otra identidad
- [ ] 2.2 Implementar `Mempool` (admite solo válidas, rechaza duplicados, `pop_batch` en orden de llegada con máximo); verificar con tests de los tres escenarios

## 3. Merkle

- [ ] 3.1 Implementar `merkle_root` con separación de dominio y promoción de nodo impar; verificar con tests: determinista, el orden importa, [A,B,C] != [A,B,C,C], lista vacía constante

## 4. Bloque y cadena

- [ ] 4.1 Extender `Block` con `merkle_root` y `nonce` dentro de `compute_hash()`; actualizar génesis y test de vector fijo; verificar que los tests de `blockchain-core` adaptados pasan
- [ ] 4.2 Implementar PoW (`mine()` con intentos reportados, dificultad por bits, `Blockchain(difficulty=...)`); verificar con tests: cumple dificultad, dificultad 0, intentos crecen en promedio
- [ ] 4.3 Extender `is_valid()` con Merkle, firmas, no-replay y dificultad; verificar con tests: tx alterada con Merkle y hash recalculados, Merkle inconsistente, reinclusión, bloque sin trabajo, nonce alterado
- [ ] 4.4 Agregar `Blockchain.add_block_from_mempool()` (o equivalente) que mina un bloque con el lote del mempool; verificar con test end-to-end: firmar → mempool → minar → cadena válida

## 5. Demo y cierre

- [ ] 5.1 Actualizar `demo_tamper.py` para mostrar la falsificación de una transacción y el costo de re-minar; verificar ejecutando la demo
- [ ] 5.2 Ejecutar `uv run pytest` y `openspec validate signed-transactions --strict`; ambos deben pasar
- [ ] 5.3 Revisar cambios con `code-review-graph` (detect_changes) antes de archivar
