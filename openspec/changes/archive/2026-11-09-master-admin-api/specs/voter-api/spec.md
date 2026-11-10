## ADDED Requirements

### Requirement: Credential redemption endpoint
La API SHALL ofrecer a cualquier cliente (sin token de master) canjear `(correo, código, valor ciego)` de una elección por una firma ciega. Cualquier fallo (elección desconocida, correo no habilitado, código incorrecto, expirado, agotado, ya canjeado, valor ciego inválido) MUST responder idénticamente 400 con `{"detail": "invalid_request"}`, sin distinguir motivo. El valor ciego y la firma MUST NOT persistirse ni registrarse.

#### Scenario: Canje exitoso
- **WHEN** un votante habilitado envía su código vigente y un valor ciego válido
- **THEN** responde 200 con la firma ciega y el votante queda marcado como servido

#### Scenario: Motivos indistinguibles
- **WHEN** se canjea con correo no habilitado, con código incorrecto y con elección inexistente
- **THEN** las tres respuestas son idénticas (mismo estado y cuerpo)

#### Scenario: Segundo canje
- **WHEN** el mismo votante canjea otra vez con el mismo código
- **THEN** responde 400 `invalid_request` y no obtiene segunda firma

### Requirement: Ballot submission endpoint
La API SHALL aceptar una transacción `CAST_BALLOT` ya firmada por el votante con su clave de credencial y minarla si el dominio la acepta. Transacciones de cualquier otro tipo MUST rechazarse. Todo rechazo (firma inválida, tipo incorrecto, credencial inválida, doble voto, elección cerrada, picks inválidos) MUST responder idénticamente 400 con `{"detail": "ballot_rejected"}`. La API MUST NOT asociar la papeleta con correo, IP ni canje previo.

#### Scenario: Papeleta aceptada
- **WHEN** un votante envía una papeleta válida con credencial emitida
- **THEN** responde 202, la transacción queda en un bloque y cuenta en el conteo

#### Scenario: Doble voto
- **WHEN** la misma credencial envía una segunda papeleta en la misma categoría
- **THEN** responde 400 `ballot_rejected` y la cadena no crece

#### Scenario: Tipo no permitido
- **WHEN** se envía por esta ruta una transacción `CREATE_ELECTION` o `CLOSE_ELECTION`
- **THEN** responde 400 `ballot_rejected` y no se mina

#### Scenario: Motivos indistinguibles
- **WHEN** se envían una papeleta con credencial falsa y otra de elección cerrada
- **THEN** ambas respuestas son idénticas
