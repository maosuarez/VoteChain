# ROADMAP — votechain

Estado: `[ ]` pendiente · `[~]` activa · `[x]` completada

## Protocolo de fase

Cada fase sigue este orden:
1. **Concepto**: explicar en el chat qué se va a entender y por qué, antes de escribir código.
2. **Diseño**: acordar estructura y decisiones; confirmar con el usuario.
3. **Implementación**: código mínimo que cumpla el entregable (solo cuando el usuario lo pida).
4. **Rompe-lo**: demo o test que intente vulnerar lo construido, para ver el concepto fallar y corregirse.
5. **Cierre**: checklist de criterios cumplidos, revisión con `code-review-graph`, actualizar estado aquí.

---

## Fase 1 — Núcleo de la cadena `[~]`
**Entiendes:** inmutabilidad; por qué alterar un bloque invalida todos los siguientes.
**Construyes:** `Block` (index, timestamp, prev_hash, data, hash), `Blockchain` (agregar bloque, validar cadena), bloque génesis fijo, serialización canónica.
**Entregable:** `demo_tamper.py` que altera un bloque intermedio y muestra dónde se rompe; tests de los tres chequeos (hash recalculado, `prev_hash`, índices consecutivos).
**Hecho cuando:** `is_valid()` detecta cualquier alteración y los tests pasan.

## Fase 2 — Transacciones y PoW `[ ]`
**Entiendes:** identidad = clave pública; integridad de los datos del bloque; qué hace realmente la prueba de trabajo.
**Construyes:** firmas Ed25519, transacciones firmadas, Merkle tree, mempool, `nonce` + PoW simple con dificultad ajustable.
**Hecho cuando:** una transacción con firma inválida o alterada es rechazada, y minar un bloque requiere trabajo medible.

## Fase 3 — Red P2P `[ ]`
**Entiendes:** consenso distribuido; qué ocurre cuando los nodos discrepan.
**Construyes:** varios nodos, propagación de transacciones y bloques, sincronización inicial, resolución de forks (cadena válida más larga).
**Hecho cuando:** 3 nodos convergen al mismo estado tras partición y reconexión.

## Fase 4 — Consenso PoA `[ ]`
**Entiendes:** por qué las cadenas permisionadas son más eficientes que PoW; trade-off de confianza.
**Construyes:** conjunto de validadores, bloques firmados por el validador en turno, rotación round-robin, rechazo de bloques de no validadores.
**Hecho cuando:** PoW queda reemplazado y un nodo no autorizado no puede producir bloques válidos.

## Fase 5 — Dominio de votación (nivel A) `[ ]`
**Entiendes:** la cadena como log y las reglas como máquina de estados determinista.
**Construyes:** transacciones `CREATE_ELECTION`, `REGISTER_VOTER` (lista firmada por el administrador), `CAST_VOTE`, `CLOSE_ELECTION`; reglas: un voto por votante, ventana de tiempo, solo votantes habilitados; conteo derivado de la cadena.
**Hecho cuando:** intentos de doble voto, voto fuera de ventana o de no habilitado son rechazados, y cualquier nodo recalcula el mismo resultado.

## Fase 6 — Privacidad (nivel B: firmas ciegas) `[ ]`
**Entiendes:** el problema central del voto electrónico: verificable pero no vinculable a la persona.
**Construyes:** emisión de credenciales de voto con firma ciega, voto con credencial anónima, verificación de que cada credencial se usa una sola vez.
**Hecho cuando:** el administrador no puede vincular una credencial usada con un votante, y el sistema sigue impidiendo el doble voto.

## Fase 7 — Producto y piloto `[ ]`
**Entiendes:** operar y auditar una red real.
**Construyes:** API FastAPI, CLI con Rich, explorador web en Next.js con página pública de auditoría, `docker compose` con 3-5 nodos, guía de uso para el administrador.
**Hecho cuando:** se corre una elección de prueba completa de extremo a extremo y un tercero puede auditar el resultado sin confiar en el administrador.

---

## Extensiones futuras (fuera de alcance)
ZK-proofs o firmas de anillo, resistencia a coerción, múltiples elecciones concurrentes, integración con identidad institucional.
