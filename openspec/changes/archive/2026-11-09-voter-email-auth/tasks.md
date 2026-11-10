## 1. Censo

- [x] 1.1 Crear `src/votechain/auth/` con almacenamiento SQLite y censo (`load_roll`, `is_eligible`, indicador de credencial); verificar con `tests/test_voter_roll.py` (escenarios de voter-roll) en verde.

## 2. Códigos por correo

- [x] 2.1 Agregar `Mailer` (Protocol) y `FakeMailer`, y el servicio de emisión/canje con hash, expiración, un solo uso, límite de intentos y de reenvíos, y auditoría; verificar con `tests/test_email_auth.py` (escenarios de email-code-auth) en verde.

## 3. Cierre

- [x] 3.1 Correr la suite completa y `openspec validate voter-email-auth --strict`; verificar ambos sin errores.
