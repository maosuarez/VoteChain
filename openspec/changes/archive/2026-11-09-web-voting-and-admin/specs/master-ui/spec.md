## ADDED Requirements

### Requirement: Master authentication with static token
El panel SHALL pedir el token estático de `master-admin-api`, validarlo sin efectos secundarios contra la API y enviarlo como `Authorization: Bearer` en las rutas administrativas. El token MUST guardarse solo en `sessionStorage`, nunca en la URL, y MUST descartarse al salir o por inactividad.

#### Scenario: Token válido
- **WHEN** el master ingresa un token aceptado por la API
- **THEN** accede a la lista de elecciones

#### Scenario: Token inválido
- **WHEN** la API responde 401 a la validación
- **THEN** se muestra un error y no se accede al panel

#### Scenario: Inactividad
- **WHEN** pasa el tiempo de inactividad configurado
- **THEN** se avisa 60 s antes con opción de extender y, si no se extiende, se cierra la sesión

### Requirement: Election management
El panel SHALL listar las elecciones (descubiertas desde la cadena pública) con su estado, y permitir crear una elección con identificador y ventana de fechas, añadir categorías y candidatos (manual y desde lista CSV con vista previa y errores por fila) mientras esté en borrador, sin duplicar candidatos en una categoría.

#### Scenario: Crear elección
- **WHEN** el master completa identificador y fechas válidas
- **THEN** se envía `POST /admin/elections` y la elección aparece en estado Borrador

#### Scenario: Candidato duplicado
- **WHEN** el master añade un candidato con el mismo identificador en la misma categoría
- **THEN** no se envía y se muestra el error en el campo

#### Scenario: Vista previa CSV
- **WHEN** el master carga una lista con filas vacías o repetidas
- **THEN** la vista previa las marca con su error y solo se aplican las filas válidas

#### Scenario: Edición bloqueada
- **WHEN** la elección no está en borrador
- **THEN** no se ofrecen acciones para añadir categorías ni candidatos

### Requirement: Census and codes
El panel SHALL permitir cargar el censo desde una lista de correos con vista previa (válidos, duplicados, formato inválido) y reenviar el código a un correo concreto con confirmación. MUST NOT mostrar ni requerir información de por quién votó alguien.

#### Scenario: Carga de censo
- **WHEN** el master aplica una lista con correos válidos
- **THEN** se envía `POST /admin/elections/{id}/voters` solo con los válidos únicos y se informa cuántos se enviaron

#### Scenario: Reenvío de código
- **WHEN** el master confirma el reenvío a un correo
- **THEN** se envía `POST /admin/elections/{id}/codes` y se informa el resultado `sent`

### Requirement: Open and close with safeguards
El panel SHALL habilitar "Abrir votación" solo cuando haya al menos una categoría y todas tengan 3 o más candidatos, con modal de confirmación; y "Cerrar votación" MUST exigir teclear el nombre de la elección. Mientras la elección no esté cerrada MUST NOT mostrar ranking.

#### Scenario: Prerrequisitos incompletos
- **WHEN** una categoría tiene menos de 3 candidatos
- **THEN** "Abrir votación" está deshabilitado y la lista muestra el prerrequisito pendiente

#### Scenario: Cierre con confirmación escrita
- **WHEN** el master escribe un texto distinto al nombre de la elección
- **THEN** el botón de confirmar cierre permanece deshabilitado

#### Scenario: Estado sin ranking
- **WHEN** la elección está abierta
- **THEN** el estado muestra votos emitidos (papeletas en la cadena) y ningún ranking

#### Scenario: Cierre completado
- **WHEN** el cierre tiene éxito
- **THEN** se informa que es definitivo y se enlaza el explorador público

### Requirement: API error handling
Los errores de la API MUST mostrarse en un banner con `role="alert"` y causa legible, sin perder lo digitado, y un 401 MUST cerrar la sesión.

#### Scenario: Conflicto de dominio
- **WHEN** la API responde 409 con un motivo
- **THEN** el motivo se muestra en el banner

#### Scenario: Sesión rechazada
- **WHEN** una llamada administrativa responde 401
- **THEN** se cierra la sesión y se vuelve al login
