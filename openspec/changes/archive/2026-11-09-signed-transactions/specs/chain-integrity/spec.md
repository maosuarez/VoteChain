## MODIFIED Requirements

### Requirement: Block structure
Un bloque SHALL contener índice, timestamp (UTC, entero en segundos), hash del bloque previo, datos, raíz de Merkle de sus transacciones, nonce y su propio hash. El hash MUST calcularse con SHA-256 sobre la serialización canónica de todos los campos excepto el propio hash.

#### Scenario: Hash determinista
- **WHEN** se construyen dos bloques con los mismos campos
- **THEN** ambos producen exactamente el mismo hash

#### Scenario: El hash no se incluye en su propio cálculo
- **WHEN** se calcula el hash de un bloque
- **THEN** el valor del campo hash no influye en el resultado

#### Scenario: Cambio mínimo cambia el hash
- **WHEN** se altera cualquier campo de los datos, la raíz de Merkle o el nonce de un bloque
- **THEN** el hash recalculado difiere del almacenado

### Requirement: Chain validation
La validación de la cadena MUST verificar, para cada bloque, (a) que su hash coincide con el recalculado, (b) que su `prev_hash` coincide con el hash del bloque anterior, (c) que los índices son consecutivos desde 0, (d) que su raíz de Merkle coincide con la de sus transacciones, (e) que cada transacción tiene firma válida y no repite un identificador ya incluido, y (f) que el hash cumple la dificultad configurada. También MUST verificar que el bloque 0 es el génesis esperado. Ante cualquier fallo SHALL reportar que la cadena es inválida e indicar el índice del primer bloque defectuoso.

#### Scenario: Alteración de datos detectada
- **WHEN** se modifican los datos de un bloque intermedio sin recalcular su hash
- **THEN** la validación falla e indica el índice de ese bloque

#### Scenario: Alteración con hash recalculado detectada
- **WHEN** se modifican los datos de un bloque intermedio y se recalcula su hash
- **THEN** la validación falla en ese bloque o en el siguiente

#### Scenario: Índices no consecutivos
- **WHEN** un bloque tiene un índice que no sigue al anterior
- **THEN** la validación falla e indica ese bloque

#### Scenario: Génesis alterado
- **WHEN** se modifica el bloque génesis
- **THEN** la validación falla en el índice 0

#### Scenario: Eliminación de bloque intermedio
- **WHEN** se elimina un bloque intermedio de la cadena
- **THEN** la validación falla

#### Scenario: Transacción con firma inválida dentro de un bloque
- **WHEN** un bloque contiene una transacción alterada y se recalculan su raíz de Merkle y su hash
- **THEN** la validación falla en ese bloque por firma inválida

#### Scenario: Raíz de Merkle inconsistente
- **WHEN** la raíz de Merkle de un bloque no corresponde a sus transacciones
- **THEN** la validación falla en ese bloque
