## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Not production consensus
PoW SHALL permanecer solo como mecanismo didáctico (cadenas sin conjunto de validadores). El consenso de producción MUST ser PoA; una red de nodos MUST construirse sobre cadenas con conjunto de validadores.

#### Scenario: Nodos de red usan PoA
- **WHEN** se crea un nodo de la red
- **THEN** su cadena exige conjunto de validadores y valida por autoridad, no por trabajo
