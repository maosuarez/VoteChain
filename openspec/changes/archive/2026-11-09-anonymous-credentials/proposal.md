## Why

Verificable no debe significar vinculable: el sistema debe impedir el doble voto sin saber por quién votó cada persona, ni siquiera el master.

## What Changes

- Firma ciega (RSA) para emitir una credencial de voto por votante tras canjear el código del correo.
- `CAST_BALLOT` pasa a usar la credencial anónima en lugar de la clave pseudónima.
- Verificación en cadena de que cada credencial se usa una sola vez por categoría.
- Demo "rompe-lo": el master intenta vincular credencial con votante y no puede.

## Capabilities

### New Capabilities
- `blind-credentials`: emisión por firma ciega y verificación de credenciales.

### Modified Capabilities
- `ballot-casting`: **BREAKING** la identidad del votante pasa de clave pseudónima a credencial anónima.
- `email-code-auth`: el canje del código entrega la credencial ciega firmada.

## Impact

- Código: `crypto/blind.py`, ajustes en `voting/` y `auth/`.
- Depende de: `voter-email-auth`.
- Límite conocido: correlación por tiempo/IP; se mitiga en piloto y se documenta.
