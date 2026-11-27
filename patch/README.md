# rkgame: Factory Setting cambia el perfil de joystick

Version parcheada de `rkgame` donde **Settings > Factory Setting > Yes**
intercambia los dos perfiles de botones y **no borra nada**.

```
joystick.cpd    -> joystick.tmp
joystickbk.cpd  -> joystick.cpd
joystick.tmp    -> joystick.cpd
```

Cada confirmacion alterna entre un perfil y el otro. Confirmando dos veces
volves al estado inicial.

## El error de la version anterior

La version previa hookeaba `0x41A804`. Ese offset esta dentro de la funcion
`0x4183A0`, que es el parser de configuracion y textos de la UI (carga
`Config_Setting%d`, `Setting_RecoverInfo1/2`, `Game_JoystickTab%d`, etc).

No tiene nada que ver con el reset. Por eso el parche no hacia nada y el
reset original seguia corriendo: el idioma volvia a ingles y se borraba el
history.

## Donde esta el reset de verdad

Funcion `0x4206A8`. Es la que toca los tres archivos:

```
0x4eac38  setting.raw
0x4ea2d0  %s/setting.xml
0x4ea2f8  config
0x4ea300  language
0x4eab54  %s/recent.lst
0x4ea120  %s/favorites.lst
```

El punto del "Yes" es `0x4210E0`:

```
0x4210E0  addiu $v0, $zero, 1
0x4210E4  bne   $s7, $v0, 0x420DB4     ; s7 != 1 -> cancela
0x4210E8  addiu $v0, $zero, -1          ; delay slot
0x4210EC  lw    $v1, 0xa4($sp)          ; <- arranca el reset
```

Se reemplazan las dos primeras instrucciones por `j 0x512A94`.

## Casos borde (verificados por emulacion)

| Situacion | Que hace |
|---|---|
| Existen los dos | Hace el swap |
| No existe `joystick.cpd` | Copia `joystickbk.cpd` -> `joystick.cpd` |
| No existe `joystickbk.cpd` | No toca nada, vuelve al menu |
| No existe ninguno | No toca nada |
| El usuario cancela | No toca nada, vuelve al menu |

En ningun caso se toca `setting.xml`, `recent.lst` ni `favorites.lst`.

## Instalacion

1. Backup del original:

   ```
   /mnt/sdcard/cubegm/rkgame  ->  rkgame.orig
   ```

2. Copiar el `rkgame` de esta carpeta a `/mnt/sdcard/cubegm/rkgame`.
3. Tener `/mnt/sdcard/cubegm/joystickbk.cpd` (viene en el firmware).
4. Reiniciar.

## Como esta hecho

| Offset | Que |
|---|---|
| `0x4210E0` | hook: `j 0x512A94` (2 instrucciones reemplazadas) |
| `0x512970` | subrutina `copysub` (292 bytes) |
| `0x512A94` | cuerpo principal (508 bytes) |
| `0x512FC8` | strings: rutas y modos |
| PHDR `LOAD1` | `filesz`/`memsz` `0x112970` -> `0x113000` |

`rkgame` no importa `rename` ni `unlink`, pero si `fopen`, `fread`, `fwrite`,
`fclose`, `malloc` y `free`. El swap se hace copiando en streaming.

### Orden de copia

`bk -> tmp`, `cpd -> bk`, `tmp -> cpd`, y al final `cpd -> tmp`. Asi el `.cpd`
activo se escribe ultimo y un corte a mitad no lo deja truncado.

### Trampas de keystone que hubo que esquivar

| Trampa | Sintoma | Solucion |
|---|---|---|
| `jal` a label local | se ensambla como `lw $t9,($gp)` | ensamblar la subrutina primero y usar `jal <direccion>` |
| delay slot con instruccion util | `fclose` con `$a0` viejo | siempre `nop` en el delay slot |
| `$s0` pisado | el menu pierde el puntero al objeto | guardar el `$s0` original en un slot del frame |
| `sprintf` vs `snprintf` | firma distinta, crash | `0x5128C0` es `snprintf(buf, size, fmt, ...)` |

## Regenerar el binario

```
pip install keystone-engine capstone
python3 mk_rkgame_factoryswap.py rkgame_original rkgame
```

Es deterministico. El generador valida solo: que los delay slots tengan `nop`,
que los saltos queden dentro del cave, y que cada `jal` apunte a un stub
conocido.

## Verificacion

Emulado con Unicorn contra un filesystem simulado, con tamanos reales de
322 KB:

- swap completo, byte a byte
- primer uso (sin `joystick.cpd`)
- sin `joystickbk.cpd`
- sin ninguno de los dos
- cancelar
- dos swaps seguidos vuelven al original

## Pendiente

- Probar en el equipo.
