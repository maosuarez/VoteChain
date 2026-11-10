# tally Specification

## Purpose
TBD - created by archiving change voting-domain-borda. Update Purpose after archive.

## Requirements

### Requirement: Deterministic derivation from the chain
El estado de las elecciones y el conteo SHALL derivarse únicamente del log de transacciones de la cadena, procesadas en orden de bloque y de posición. Las transacciones inválidas según las reglas de dominio MUST ignorarse de forma determinista, sin afectar a las demás. Dos nodos con la misma cadena MUST obtener el mismo resultado.

#### Scenario: Recalculable
- **WHEN** el conteo se calcula dos veces sobre la misma cadena
- **THEN** los resultados son idénticos

#### Scenario: Transacción inválida ignorada
- **WHEN** la cadena contiene una papeleta inválida entre papeletas válidas
- **THEN** el conteo solo refleja las válidas

### Requirement: Points per category
El puntaje de un candidato SHALL ser la suma de puntos recibidos (3/2/1) en las papeletas aceptadas de su categoría. El conteo MUST llevar además cuántos primeros y cuántos segundos lugares recibió. Candidatos sin votos MUST aparecer con 0.

#### Scenario: Suma de puntos
- **WHEN** hay dos papeletas aceptadas con picks [A,B,C] y [B,A,C]
- **THEN** A=5, B=5, C=2

### Requirement: Ranking and tie-break
El ranking SHALL ordenar por puntos descendente, luego por primeros lugares descendente, luego por segundos lugares descendente. Candidatos con los tres valores iguales MUST compartir posición y marcarse como empate declarado.

#### Scenario: Desempate por primeros lugares
- **WHEN** dos candidatos tienen los mismos puntos pero distinto número de primeros lugares
- **THEN** queda primero el de más primeros lugares

#### Scenario: Desempate por segundos lugares
- **WHEN** puntos y primeros lugares coinciden pero difieren los segundos
- **THEN** queda primero el de más segundos lugares

#### Scenario: Empate declarado
- **WHEN** puntos, primeros y segundos lugares coinciden
- **THEN** ambos comparten posición y se marcan como empatados

### Requirement: Tally availability
El conteo SHALL poder calcularse sobre una cadena con la elección abierta o cerrada. La política de visibilidad previa al cierre queda fuera de este change (decisión abierta) y no se aplica en esta capa.

#### Scenario: Conteo parcial
- **WHEN** se calcula el conteo con la elección abierta
- **THEN** refleja las papeletas aceptadas hasta ese punto
