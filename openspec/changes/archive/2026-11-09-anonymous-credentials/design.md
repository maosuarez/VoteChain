# Design

## Context

`voting.py` identifica al votante por la clave del emisor de la transacción y no aplica elegibilidad; `auth/service.py` canjea códigos y marca "ya recibió credencial" pero no entrega nada. Este change conecta ambos con firma ciega RSA (Chaum). Ver proposal.md para la motivación.

## Goals / Non-Goals

**Goals:**
- Credencial verificable públicamente que no se vincule a la persona, ni para el master.
- Un voto por credencial por categoría, verificado al reproducir la cadena.
- Demo/prueba de que el master no puede vincular.

**Non-Goals:**
- Endpoint HTTP, SMTP real, autenticación del master, anti-coerción.
- Mitigar correlación por tiempo/IP (se documenta; es de piloto/despliegue).
- Rotación o custodia de la clave de emisión más allá de mantenerla en memoria del servicio.

## Decisions

- **Credencial = (clave Ed25519 del votante, firma RSA ciega del emisor sobre ella)**. La papeleta se firma con esa clave: `tx.sender` es la credencial y la firma de la transacción impide que quien vea la credencial en el mempool la use con otros picks. Alternativa descartada: token aleatorio + clave efímera por voto; añade un campo y permite robo de credencial en mempool.
- **Una credencial por elección, reusable una vez por categoría**: coincide con `(sender, category)` ya existente en `Election.ballots`; no cambia el tally. Trade-off: las papeletas de un mismo votante en distintas categorías son enlazables entre sí (no con la persona).
- **RSA ciego con FDH sobre SHA-256** implementado en `votechain/blind.py` con aritmética modular de Python sobre llaves generadas por `cryptography` (2048 bits). Textbook RSA es seguro aquí porque se firma un hash de dominio completo (FDH), no datos del usuario. Se evita RSA-PSS ciego (RFC 9474) por complejidad sin evidencia de necesidad. Se ubica en `blind.py` y no en `crypto/blind.py` para no convertir `crypto.py` en paquete (refactor ajeno al alcance).
- **Mensaje firmado ligado a elección**: `votechain-credential-v1:<election_id>:<pubkey_hex>`; evita reuso entre elecciones aun con la misma clave de emisión.
- **Clave pública de emisión en `CREATE_ELECTION`** (campo `issuer_key` `{n, e}` hex): la cadena es la fuente pública para verificar; modifica `election-lifecycle` mínimamente. Alternativa: tx `SET_ISSUER_KEY` en borrador; descartada por añadir un tipo y un estado.
- **Servicio**: `VoterAuth.set_issuer_key(election_id, key)` y `redeem_credential(election_id, email, code, blinded)` devuelve `(firma_ciega | None, motivo | None)`. Valida el valor ciego, luego reutiliza `redeem_code` (hash, expiración, intentos, marca) y firma. Se mantiene `redeem_code` sin cambios para no romper el change anterior. Ni el valor ciego ni la firma se persisten ni registran.
- **Verificación en cadena**: `_cast_ballot` verifica `credential_sig` con `issuer_key` de la elección antes de las demás reglas de unicidad. Un voto sin credencial válida se rechaza determinísticamente al reproducir.

## Risks / Trade-offs

- [Master emite credenciales a no votantes (relleno de urnas)] → fuera de alcance; mitigable con auditoría del número de emisiones vs. credenciales usadas (`voters.credential_issued`). Documentado.
- [Correlación por tiempo/IP entre canje y voto] → límite conocido; el votante debe votar con retraso y por otra red en piloto.
- [Clave de emisión en memoria] → suficiente para piloto de aprendizaje; custodia real queda diferida.
- [Cambio BREAKING] → `CREATE_ELECTION` exige `issuer_key` y `CAST_BALLOT` exige `credential_sig`; los tests existentes se adaptan.
