# signed-transactions Specification

## Purpose
Establecer que la identidad en la cadena es una clave pública y que toda transacción debe estar firmada, de modo que nadie pueda inyectar ni alterar transacciones sin ser detectado.

## Requirements

### Requirement: Key identity
Una identidad SHALL ser un par de claves Ed25519; su identificador público MUST ser la clave pública codificada en hexadecimal.

#### Scenario: Identidades distintas
- **WHEN** se generan dos pares de claves
- **THEN** sus identificadores públicos son distintos

### Requirement: Signed transaction
Una transacción SHALL contener tipo, payload, emisor (identificador público), timestamp (UTC, entero en segundos) y firma. La firma MUST cubrir la serialización canónica de todos los campos excepto la propia firma. El identificador de la transacción MUST ser el SHA-256 de esa misma serialización.

#### Scenario: Transacción válida
- **WHEN** una transacción es firmada por la clave privada correspondiente a su emisor
- **THEN** la verificación es exitosa

#### Scenario: Payload alterado
- **WHEN** se modifica cualquier campo de una transacción firmada
- **THEN** la verificación falla

#### Scenario: Firma de otra identidad
- **WHEN** la transacción declara un emisor pero está firmada con otra clave
- **THEN** la verificación falla

#### Scenario: Firma malformada
- **WHEN** la firma o el emisor no son hexadecimal válido de la longitud esperada
- **THEN** la verificación falla sin lanzar excepción al llamador

### Requirement: Mempool admission
El mempool MUST aceptar únicamente transacciones con firma válida y rechazar las duplicadas (mismo identificador de transacción).

#### Scenario: Firma inválida rechazada
- **WHEN** se intenta agregar al mempool una transacción con firma inválida
- **THEN** es rechazada y el mempool no cambia

#### Scenario: Duplicado rechazado
- **WHEN** se agrega dos veces la misma transacción
- **THEN** la segunda es rechazada

#### Scenario: Orden de llegada
- **WHEN** se extraen transacciones del mempool para un bloque
- **THEN** se entregan en orden de llegada, hasta un máximo configurable, y salen del mempool

### Requirement: No replay on chain
Una transacción con un identificador ya incluido en la cadena MUST ser rechazada al validar un bloque que la repita.

#### Scenario: Reinclusión rechazada
- **WHEN** un bloque contiene una transacción cuyo identificador ya aparece en un bloque anterior
- **THEN** la validación de la cadena falla en ese bloque

### Requirement: Merkle commitment
Cada bloque SHALL comprometerse con su lista de transacciones mediante una raíz de Merkle. El cálculo MUST usar separación de dominio entre hojas y nodos internos y MUST NOT permitir que dos listas distintas produzcan la misma raíz.

#### Scenario: Raíz determinista
- **WHEN** se calcula la raíz de la misma lista de transacciones dos veces
- **THEN** el resultado es idéntico

#### Scenario: Orden importa
- **WHEN** se intercambian dos transacciones de la lista
- **THEN** la raíz cambia

#### Scenario: Lista con número impar no colisiona
- **WHEN** se compara la raíz de [A, B, C] con la de [A, B, C, C]
- **THEN** las raíces son distintas

#### Scenario: Bloque sin transacciones
- **WHEN** un bloque no tiene transacciones
- **THEN** su raíz es un valor constante y definido
