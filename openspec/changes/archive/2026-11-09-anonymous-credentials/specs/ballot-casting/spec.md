# Spec Delta

## MODIFIED Requirements

### Requirement: One ballot per credential per category
Cada credencial anónima (clave pública del votante con firma válida del emisor de la elección) SHALL poder emitir como máximo una papeleta por categoría por elección. Las papeletas en categorías distintas son independientes. `CAST_BALLOT` MUST ser rechazado si la credencial no trae una firma de emisor válida para esa elección.

#### Scenario: Doble voto
- **WHEN** la misma credencial emite una segunda papeleta en la misma categoría
- **THEN** la segunda es rechazada y solo cuenta la primera

#### Scenario: Otra categoría
- **WHEN** la misma credencial vota en otra categoría de la misma elección
- **THEN** es aceptada

#### Scenario: Credencial sin firma válida
- **WHEN** se emite una papeleta con credencial sin firma, con firma alterada o firmada por otra elección
- **THEN** es rechazada

#### Scenario: Papeleta firmada por otra clave
- **WHEN** alguien reutiliza una credencial ajena pero firma la transacción con otra clave
- **THEN** es rechazada

### Requirement: Ballot privacy of content
La papeleta MUST NOT contener datos personales (correo, nombre ni documento del votante) ni referencia a la identidad con la que se canjeó el código. El emisor de la transacción es únicamente la clave pública de la credencial anónima.

#### Scenario: Payload sin datos personales
- **WHEN** se inspecciona el payload de una papeleta
- **THEN** solo contiene elección, categoría, picks y la firma del emisor sobre la credencial
