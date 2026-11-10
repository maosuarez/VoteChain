## Purpose

Exigir trabajo computacional medible para producir un bloque, con dificultad ajustable, como mecanismo didáctico previo al consenso por autoridad.

## ADDED Requirements

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
La validación MUST rechazar cualquier bloque (salvo el génesis) cuyo hash no cumpla la dificultad configurada de la cadena.

#### Scenario: Bloque sin trabajo
- **WHEN** se inserta un bloque con hash correcto pero sin cumplir la dificultad
- **THEN** la validación falla en ese bloque

#### Scenario: Nonce alterado
- **WHEN** se modifica el nonce de un bloque minado
- **THEN** la validación falla en ese bloque
