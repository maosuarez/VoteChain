# Spec Delta

## ADDED Requirements

### Requirement: Blind credential delivery
El canje exitoso de un código SHALL entregar la firma ciega del emisor sobre el valor ciego presentado, como máximo una vez por votante y elección. El valor ciego MUST validarse antes de consumir el código; si es inválido el código no se consume. Si la elección no tiene clave de emisión registrada, el canje MUST ser rechazado sin consumir el código.

#### Scenario: Canje entrega firma ciega
- **WHEN** el votante canjea un código vigente junto con un valor ciego válido
- **THEN** recibe la firma ciega, queda marcado como "ya recibió credencial" y el código no puede reusarse

#### Scenario: Valor ciego inválido
- **WHEN** el votante canjea un código vigente con un valor ciego inválido
- **THEN** el canje es rechazado y el código sigue siendo canjeable

#### Scenario: Segundo canje
- **WHEN** un votante que ya recibió credencial intenta canjear otro código
- **THEN** no recibe una segunda firma

#### Scenario: Auditoría sin credencial
- **WHEN** se inspecciona el registro de auditoría tras entregar la credencial
- **THEN** registra el canje pero no el valor ciego ni la firma entregada
