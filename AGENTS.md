# Segam M8 V6 (A3101/HC16xx) — notas de ingenieria inversa

Contexto tecnico del repo. El resultado final (swap de gatillos) esta en `README.md`.

## Estado del problema

**RESUELTO y probado en hardware.** El swap `TL1<->TL2` y `TR1<->TR2` en
`joystick.cpd` hace que L2 y R2 simultaneos funcionen.

Hallazgo central: el firmware resuelve `TL2`/`TR2` contra el eje compartido (un
solo valor por vez), pero trata `TL1`/`TR1` como botones independientes. El
conflicto era del mapeo de nombres, no del eje fisico ni del emulador.

## Binario `cubegm/rkgame`

- ELF MIPS32 LE, base `0x400000`, gp = `0x110000 + 0x3fe0 + addr`.
- Segmentos cargables: `(0x400000, off 0x0, 0x112970)`, `(0x523000, off 0x113000, 0x5bc0)`,
  `(0x505b50, off 0x105b50, 0x247c)`.
- Desensamblar con `capstone` + `skipdata=True` (hay data embebida que corta el flujo).
- Strings: la mayoria se referencia como `gp + imm` con base `0xF0000`, no con
  `lui/addiu`. Buscar por offset de 16 bits es mucho mas productivo.

## Funciones clave

| addr | nombre | nota |
|---|---|---|
| `0x405bb8` | `main` | lee config, init, despues despacha |
| `0x405dd8` | dispatch por nombre de ejecutable | ver abajo |
| `0x406d14` | pantalla `USB Joystick Test` | imprime eventos del js |
| `0x41f008` | `GetJoystickConfig` | carga config por VID/PID |
| `0x41f2ec` | variante de carga | usada en 0x405e1c, 0x420b54, 0x428aa8 |
| `0x4088a8` | `GetInputInfo` | abre el js y lee eventos |
| `0x4089b4` | bucle de eventos por joystick | compara `code` contra 8 slots |
| `0x40a274` | `InitJoystick` | |
| `0x41c260` | `InitKeyMapping0fEmuType` | tabla default PS @ `0x4eb0c4` |
| `0x41c784` | `SaveKeyMappingConfigFile` | escribe `.scf` |

## Formato de nombre de config de joystick (VERIFICADO)

```
"%04x_%04x_%04x"   ->  <vid>_<pid>_<version>
"%04x_%04x"        ->  fallback si no existe la de 3 campos
```

Entradas en `joystick.cpd`: `0810_0001_0100`, `0810_0001_0110`, `0810_0001_0111`,
`20bc_5500`, `2563_0555`, `0000_0000` (fallback), `ui.cfg`, `joystick.raw`.

Cada entrada es un CSV. El conteo de campos **no es fijo** entre dispositivos
(20 en casi todos), asi que no conviene asumir una particion fija tipo
"6 fisicos + 6 destinos". Lo que si es estable son los nombres de boton.

## Conversion eje -> boton (VERIFICADO en `0x408cb0`)

```
valor < -22767  ->  ori 0x1000
valor > +22767  ->  ori 0x4000
zona muerta     ->  ninguno
```

Un eje tiene **un solo valor** por vez: los dos bits son mutuamente excluyentes.
Esto describe el eje compartido. La solucion no fue pelear con esto, sino evitar
que los gatillos llegaran a este camino: renombrados a `TL1`/`TR1` el firmware
los trata como botones y no pasan por la conversion de eje.

## Pantalla de test: se dispara por el nombre del ejecutable

No hay tecla ni opcion de menu. En `0x405dd8` el binario:

1. lee su propio path de `/proc/self/exe`
2. hace `strstr` buscando `/USBJoystickTest`
3. si no, busca `/JoystickTest`
4. si tampoco, arranca normal

```
cp rkgame USBJoystickTest && ./USBJoystickTest
```

Imprime `JS%d value %6hd, type: %2u, axis/button: %u`.
`type 1 = boton`, `type 2 = eje` (verificado: compara el byte de tipo contra 2 y 1).

Requiere consola o telnet en el stick, que el dispositivo de stock no expone.
Por eso el diagnostico se hizo por comportamiento observable, no con esta pantalla.

## `menu.log` NO es texto

444 bytes de struct binario (ceros, `0x35`, `0x37f`, `-1`). No contiene lineas de
texto ni el log de `Opened!`. No sirve para identificar el mando.

## Formato `.scf`

- 100 bytes: 4 de header (`ff010000`) + 4 bloques de 6 words LE de 4 bytes.
- Cada bloque = un jugador. Las 6 posiciones son las **filas del menu**
  (`L1, R1, X, A, B, Y`), no los botones PS1.
- El valor guardado es que entrada fisica alimenta esa fila
  (`0x0a,0x0b,0x09,0x08,0x00,0x01`).
- **No hay slot para L2 ni R2** -> el `.scf` no puede resolver este problema.
  Se probaron 4 variantes y ninguna funciono; por eso el repo no las conserva.

## Errores cometidos (no repetir)

1. Asumir que las 6 words del `.scf` eran `L1,R1,R2,L2,SELECT,L3`. Son los valores de pantalla.
2. Asumir `6 entradas + 6 destinos` en `joystick.cpd`. Esa particion era inventada,
   no leida del codigo; el conteo de campos ni siquiera es fijo.
3. Afirmar que era una limitacion fisica del hardware. Era del mapeo de nombres.
   El usuario insistio con el `.cpd` y tenia razon.
4. Buscar strings del binario con `lui/addiu`. La mayoria son `gp + imm` con base `0xF0000`.

## Archivo generado

`joystick - TL1-TL2 y TR1-TR2 intercambiados.cpd` (339011 bytes).
Swap aplicado en 6 miembros: `0000_0000`, `0810_0001_0100`, `0810_0001_0110`,
`0810_0001_0111`, `20bc_5500`, `2563_0555`. Sin tocar `joystick.raw` ni `ui.cfg`.

Metodo: sustitucion con marcadores intermedios para evitar doble reemplazo
(`TL1->TL2->TL1`). Round-trip verificado: extraer el `.cpd` generado reproduce
los 8 miembros byte a byte. Numero de campos por linea sin cambios.
