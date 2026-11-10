## ADDED Requirements

### Requirement: Validator set
Una cadena PoA SHALL tener un conjunto fijo y ordenado de validadores identificados por su clave pública Ed25519 (hex). El conjunto MUST ser no vacío y sin duplicados; un conjunto inválido SHALL rechazarse al crearlo.

#### Scenario: Conjunto válido
- **WHEN** se crea un conjunto con 3 claves públicas distintas
- **THEN** el conjunto se crea y conserva el orden dado

#### Scenario: Conjunto vacío o con duplicados
- **WHEN** se intenta crear un conjunto vacío o con una clave repetida
- **THEN** la creación falla

### Requirement: Round-robin proposer
El validador autorizado para proponer el bloque de índice `i` (i >= 1) SHALL ser el que ocupa la posición `i mod N` del conjunto de N validadores.

#### Scenario: Rotación
- **WHEN** se consulta el proponente de los bloques 1 a 4 con 3 validadores [V0, V1, V2]
- **THEN** son V1, V2, V0, V1

### Requirement: Signed blocks
Un bloque de una cadena PoA SHALL declarar su proponente y llevar la firma del proponente sobre el hash del bloque. El proponente MUST formar parte de los campos hasheados; la firma NO.

#### Scenario: Bloque propuesto es válido
- **WHEN** el validador en turno propone y firma un bloque sobre la punta de la cadena
- **THEN** la cadena con ese bloque es válida

#### Scenario: Firma alterada
- **WHEN** se modifica la firma de un bloque de una cadena PoA
- **THEN** la validación falla en ese bloque

### Requirement: Unauthorized proposers rejected
La validación de una cadena PoA MUST rechazar un bloque cuyo proponente no esté en el conjunto de validadores, o que esté en el conjunto pero no sea el del turno de ese índice, indicando el índice defectuoso.

#### Scenario: Nodo no autorizado
- **WHEN** una clave fuera del conjunto firma un bloque sobre la punta de la cadena
- **THEN** la validación rechaza el bloque por proponente no autorizado y la cadena no lo incorpora

#### Scenario: Validador fuera de turno
- **WHEN** un validador del conjunto firma el bloque de un índice que no le corresponde
- **THEN** la validación rechaza el bloque por fuera de turno

#### Scenario: Un no validador no produce
- **WHEN** un nodo cuya clave no está en el conjunto intenta producir un bloque
- **THEN** no se produce ningún bloque

### Requirement: Block production by turn
Un nodo validador SHALL producir un bloque solo cuando sea su turno, con el lote de su mempool, omitiendo transacciones ya incluidas en la cadena.

#### Scenario: Producción en turno
- **WHEN** el validador en turno produce un bloque con transacciones en su mempool
- **THEN** el bloque contiene ese lote y la cadena sigue siendo válida

#### Scenario: Producción fuera de turno
- **WHEN** un validador intenta producir cuando no es su turno
- **THEN** no se produce ningún bloque
