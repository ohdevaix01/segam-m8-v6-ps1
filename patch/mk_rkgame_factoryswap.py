#!/usr/bin/env python3
"""rkgame: Factory Setting cambia el perfil de joystick en vez de resetear.

Punto del "Yes" del dialogo Factory Setting (funcion 0x4206A8):

    0x4210E0  addiu $v0, $zero, 1
    0x4210E4  bne   $s7, $v0, 0x420DB4     ; s7 != 1 -> cancela
    0x4210E8  addiu $v0, $zero, -1          ; delay slot
    0x4210EC  lw    $v1, 0xa4($sp)          ; <- arranca el reset destructivo

Se reemplazan las dos primeras instrucciones por un salto al cave, que hace:

    joystick.cpd    -> joystick.tmp
    joystickbk.cpd  -> joystick.cpd
    joystick.tmp    -> joystickbk.cpd

Si joystick.cpd no existe (primer uso) copia joystickbk.cpd -> joystick.cpd.
Si falta el bk no toca nada. En todos los casos vuelve al menu sin ejecutar el
reset: setting.xml, recent.lst y favorites.lst quedan intactos.

Uso: python3 mk_rkgame_factoryswap.py <rkgame_original> <salida>
"""
from keystone import *
from capstone import *
import struct, sys

SRC = sys.argv[1] if len(sys.argv) > 1 else 'rkgame.orig'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'rkgame'

CAVE, CAVE_END = 0x512970, 0x513000
HOOK = 0x4210E0
RET_MENU, RET_NO = 0x420784, 0x420DB4
SNPRINTF = 0x5128c0
FOPEN, FREAD, FWRITE, FCLOSE = 0x5124a0, 0x512420, 0x512530, 0x512630
MALLOC, FREE = 0x512550, 0x512760

FMT_CPD = b"%s/joystick.cpd\x00"
FMT_BK  = b"%s/joystickbk.cpd\x00"
FMT_TMP = b"%s/joystick.tmp\x00"
STRINGS = FMT_CPD + FMT_BK + FMT_TMP + b"rb\x00wb\x00"

STRV = CAVE_END - len(STRINGS)
V_CPD = STRV
V_BK  = STRV + len(FMT_CPD)
V_TMP = V_BK + len(FMT_BK)
V_RB  = V_TMP + len(FMT_TMP)
V_WB  = V_RB + 3

def hi(v): return ((v >> 16) + ((v & 0xffff) >= 0x8000)) & 0xffff
def lo(v):
    x = v & 0xffff
    return x - 0x10000 if x >= 0x8000 else x
def la(r, va): return f"lui ${r},{hi(va)&0xffff}\naddiu ${r},${r},{lo(va)}"

BUF_CPD, BUF_BK, BUF_TMP = 0, 128, 256
FR, FG = 544, 540
F0, F1, F2, F3, F4 = 536, 532, 528, 524, 520
FS0 = 516
FRAME = 552

KS = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 + KS_MODE_LITTLE_ENDIAN)
MD = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)

def asm_at(code, va):
    return bytes(KS.asm(code, va)[0])

# copysub va primero, para saber su direccion exacta antes de referenciarla.
# jal a un label local se ensambla mal (keystone lo resuelve como lw $t9,($gp)).
COPYSUB = f"""
    addiu $sp, $sp, -40
    sw $ra, 36($sp)
    sw $s0, 32($sp)
    sw $s1, 28($sp)
    sw $s2, 24($sp)
    sw $s3, 20($sp)
    sw $a0, 16($sp)
    sw $a1, 12($sp)

    {la('a1', V_RB)}
    jal {FOPEN:#x}
    nop
    beqz $v0, cs_end
    move $s0, $v0

    lw $a0, 12($sp)
    {la('a1', V_WB)}
    jal {FOPEN:#x}
    nop
    beqz $v0, cs_src
    move $s1, $v0

    addiu $a0, $zero, 4096
    jal {MALLOC:#x}
    nop
    beqz $v0, cs_both
    move $s2, $v0

cs_loop:
    move $a0, $s2
    addiu $a1, $zero, 1
    addiu $a2, $zero, 4096
    move $a3, $s0
    jal {FREAD:#x}
    nop
    beqz $v0, cs_free
    move $s3, $v0
    move $a0, $s2
    addiu $a1, $zero, 1
    move $a2, $s3
    move $a3, $s1
    jal {FWRITE:#x}
    nop
    b cs_loop
    nop

cs_free:
    move $a0, $s2
    jal {FREE:#x}
    nop
cs_both:
    move $a0, $s1
    jal {FCLOSE:#x}
    nop
cs_src:
    move $a0, $s0
    jal {FCLOSE:#x}
    nop
cs_end:
    lw $ra, 36($sp)
    lw $s0, 32($sp)
    lw $s1, 28($sp)
    lw $s2, 24($sp)
    lw $s3, 20($sp)
    addiu $sp, $sp, 40
    jr $ra
    nop
"""
copy_bytes = asm_at(COPYSUB, CAVE)
COPYSUB_VA = CAVE
MAIN_VA = CAVE + len(copy_bytes)

MAIN = f"""
    addiu $sp, $sp, -{FRAME}
    sw $ra, {FR}($sp)
    sw $gp, {FG}($sp)
    sw $s0, {F0}($sp)
    sw $s1, {F1}($sp)
    sw $s2, {F2}($sp)
    sw $s3, {F3}($sp)
    sw $s4, {F4}($sp)
    sw $s0, {FS0}($sp)

    addiu $v0, $zero, 1
    bne $s7, $v0, notconf
    nop

    lw $s4, -0x7fa8($gp)
    beqz $s4, notconf
    nop

    addiu $a0, $sp, {BUF_CPD}
    addiu $a1, $zero, 128
    {la('a2', V_CPD)}
    move $a3, $s4
    jal {SNPRINTF:#x}
    nop

    addiu $a0, $sp, {BUF_BK}
    addiu $a1, $zero, 128
    {la('a2', V_BK)}
    move $a3, $s4
    jal {SNPRINTF:#x}
    nop

    addiu $a0, $sp, {BUF_TMP}
    addiu $a1, $zero, 128
    {la('a2', V_TMP)}
    move $a3, $s4
    jal {SNPRINTF:#x}
    nop

    addiu $a0, $sp, {BUF_CPD}
    {la('a1', V_RB)}
    jal {FOPEN:#x}
    nop
    beqz $v0, init_only
    move $s0, $v0
    move $a0, $s0
    jal {FCLOSE:#x}
    nop

    addiu $a0, $sp, {BUF_BK}
    {la('a1', V_RB)}
    jal {FOPEN:#x}
    nop
    beqz $v0, done
    move $s0, $v0
    move $a0, $s0
    jal {FCLOSE:#x}
    nop

    # bk -> tmp, cpd -> bk, tmp -> cpd: el cpd se escribe ultimo, asi un
    # corte a mitad deja el cpd original intacto.
    addiu $a0, $sp, {BUF_BK}
    addiu $a1, $sp, {BUF_TMP}
    jal {COPYSUB_VA:#x}
    nop
    addiu $a0, $sp, {BUF_CPD}
    addiu $a1, $sp, {BUF_BK}
    jal {COPYSUB_VA:#x}
    nop
    addiu $a0, $sp, {BUF_TMP}
    addiu $a1, $sp, {BUF_CPD}
    jal {COPYSUB_VA:#x}
    nop
    # deja tmp igual a cpd: si un corte lo dejo a medias, no confunde al
    # siguiente swap (se sobrescribe antes de usarse).
    addiu $a0, $sp, {BUF_CPD}
    addiu $a1, $sp, {BUF_TMP}
    jal {COPYSUB_VA:#x}
    nop
    b done
    nop

init_only:
    addiu $a0, $sp, {BUF_BK}
    addiu $a1, $sp, {BUF_CPD}
    jal {COPYSUB_VA:#x}
    nop

done:
    lw $t0, {FS0}($sp)
    addiu $v0, $zero, -1
    sw $v0, 0x18($t0)
    lw $ra, {FR}($sp)
    lw $gp, {FG}($sp)
    lw $s0, {F0}($sp)
    lw $s1, {F1}($sp)
    lw $s2, {F2}($sp)
    lw $s3, {F3}($sp)
    lw $s4, {F4}($sp)
    addiu $sp, $sp, {FRAME}
    {la('t9', RET_MENU)}
    jr $t9
    nop

notconf:
    lw $t0, {FS0}($sp)
    addiu $v0, $zero, -1
    sw $v0, 0x18($t0)
    lw $ra, {FR}($sp)
    lw $gp, {FG}($sp)
    lw $s0, {F0}($sp)
    lw $s1, {F1}($sp)
    lw $s2, {F2}($sp)
    lw $s3, {F3}($sp)
    lw $s4, {F4}($sp)
    addiu $sp, $sp, {FRAME}
    {la('t9', RET_NO)}
    jr $t9
    nop
"""
main_bytes = asm_at(MAIN, MAIN_VA)
enc = copy_bytes + main_bytes
print(f"copysub {COPYSUB_VA:#x} ({len(copy_bytes)}b) | main {MAIN_VA:#x} ({len(main_bytes)}b)")
print(f"end {CAVE+len(enc):#x} | strings {STRV:#x} | margen {STRV-(CAVE+len(enc))}b")
assert CAVE + len(enc) <= STRV, f"solape: {CAVE+len(enc):#x} > {STRV:#x}"

ins = list(MD.disasm(enc, CAVE))
assert sum(i.size for i in ins) == len(enc), "desensamblado incompleto"
errs = []
for k, i in enumerate(ins):
    if i.mnemonic in ('jal', 'jalr', 'jr'):
        nxt = ins[k+1] if k+1 < len(ins) else None
        if not nxt or nxt.mnemonic != 'nop':
            errs.append(f"{i.address:#x} {i.mnemonic} sin nop en delay slot")
    if i.mnemonic in ('b', 'beq', 'bne', 'beqz', 'bnez'):
        t = int(i.op_str.split(',')[-1].strip(), 16)
        if not (CAVE <= t < CAVE + len(enc)):
            errs.append(f"{i.address:#x} {i.mnemonic} -> {t:#x} fuera del cave")
    if i.mnemonic == 'jal':
        t = int(i.op_str.strip(), 16)
        ok = t in (SNPRINTF, FOPEN, FREAD, FWRITE, FCLOSE, MALLOC, FREE, COPYSUB_VA)
        if not ok:
            errs.append(f"{i.address:#x} jal -> {t:#x} no es un stub conocido")
assert not errs, errs

hook = asm_at(f"j {MAIN_VA:#x}", HOOK)[:8].ljust(8, b"\x00")
assert len(hook) == 8, len(hook)

d = bytearray(open(SRC, 'rb').read())
assert len(d) == 0x1192ec
assert set(d[CAVE-0x400000:CAVE_END-0x400000]) == {0}, "cave no esta en cero"
assert bytes(d[HOOK-0x400000:HOOK-0x400000+8]) == struct.pack('<II', 0x24020001, 0x16e2ff33)

d[CAVE-0x400000:CAVE-0x400000+len(enc)] = enc
d[STRV-0x400000:STRV-0x400000+len(STRINGS)] = STRINGS
d[HOOK-0x400000:HOOK-0x400000+8] = hook

e_phoff, = struct.unpack_from('<I', d, 0x1c)
ph = e_phoff + 3*0x20
assert struct.unpack_from('<I', d, ph+16)[0] == 0x112970
struct.pack_into('<II', d, ph+16, 0x113000, 0x113000)

open(OUT, 'wb').write(d)
print(f"OK -> {OUT} ({len(d)} bytes)")
