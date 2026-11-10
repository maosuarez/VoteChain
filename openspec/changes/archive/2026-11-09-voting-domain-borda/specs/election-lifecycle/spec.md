## ADDED Requirements

### Requirement: Election creation
Una elección SHALL crearse con una transacción `CREATE_ELECTION` que declara identificador, `opens_at` y `closes_at` (enteros UTC en segundos, con `opens_at` < `closes_at`). El emisor MUST quedar registrado como administrador de esa elección. Un identificador de elección MUST NOT poder crearse dos veces.

#### Scenario: Elección creada
- **WHEN** se procesa un `CREATE_ELECTION` válido
- **THEN** la elección existe en estado borrador y su administrador es el emisor

#### Scenario: Identificador repetido
- **WHEN** se procesa un segundo `CREATE_ELECTION` con el mismo identificador
- **THEN** es rechazado y la elección original no cambia

#### Scenario: Ventana inválida
- **WHEN** `opens_at` es mayor o igual que `closes_at`
- **THEN** la transacción es rechazada

### Requirement: Categories and candidates
`ADD_CATEGORY` y `ADD_CANDIDATE` SHALL ser aceptadas solo del administrador y solo mientras la elección está en borrador. Cada categoría tiene su propio listado de candidatos; un candidato se identifica por un `candidate_id` único dentro de su categoría. La cadena MUST NOT contener datos personales de candidatos más allá de su identificador y nombre público.

#### Scenario: Estructura por el administrador
- **WHEN** el administrador agrega una categoría y candidatos en borrador
- **THEN** quedan registrados en esa elección

#### Scenario: Emisor no administrador
- **WHEN** otra identidad envía `ADD_CATEGORY` o `ADD_CANDIDATE`
- **THEN** es rechazada

#### Scenario: Cambio tras la apertura
- **WHEN** se intenta agregar una categoría o candidato con la elección abierta o cerrada
- **THEN** es rechazado

#### Scenario: Duplicados
- **WHEN** se agrega una categoría o un candidato ya existente en su ámbito
- **THEN** es rechazado

### Requirement: Open and close
`OPEN_ELECTION` SHALL ser aceptada solo del administrador, desde borrador, y solo si la elección tiene al menos una categoría y todas sus categorías tienen al menos 3 candidatos. `CLOSE_ELECTION` SHALL ser aceptada solo del administrador y solo desde abierta. El estado cerrado MUST ser definitivo.

#### Scenario: Apertura válida
- **WHEN** el administrador abre una elección completa
- **THEN** el estado pasa a abierta

#### Scenario: Apertura con categoría insuficiente
- **WHEN** alguna categoría tiene menos de 3 candidatos, o no hay categorías
- **THEN** la apertura es rechazada

#### Scenario: Cierre y reapertura
- **WHEN** el administrador cierra una elección abierta y luego intenta abrirla o cerrarla de nuevo
- **THEN** ambas operaciones son rechazadas

#### Scenario: Cierre por no administrador
- **WHEN** otra identidad envía `CLOSE_ELECTION`
- **THEN** es rechazada
