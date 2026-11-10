# blind-credentials Specification

## Purpose
Emisión de credenciales de voto por firma ciega y su verificación pública, de modo que la credencial pruebe elegibilidad sin poder vincularse a la persona que la recibió, ni siquiera por el emisor.

## Requirements

### Requirement: Blind signature issuance
El emisor SHALL firmar un mensaje ciego sin conocer su contenido. El votante MUST poder quitar el cegado y obtener una firma válida sobre el mensaje original. Cada elección SHALL tener su propio par de claves de emisión; la clave pública MUST ser consultable en la cadena.

#### Scenario: Ciclo ciego/firma/descegado
- **WHEN** el votante ciega un mensaje, el emisor lo firma y el votante quita el cegado
- **THEN** la firma resultante verifica contra la clave pública sobre el mensaje original

#### Scenario: Emisor no ve el mensaje
- **WHEN** se compara el valor ciego recibido por el emisor con el mensaje original y con la firma final
- **THEN** ninguno es derivable del valor ciego sin el factor de cegado del votante

#### Scenario: Mensaje ciego inválido
- **WHEN** el emisor recibe un valor ciego mal formado o fuera de rango
- **THEN** lo rechaza sin firmar

### Requirement: Credential verification
Una credencial SHALL consistir en una clave pública de votante generada por el votante y una firma del emisor sobre ella (ligada a la elección). La verificación MUST ser pública y determinista usando solo la clave pública de emisión. Una firma de otra elección, de otra clave o alterada MUST fallar sin lanzar excepciones.

#### Scenario: Credencial válida
- **WHEN** se verifica una credencial firmada por el emisor de esa elección
- **THEN** la verificación es exitosa

#### Scenario: Credencial inválida
- **WHEN** la firma está alterada, es de otra elección o pertenece a otra clave de votante
- **THEN** la verificación falla

### Requirement: Issuer cannot link credential to voter
El emisor (master) MUST NOT poder determinar qué credencial pertenece a qué votante con la información que posee (censo, registro de auditoría y valores ciegos recibidos) más la cadena pública. El sistema MUST NOT persistir valores ciegos ni firmas ciegas emitidas.

#### Scenario: Toda asociación es igualmente consistente
- **WHEN** el master intenta emparejar cada valor ciego recibido con cada credencial de la cadena
- **THEN** cada emparejamiento es matemáticamente consistente y no hay ninguno preferible

#### Scenario: Sin rastro persistido
- **WHEN** se inspecciona lo persistido tras emitir una credencial
- **THEN** no contiene el valor ciego, la firma ni la clave pública de la credencial
