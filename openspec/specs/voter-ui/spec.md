# voter-ui Specification

## Purpose
TBD - created by archiving change web-voting-and-admin. Update Purpose after archive.

## Requirements

### Requirement: Credential redemption in the browser
La interfaz del votante SHALL canjear el correo y el código de un solo uso por una credencial anónima generando en el navegador la clave Ed25519, cegando el valor y desbloqueando la firma recibida; la clave privada y el factor de cegado MUST NOT salir del navegador. La credencial desbloqueada MUST verificarse contra la clave pública de emisión de la elección antes de aceptarse.

#### Scenario: Canje exitoso
- **WHEN** el votante ingresa correo y un código válido para una elección abierta
- **THEN** el navegador envía solo correo, código y valor cegado, y avanza a la papeleta con una credencial verificada

#### Scenario: Rechazo uniforme
- **WHEN** la API responde 400 al canje
- **THEN** la interfaz muestra un único mensaje de código no válido o ya usado, sin distinguir causas, y no avanza

#### Scenario: Normalización del código
- **WHEN** el votante pega un código con espacios y minúsculas
- **THEN** se envía normalizado (sin espacios, en mayúsculas)

#### Scenario: Elección no abierta
- **WHEN** la elección elegida no está abierta
- **THEN** la interfaz informa que la votación no está abierta y no ofrece canjear

### Requirement: Ordered ballot with 3/2/1 points
La papeleta SHALL pedir por categoría exactamente 3 candidatos distintos en orden, mostrando junto a cada posición sus puntos (1.º = 3, 2.º = 2, 3.º = 1). Un candidato ya elegido en otra posición de la misma categoría MUST aparecer deshabilitado con el motivo y MUST NOT moverse en silencio. No existe voto en blanco ni papeleta con menos de 3 picks.

#### Scenario: Sin repetir candidato
- **WHEN** el candidato A ya es el 1.er lugar y el votante abre el selector del 2.º
- **THEN** A aparece deshabilitado con la etiqueta "Ya es tu 1.º lugar" y no puede elegirse

#### Scenario: Papeleta incompleta
- **WHEN** el votante intenta continuar con una ranura vacía
- **THEN** no avanza, se enfoca la primera ranura vacía y se muestra "Falta elegir tu 2.º lugar."

#### Scenario: Puntos visibles
- **WHEN** se muestra una ranura o el resumen
- **THEN** cada posición muestra su ordinal y sus puntos como texto

#### Scenario: Categoría sin candidatos suficientes
- **WHEN** una categoría tiene menos de 3 candidatos
- **THEN** se informa que no se puede votar en ella y se evita el envío

### Requirement: Review and signed submission
La interfaz SHALL mostrar un resumen por categoría con enlace para editar, y al confirmar MUST construir una transacción `CAST_BALLOT` por categoría, firmada en el navegador con la clave de la credencial y con serialización canónica compatible con el backend, y enviarla a `POST /ballots`. El envío MUST ser idempotente ante reintentos: no duplica papeletas y, si la API rechaza una papeleta cuyo comprobante ya consta en la cadena, se trata como registrada.

#### Scenario: Firma compatible con el backend
- **WHEN** el navegador firma una papeleta con una clave y marca de tiempo dados
- **THEN** la transacción resultante (tx_id y firma) es idéntica a la que produce el backend para los mismos datos

#### Scenario: Envío con red lenta
- **WHEN** el votante confirma
- **THEN** el botón queda deshabilitado mientras envía y no se puede enviar dos veces

#### Scenario: Error recuperable
- **WHEN** el envío falla por red
- **THEN** la selección se conserva y se ofrece "Reintentar" que reenvía la misma transacción firmada

#### Scenario: Respuesta perdida
- **WHEN** un reintento recibe rechazo pero `/chain/receipts/{tx_id}` del tx_id calculado localmente responde 200
- **THEN** la papeleta se considera registrada y se muestra su comprobante

### Requirement: Verifiable receipt
Tras el envío la interfaz SHALL mostrar el `tx_id` de cada papeleta como comprobante, con copiar, descarga como texto y enlace al explorador público. MUST NOT mostrar ni almacenar de forma persistente los candidatos elegidos en el comprobante, y MUST NOT ofrecer votar de nuevo.

#### Scenario: Comprobante
- **WHEN** todas las papeletas quedan registradas
- **THEN** se muestra "Tu voto quedó registrado", un identificador por categoría y el enlace a `/explorer`, sin los candidatos elegidos

#### Scenario: Limpieza
- **WHEN** se muestra el comprobante
- **THEN** la credencial y el borrador se eliminan del almacenamiento del navegador

### Requirement: Accessible mobile-first voter flow
El flujo del votante SHALL ser usable en 360 px sin scroll horizontal, operable con teclado, con un `h1` por pantalla, etiquetas reales, errores con `role="alert"` y progreso con `aria-live`, en español.

#### Scenario: Error accesible
- **WHEN** falla la validación de un campo
- **THEN** el mensaje se asocia al campo con `aria-describedby` y se anuncia con `role="alert"`
