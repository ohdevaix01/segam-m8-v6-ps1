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
| `clip_368` | recorte horizontal en modo 368 (ver abajo) | `0`/`1` |
| `lighting` | iluminacion | `0`/`1` |
| `fast_lighting` | iluminacion rapida (menos precisa) | `0`/`1` |
| `blending` | transparencias | `0`/`1` |
| `dithering` | tramado | `0`/`1` |

### clip_368: que hace exactamente

No es un parametro de pcsx4all original. Es el **`pixel_skip`** de gpu_unai con
otro nombre, apuntado a la resolucion 368 de PS1.

**Que es 368.** PS1 tiene 8 resoluciones horizontales reales, y 368 es una de
ellas. La usan bastantes juegos de alta resolucion (Tekken 3, Ridge Racer, menus
de varios titulos). En el fuente de gpu_unai upstream:

```c
static const uint32_t HorizontalResolution[8] = { 256, 368, 320, 384, 512, 512, 640, 640 };
```

**Que hace el flag.** El panel del stick es de 320x240, o sea 320 pixeles de
ancho. Cuando el juego pide 368, sobran 48 columnas que no entran. La rama
`case 368` del blit llama a `GPU_BlitWWWWWWWWS(src, dst, isRGB24, 4)`: ese ultimo
argumento (`uClip_src = 4`) hace que **saltee los primeros 4 pixeles de cada grupo
de 18 y escriba 16**. Resultado: 20 grupos x 16 = 320 exacto, justo el ancho del
panel. Las 48 columnas se descartan en la cuenta de punteros, sin llegar a
escribirse.

**Donde esta en el binario.** El parser guarda el valor en el bit 0 de la
estructura `gpu_unai_config_t`, la misma posicion que `pixel_skip` en el fuente
upstream. En el fork publico esa opcion esta comentada (`/* ... */`); Segam la
volvio a habilitar bajo el nombre `clip_368`.

```
0x467f30  lui   $a1, 0x50          ; string "clip_368"
0x467f38  jal   0x5125e0           ; strcmp
0x4680b8  ins   $v1, $a0, 0, 1     ; escribe bit 0
...
0x468e8c  lbu   $v0, 0x7560($v0)   ; lee el byte de config
0x468ea4  ext   $v0, $v0, 0, 1     ; extrae bit 0
0x468eb8  sb    $v0, -0x7184($s0)  ; global "pixel skip activo"
...
0x46244c  lbu   $t6, -0x7184($v0)  ; dentro de case 368
0x462450  beqz  $t6, 0x462b14      ; 0 -> ruta sin recorte
0x462f00  ...                      ; 1 -> ruta con recorte de 4 pixeles
```

**Consecuencia practica:** solo afecta a juegos que corren a 368 de ancho. En
juegos a 320 no hace absolutamente nada, y en 512/640 tampoco (esos van por
`blit_mask`, otro camino).

**Riesgo.** El fuente de gpu_unai advierte que si un juego lee el framebuffer de
vuelta para hacer efectos, puede notar los pixeles descartados. Es poco comun y
en el peor caso no cambia nada.

Recomendacion: **`clip_368 1`** si jugas titulos de 368. Si ves algun artefacto
raro, volve a `0`.

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
| `clip_368` | 0 | **1** | recorta 368->320 en el blit; menos trabajo y se ve igual |

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
