# Segam M8 V6 (game stick 4K) - mapeo de botones PS1

Archivos de configuracion de pcsx4all para Soul Reaver (PS1).

## El problema

Los gatillos L2 y R2 del mando comparten el mismo eje (eje Z). L2 manda +Z y R2
manda -Z, asi que al apretarlos juntos los valores se anulan y el emulador
registra uno solo (gana R2). Es una limitacion fisica del mando, no del juego
ni del emulador.

## El archivo .scf

`cubegm/cores/saves/Soul Reaver.scf`, 100 bytes:

```
ff 01                      header
0a 20 20 20                L1 fisico   -> manda L1
0b 20 20 20                R1 fisico   -> manda R1
09 20 20 20                A  fisico   -> manda R2
08 20 20 20                B  fisico   -> manda L2
20 20 20 20                X  fisico   -> sin asignar
01 20 20 20                Y  fisico   -> manda L3
```

Cada entrada son 4 bytes: jugador 1, 2, 3 y 4. `20` (32) = sin asignar.
El bloque de 24 bytes se repite 4 veces (100 = 4 + 24*4).

## Tabla de valores (pcsx4all, identica desde 2013)

| Hex | Boton | Hex | Boton |
|-----|-------|-----|-------|
| 00 | Select | 08 | L2 |
| 01 | L3 | 09 | R2 |
| 02 | R3 | 0a | L1 |
| 03 | Start | 0b | R1 |
| 04 | Arriba | 0c | Triangulo |
| 05 | Derecha | 0d | Circulo |
| 06 | Abajo | 0e | Cruz |
| 07 | Izquierda | 0f | Cuadrado |
|  |  | 20 | sin asignar |

## Archivos

- `Soul Reaver - original.scf` — el original, sin tocar.
- `Soul Reaver - opcion1 X=L2 Y=R2.scf` — X manda L2, Y manda R2.
  Apretando X+Y se mandan L2+R2 juntos. A y B siguen funcionando.
- `Soul Reaver - opcion2 R1=R2 X=R1.scf` — el R1 fisico manda R2 (swap), y
  X manda R1 para no perder la funcion de R1.

## Como usar

1. Backup del original.
2. Copiar el `.scf` elegido a `cubegm/cores/saves/` con el nombre exacto
   `Soul Reaver.scf`.
3. El archivo tiene que quedar en 100 bytes. Si cambia el tamano, el
   emulador lo ignora.
4. Cerrar el emulador y volver a abrir el juego.

Editar con HxD (Windows) o ghex/bless (Linux).
