# Segam M8 V6 (game stick 4K) - mapeo de botones PS1

Configuracion de pcsx4all / frontend rkgame para Soul Reaver (PS1).

## El problema

L2 y R2 comparten el mismo eje (eje Z): L2 manda +Z y R2 manda -Z. Al
apretarlos juntos los valores se anulan y el emulador registra uno solo.
Es una limitacion del mando, no del juego ni del emulador.

## Formato del .scf (verificado contra los 5 archivos del firmware)

`cubegm/saves/PS/Soul Reaver.scf`, 100 bytes:

```
ff 01                      header
0a 00 00 00                slot 1, jugadores 1-4
0b 00 00 00                slot 2
09 00 00 00                slot 3
08 00 00 00                slot 4
00 00 00 00                slot 5
01 00 00 00                slot 6
```

El bloque de 24 bytes se repite 4 veces identico (4 + 24*4 = 100).

- El relleno de los jugadores sin configurar es `00`, **no** `20`.
- Los valores que aparecen en todo el firmware son solo: `08 09 0a 0b 00 01`.

## Orden de slots: NO confirmado

El orden de los slots varia segun el core. Comparando los archivos:

| Archivo | slot1 | slot2 | slot3 | slot4 | slot5 | slot6 |
|---|---|---|---|---|---|---|
| PS / Soul Reaver | 0a | 0b | 09 | 08 | 00 | 01 |
| ARCADE / default | 0a | 0b | 01 | 00 | 08 | 09 |
| SFC / UMK3 | 0a | 0b | 09 | 08 | 00 | 01 |

En PS el orden es L1, R1, R2, L2, ?, L3. En ARCADE es L1, R1, L3, ?, L2, R2.
Falta confirmar a que boton fisico corresponde cada slot.

## Botones fisicos del mando (de joystick.cpd)

`joystickbk.cpd` es un ZIP ofuscado (ver `cpdtool.py`). Sus entradas revelan
los nombres de botones del firmware:

```
0000_0000:
  SELECT,START,UP,DOWN,LEFT,RIGHT,A,B,TL1,X,Y,TR1,RESET

0810_0001_0100:
  A,B,TL1,X,Y,TR1,TL1,TR1,TL2,TR2,SELECT,START
```

O sea el mando tiene 6 botones: **A, B, TL1, X, Y, TR1**.
TL1/TR1 son los hombros; TL2/TR2 (L2/R2) son los gatillos del eje Z.

## Archivos

- `Soul Reaver - original.scf` — copia exacta del original del firmware.
- `Soul Reaver - opcion1 X=L2 Y=R2.scf` — slot5 pasa a L2, slot6 a R2.
- `Soul Reaver - opcion2 R1=R2 X=R1.scf` — slot2 pasa a R2, slot5 a R1.

Los tres son de 100 bytes. Los parches mueven solo el byte de valor del
jugador 1; los otros tres jugadores quedan como estaban.

## Como usar

1. Backup del original.
2. Copiar el `.scf` elegido a `cubegm/saves/PS/` con el nombre exacto
   `Soul Reaver.scf`.
3. Cerrar y reabrir el juego.

Editar con HxD (Windows) o ghex/bless (Linux). Nunca cambiar el tamano.


## Desensamblado de rkgame (MIPS32, tabla de simbolos presente)

Herramientas: `capstone` (MIPS32 LE). Base de codigo 0x400000, gp de cada
funcion = `0x110000 + 0x3fe0 + addr` para las de InitKeyMapping.

| Direccion | Simbolo | Funcion |
|---|---|---|
| 0x41c260 | InitKeyMapping0fEmuType | elige tabla default segun tipo de core |
| 0x4eb0c4 | (dato) | tabla default PS: 0a 0b 09 08 00 01 x4 jugadores |
| 0x41c784 | SaveKeyMappingConfigFile | escribe el .scf |
| 0x41f008 | GetJoystickConfig | lee joystick.cpd por VID_PID |
| 0x41f2ec | JoystickTest | test interno de ejes/botones |
| 0x4eae80 | (dato) | tabla de etiquetas del menu |

### Tabla de etiquetas (0x4eae80)

Contiene nombres de EJE y de BOTON mezclados:

```
G12 G13 G14 G15 B C UP A Z Y 5 7 8 10 13 15 16 ... 29 P2 P3 P4
```

`Z` e `Y` son nombres de eje SDL, no botones. El menu los muestra tal cual
al capturar, o sea que si distingue y captura correctamente.

### Formato de joystick.cpd

ZIP ofuscado. Nombres de entrada = `VID_PID[_VER]` en hex:

```
0810_0001_0100  -> mando del Segam M8 V6 (VID 0x0810, PID 0x0001)
```

Cada entrada es un CSV de 20 campos:

```
<6 botones fisicos>, <6 botones destino>, <resto: indices>
A,B,TL1,X,Y,TR1,TL1,TR1,TL2,TR2,SELECT,START,0,0,0,0,0,1,0,1
```

Los primeros 6 son botones fisicos; los 6 siguientes, destinos por defecto.
OJO: NO esta confirmado que las 6 filas del menu correspondan a esos 6
botones en ese orden. Esa correspondencia se dedujo, no se verifico.

### Verificacion importante

El `.scf` del firmware es **identico** a la tabla default PS embebida en el
binario (0x4eb0c4). Nadie lo modifico: es el default de fabrica.

## Pendiente

Confirmar el orden real de slots: cambiar UN boton desde el menu del
frontend, guardar, y comparar el archivo con el original.
