## Context

Ver proposal.md. La cadena ya ofrece transacciones firmadas (`Transaction`, emisor = clave pública Ed25519) y bloques con `timestamp`. El dominio de votación es una función pura sobre el log, sin estado persistente propio.

## Goals / Non-Goals

**Goals:**
- Máquina de estados determinista reconstruida desde la cadena.
- Reglas 3 picks distintos y ordenados, 3/2/1, una papeleta por credencial y categoría.

**Non-Goals:**
- Elegibilidad del votante, códigos por correo, firmas ciegas (changes posteriores).
- Integración al mempool/consenso (rechazo previo a minado) y política de visibilidad del ranking.

## Decisions

- **Módulo `voting.py` con replay**: `build_state(chain)` recorre bloques y transacciones en orden y aplica cada una con `apply(tx, block_timestamp)`, que devuelve `None` o el motivo de rechazo. Alternativa: validar en `Blockchain.is_valid`; se descarta para no acoplar la capa de cadena al dominio ni invalidar toda la cadena por un voto inválido.
- **Transacciones inválidas se ignoran, no invalidan la cadena**: el resultado es determinista y cualquier nodo coincide. Trade-off: la cadena puede contener basura inocua; el filtrado previo (mempool) llega con la capa de API.
- **Administrador = emisor de `CREATE_ELECTION`**: sin lista global de masters; cada elección tiene su admin. Alternativa (clave master global en génesis) se pospone a `master-admin-api`.
- **Tiempo = timestamp del bloque**, no el de la transacción, que controla el emisor. Los timestamps de bloque no son confiables frente a un minero malicioso; mitigado después por PoA con validadores conocidos.
- **Sin papeleta en blanco ni parcial**: exactamente 3 picks (decisión abierta resuelta de la forma más restrictiva, alineada con la regla de dominio; reversible por spec).
- **Apertura exige >=3 candidatos por categoría**: de lo contrario ninguna papeleta válida sería posible.
- **Desempate**: clave de orden `(-puntos, -primeros, -segundos)`; igualdad total = posición compartida y `tied=True`. Orden estable final por `candidate_id` solo para presentación.
- **Voto pseudónimo**: la credencial es la clave del emisor; todo emisor puede votar (sin censo). Limitación declarada; `anonymous-credentials` y `voter-email-auth` la resuelven.

## Risks / Trade-offs

- [Cualquier clave puede votar] → los controles de elegibilidad llegan en `voter-email-auth`; no usar en piloto antes.
- [Clave pseudónima vinculable si se asocia a persona] → el change `anonymous-credentials` rompe el vínculo.
- [Timestamp de bloque manipulable] → PoA y validadores conocidos.
- [Replay O(n) por consulta] → aceptable a escala de piloto; sin optimización prematura.
