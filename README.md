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

## Archivos

```
joystick - TL1-TL2 y TR1-TR2 intercambiados.cpd   el archivo para instalar
cpdtool.py                                        herramienta .cpd
cubegm.zip                                        firmware original de referencia
AGENTS.md                                         notas de ingenieria inversa
```
