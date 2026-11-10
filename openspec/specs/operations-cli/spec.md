# operations-cli Specification

## Purpose
TBD - created by archiving change pilot-deployment. Update Purpose after archive.

## Requirements

### Requirement: Operations CLI with rich output
El sistema SHALL ofrecer la orden `votechain` con subcomandos de operación cuya salida legible use tablas y estilos de la biblioteca Rich, y que terminen con código de salida distinto de cero ante cualquier fallo o inconsistencia detectada. La CLI MUST NOT imprimir el token del master, claves privadas ni códigos de votación salvo en la generación inicial de secretos (que los escribe a un archivo y no los muestra).

#### Scenario: Ayuda
- **WHEN** se ejecuta `votechain --help`
- **THEN** lista los subcomandos de inicialización, estado, diagnóstico, administración de elección y auditoría

#### Scenario: Sin secretos en salida
- **WHEN** se ejecuta cualquier subcomando con token configurado
- **THEN** la salida no contiene el token

### Requirement: Secrets and configuration bootstrap
`votechain init` SHALL generar el token del master, la clave del master y las claves de los validadores (3 a 5, con el perfil de compose correspondiente) y escribirlos en un archivo `.env` con permisos solo del propietario, junto con el conjunto ordenado de claves públicas de validadores y las direcciones de pares. MUST negarse a sobrescribir un `.env` existente salvo con `--force`. Un número de validadores fuera de 3 a 5 MUST rechazarse.

#### Scenario: Generación
- **WHEN** se ejecuta `votechain init --validators 3`
- **THEN** el `.env` contiene token, clave de master, 3 claves de validador y la lista ordenada de públicas, con permisos 600

#### Scenario: No sobrescribe
- **WHEN** ya existe `.env` y se ejecuta `init` sin `--force`
- **THEN** falla sin modificar el archivo

#### Scenario: Número inválido
- **WHEN** se ejecuta `init --validators 2` o `--validators 6`
- **THEN** falla con error y no escribe archivo

### Requirement: Network status and diagnosis
`votechain status` SHALL mostrar por cada nodo configurado su altura, hash de la punta, transacciones pendientes y si responde. `votechain check` SHALL diagnosticar la red: nodos caídos, alturas distintas, puntas distintas con la misma altura (fork) y cadenas inválidas, y terminar con código 0 solo si todos los nodos responden con la misma cadena válida.

#### Scenario: Red sana
- **WHEN** todos los nodos responden con la misma cadena válida
- **THEN** `check` informa OK y termina con código 0

#### Scenario: Nodo caído
- **WHEN** un nodo no responde
- **THEN** `status` lo marca como caído y `check` termina con código distinto de cero indicando cuál

#### Scenario: Fork
- **WHEN** dos nodos tienen la misma altura con puntas distintas
- **THEN** `check` reporta el fork y termina con código distinto de cero

### Requirement: Election operation commands
La CLI SHALL ofrecer subcomandos que invoquen la API del master con el token configurado: crear elección, agregar categoría y candidato, cargar censo desde un CSV de correos, reenviar código, abrir, cerrar y ver el conteo. Un rechazo de la API (401, 409, 503) MUST mostrarse como error legible con código de salida distinto de cero. El CSV con correos inválidos MUST rechazarse completo antes de enviarse.

#### Scenario: Ciclo desde la CLI
- **WHEN** se ejecutan crear elección, categoría, candidatos, cargar censo, abrir y cerrar contra una API válida
- **THEN** cada comando termina con código 0 y la elección queda cerrada

#### Scenario: Token incorrecto
- **WHEN** se ejecuta un comando de administración con token inválido
- **THEN** muestra error de autorización y termina con código distinto de cero

#### Scenario: CSV inválido
- **WHEN** el CSV contiene una fila que no es un correo válido
- **THEN** no se envía nada a la API y el comando falla indicando la fila

### Requirement: Independent audit command
`votechain audit` SHALL descargar la cadena de cada nodo indicado, validarla de forma independiente con el conjunto de validadores de confianza proporcionado (no el que informe la red), comprobar que los nodos coinciden, recalcular el conteo de una elección desde la cadena y, si la elección está cerrada, compararlo con el publicado por la API. MUST terminar con código distinto de cero ante cualquier discrepancia e indicar nodo y bloque de la primera falla.

#### Scenario: Auditoría correcta
- **WHEN** las cadenas son válidas, idénticas y el conteo publicado coincide
- **THEN** informa el conteo recalculado y termina con código 0

#### Scenario: Cadena alterada
- **WHEN** la cadena de un nodo tiene un bloque modificado
- **THEN** termina con código distinto de cero indicando nodo e índice de bloque

#### Scenario: Validadores de confianza distintos
- **WHEN** se audita con un conjunto de validadores que no coincide con los firmantes de la cadena
- **THEN** la auditoría falla indicando firmante no autorizado
