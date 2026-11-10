# master-admin Specification

## Purpose
TBD - created by archiving change master-admin-api. Update Purpose after archive.

## Requirements

### Requirement: Master authentication
Toda ruta administrativa SHALL exigir un token de master configurable enviado como `Authorization: Bearer <token>`. La comparación MUST ser en tiempo constante. Sin token, con token incorrecto o con esquema distinto, la ruta MUST responder 401 sin ejecutar ninguna acción. El sistema MUST negarse a arrancar con un token vacío. El token MUST NOT aparecer en respuestas, auditoría ni cadena.

#### Scenario: Sin credenciales
- **WHEN** se invoca una ruta administrativa sin cabecera `Authorization`
- **THEN** responde 401 y no cambia el estado de la cadena ni del censo

#### Scenario: Token incorrecto
- **WHEN** se invoca una ruta administrativa con un token distinto al configurado
- **THEN** responde 401 y no cambia el estado

#### Scenario: Token vacío en configuración
- **WHEN** se intenta crear la aplicación con token de master vacío
- **THEN** la creación falla

### Requirement: Election administration recorded on chain
Crear elección, agregar categoría, agregar candidato, abrir y cerrar SHALL registrarse como transacciones firmadas con la clave del master y minadas en un bloque. La clave privada del master MUST NOT salir del servidor. Antes de aceptar una acción, la API MUST validarla contra el estado derivado de la cadena y, si el dominio la rechaza, MUST responder 409 con el motivo y MUST NOT minar nada.

#### Scenario: Elección configurada y abierta
- **WHEN** el master crea una elección, agrega una categoría con 3 candidatos y la abre
- **THEN** cada acción queda en un bloque como transacción firmada por el master y el estado derivado de la cadena es `open`

#### Scenario: Acción rechazada por el dominio
- **WHEN** el master intenta abrir una elección con una categoría de menos de 3 candidatos
- **THEN** responde 409 con el motivo y la cadena no crece

### Requirement: Issuer key generation
Al crear una elección la API SHALL generar la clave de emisión de credenciales, registrar solo su parte pública en `CREATE_ELECTION` y entregar la privada únicamente al servicio de códigos, nunca a la cadena ni a una respuesta.

#### Scenario: Clave de emisión pública
- **WHEN** se crea una elección
- **THEN** la respuesta y la cadena contienen la clave pública de emisión y ninguno contiene la privada

### Requirement: Voter roll upload and code resend
El master SHALL poder cargar el censo de una elección (lista de correos) y reenviar el código a un correo del censo. El censo, los correos y los códigos MUST NOT escribirse en la cadena. Una lista con algún correo inválido MUST rechazarse completa con 400. Reenviar a un correo no habilitado o ya servido MUST responder igual que un rechazo genérico del servicio de códigos, sin detallar el motivo.

#### Scenario: Censo cargado
- **WHEN** el master carga una lista de correos válidos
- **THEN** los votantes quedan habilitados en el servicio de códigos y la cadena no cambia

#### Scenario: Correo inválido en el censo
- **WHEN** la lista contiene un correo mal formado
- **THEN** responde 400 y no se habilita a nadie

#### Scenario: Reenvío
- **WHEN** el master solicita código para un correo habilitado
- **THEN** el correo recibe un código nuevo y la respuesta indica `sent: true`

#### Scenario: Reenvío rechazado
- **WHEN** el master solicita código para un correo no habilitado, o ya con credencial
- **THEN** no se envía nada y la respuesta indica `sent: false` sin motivo

### Requirement: Master cannot link vote and identity
Ninguna ruta administrativa SHALL devolver papeletas, credenciales, valores ciegos ni asociación entre un correo y una credencial. La API MUST NOT persistir ni registrar valor ciego, firma ciega ni credencial recibida en rutas del votante.

#### Scenario: Sin rutas de vínculo
- **WHEN** se enumeran las rutas administrativas
- **THEN** ninguna acepta o devuelve credenciales, papeletas o valores ciegos
