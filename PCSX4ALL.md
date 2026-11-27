# pcsx4all en el Segam M8 V6 — parametros y configuracion optima

El modulo de PSX es **pcsx4all**. `rkgame` lo levanta y lee su config de:

```
cubegm/cores/.pcsx4all/pcsx4all.cfg
```

## Reglas del formato (verificadas en el binario `rkgame`)

- La **primera linea tiene que ser** `CONFIG_VERSION 0`. Si el numero no coincide,
  el parser corta y **ignora el archivo entero** (no avisa en pantalla, arranca
  con los defaults compilados). Es la causa mas comun de "no me tomo los cambios".
- Formato `clave valor`, una por linea, separadas por un espacio.
- Claves desconocidas se ignoran en silencio.
- **`CycleMultiplier` se lee en HEXADECIMAL** (`%03x`). `200` = 0x200 = 2.00x.
  Si escribis `512` pensando en decimal, te queda 0x512 = 5.07x y el emulador
  va lentisimo. Es el error mas facil de cometer.
- Si falta una clave, queda el default compilado, no rompe nada.

## Parametros, uno por uno

| Clave | Que hace | Valores |
|---|---|---|
| `CONFIG_VERSION` | version de formato | `0` fijo |
| `Xa` | audio XA (musica/voces de CD) | `0` habilitado, `1` deshabilitado |
| `Mdec` | solo MDEC en blanco y negro | `0` normal, `1` solo ByN |
| `PsxAuto` | autodetecta NTSC/PAL | `1` auto, `0` usa `PsxType` |
| `Cdda` | audio de pista de CD | `0` habilitado, `1` deshabilitado |
| `HLE` | BIOS | `0` usa BIOS real, `1` HLE emulado |
| `RCntFix` | fix de timing | `1` para Parasite Eve 2, Vandal Hearts 1/2 |
| `VSyncWA` | fix de vsync | `1` para InuYasha Sengoku Battle |
| `Cpu` | nucleo | `0` recompilador (rapido), `1` interprete (lento) |
| `PsxType` | region forzada | `0` NTSC, `1` PAL |
| `SpuIrq` | IRQ de SPU siempre activa | `1` arregla audio en algunos juegos |
| `SyncAudio` | bloquea el hilo si el buffer de audio se llena | `0` off, `1` on |
| `SpuUpdateFreq` | frecuencia de update del SPU | `0`=1x, `1`=2x, `2`=4x, `3`=8x, `4`=16x, `5`=32x por frame |
| `ForcedXAUpdates` | adelanta interrupciones de CDREAD | `0` off, `1` auto, `2`=2x, `3`=4x, `4`=8x, `5`=16x, `6`=32x |
| `ShowFps` | contador de FPS en pantalla | `0`/`1` |
| `FrameLimit` | limita a la velocidad real de la consola | `1` recomendado |
| `FrameSkip` | salteo de cuadros | `-1` auto, `0` off, `1`-`3` fijo |
| `AnalogArrow` | stick izq como cruceta | `0`/`1` |
| `Analog_Mode` | tipo de mando reportado | `0` digital, `1` DualAnalog, `2` DualShock |
| `SpuUseInterpolation` | suavizado de audio | `0`/`1` |
| `SpuUseReverb` | reverb | `0`/`1` |
| `SpuVolume` | volumen | `0`-`1024` |
| `CycleMultiplier` | ciclos por instruccion, **en hex** | `050`=0.31x a `300`=3.00x, `200`=2.00x |
| `interlace` | fuerza salteo de lineas | `0` normal, `1` saltea impares |
| `clip_368` | recorte horizontal, **parche propio de Segam** | `0`/`1` |
| `lighting` | iluminacion | `0`/`1` |
| `fast_lighting` | iluminacion rapida (menos precisa) | `0`/`1` |
| `blending` | transparencias | `0`/`1` |
| `dithering` | tramado | `0`/`1` |

`clip_368` no existe en los forks publicos de pcsx4all: es un parche del firmware
de Segam. Se deja en `0`.

## Perfil recomendado: `pcsx4all - fluido y calidad.cfg`

Ajustes sobre el de fabrica y por que:

| Clave | Fabrica | Recomendado | Motivo |
|---|---|---|---|
| `HLE` | 0 | **0** | esta el BIOS `PSXONPSP660.bin`; compatibilidad muy superior al HLE |
| `Cpu` | 0 | **0** | recompilador siempre; el interprete no corre a velocidad jugable |
| `SyncAudio` | 0 | **1** | sin esto el audio se desincroniza y aparecen crujidos |
| `SpuUpdateFreq` | 4 (16x) | **3 (8x)** | mismo audio, bastante menos CPU |
| `ForcedXAUpdates` | 1 | **1** | evita cortes en musica y voces |
| `SpuUseInterpolation` | 0 | **1** | saca el sonido aspero tipo 8 bits, cuesta muy poco |
| `SpuUseReverb` | 0 | **0** | caro en CPU y casi no se nota |
| `Analog_Mode` | 1 | **2** | DualShock: habilita sticks y vibracion |
| `FrameSkip` | -1 | **-1** | auto: no pierde cuadros si va bien, saltea si se traba |
| `FrameLimit` | 1 | **1** | sin esto los juegos corren acelerados |
| `lighting` | 1 | **1** | se nota mucho, el costo es bajo |
| `fast_lighting` | 0 | **1** | casi identico a la vista, ahorra CPU |
| `blending` | 1 | **1** | las transparencias cambian bastante el look |
| `dithering` | 0 | **0** | apagado se ve mas limpio en panel chico |
| `CycleMultiplier` | 200 | **200** | 2.00x es el equilibrio; subir a `300` da mas compatibilidad y menos FPS |
| `interlace` | 0 | **0** | el panel es progresivo, no hace falta |
| `clip_368` | 0 | **0** | sin documentacion, se deja como viene |

### Si un juego puntual va lento
1. Bajar `CycleMultiplier` a `180` (1.50x). Es lo que mas rinde.
2. Recien despues tocar `FrameSkip` a `1`.
3. Ultimo recurso: `dithering 0` + `blending 0`.

### Si un juego se ve mal o no arranca
1. `RCntFix 1` (Parasite Eve 2, Vandal Hearts).
2. `VSyncWA 1` (InuYasha).
3. `SpuIrq 1` si no hay musica ni voces.

## Como instalarlo

1. Copiar el archivo a la carpeta `cubegm/cores/.pcsx4all/` del stick.
2. Renombrarlo a `pcsx4all.cfg`.
3. Guardar el original como `pcsx4all.cfg.bak`.
4. Verificar que la primera linea siga siendo `CONFIG_VERSION 0`.

Los BIOS que no existen se ignoran solos; se listan todos para que el firmware
pruebe en orden hasta encontrar uno presente.
