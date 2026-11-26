# Segam M8 V6 (A3101/HC16xx) — notas de ingenieria inversa

## Binario `cubegm/rkgame`
- ELF MIPS32 LE, base `0x400000`, gp = `0x110000 + 0x3fe0 + addr`.
- Segmentos cargables: `(0x400000, off 0x0, 0x112970)`, `(0x523000, off 0x113000, 0x5bc0)`,
  `(0x505b50, off 0x105b50, 0x247c)`.
- Desensamblar con `capstone` + `skipdata=True` (hay data embebida que corta el flujo).

## Funciones clave
| addr | nombre | nota |
|---|---|---|
| `0x41f008` | `GetJoystickConfig` | carga config por VID/PID |
| `0x41f2ec` | variante de carga | usada en 0x405e1c, 0x420b54, 0x428aa8 |
| `0x4088a8` | `GetInputInfo` | abre el js y lee eventos |
| `0x4089b4` | bucle de eventos por joystick | compara `code` contra 8 slots |
| `0x40a274` | `InitJoystick` | |
| `0x41c260` | `InitKeyMapping0fEmuType` | tabla default PS @ `0x4eb0c4` |
| `0x41c784` | `SaveKeyMappingConfigFile` | escribe `.scf` |

## Formato de nombre de config de joystick (VERIFICADO en codigo)
```
"%04x_%04x_%04x"   ->  <vid>_<pid>_<version>
"%04x_%04x"        ->  fallback si no existe la de 3 campos
```
Entradas actuales en `joystick.cpd`: `0810_0001_0100`, `0810_0001_0110`, `0810_0001_0111`,
`20bc_5500`, `2563_0555`, `0000_0000` (fallback), `ui.cfg`, `joystick.raw`.

## Log util para identificar el mando (VERIFICADO)
- `"%s %04x %04x %x js%d Opened!"` -> vid, pid, y numero de js. Se escribe en `cubegm/menu.log`.
- `"JS%d value %6hd, type: %2u, axis/button: %u"` -> `type 1 = boton`, `type 2 = eje`.
- Strings de menu: `USB Joystick Test`, `/JoystickTest`.

## Conversion eje -> boton (VERIFICADO en `0x408cb0`)
```
valor < -22767  ->  ori 0x1000
valor > +22767  ->  ori 0x4000
zona muerta     ->  ninguno
```
Un eje tiene **un solo valor** por vez: los dos bits son mutuamente excluyentes.
Esto explica por que al apretar L2+R2 (si comparten eje) gana R2.

## Formato `.scf` (VERIFICADO por observacion del usuario en pantalla)
- 100 bytes: 4 bytes de header (`ff010000`) + 4 bloques de 6 words LE de 4 bytes.
- Cada bloque = un jugador. Las 6 posiciones son las **filas del menu**, no los botones PS1:
  filas visibles = `L1, R1, X, A, B, Y`.
- El valor guardado es **que entrada fisica alimenta esa fila** (codigos `0x0a,0x0b,0x09,0x08,0x00,0x01`).
- **No hay slot para L2 ni R2** -> no se pueden remapear por `.scf`.

## Errores cometidos (no repetir)
1. Asumir que las 6 words del `.scf` eran `L1,R1,R2,L2,SELECT,L3`. Falso: son los valores de pantalla.
2. Asumir `6 entradas + 6 destinos` en `joystick.cpd`. El conteo de campos no es fijo
   (12+8, 10+10, 13+7) -> esa particion era inventada, no leida del codigo.
3. El swap `Soul Reaver - swap L1R1 por L2R2.scf` esta armado sobre la tabla equivocada. No usar.

## Estado
- Pendiente: confirmar con el usuario si L2 y R2 dan el **mismo indice de eje** (type 2) en el test.
  Si el indice es distinto, toda la teoria del eje compartido se cae.
