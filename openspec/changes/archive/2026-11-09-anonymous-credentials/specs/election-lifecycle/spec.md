# Spec Delta

## MODIFIED Requirements

### Requirement: Election creation
Una elección SHALL crearse con una transacción `CREATE_ELECTION` que declara identificador, `opens_at` y `closes_at` (enteros UTC en segundos, con `opens_at` < `closes_at`) y la clave pública de emisión de credenciales de esa elección. El emisor MUST quedar registrado como administrador de esa elección. Un identificador de elección MUST NOT poder crearse dos veces. Una clave de emisión ausente o mal formada MUST ser rechazada.

#### Scenario: Elección creada
- **WHEN** se procesa un `CREATE_ELECTION` válido
- **THEN** la elección existe en estado borrador, su administrador es el emisor y su clave de emisión queda registrada

#### Scenario: Identificador repetido
- **WHEN** se procesa un segundo `CREATE_ELECTION` con el mismo identificador
- **THEN** es rechazado y la elección original no cambia

#### Scenario: Ventana inválida
- **WHEN** `opens_at` es mayor o igual que `closes_at`
- **THEN** la transacción es rechazada

#### Scenario: Clave de emisión inválida
- **WHEN** falta la clave de emisión o está mal formada
- **THEN** la transacción es rechazada
