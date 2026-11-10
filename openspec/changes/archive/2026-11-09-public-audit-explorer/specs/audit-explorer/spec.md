## ADDED Requirements

### Requirement: Public static explorer
La API SHALL servir sin autenticación un explorador web estático (HTML y JavaScript sin paso de build) bajo la ruta `/explorer`. El explorador MUST obtener sus datos solo de las rutas públicas de lectura y MUST NOT requerir cuenta, token ni datos personales.

#### Scenario: Acceso sin credenciales
- **WHEN** se solicita `/explorer/` sin cabecera de autorización
- **THEN** responde 200 con la página del explorador

#### Scenario: Rutas administrativas no expuestas por el explorador
- **WHEN** se revisa el código estático del explorador
- **THEN** no contiene referencias a `/admin`, correos ni códigos

### Requirement: Block and transaction browsing
El explorador SHALL listar los bloques de la cadena y mostrar, para cada bloque, su índice, hash, hash previo, raíz de Merkle, marca de tiempo y sus transacciones (tipo y payload).

#### Scenario: Lista de bloques
- **WHEN** el usuario abre el explorador con una cadena de N bloques
- **THEN** ve N bloques en orden de índice, incluido el génesis

#### Scenario: Detalle de bloque
- **WHEN** el usuario selecciona un bloque
- **THEN** ve sus campos y las transacciones que contiene

### Requirement: Browser-side chain verification
El explorador SHALL recalcular en el navegador, sin confiar en el campo `valid` del servidor, el hash de cada bloque, el enlace `prev_hash`, la raíz de Merkle y el génesis fijo, e indicar el primer bloque inconsistente. Las firmas quedan fuera.

#### Scenario: Cadena íntegra
- **WHEN** se verifica una cadena sin alteraciones
- **THEN** el resultado es válido

#### Scenario: Transacción alterada
- **WHEN** se modifica el payload de una transacción en un bloque recibido
- **THEN** la verificación falla indicando ese bloque (raíz de Merkle o hash no coinciden)

#### Scenario: Bloque reordenado o enlace roto
- **WHEN** el `prev_hash` de un bloque no coincide con el hash del anterior
- **THEN** la verificación falla indicando ese bloque

### Requirement: Backend hash parity
La lógica de hash del navegador (JSON canónico, SHA-256, Merkle con separación de dominio y nodo impar promovido) MUST producir exactamente los mismos resultados que el backend para los mismos datos.

#### Scenario: Paridad con el backend
- **WHEN** el código de verificación del navegador procesa los vectores fijos generados por el backend (JSON canónico con Unicode, hash de bloque, raíces de Merkle con 0, 1, 2, 3 y 5 hojas)
- **THEN** obtiene exactamente los valores esperados

### Requirement: Published ranking
El explorador SHALL mostrar el ranking por categoría solo cuando la elección está cerrada, tomándolo de la ruta pública del conteo, y MUST NOT calcular ni mostrar puntos mientras esté abierta o en borrador.

#### Scenario: Elección abierta
- **WHEN** el usuario consulta una elección abierta
- **THEN** el explorador indica que el ranking se publica al cierre y no muestra puntos

#### Scenario: Elección cerrada con conteo coincidente
- **WHEN** el usuario consulta una elección cerrada
- **THEN** ve el ranking por categoría con puntos y posición, y la indicación de que el conteo recalculado coincide con el publicado

### Requirement: Browser-side tally recomputation
Para una elección cerrada el explorador SHALL recalcular el conteo desde las papeletas de la cadena (puntos 3/2/1, una por credencial y categoría, mismo desempate) y compararlo con el publicado. El recálculo no re-verifica firmas.

#### Scenario: Conteo publicado inconsistente
- **WHEN** el conteo publicado difiere del recalculado desde la cadena
- **THEN** el explorador indica la discrepancia

#### Scenario: Paridad del conteo
- **WHEN** el recálculo del navegador procesa la cadena de vectores fijos con empate
- **THEN** puntos, posiciones y marca de empate coinciden con el conteo del backend
