## ADDED Requirements

### Requirement: Public chain read
La API SHALL exponer sin autenticación la cadena completa, un bloque por índice y el resultado de la validación de integridad. Las respuestas MUST NOT incluir correos, códigos ni datos del censo.

#### Scenario: Lectura de la cadena
- **WHEN** se consulta la cadena
- **THEN** devuelve los bloques en orden, su longitud y si la cadena es válida

#### Scenario: Bloque inexistente
- **WHEN** se consulta un índice fuera de rango
- **THEN** responde 404

### Requirement: Public election view
La API SHALL exponer sin autenticación el estado de una elección derivado de la cadena: estado, ventana, clave pública de emisión, categorías y candidatos.

#### Scenario: Elección existente
- **WHEN** se consulta una elección creada
- **THEN** devuelve estado, ventana, clave pública de emisión y candidatos por categoría

#### Scenario: Elección desconocida
- **WHEN** se consulta un identificador inexistente
- **THEN** responde 404

### Requirement: Tally visibility
El conteo SHALL estar disponible públicamente solo cuando la elección está cerrada, derivado de la cadena con el desempate definido en `tally`. Antes del cierre MUST responder 403, para no sesgar el voto (decisión abierta de visibilidad resuelta de la forma más restrictiva; reversible por spec).

#### Scenario: Conteo tras el cierre
- **WHEN** la elección está cerrada y se consulta el conteo
- **THEN** devuelve el ranking por categoría con puntos, posición y empate

#### Scenario: Conteo antes del cierre
- **WHEN** la elección está abierta o en borrador
- **THEN** responde 403 y no revela puntos
