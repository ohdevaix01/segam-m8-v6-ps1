# rkgame con swap de joystick en "Factory Setting"

Version parcheada de `rkgame` que convierte la opcion **Settings > Factory Setting**
en un intercambio de perfiles de botones, sin tocar nada mas.

## Que hace

Cuando entras a `Settings > Factory Setting`, elegi **Yes** y el programa
intercambia los dos archivos de mapeo:

```
joystick.cpd    ->  joystick.tmp
joystickbk.cpd  ->  joystick.cpd
joystick.tmp    ->  joystickbk.cpd
```

Resultado: los dos archivos quedan invertidos. Cada vez que confirmas, cambia
el perfil de botones.

Si `joystick.cpd` no existe todavia (primer arranque), copia `joystickbk.cpd`
como `joystick.cpd`. Eso sirve de "restaurar perfil".

El reset de settings de fabrica **ya no se ejecuta**. Esa opcion pasa a ser
"cambiar perfil de botones".

## Instalacion

1. Backup del original (por si acaso):

   ```
   /mnt/sdcard/cubegm/rkgame  ->  rkgame.orig
   ```

2. Copiar el `rkgame` de esta carpeta a `/mnt/sdcard/cubegm/rkgame`.
3. Asegurarse de que exista `/mnt/sdcard/cubegm/joystickbk.cpd`.
4. Arrancar el equipo.

Si algo sale mal, se restaura `rkgame.orig` desde la PC.

## Uso

- Entrar a `Settings > Factory Setting > Yes` = cambiar perfil.
- El cambio se toma al instante: `GetJoystickConfig` abre y parsea
  `joystick.cpd` en cada llamada, no lo cachea.

## Como esta hecho

Tres modificaciones, nada mas:

| Offset | Que | Detalle |
|---|---|---|
| `0x1A804` | hook | `j 0x512970` (4 instrucciones originales reemplazadas) |
| `0x112970` | codigo nuevo | rutina de copia en streaming, 1032 bytes |
| `0x112F98` | strings | rutas y modos de apertura |
| PHDR `LOAD1` | `filesz`/`memsz` | `0x112970` -> `0x113000` para mapear la cola |

El codigo nuevo vive en los 1680 bytes de ceros que hay entre el fin de `.plt`
y el siguiente segmento. Se verifico que esa zona esta toda en cero en el
original y que no hay solape: `LOAD1` termina en `0x513000` y `LOAD2` arranca
en `0x523000`.

### Por que el hook es seguro

`0x41A804` es el destino de un unico `beq` (`0x41958C`), que es la rama "Yes"
del dialogo de Factory Setting. Se verifico que ninguna otra rama del binario
cae en ese bloque ni salta al medio de el.

El bloque original copiaba 45 bytes de settings por defecto de `.rodata` a
`.data` y despues hacia `b 0x419960`. El parche saltea esa copia y retoma
exactamente en `0x419960`, asi que el resto de la pantalla sigue funcionando
igual.

### Por que no usa rename

`rkgame` no importa `rename` ni `unlink` (se verificaron los 557 simbolos
dinamicos). Lo unico parecido es `shm_unlink`, que es memoria compartida.

Pero si tiene `fopen`, `fread`, `fwrite`, `fclose`, `malloc` y `free`. Copiar
en streaming hace el mismo efecto que renombrar, sin agregar simbolos nuevos
ni tocar la tabla de imports.

Se usan los stubs de `.plt` (no los de `.MIPS.stubs`) porque los primeros
calculan la GOT con `lui`/`lw` sobre `$t7` y no dependen de `$gp`.

| Funcion | Stub |
|---|---|
| `fopen` | `0x5124A0` |
| `fread` | `0x512420` |
| `fwrite` | `0x512530` |
| `fclose` | `0x512630` |
| `malloc` | `0x512550` |
| `free` | `0x512760` |

## Regenerar el binario

```
pip install keystone-engine capstone
python3 mk_rkgame_factoryswap.py rkgame_original rkgame
```

El script escribe el hook, el codigo, las strings y ajusta el PHDR. Es
deterministico: con el mismo `rkgame` original da el mismo resultado.

## Verificacion

El diff contra el original toca solo tres zonas: el hook (`0x1A804`), la cola
del segmento (`0x112970..0x113000`) y los bytes `filesz`/`memsz` del PHDR.
`.plt`, `.got`, `.dynamic` y el resto de `.text` quedan intactos.

```
$ python3 -c "..."
diff fuera de hook/cueva/phdr: NINGUNO - limpio
```

## Pendiente de probar en el equipo

- Que el stick arranque con el binario parcheado.
- Que el swap se refleje sin reiniciar (muy probable, `GetJoystickConfig`
  abre el archivo en cada llamada, pero no se pudo ejecutar en el hardware).
- Que los dos perfiles se distingan bien en la practica.

## Aviso

Esto modifica el binario principal del equipo. Si el parche fallara, el stick
no arranca. Por eso el paso 1 es el backup.
