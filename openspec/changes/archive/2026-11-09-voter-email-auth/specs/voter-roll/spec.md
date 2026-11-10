## ADDED Requirements

### Requirement: Voter roll per election
El sistema SHALL mantener un censo de votantes habilitados por elección, identificados por correo institucional normalizado (minúsculas, sin espacios). El censo MUST almacenarse fuera de la cadena. Solo el master SHALL poder cargarlo. Un correo MUST NOT aparecer dos veces en el mismo censo.

#### Scenario: Carga de censo
- **WHEN** el master carga una lista de correos para una elección
- **THEN** cada correo queda habilitado en esa elección y no habilitado en otras

#### Scenario: Normalización y duplicados
- **WHEN** la lista contiene `A@x.edu` y ` a@x.edu `
- **THEN** se registra un solo votante

#### Scenario: Correo inválido
- **WHEN** un elemento no tiene forma de correo (`algo@dominio`)
- **THEN** la carga es rechazada completa y el censo no cambia

#### Scenario: Consulta de elegibilidad
- **WHEN** se consulta un correo que no está en el censo de la elección
- **THEN** el sistema responde que no es elegible

### Requirement: Credential-received flag
Cada votante del censo SHALL tener un indicador "ya recibió credencial", inicialmente falso. El indicador MUST pasar a verdadero solo al canjear con éxito un código y MUST NOT volver a falso.

#### Scenario: Estado inicial
- **WHEN** se carga un votante
- **THEN** su indicador es falso

#### Scenario: Votante que ya recibió credencial
- **WHEN** un votante con indicador verdadero solicita un nuevo código
- **THEN** la solicitud es rechazada
