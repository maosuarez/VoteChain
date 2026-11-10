## Context

Ver proposal.md (Why). La API (`master-admin-api`) ya expone `/chain`, `/chain/blocks/{i}`, `/elections/{id}` y `/elections/{id}/tally` (solo cerrada). `POST /ballots` devuelve `tx_id`. Hash de bloque = SHA-256 de JSON canónico (claves ordenadas, sin espacios, UTF-8, `ensure_ascii=False`); Merkle con prefijos `0x00` hoja / `0x01` nodo, nodo impar promovido; `tx_id` = SHA-256 del cuerpo canónico sin firma.

## Goals / Non-Goals

**Goals:**
- Explorador estático servido por FastAPI, JS vanilla sin build.
- Verificación en el navegador con paridad demostrada contra vectores del backend.
- Comprobante de inclusión por `tx_id` con prueba de Merkle, sin datos de identidad.

**Non-Goals:**
- Verificar firmas Ed25519 / RSA en el navegador (requeriría librerías o BigInt+WebCrypto; el backend ya las valida al replicar).
- Next.js (el context.md lo menciona; aquí se cumple el requisito de "sin build"), autenticación, paginación, tiempo real.
- Ocultar el contenido de la cadena: ya es pública por diseño.

## Decisions

- **Ubicación y servicio**: `web/` en la raíz del repo, montado con `StaticFiles` en `/explorer` dentro de `create_app` (último, para no tapar rutas). Alternativa: servidor aparte; descartada por añadir un proceso. Limitación: se resuelve relativo al repo (piloto en docker lo copia; ver `pilot-deployment`).
- **Un módulo de lógica pura `web/verify.js`** (sin DOM), cargado en el navegador como script clásico y en Node con `require`. `app.js` solo hace DOM/fetch. Así la lógica se prueba con Node.
- **SHA-256 en JS puro** (sin `crypto.subtle`): `subtle` exige contexto seguro y es asíncrono; en un piloto por HTTP en LAN no estaría disponible. Trade-off: ~40 líneas propias, probadas contra vectores y contra `hashlib`.
- **JSON canónico en JS**: ordenar claves recursivamente y serializar con `JSON.stringify` (sin espacios; no escapa Unicode, igual que `ensure_ascii=False`). Limitación documentada: solo enteros, cadenas, listas y objetos (la cadena no contiene floats); enteros > 2^53 no soportados.
- **Paridad por vectores fijos**: `tests/vectors/audit_vectors.json` contiene entradas y salidas generadas por el backend (JSON canónico con Unicode, hash de bloque, raíces y pruebas de Merkle de 0/1/2/3/5 hojas, cadena con empate y su conteo). Test Python: el archivo coincide con lo que el backend calcula hoy (detecta deriva del backend). Test Node (`tests/js/parity.test.js`): el JS reproduce los vectores. `tests/test_web_parity.py` ejecuta el test Node con `subprocess` y se omite (`skip`) si `node` no está; Node v22 disponible en el entorno de desarrollo.
- **Prueba de Merkle**: nueva `merkle_proof(tx_dicts, index) -> list[{side, hash}]` en `merkle.py` (misma construcción que `merkle_root`; el nodo impar promovido no aporta hermano). `GET /chain/receipts/{tx_id}` la devuelve; busca la tx recorriendo la cadena (O(n), escala de piloto). Respuesta: `tx_id`, `block_index`, `block_hash`, `merkle_root`, `proof`. Sin sender/firma/picks.
- **Comprobante sin vínculo**: el único dato de entrada es el `tx_id` (hash que ya devolvió `POST /ballots`); no hay campo de correo ni código y el endpoint no lee el censo. El navegador hace el chequeo contra el bloque público, no confía en que el servidor afirme "incluida". Límite: quien posea el `tx_id` puede mostrar su papeleta (la cadena es pública y no se resiste a coerción, ver context.md); la correlación tiempo/IP sigue siendo la de `anonymous-credentials`.
- **Política de ranking = solo al cierre** (decisión de `master-admin-api`): el explorador usa `/tally` (403 antes del cierre) y solo recalcula localmente cuando `status == closed`. Nota: las papeletas están en la cadena pública, así que un tercero técnico podría calcular un parcial; la política restringe lo que la API y el explorador publican, no la cadena. Se deja explícito, no se oculta contenido de cadena (lo contrario exigiría papeletas cifradas, fuera de alcance).
- **Recalculo del conteo en navegador**: reproduce `_cast_ballot` sin firmas: se acepta una papeleta si la elección está abierta en ese punto del replay, la categoría existe, 3 picks distintos de la categoría y es la primera del (remitente, categoría); desempate igual que `tally`. Discrepancia con el publicado se muestra.
- **Elecciones descubiertas desde la cadena** (txs `CREATE_ELECTION`), sin endpoint de listado nuevo.
- **Génesis**: el navegador compara contra el génesis fijo (`index 0`, `prev_hash` ceros, sin txs, `timestamp 0`, raíz de lista vacía).

## Risks / Trade-offs

- [Verificación sin firmas: un servidor malicioso podría servir una cadena autoconsistente falsa] → el hash/Merkle detectan manipulación parcial pero no reescritura completa; mitigación real es comparar el hash de cabeza con otros nodos/auditores (`p2p`/`pilot-deployment`). Documentado.
- [SHA-256 propio] → vectores contra backend y NIST ("abc", vacío).
- [Cadena grande en el navegador] → se descarga `/chain` completa; suficiente para piloto, sin optimización prematura.
- [Ranking derivable de la cadena pública durante la votación] → ver decisión de política; límite conocido.
- [`web/` fuera del paquete Python] → se resuelve relativo al repo; montaje omitido si el directorio no existe.

## Migration Plan

Aditivo: nueva ruta de lectura, nuevo montaje estático y `web/`. Rollback: revertir el commit; no hay datos ni cambios en cadena.
