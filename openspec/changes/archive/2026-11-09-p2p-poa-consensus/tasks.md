## 1. Bloque y consenso PoA

- [x] 1.1 Extender `Block` con `proposer` (en el hash) y `signature` (fuera del hash); actualizar génesis y vector fijo; verificar con tests: cambiar proponente cambia el hash, cambiar firma no, tests existentes pasan
- [x] 1.2 Implementar `consensus.py` (`ValidatorSet` con validación, proponente por `index mod N`, `seal_block`); verificar con tests: conjunto válido/vacío/duplicado, rotación 1..4
- [x] 1.3 Extender `Blockchain` con `validators`, validación PoA (autorizado, en turno, firma válida, sin PoW) y `try_append`; verificar con tests: bloque válido, firma alterada, no autorizado, fuera de turno, PoA no exige trabajo

## 2. Red P2P

- [x] 2.1 Implementar `Transport` (Protocol) e `InMemoryTransport` con `partition`/`heal`; verificar con tests de entrega y de partición
- [x] 2.2 Implementar `Node`: propagación de transacciones (inválida/duplicada descartada) y producción en turno (`produce_block`); verificar con tests: propagación, inválida, no validador no produce, fuera de turno no produce
- [x] 2.3 Implementar recepción y propagación de bloques, `sync()` y `Blockchain.replace_chain` con desempate; verificar con tests: propagación, bloque de no validador rechazado, sync inicial, bloque con hueco, candidata inválida más larga, empate determinista
- [x] 2.4 Test de integración: 3 nodos convergen tras partición y reconexión; nodo no autorizado no logra que su bloque sea aceptado

## 3. Cierre

- [x] 3.1 Adaptar spec/tests de PoW (`test_pow.py`) al modo con validadores sin perder cobertura; actualizar `docs/context.md` (arquitectura: PoA implementado, módulos)
- [x] 3.2 Suite completa, `openspec validate p2p-poa-consensus --strict`, revisión con code-review-graph
