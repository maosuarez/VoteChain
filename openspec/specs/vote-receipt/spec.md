# vote-receipt Specification

## Purpose
TBD - created by archiving change public-audit-explorer. Update Purpose after archive.

## Requirements

### Requirement: Receipt proof endpoint
La API SHALL exponer sin autenticación `GET /chain/receipts/{tx_id}`, que para una transacción incluida en la cadena devuelve el índice y hash del bloque, la raíz de Merkle del bloque y la prueba de inclusión de Merkle (lista ordenada de hashes hermanos con su lado). La respuesta MUST NOT incluir remitente, credencial, firma, picks ni datos personales. Para un `tx_id` no incluido responde 404.

#### Scenario: Papeleta incluida
- **WHEN** se consulta el `tx_id` devuelto al emitir una papeleta
- **THEN** responde 200 con índice y hash de bloque, raíz de Merkle y prueba de inclusión

#### Scenario: Transacción desconocida
- **WHEN** se consulta un `tx_id` que no está en la cadena
- **THEN** responde 404

#### Scenario: Respuesta sin datos vinculantes
- **WHEN** se consulta un comprobante válido
- **THEN** la respuesta contiene solo los campos de bloque y prueba, sin remitente, firma ni picks

### Requirement: In-browser receipt verification
El explorador SHALL permitir al votante introducir el `tx_id` de su papeleta y comprobar en el navegador que está incluida: obtener el bloque, recalcular su hash, verificar que la prueba de Merkle lleva de la transacción (hallada en el bloque por su `tx_id`) a la raíz del bloque, y mostrar el resultado. La verificación de la prueba MUST coincidir con la construcción del backend. El flujo MUST NOT solicitar ni enviar correo, código, credencial ni clave del votante.

#### Scenario: Comprobante válido
- **WHEN** el votante introduce el `tx_id` de una papeleta incluida
- **THEN** el explorador muestra que está incluida y en qué bloque

#### Scenario: Prueba manipulada
- **WHEN** la prueba de Merkle recibida es alterada
- **THEN** la verificación indica que no se pudo comprobar la inclusión

#### Scenario: Comprobante inexistente
- **WHEN** el votante introduce un `tx_id` que no está en la cadena
- **THEN** el explorador indica que no se encontró

#### Scenario: Paridad de la prueba
- **WHEN** el verificador del navegador procesa las pruebas de Merkle fijas generadas por el backend (árboles de 1, 2, 3 y 5 hojas, cada hoja)
- **THEN** todas verifican contra la raíz esperada y una prueba alterada falla

#### Scenario: Sin vínculo con identidad
- **WHEN** se revisa el flujo de comprobante (ruta y código del navegador)
- **THEN** el único dato de entrada es el `tx_id` y ningún dato de identidad interviene
