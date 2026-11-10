## Context

Ver proposal.md. `Blockchain` (`block.py`, `blockchain.py`), `Mempool`, `Transaction` y la API (`api/app.py`, cadena en memoria con `create_app(chain=...)`) ya existen. Este change añade consenso PoA y una red de nodos probable en un solo proceso. La API no cambia.

## Goals / Non-Goals

**Goals:**
- Bloques firmados por el validador en turno (round-robin); rechazo de no validadores.
- Nodos que propagan transacciones/bloques, se sincronizan y resuelven forks.
- Red probada en un proceso, con transporte inyectable y particiones simuladas.

**Non-Goals:**
- Transporte real (HTTP/sockets), descubrimiento dinámico de pares, cambio de validadores en caliente, view-change/timeouts, persistencia, finalidad, conectar la API a un `Node` (queda para `pilot-deployment`).

## Decisions

- **PoA dentro de `Blockchain`**: `Blockchain(difficulty=0, validators=None)`. Con `validators` (un `ValidatorSet`) la validación exige autoridad y NO evalúa PoW; sin él, se conserva el comportamiento PoW (didáctico, tests existentes intactos). Alternativa: borrar PoW; descartada, rompería la cobertura y el valor didáctico.
- **Bloque**: campos nuevos `proposer` (dentro del hash) y `signature` (fuera del hash, firma Ed25519 del hash hex). Hashear el proponente impide cambiarlo sin invalidar el hash; la firma no puede estar en lo que firma. **BREAKING** del formato: cambian hash del génesis y vector fijo (se actualizan); aceptable, no hay cadenas persistidas. Campos con valor por defecto al final para no romper construcciones existentes.
- **Turno = `index mod N`** sobre el orden del conjunto. Simple y determinista. Trade-off: si el validador en turno está caído, la cadena se detiene (sin timeouts ni view-change); aceptado en piloto.
- **Validación incremental**: `try_append(block)` agrega el bloque y reutiliza `is_valid()` (O(n)), revirtiendo si falla. Coherente con el estilo actual; sin optimización prematura.
- **Fork resolution**: `replace_chain(candidate)` adopta si es válida y (más larga, o igual longitud con hash de punta menor). El desempate determinista garantiza convergencia. Con turnos estrictos los forks solo surgen por equivocación (un validador firma dos bloques al mismo índice); no hay detección/penalización, solo resolución.
- **Módulos planos** (`consensus.py`, `network.py`) siguiendo el layout existente, en vez de los paquetes `consensus/` y `network/` del proposal. `consensus.py`: `ValidatorSet`, `seal_block`, verificación de autoridad. `network.py`: `Node`, `Transport` (Protocol) e `InMemoryTransport`.
- **Transporte**: Protocol con `peers(node_id)`, `send_tx`, `send_block`, `fetch_chain`; mensajes como dicts serializables (`asdict`/`Transaction.to_dict`), de modo que un transporte HTTP futuro sea un adaptador. `InMemoryTransport` entrega de forma síncrona e implementa `partition(*grupos)` y `heal()`. "Descubrimiento" se reduce a la lista de pares que expone el transporte (estática): reducción consciente del proposal.
- **Node**: `Node(node_id, transport, validators, private_key=None, now=...)`. `submit_tx`/`receive_tx`, `produce_block()` (solo en turno, y solo con clave), `receive_block(dict, sender)`, `sync()`. Los duplicados cortan el gossip (mempool, bloque ya conocido). Un bloque con proponente fuera del conjunto se descarta sin sincronizar; un bloque que no encaja de un proponente válido dispara sync con el emisor.
- **Reconexión**: `sync()` explícito (el transporte no notifica reconexiones); las pruebas llaman `heal()` y luego `sync()` en cada nodo.
- **PoW → PoA**: spec `proof-of-work` modificado: sin validadores rige PoW; con validadores no se evalúa. Los nodos de red siempre usan PoA.

## Risks / Trade-offs

- [Validador en turno caído detiene la cadena] -> aceptado; view-change en un change futuro.
- [Equivocación sin penalización; sync forzable por un emisor malicioso] -> red permisionada con validadores conocidos; fuera de alcance.
- [Validación O(n) por bloque y por candidata] -> escala de piloto.
- [La API aún no usa `Node`] -> pasar `chain` y la integración quedan para despliegue.
