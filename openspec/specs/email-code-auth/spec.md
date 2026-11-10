# email-code-auth Specification

## Purpose
TBD - created by archiving change voter-email-auth. Update Purpose after archive.

## Requirements

### Requirement: Code issuance
El sistema SHALL emitir un código aleatorio a un votante elegible del censo y entregarlo únicamente por correo mediante un proveedor de envío intercambiable. El código MUST ser generado con una fuente criptográficamente segura. Solicitar un código para un correo no elegible SHALL ser rechazado sin enviar correo.

#### Scenario: Emisión a elegible
- **WHEN** se solicita un código para un votante del censo
- **THEN** se envía un correo con el código a esa dirección y se registra la emisión

#### Scenario: No elegible
- **WHEN** se solicita un código para un correo fuera del censo
- **THEN** la solicitud es rechazada y no se envía correo

### Requirement: Hash-only storage and expiry
El código MUST almacenarse solo como hash; el valor en claro MUST NOT persistirse ni registrarse. Cada código SHALL expirar tras un tiempo configurable (por defecto 10 minutos) medido en segundos UTC.

#### Scenario: Sin texto claro
- **WHEN** se emite un código
- **THEN** ningún dato persistido contiene el código en claro

#### Scenario: Código expirado
- **WHEN** se canjea un código después de su expiración
- **THEN** el canje es rechazado y el votante no queda marcado

### Requirement: Single use
Un código SHALL poder canjearse una sola vez. Al canjearse con éxito, el votante MUST quedar marcado como "ya recibió credencial".

#### Scenario: Canje exitoso
- **WHEN** el votante canjea su código vigente y correcto
- **THEN** el canje es aceptado y el votante queda marcado

#### Scenario: Reuso
- **WHEN** se canjea de nuevo un código ya canjeado
- **THEN** es rechazado

### Requirement: Attempt limit
Cada código SHALL admitir un número máximo de intentos de canje fallidos (por defecto 5). Al superarlo el código MUST quedar inutilizable, incluso si luego se presenta el valor correcto.

#### Scenario: Intentos agotados
- **WHEN** se presentan 5 valores incorrectos y luego el correcto
- **THEN** el canje correcto es rechazado

#### Scenario: Código incorrecto
- **WHEN** se presenta un valor incorrecto dentro del límite
- **THEN** es rechazado y el código sigue siendo válido

### Requirement: Resend limit
Cada votante SHALL poder recibir como máximo un número configurable de emisiones por elección (por defecto 3). Una nueva emisión MUST invalidar los códigos anteriores del votante.

#### Scenario: Reenvío invalida el anterior
- **WHEN** se emite un segundo código al mismo votante
- **THEN** el primer código ya no puede canjearse

#### Scenario: Límite de reenvíos
- **WHEN** se solicita una emisión por encima del límite
- **THEN** es rechazada y no se envía correo

### Requirement: Issuance audit log
El sistema SHALL registrar cada emisión, canje y rechazo con elección, correo, tipo de evento y timestamp. El registro MUST NOT contener códigos ni referencias a papeletas, claves de firma o transacciones de voto.

#### Scenario: Registro de eventos
- **WHEN** ocurre una emisión y un canje
- **THEN** el registro contiene ambos eventos en orden con su timestamp

#### Scenario: Sin vínculo con votos
- **WHEN** se inspecciona el registro de auditoría
- **THEN** no existe ningún campo que referencie un voto, papeleta o clave pública de votante

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
