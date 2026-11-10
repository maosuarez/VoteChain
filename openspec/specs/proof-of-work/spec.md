# proof-of-work Specification

## Purpose
Exigir trabajo computacional medible para producir un bloque, con dificultad ajustable, como mecanismo didáctico previo al consenso por autoridad.

## Requirements

### Requirement: Mining
Minar un bloque SHALL buscar un nonce tal que el hash del bloque tenga al menos `difficulty` bits iniciales en cero. El nonce MUST formar parte de los campos hasheados.

#### Scenario: Bloque minado cumple dificultad
- **WHEN** se mina un bloque con dificultad D
- **THEN** su hash tiene al menos D bits iniciales en cero y el hash coincide con el recalculado

#### Scenario: Dificultad cero
- **WHEN** la dificultad es 0
- **THEN** cualquier nonce es válido y el bloque se acepta de inmediato

#### Scenario: Trabajo medible
- **WHEN** se mina con dificultades crecientes
- **THEN** el número de intentos necesarios se reporta y crece en promedio con la dificultad

### Requirement: Difficulty enforcement
La validación MUST rechazar cualquier bloque (salvo el génesis) de una cadena sin conjunto de validadores cuyo hash no cumpla la dificultad configurada de la cadena. En una cadena con conjunto de validadores (PoA) la dificultad MUST NOT evaluarse: la autoridad del proponente la reemplaza.

#### Scenario: Bloque sin trabajo
- **WHEN** se inserta un bloque con hash correcto pero sin cumplir la dificultad en una cadena sin validadores
- **THEN** la validación falla en ese bloque

#### Scenario: Nonce alterado
- **WHEN** se modifica el nonce de un bloque minado en una cadena sin validadores
- **THEN** la validación falla en ese bloque

#### Scenario: PoA no exige trabajo
- **WHEN** una cadena PoA contiene un bloque válido por autoridad cuyo hash no cumple la dificultad configurada
- **THEN** la validación no lo rechaza por falta de trabajo

### Requirement: Not production consensus
PoW SHALL permanecer solo como mecanismo didáctico (cadenas sin conjunto de validadores). El consenso de producción MUST ser PoA; una red de nodos MUST construirse sobre cadenas con conjunto de validadores.

#### Scenario: Nodos de red usan PoA
- **WHEN** se crea un nodo de la red
- **THEN** su cadena exige conjunto de validadores y valida por autoridad, no por trabajo
