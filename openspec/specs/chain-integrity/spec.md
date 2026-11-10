# chain-integrity Specification

## Purpose
Garantizar que el registro de bloques sea inmutable de forma verificable: cualquier alteración de un bloque o de su orden debe ser detectable por quien valide la cadena.

## Requirements

### Requirement: Block structure
Un bloque SHALL contener índice, timestamp (UTC, entero en segundos), hash del bloque previo, datos, raíz de Merkle de sus transacciones, nonce, proponente (vacío si no hay consenso por autoridad), su propio hash y la firma del proponente (vacía si no aplica). El hash MUST calcularse con SHA-256 sobre la serialización canónica de todos los campos excepto el propio hash y la firma.

#### Scenario: Hash determinista
- **WHEN** se construyen dos bloques con los mismos campos
- **THEN** ambos producen exactamente el mismo hash

#### Scenario: El hash no se incluye en su propio cálculo
- **WHEN** se calcula el hash de un bloque
- **THEN** el valor del campo hash no influye en el resultado

#### Scenario: Cambio mínimo cambia el hash
- **WHEN** se altera cualquier campo de los datos, la raíz de Merkle, el nonce o el proponente de un bloque
- **THEN** el hash recalculado difiere del almacenado

#### Scenario: La firma no se incluye en el hash
- **WHEN** se cambia solo la firma de un bloque
- **THEN** el hash recalculado no cambia

### Requirement: Canonical serialization
La serialización usada para hashear MUST ser JSON con claves ordenadas, sin espacios y codificación UTF-8, de modo que el resultado no dependa del orden de inserción ni de la plataforma.

#### Scenario: Orden de claves irrelevante
- **WHEN** dos diccionarios de datos tienen las mismas claves y valores en distinto orden
- **THEN** su serialización canónica es idéntica

### Requirement: Genesis block
La cadena SHALL iniciar con un bloque génesis fijo y determinista: índice 0, `prev_hash` de 64 ceros, timestamp constante y datos constantes.

#### Scenario: Génesis idéntico entre instancias
- **WHEN** se crean dos cadenas nuevas
- **THEN** sus bloques génesis tienen el mismo hash

#### Scenario: Cadena nueva es válida
- **WHEN** se valida una cadena recién creada
- **THEN** la validación es exitosa

### Requirement: Appending blocks
Al agregar un bloque, el sistema SHALL asignar el índice consecutivo, tomar como `prev_hash` el hash del último bloque y calcular el hash del nuevo bloque.

#### Scenario: Encadenamiento
- **WHEN** se agrega un bloque a una cadena de longitud N
- **THEN** el nuevo bloque tiene índice N y su `prev_hash` es el hash del bloque N-1

### Requirement: Chain validation
La validación de la cadena MUST verificar, para cada bloque, (a) que su hash coincide con el recalculado, (b) que su `prev_hash` coincide con el hash del bloque anterior, (c) que los índices son consecutivos desde 0, (d) que su raíz de Merkle coincide con la de sus transacciones, (e) que cada transacción tiene firma válida y no repite un identificador ya incluido, y (f) que cumple el consenso configurado: la dificultad si la cadena es PoW, o proponente autorizado, en turno y con firma válida si la cadena es PoA. También MUST verificar que el bloque 0 es el génesis esperado. Ante cualquier fallo SHALL reportar que la cadena es inválida e indicar el índice del primer bloque defectuoso.

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

#### Scenario: Bloque PoA con proponente no autorizado
- **WHEN** una cadena PoA contiene un bloque firmado por una clave fuera del conjunto de validadores
- **THEN** la validación falla en ese bloque

### Requirement: Tamper demonstration
El proyecto SHALL incluir un script de demostración que altere un bloque intermedio y muestre en qué bloque se rompe la cadena.

#### Scenario: Demo muestra el punto de ruptura
- **WHEN** se ejecuta el script de demostración
- **THEN** imprime que la cadena es válida antes de la alteración e inválida después, con el índice del bloque donde se detecta
