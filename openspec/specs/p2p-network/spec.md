# p2p-network Specification

## Purpose
Hacer que varios nodos mantengan la misma cadena: propagación de transacciones y bloques, sincronización, resolución de forks y convergencia tras particiones, sobre un transporte inyectable.

## Requirements

### Requirement: Pluggable transport
La comunicación entre nodos (enviar transacción, enviar bloque, pedir cadena) SHALL pasar por un transporte inyectable, de modo que la red completa pueda ejecutarse en un solo proceso sin infraestructura externa. El conjunto de pares de un nodo SHALL ser el que expone el transporte.

#### Scenario: Red en un proceso
- **WHEN** se crean 3 nodos sobre un transporte en memoria
- **THEN** pueden intercambiar transacciones, bloques y cadenas sin sockets ni procesos externos

#### Scenario: Transporte con partición
- **WHEN** el transporte en memoria se particiona en dos grupos
- **THEN** los mensajes solo llegan entre nodos del mismo grupo

### Requirement: Transaction propagation
Un nodo que acepte una transacción válida y nueva SHALL reenviarla a sus pares alcanzables. Una transacción con firma inválida, duplicada o ya incluida en la cadena MUST descartarse sin reenviarse.

#### Scenario: Propagación
- **WHEN** se envía una transacción válida a un nodo
- **THEN** todos los nodos alcanzables la tienen en su mempool, sin reenvíos infinitos

#### Scenario: Transacción inválida
- **WHEN** un nodo recibe una transacción con firma inválida
- **THEN** la descarta y sus pares no la reciben

### Requirement: Block propagation
Un nodo que acepte un bloque válido que extiende su cadena SHALL reenviarlo a sus pares y retirar de su mempool las transacciones incluidas. Un bloque inválido MUST descartarse sin reenviarse y sin modificar la cadena.

#### Scenario: Propagación de bloque
- **WHEN** el validador en turno produce un bloque
- **THEN** todos los nodos alcanzables lo añaden y sus mempools no conservan sus transacciones

#### Scenario: Bloque de no validador
- **WHEN** un nodo recibe un bloque firmado por una clave fuera del conjunto de validadores
- **THEN** lo rechaza, su cadena no cambia y no lo reenvía

### Requirement: Chain synchronization
Un nodo SHALL poder sincronizarse con sus pares: pedir sus cadenas y adoptar la mejor. Al recibir un bloque que no encaja con su punta, el nodo SHALL intentar sincronizarse con el emisor.

#### Scenario: Sincronización inicial
- **WHEN** un nodo nuevo con solo el génesis se sincroniza con un par que tiene una cadena válida más larga
- **THEN** adopta esa cadena

#### Scenario: Bloque con hueco
- **WHEN** un nodo recibe un bloque cuyo índice supera su longitud
- **THEN** se sincroniza con el emisor y adopta su cadena válida

### Requirement: Fork resolution
Un nodo SHALL adoptar una cadena candidata solo si es válida y (a) es más larga que la propia o (b) tiene igual longitud y el hash de su punta es menor. Una cadena inválida MUST rechazarse aunque sea más larga.

#### Scenario: Gana la cadena válida más larga
- **WHEN** un nodo recibe una candidata válida más larga que la suya
- **THEN** reemplaza su cadena por la candidata

#### Scenario: Candidata inválida más larga
- **WHEN** la candidata es más larga pero contiene un bloque inválido
- **THEN** el nodo conserva su cadena

#### Scenario: Empate determinista
- **WHEN** dos cadenas válidas tienen igual longitud y puntas distintas
- **THEN** todos los nodos eligen la misma, la de menor hash de punta

### Requirement: Convergence after partition
Tras una partición y la reconexión de la red, los nodos SHALL converger a la misma cadena válida una vez sincronizados.

#### Scenario: Tres nodos convergen
- **WHEN** 3 nodos validadores se particionan, la parte con los validadores en turno produce bloques, y la red se reconecta y se sincroniza
- **THEN** los 3 nodos tienen la misma punta y la cadena es válida

#### Scenario: Nodo no autorizado en la red
- **WHEN** un nodo no autorizado difunde un bloque a la red
- **THEN** ningún nodo lo incorpora y todos mantienen la misma cadena
