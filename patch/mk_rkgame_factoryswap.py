#!/usr/bin/env python3
"""rkgame v3: Factory Setting cambia el perfil de joystick.

Cambios respecto de v2:
  - usa rutas absolutas (/mnt/sdcard/cubegm/...) en vez de la workpath
  - deja dbg.txt con lo que paso, para diagnosticar desde la SD
  - si algo falla no toca nada y vuelve al menu igual
"""
from keystone import *
from capstone import *
import struct
import sys

SRC, OUT = sys.argv[1], sys.argv[2]
CAVE, CAVE_END = 0x512970, 0x513000
HOOK, RET_MENU = 0x4210E0, 0x420784
FOPEN, FREAD, FWRITE, FCLOSE = 0x5124A0, 0x512420, 0x512530, 0x512630
MALLOC, FREE = 0x512550, 0x512760

S_CPD = b"/mnt/sdcard/cubegm/joystick.cpd\x00"
S_BK = b"/mnt/sdcard/cubegm/joystickbk.cpd\x00"
S_TMP = b"/mnt/sdcard/cubegm/joystick.tmp\x00"
S_RB = b"rb\x00"
S_WB = b"wb\x00"
S_TAG = b"hook: "
S_SWAP = b"swap\n\x00"
S_FAIL = b"no-swap\n\x00"
S_NULL = b"wp=NULL\n\x00"
S_NL = b"\n\x00"
S_INIT = b"init\n\x00"
L1 = b"/mnt/sdcard/cubegm/dbg.txt\x00"
L2 = b"/mnt/sdcard/dbg.txt\x00"
L3 = b"/tmp/dbg.txt\x00"

BLOCKS = [S_CPD, S_BK, S_TMP, S_RB, S_WB, S_TAG, S_SWAP, S_FAIL, S_NULL,
          S_NL, S_INIT, L1, L2, L3]
NAMES = ['CPD', 'BK', 'TMP', 'RB', 'WB', 'TAG', 'SWAP', 'FAIL', 'NULL',
         'NL', 'INIT', 'L1', 'L2', 'L3']
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

# frame del main: buffer de log abajo, registros guardados arriba
BUF = 0
S_RA, S_GP = 700, 696
S_S0, S_S1, S_S2, S_S3 = 692, 688, 684, 680
FRAME = 712

MAIN = """
    addiu $sp, $sp, -{FRAME}
    sw $ra, {S_RA}($sp)
    sw $gp, {S_GP}($sp)
    sw $s0, {S_S0}($sp)
    sw $s1, {S_S1}($sp)
    sw $s2, {S_S2}($sp)
    sw $s3, {S_S3}($sp)

    addiu $s3, $zero, 0

    addiu $v0, $zero, 1
    bne $s7, $v0, m_log
    nop

    # bk -> tmp
    {LA_BK_A}
    {LA_TMP_D}
    jal {CPY}
    nop
    beqz $v0, m_log
    nop

    # cpd -> bk. Si no hay cpd es el primer uso: bk -> cpd y listo.
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
    beqz $v0, m_log
    nop

    # cpd -> tmp
    {LA_CPD_A}
    {LA_TMP_D}
    jal {CPY}
    nop
    addiu $s3, $zero, 1
    b m_log
    nop

m_first:
    {LA_BK_A}
    {LA_CPD_D}
    jal {CPY}
    nop
    beqz $v0, m_log
    nop
    addiu $s3, $zero, 2

m_log:
    addiu $s0, $sp, {BUF}
    move $s1, $s0

    # "hook: " + workpath (o "wp=NULL") + resultado
    move $a0, $s1
    {LA_TAG}
    jal {APP}
    nop
    move $s1, $v0

    lw $s2, -0x7fa8($gp)
    bnez $s2, m_wp
    nop
    move $a0, $s1
    {LA_NULL}
    jal {APP}
    nop
    b m_res
    nop
m_wp:
    move $a0, $s1
    move $a1, $s2
    jal {APP}
    nop
    move $s1, $v0
    move $a0, $s1
    {LA_NL}
    jal {APP}
    nop
m_res:
    move $s1, $v0
    move $a0, $s1
    beqz $s3, m_none
    nop
    addiu $t0, $zero, 2
    beq $s3, $t0, m_init
    nop
    {LA_SWAP}
    jal {APP}
    nop
    b m_wr
    nop
m_init:
    {LA_INIT}
    jal {APP}
    nop
    b m_wr
    nop
m_none:
    {LA_FAIL}
    jal {APP}
    nop
m_wr:
    move $s2, $v0
    subu $s2, $s2, $s0

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
    {LA_RET}
    jr $t9
    nop
""".format(FRAME=FRAME, S_RA=S_RA, S_GP=S_GP, S_S0=S_S0, S_S1=S_S1,
           S_S2=S_S2, S_S3=S_S3, BUF=BUF,
           LA_CPD_A=la('a0', V['CPD']), LA_BK_A=la('a0', V['BK']),
           LA_TMP_A=la('a0', V['TMP']), LA_CPD_D=la('a1', V['CPD']),
           LA_BK_D=la('a1', V['BK']), LA_TMP_D=la('a1', V['TMP']),
           LA_TAG=la('a1', V['TAG']), LA_SWAP=la('a1', V['SWAP']),
           LA_FAIL=la('a1', V['FAIL']), LA_NULL=la('a1', V['NULL']),
           LA_NL=la('a1', V['NL']), LA_INIT=la('a1', V['INIT']),
           LA_L1=la('a0', V['L1']), LA_L2=la('a0', V['L2']),
           LA_L3=la('a0', V['L3']),
           LA_RET=la('t9', RET_MENU), APP=A_APP, CPY=A_CPY, LOG=A_LOG)

mn = A(MAIN, A_MAIN)
enc = ap + cp + wl + mn
print("app %#x copy %#x log %#x main %#x end %#x strs %#x margen %d" %
      (A_APP, A_CPY, A_LOG, A_MAIN, CAVE + len(enc), STRV,
       STRV - (CAVE + len(enc))))
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
