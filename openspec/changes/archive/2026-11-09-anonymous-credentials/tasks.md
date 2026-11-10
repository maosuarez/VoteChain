# Tasks

## 1. Firma ciega

- [x] 1.1 Crear `src/votechain/blind.py` (generación de clave de emisión, ciegar, firmar ciego, quitar cegado, verificar, solicitud de credencial) y `tests/test_blind.py` con los escenarios de blind-credentials (ciclo, valor inválido, verificación, credencial inválida) en verde.

## 2. Emisión en el servicio de códigos

- [x] 2.1 Agregar `set_issuer_key` y `redeem_credential` a `auth/service.py`, con `tests/test_credential_issuance.py` (escenarios de email-code-auth: entrega, valor inválido, segundo canje, sin rastro persistido) en verde.

## 3. Voto con credencial anónima

- [x] 3.1 Exigir `issuer_key` en `CREATE_ELECTION` y `credential_sig` válido en `CAST_BALLOT` en `voting.py`; adaptar `tests/voting_helpers.py` y tests existentes, y agregar escenarios de ballot-casting y election-lifecycle (credencial sin firma, alterada, otra elección, firma de otra clave, clave de emisión inválida) en verde.

## 4. No vinculabilidad

- [x] 4.1 Agregar `tests/test_unlinkability.py` (flujo completo correo -> credencial -> voto en cadena; todo emparejamiento valor ciego/credencial es consistente) y `demo_unlinkability.py` "rompe-lo".

## 5. Cierre

- [x] 5.1 Correr la suite completa y `openspec validate anonymous-credentials --strict`; verificar ambos sin errores.
