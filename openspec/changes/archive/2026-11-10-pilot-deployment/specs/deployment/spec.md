## ADDED Requirements

### Requirement: Multi-node PoA network over HTTP
El sistema SHALL poder ejecutarse como una red de 3 a 5 nodos validadores PoA en procesos separados que se comunican por HTTP (transacciones, bloques y cadena), con el conjunto ordenado de validadores y la lista de pares fijados por configuración.

#### Scenario: Tres validadores convergen
- **WHEN** se envía una transacción válida a cualquier nodo de una red de 3 validadores
- **THEN** un bloque firmado por el validador en turno la incluye y los tres nodos y la API terminan con la misma cadena y la misma punta

#### Scenario: Bloque de no validador
- **WHEN** un cliente envía por HTTP un bloque firmado por una clave fuera del conjunto de validadores
- **THEN** el nodo lo descarta y su cadena no cambia

### Requirement: Validator liveness and recovery
Un validador SHALL producir un bloque solo cuando le toca el turno y tiene transacciones pendientes. Un nodo inalcanzable MUST NOT impedir que los demás acepten y propaguen mensajes. La cadena se detiene mientras el validador en turno esté caído y MUST continuar al volver sin intervención manual (sincronización periódica).

#### Scenario: Par caído
- **WHEN** un validador que no está en turno se detiene y se envían transacciones
- **THEN** los nodos restantes siguen produciendo y aceptando bloques sin errores no controlados

#### Scenario: Recuperación tras caída
- **WHEN** un validador detenido vuelve a arrancar tras haberse producido bloques
- **THEN** alcanza la cadena de sus pares sin intervención manual

### Requirement: API backed by the PoA network
La API SHALL poder funcionar sobre un nodo de la red en lugar de minar localmente. En ese modo MUST validar la acción contra el estado derivado de la cadena, entregarla a la red y responder éxito solo cuando la transacción esté incluida en la cadena del nodo; si no se confirma dentro de un plazo configurable MUST responder 503 sin presentar la acción como aplicada. Las reglas de privacidad y de rechazos unificados de la API MUST mantenerse idénticas.

#### Scenario: Acción confirmada
- **WHEN** el master crea una elección con la API conectada a la red
- **THEN** la respuesta es de éxito y la elección aparece en la cadena de todos los nodos

#### Scenario: Sin confirmación
- **WHEN** ningún validador puede producir el bloque dentro del plazo
- **THEN** la API responde 503 y no reporta la acción como aplicada

#### Scenario: Rechazo de dominio sin cambios
- **WHEN** se envía una papeleta inválida con la API conectada a la red
- **THEN** responde 400 `ballot_rejected` y no se propaga nada

### Requirement: State persistence across restarts
Cada nodo y la API SHALL persistir su estado en un directorio de datos y recuperarlo al arrancar: la cadena, el censo con hashes de códigos y auditoría, y las claves de emisión por elección (legibles solo por el propietario). La clave del master y los tokens MUST provenir de la configuración y MUST NOT escribirse en datos.

#### Scenario: Reinicio conserva cadena
- **WHEN** un nodo con bloques se detiene y se reinicia con el mismo directorio de datos
- **THEN** recupera exactamente la misma cadena

#### Scenario: Elección sobrevive al reinicio de la API
- **WHEN** se crea una elección, se carga el censo, se reinicia la API y un votante canjea su código
- **THEN** el canje funciona con la misma clave de emisión y la credencial verifica contra la clave publicada en la cadena

#### Scenario: Permisos de claves
- **WHEN** se guarda una clave de emisión
- **THEN** el archivo no es legible por grupo ni otros

### Requirement: Persisted chain integrity at startup
La cadena persistida SHALL validarse completa (hashes, firmas y autoridad) antes de aceptarla. Si es inválida el proceso MUST negarse a arrancar con un error explícito, en lugar de descartarla o aceptarla.

#### Scenario: Cadena corrupta
- **WHEN** el archivo de cadena persistida fue alterado
- **THEN** el proceso no arranca y reporta que la cadena persistida es inválida

### Requirement: Configurable mail delivery
El envío de códigos SHALL usar SMTP configurable por variables de entorno (servidor, puerto, usuario, contraseña, remitente, STARTTLS). Sin servidor SMTP configurado el sistema SHALL usar un buzón local en archivo solo para desarrollo y pruebas, advirtiéndolo al arrancar. Un fallo de envío SMTP MUST NOT exponer el código ni credenciales en respuestas HTTP.

#### Scenario: SMTP configurado
- **WHEN** se configura servidor SMTP y se envía un código
- **THEN** el mensaje se entrega a ese servidor con el remitente configurado

#### Scenario: Sin SMTP
- **WHEN** no hay servidor SMTP configurado
- **THEN** el sistema usa el buzón en archivo y lo advierte en el arranque

### Requirement: Reproducible container deployment
El repositorio SHALL incluir una definición `docker compose` que levante 3 validadores (hasta 5 con un perfil opcional), la API y el frontend, con configuración exclusivamente por variables de entorno desde un archivo `.env` generado por la CLI, volúmenes persistentes por servicio y sin secretos en el repositorio. Los puertos de los validadores MUST NOT publicarse en el host; la API y el frontend se publican solo en la interfaz local por defecto. La definición MUST pasar `docker compose config`.

#### Scenario: Configuración válida
- **WHEN** se ejecuta `docker compose config` con el `.env` generado para 3 validadores
- **THEN** termina sin errores y define los servicios de 3 validadores, API y frontend

#### Scenario: Perfil de 5 validadores
- **WHEN** se genera la configuración para 5 validadores
- **THEN** el `.env` activa el perfil opcional y los 5 comparten el mismo conjunto ordenado de validadores

#### Scenario: Sin secretos versionados
- **WHEN** se revisa el repositorio
- **THEN** no contiene `.env` ni claves; el `.env` está ignorado por git

### Requirement: Pilot documentation
El repositorio SHALL documentar la guía operativa del master (despliegue, ciclo de una elección, recuperación), un checklist de seguridad previo al piloto y una guía de auditoría para un tercero independiente, indicando explícitamente los límites conocidos del sistema (correlación por tiempo/IP, parada con validador en turno caído, token estático, claves en un solo host).

#### Scenario: Documentos presentes
- **WHEN** se revisa `docs/`
- **THEN** existen la guía del master, el checklist de seguridad y la guía de auditoría, y esta última declara que la auditoría humana está pendiente

### Requirement: Automated end-to-end election
El repositorio SHALL incluir una prueba automatizada que ejecute una elección completa sobre una red PoA de al menos 3 nodos con servidores HTTP reales, desde la creación hasta el cierre y conteo, con varios votantes anónimos y un doble voto rechazado. Luego SHALL verificar el conteo de forma independiente (ver el requisito siguiente). Esta prueba no sustituye la auditoría humana por un tercero, que MUST permanecer marcada como pendiente.

#### Scenario: Elección completa
- **WHEN** se ejecuta la prueba end-to-end
- **THEN** el conteo recalculado desde la cadena coincide con el esperado a partir de las papeletas emitidas y con el publicado por la API

### Requirement: Independent tally verification
La verificación independiente SHALL validar la cadena de cada nodo con el conjunto de validadores de confianza, comprobar que todos los nodos coinciden, recalcular el conteo desde la cadena sin usar la API de conteo, compararlo con el publicado y comprobarlo con el verificador del explorador.

#### Scenario: Verificador del explorador
- **WHEN** Node está disponible
- **THEN** el verificador JavaScript del explorador valida la cadena final y obtiene el mismo conteo; si Node no está disponible la prueba lo informa como omitido, no como superado

#### Scenario: Manipulación detectada
- **WHEN** se altera una papeleta en la copia de la cadena de un nodo
- **THEN** la verificación independiente falla e identifica el nodo y el bloque
