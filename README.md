# Segam M8 V6 (game stick 4K) — L2 y R2 simultaneos en PS1

Solucion al problema de los gatillos L2/R2 en el emulador de PS1 (pcsx4all)
del frontend `rkgame`, corriendo sobre un game stick Segam M8 V6.0
(chip A3101 / HC16xx, MIPS).

## El problema

El mando comparte un solo eje para L2 y R2: al apretar los dos juntos, el
emulador registraba uno solo. En juegos de PS1 eso rompe combinaciones que
necesitan los dos gatillos a la vez.

## La solucion (probada en hardware)

Reemplazar `cubegm/joystick.cpd` por el archivo de este repo:

```
joystick - TL1-TL2 y TR1-TR2 intercambiados.cpd
```

Renombrarlo a `joystick.cpd` y copiarlo a la carpeta `cubegm` del stick.
Guardar el original como `joystick.cpd.bak`.

Con eso, apretando L2 y R2 juntos **responden los dos**.

## Por que funciona

El firmware no interpreta igual todos los nombres de boton:

| Nombre | Como lo lee el firmware |
|---|---|
| `TL2` / `TR2` | contra el eje compartido: un solo valor por vez, gana uno |
| `TL1` / `TR1` | como botones independientes: cada uno tiene su propio estado |

El conflicto no estaba en el hardware ni en el eje fisico del mando: estaba en
como el firmware resolvia cada nombre. Al renombrar los gatillos a `TL1`/`TR1`,
dejan de competir por el mismo valor y pasan a ser dos botones separados.

Por eso ningun ajuste del emulador ni del `.scf` lo resolvia: el problema estaba
una capa mas abajo, en el mapeo de entrada del frontend.

### Efecto colateral

Los hombros fisicos (L1/R1) pasan a reportarse como `TL2`/`TR2`. Si se necesita
el mapeo original de hombros, restaurar el `.bak`.

## Que se modifico

Se intercambio `TL1` <-> `TL2` y `TR1` <-> `TR2` en los 6 miembros de
`joystick.cpd` que contienen nombres de boton:

| Miembro | Antes | Despues |
|---|---|---|
| `0000_0000` | `...A,B,TL1,X,Y,TR1,RESET...` | `...A,B,TL2,X,Y,TR2,RESET...` |
| `0810_0001_0100` | `A,B,TL1,X,Y,TR1,TL1,TR1,TL2,TR2,SELECT,START,...` | `A,B,TL2,X,Y,TR2,TL2,TR2,TL1,TR1,SELECT,START,...` |
| `0810_0001_0110` | `Y,B,A,X,TL1,TR1,TL2,TR2,SELECT,START,...` | `Y,B,A,X,TL2,TR2,TL1,TR1,SELECT,START,...` |
| `0810_0001_0111` | idem `0110` | idem `0110` |
| `2563_0555` | idem `0110` | idem `0110` |
| `20bc_5500` | `A,B,0,X,Y,0,TL1,TR1,TL2,TR2,SELECT,START,RESET,...` | `A,B,0,X,Y,0,TL2,TR2,TL1,TR1,SELECT,START,RESET,...` |

Sin tocar: `joystick.raw` (data binaria, sin nombres) y `ui.cfg` (layout de la UI).

Se aplico el swap en todos los VID/PID para no depender de cual matchea el dongle.

## Herramientas

`cpdtool.py` lee y escribe los contenedores `.cpd`: son ZIP con tres firmas
sustituidas y los nombres de miembro cifrados con XOR `0xE5`.

```
cpdtool.py list    <file.cpd>
cpdtool.py extract <file.cpd> <outdir>
cpdtool.py pack    <indir> <file.cpd>
cpdtool.py tozip   <file.cpd> <file.zip>
cpdtool.py fromzip <file.zip> <file.cpd>
```

## Verificacion

- El numero de campos por linea no cambio en ningun miembro.
- El intercambio es exacto: `TL1` quedo donde estaba `TL2` y viceversa.
- Round-trip: extraer el `.cpd` generado reproduce los 8 miembros byte a byte.
- Integridad del contenedor: OK.
- Probado en el stick: L2 + R2 simultaneos funcionan.

## Creditos

`cpdtool.py` **no es nuestro**. Lo trajo Emilio y lo escribio un tercero que no
pudimos identificar: el archivo no trae autor, licencia ni URL, y el commit que
lo subio a este repo es un "Add files via upload" sin atribucion.

Si sos el autor de esa herramienta, escribinos y te ponemos el credito con
nombre y link como corresponde. Tu trabajo fue el que hizo posible todo esto:
sin una herramienta para abrir y rearmar el `.cpd` no se podia ni empezar.

### Creditos verificables

El formato que usa `cpdtool.py` (ZIP con firmas `PK\x03\x04`/`PK\x01\x02`/`PK\x05\x06`
sustituidas por `WQW\x03`/`WQW\x02`/`WQW\x01` y nombres de miembro con XOR) esta
documentado publicamente en:

- **ethersloth** — [`GameMT_E5_One_Click_Tool`](https://github.com/ethersloth/GameMT_E5_One_Click_Tool):
  `Codes/wqw_writer.py` y `wqw2zip.py` documentan el mismo esquema de firmas y el
  XOR de nombres. Comprobamos que aplica exacto a nuestro `joystick.cpd`.
- **matiasm2** — [`super-drive-mini-2-sd-backup`](https://github.com/matiasm2/super-drive-mini-2-sd-backup)
  y **jeborgesm** — [`xgo-a10-research`](https://github.com/jeborgesm/xgo-a10-research):
  documentan el mismo contenedor `WQW` en otros equipos con el mismo SoC.

Gracias a ellos por publicar el formato en vez de dejarlo cerrado.

### Lo nuestro

El analisis del binario `rkgame`, el diagnostico de `TL1`/`TR1` vs `TL2`/`TR2`
y la solucion de los gatillos son de este repo (ver `AGENTS.md`).

## Archivos

```
joystick - TL1-TL2 y TR1-TR2 intercambiados.cpd   el archivo para instalar
cpdtool.py                                        herramienta .cpd (de terceros)
cubegm.zip                                        firmware original de referencia
AGENTS.md                                         notas de ingenieria inversa
```
