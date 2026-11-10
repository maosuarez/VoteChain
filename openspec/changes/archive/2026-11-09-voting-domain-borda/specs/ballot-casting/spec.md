## ADDED Requirements

### Requirement: Ordered ballot of three
`CAST_BALLOT` SHALL declarar elección, categoría y una lista ordenada de exactamente 3 `candidate_id` distintos, todos pertenecientes al listado de esa categoría. El primer pick vale 3 puntos, el segundo 2 y el tercero 1. No se admiten papeletas en blanco ni con menos de 3 picks.

#### Scenario: Papeleta válida
- **WHEN** una identidad emite una papeleta con 3 candidatos válidos y distintos en una elección abierta dentro de su ventana
- **THEN** la papeleta es aceptada y suma 3, 2 y 1 puntos en el orden dado

#### Scenario: Picks repetidos
- **WHEN** la lista contiene un candidato repetido
- **THEN** la papeleta es rechazada

#### Scenario: Cantidad incorrecta
- **WHEN** la lista tiene menos o más de 3 picks
- **THEN** la papeleta es rechazada

#### Scenario: Candidato inexistente
- **WHEN** algún pick no pertenece a la categoría indicada
- **THEN** la papeleta es rechazada

#### Scenario: Categoría inexistente
- **WHEN** la categoría no existe en la elección
- **THEN** la papeleta es rechazada

### Requirement: One ballot per credential per category
Cada credencial (en este change, la clave pública del emisor) SHALL poder emitir como máximo una papeleta por categoría por elección. Las papeletas en categorías distintas son independientes.

#### Scenario: Doble voto
- **WHEN** la misma credencial emite una segunda papeleta en la misma categoría
- **THEN** la segunda es rechazada y solo cuenta la primera

#### Scenario: Otra categoría
- **WHEN** la misma credencial vota en otra categoría de la misma elección
- **THEN** es aceptada

### Requirement: Election window and state
Una papeleta MUST ser rechazada si la elección no está abierta, si ya fue cerrada, o si el timestamp del bloque que la contiene está fuera de `[opens_at, closes_at]`. Un voto que apunta a una elección inexistente MUST ser rechazado.

#### Scenario: Elección no abierta
- **WHEN** se emite una papeleta con la elección en borrador o cerrada
- **THEN** es rechazada

#### Scenario: Fuera de ventana
- **WHEN** el bloque que contiene la papeleta tiene timestamp anterior a `opens_at` o posterior a `closes_at`
- **THEN** es rechazada

### Requirement: Ballot privacy of content
La papeleta MUST NOT contener datos personales (correo, nombre ni documento del votante). El emisor es únicamente la clave pseudónima. La vinculación real credencial-persona queda fuera de este change.

#### Scenario: Payload sin datos personales
- **WHEN** se inspecciona el payload de una papeleta
- **THEN** solo contiene elección, categoría y picks
