#!/usr/bin/env python3
"""rkgame v4: Factory Setting cambia el perfil de joystick y reinicia.

El swap de archivos solo no alcanza: rkgame lee joystick.cpd al arrancar,
asi que el cambio no se ve hasta reiniciar. icube es un supervisor: cuando
el hijo (rkgame) termina, lo relanza con execl. Entonces el cave hace el
swap y llama exit(0); icube lo levanta de nuevo y ya toma el perfil nuevo.

Hook en 0x4210E0, el "Yes" real del dialogo:

    0x4210E0  addiu $v0, $zero, 1
    0x4210E4  bne   $s7, $v0, 0x420DB4   ; s7 != 1 -> cancela
    0x4210E8  addiu $v0, $zero, -1        ; delay slot
    0x4210EC  lw    $v1, 0xa4($sp)        ; <- reset destructivo

Si el usuario cancela se vuelve a 0x420DB4 con v0 = -1, igual que el
original. Si confirma, se hace el swap, se anota en dbg.txt y se sale.
"""
from keystone import *
from capstone import *
import struct
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
CAVE, CAVE_END = 0x512970, 0x513000
HOOK, RET_NO = 0x4210E0, 0x420DB4
FOPEN, FREAD, FWRITE, FCLOSE = 0x5124A0, 0x512420, 0x512530, 0x512630
MALLOC, FREE, EXIT = 0x512550, 0x512760, 0x512810
SDL_QUIT = 0x512430

S_CPD = b"/mnt/sdcard/cubegm/joystick.cpd\x00"
S_BK = b"/mnt/sdcard/cubegm/joystickbk.cpd\x00"
S_TMP = b"/mnt/sdcard/cubegm/joystick.tmp\x00"
S_RB = b"rb\x00"
S_WB = b"wb\x00"
S_SWAP = b"swap + restart\n\x00"
S_INIT = b"init + restart\n\x00"
S_FAIL = b"no-swap\n\x00"
S_CANCEL = b"cancel\n\x00"
L1 = b"/mnt/sdcard/cubegm/dbg.txt\x00"
L2 = b"/mnt/sdcard/dbg.txt\x00"
L3 = b"/tmp/dbg.txt\x00"

BLOCKS = [S_CPD, S_BK, S_TMP, S_RB, S_WB, S_SWAP, S_INIT, S_FAIL, S_CANCEL,
          L1, L2, L3]
NAMES = ['CPD', 'BK', 'TMP', 'RB', 'WB', 'SWAP', 'INIT', 'FAIL', 'CANCEL',
         'L1', 'L2', 'L3']
STRINGS = b''.join(BLOCKS)
STRV = CAVE_END - len(STRINGS)
V = {}
_p = STRV
for _n, _b in zip(NAMES, BLOCKS):
    V[_n] = _p
    _p += len(_b)
assert _p == CAVE_END


def hi(v):
    return ((v >> 16) + ((v & 0xFFFF) >= 0x8000)) & 0xFFFF


def lo(v):
    x = v & 0xFFFF
    return x - 0x10000 if x >= 0x8000 else x


def la(r, va):
    return "lui $%s,%d\naddiu $%s,$%s,%d" % (r, hi(va), r, r, lo(va))


KS = Ks(KS_ARCH_MIPS, KS_MODE_MIPS32 + KS_MODE_LITTLE_ENDIAN)
MD = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)


def A(code, va):
    return bytes(KS.asm(code, va)[0])


# append(dst=a0, src=a1) -> v0 = nuevo fin
APPEND = """
    move $v0, $a0
ap_l:
    lbu $t0, 0($a1)
    beqz $t0, ap_d
    sb $t0, 0($v0)
    addiu $v0, $v0, 1
    addiu $a1, $a1, 1
    b ap_l
    nop
ap_d:
    jr $ra
    nop
"""

# copysub(src=a0, dst=a1) -> v0 = 1 si copio
COPY = """
    addiu $sp, $sp, -40
    sw $ra, 36($sp)
    sw $s0, 32($sp)
    sw $s1, 28($sp)
    sw $s2, 24($sp)
    sw $s3, 20($sp)
    sw $a0, 16($sp)
    sw $a1, 12($sp)
    {LA_RB}
    jal {FOPEN}
    nop
    beqz $v0, cs_bad
    move $s0, $v0
    lw $a0, 12($sp)
    {LA_WB}
    jal {FOPEN}
    nop
    beqz $v0, cs_nodst
    move $s1, $v0
    addiu $a0, $zero, 4096
    jal {MALLOC}
    nop
    beqz $v0, cs_both
    move $s2, $v0
cs_l:
    move $a0, $s2
    addiu $a1, $zero, 1
    addiu $a2, $zero, 4096
    move $a3, $s0
    jal {FREAD}
    nop
    beqz $v0, cs_free
    move $s3, $v0
    move $a0, $s2
    addiu $a1, $zero, 1
    move $a2, $s3
    move $a3, $s1
    jal {FWRITE}
    nop
    b cs_l
    nop
cs_free:
    move $a0, $s2
    jal {FREE}
    nop
cs_both:
    move $a0, $s1
    jal {FCLOSE}
    nop
    addiu $s3, $zero, 1
    b cs_src
    nop
cs_nodst:
    move $s3, $zero
cs_src:
    move $a0, $s0
    jal {FCLOSE}
    nop
    move $v0, $s3
    b cs_e
    nop
cs_bad:
    move $v0, $zero
cs_e:
    lw $ra, 36($sp)
    lw $s0, 32($sp)
    lw $s1, 28($sp)
    lw $s2, 24($sp)
    lw $s3, 20($sp)
    addiu $sp, $sp, 40
    jr $ra
    nop
""".format(LA_RB=la('a1', V['RB']), LA_WB=la('a1', V['WB']),
           FOPEN=FOPEN, FREAD=FREAD, FWRITE=FWRITE, FCLOSE=FCLOSE,
           MALLOC=MALLOC, FREE=FREE)

# wlog(path=a0, buf=a1, len=a2)
WLOG = """
    addiu $sp, $sp, -32
    sw $ra, 28($sp)
    sw $s0, 24($sp)
    sw $s1, 20($sp)
    sw $s2, 16($sp)
    move $s1, $a1
    move $s2, $a2
    {LA_WB}
    jal {FOPEN}
    nop
    beqz $v0, wl_e
    move $s0, $v0
    move $a0, $s1
    addiu $a1, $zero, 1
    move $a2, $s2
    move $a3, $s0
    jal {FWRITE}
    nop
    move $a0, $s0
    jal {FCLOSE}
    nop
wl_e:
    lw $ra, 28($sp)
    lw $s0, 24($sp)
    lw $s1, 20($sp)
    lw $s2, 16($sp)
    addiu $sp, $sp, 32
    jr $ra
    nop
""".format(LA_WB=la('a1', V['WB']), FOPEN=FOPEN, FWRITE=FWRITE, FCLOSE=FCLOSE)

ap = A(APPEND, CAVE)
A_APP = CAVE
cp = A(COPY, A_APP + len(ap))
A_CPY = A_APP + len(ap)
wl = A(WLOG, A_CPY + len(cp))
A_LOG = A_CPY + len(cp)
A_MAIN = A_LOG + len(wl)

BUF = 0
S_RA, S_GP = 300, 296
S_S0, S_S1, S_S2, S_S3 = 292, 288, 284, 280
FRAME = 312

MAIN = """
    addiu $sp, $sp, -{FRAME}
    sw $ra, {S_RA}($sp)
    sw $gp, {S_GP}($sp)
    sw $s0, {S_S0}($sp)
    sw $s1, {S_S1}($sp)
    sw $s2, {S_S2}($sp)
    sw $s3, {S_S3}($sp)

    addiu $v0, $zero, 1
    bne $s7, $v0, m_cancel
    nop

    # bk -> tmp
    {LA_BK_A}
    {LA_TMP_D}
    jal {CPY}
    nop
    beqz $v0, m_fail
    nop

    # cpd -> bk. Si no hay cpd es el primer uso.
    {LA_CPD_A}
    {LA_BK_D}
    jal {CPY}
    nop
    beqz $v0, m_first
    nop

    # tmp -> cpd
    {LA_TMP_A}
    {LA_CPD_D}
    jal {CPY}
    nop
    beqz $v0, m_fail
    nop

    # cpd -> tmp, para que tmp quede igual al perfil nuevo
    {LA_CPD_A}
    {LA_TMP_D}
    jal {CPY}
    nop
    {LA_SWAP}
    b m_log
    nop

m_first:
    {LA_BK_A}
    {LA_CPD_D}
    jal {CPY}
    nop
    beqz $v0, m_fail
    nop
    {LA_INIT}
    b m_log
    nop

m_fail:
    {LA_FAIL}

m_log:
    move $s3, $v0
    addiu $s0, $sp, {BUF}
    move $a0, $s0
    move $a1, $s3
    jal {APP}
    nop

    addiu $s2, $zero, 0
m_len:
    addu $t0, $s0, $s2
    lbu $t1, 0($t0)
    beqz $t1, m_wr
    addiu $s2, $s2, 1
    b m_len
    nop
m_wr:
    {LA_L1}
    move $a1, $s0
    move $a2, $s2
    jal {LOG}
    nop
    {LA_L2}
    move $a1, $s0
    move $a2, $s2
    jal {LOG}
    nop
    {LA_L3}
    move $a1, $s0
    move $a2, $s2
    jal {LOG}
    nop

    # salir limpio: icube relanza rkgame y ahi se relee joystick.cpd
    jal {SDLQ}
    nop
    move $a0, $zero
    jal {EXIT}
    nop

m_cancel:
    lw $t0, {S_S0}($sp)
    addiu $v0, $zero, -1
    sw $v0, 0x18($t0)
    lw $ra, {S_RA}($sp)
    lw $gp, {S_GP}($sp)
    lw $s0, {S_S0}($sp)
    lw $s1, {S_S1}($sp)
    lw $s2, {S_S2}($sp)
    lw $s3, {S_S3}($sp)
    addiu $sp, $sp, {FRAME}
    {LA_RETNO}
    jr $t9
    nop
""".format(FRAME=FRAME, S_RA=S_RA, S_GP=S_GP, S_S0=S_S0, S_S1=S_S1,
           S_S2=S_S2, S_S3=S_S3, BUF=BUF,
           LA_CPD_A=la('a0', V['CPD']), LA_BK_A=la('a0', V['BK']),
           LA_TMP_A=la('a0', V['TMP']), LA_CPD_D=la('a1', V['CPD']),
           LA_BK_D=la('a1', V['BK']), LA_TMP_D=la('a1', V['TMP']),
           LA_SWAP=la('v0', V['SWAP']), LA_INIT=la('v0', V['INIT']),
           LA_FAIL=la('v0', V['FAIL']),
           LA_L1=la('a0', V['L1']), LA_L2=la('a0', V['L2']),
           LA_L3=la('a0', V['L3']),
           LA_RETNO=la('t9', RET_NO),
           APP=A_APP, CPY=A_CPY, LOG=A_LOG, EXIT=EXIT, SDLQ=SDL_QUIT)

mn = A(MAIN, A_MAIN)
enc = ap + cp + wl + mn
print("app %#x copy %#x log %#x main %#x end %#x strs %#x margen %d" %
      (A_APP, A_CPY, A_LOG, A_MAIN, CAVE + len(enc), STRV, STRV - (CAVE + len(enc))))
assert CAVE + len(enc) <= STRV, "solape"

ins = list(MD.disasm(enc, CAVE))
assert sum(i.size for i in ins) == len(enc), "disasm incompleto"
errs = []
for k, i in enumerate(ins):
    if i.mnemonic in ('jal', 'jalr', 'jr'):
        n = ins[k + 1] if k + 1 < len(ins) else None
        if not n or n.mnemonic != 'nop':
            errs.append("%#x %s sin nop" % (i.address, i.mnemonic))
    if i.mnemonic in ('b', 'beq', 'bne', 'beqz', 'bnez'):
        t = int(i.op_str.split(',')[-1].strip(), 16)
        if not (CAVE <= t < CAVE + len(enc)):
            errs.append("%#x %s -> %#x" % (i.address, i.mnemonic, t))
assert not errs, errs

hook = A("j %d" % A_MAIN, HOOK)[:8].ljust(8, b"\x00")
d = bytearray(open(SRC, 'rb').read())
assert set(d[CAVE - 0x400000:CAVE_END - 0x400000]) == {0}
d[CAVE - 0x400000:CAVE - 0x400000 + len(enc)] = enc
d[STRV - 0x400000:STRV - 0x400000 + len(STRINGS)] = STRINGS
d[HOOK - 0x400000:HOOK - 0x400000 + 8] = hook
ep, = struct.unpack_from('<I', d, 0x1C)
struct.pack_into('<II', d, ep + 3 * 0x20 + 16, 0x113000, 0x113000)
open(OUT, 'wb').write(d)
print("OK", OUT, len(d))
