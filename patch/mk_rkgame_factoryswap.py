#!/usr/bin/env python3
"""Genera rkgame con el swap de joystick en Factory Setting.

Uso: python3 mk_rkgame_factoryswap.py <rkgame_original> <salida>
Requiere: pip install keystone-engine
"""
from keystone import *
from capstone import *
import struct

import sys
SRC = sys.argv[1] if len(sys.argv) > 1 else 'rkgame.orig'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'rkgame'
CAVE=0x512970; CAVE_END=0x513000
HOOK=0x41A804; RESUME=0x419960
FOPEN=0x5124a0; FREAD=0x512420; FWRITE=0x512530
FCLOSE=0x512630; MALLOC=0x512550; FREE=0x512760

def hi(v): return ((v>>16)+((v&0xffff)>=0x8000))&0xffff
def lo(v):
    x=v&0xffff
    return x-0x10000 if x>=0x8000 else x
def la(r,va): return f"lui ${r},{hi(va)&0xffff}\naddiu ${r},${r},{lo(va)}"

strblob=(b'rb\x00'+b'wb\x00'
         +b'/mnt/sdcard/cubegm/joystick.cpd\x00'
         +b'/mnt/sdcard/cubegm/joystickbk.cpd\x00'
         +b'/mnt/sdcard/cubegm/joystick.tmp\x00')
sb=CAVE_END-len(strblob)
V_RB=sb; V_WB=V_RB+3
V_CPD=V_WB+3
V_BK=V_CPD+len('/mnt/sdcard/cubegm/joystick.cpd\x00')
V_TMP=V_BK+len('/mnt/sdcard/cubegm/joystickbk.cpd\x00')

def copy(src,dst,tag):
    return f"""
    {la('a0',src)}
    {la('a1',V_RB)}
    move $a2,$s3
    jal {FOPEN:#x}
    nop
    move $s0,$v0
    beqz $s0,c_{tag}_end
    nop
    {la('a0',dst)}
    {la('a1',V_WB)}
    jal {FOPEN:#x}
    nop
    move $s1,$v0
    beqz $s1,c_{tag}_cs
    nop
c_{tag}_lp:
    move $a0,$s4
    li $a1,1
    li $a2,4096
    move $a3,$s0
    jal {FREAD:#x}
    nop
    move $s2,$v0
    beqz $s2,c_{tag}_cb
    nop
    move $a0,$s4
    li $a1,1
    move $a2,$s2
    move $a3,$s1
    jal {FWRITE:#x}
    nop
    b c_{tag}_lp
    nop
c_{tag}_cb:
    move $a0,$s1
    jal {FCLOSE:#x}
    nop
c_{tag}_cs:
    move $a0,$s0
    jal {FCLOSE:#x}
    nop
c_{tag}_end:
"""

asm=f"""
    addiu $sp,$sp,-48
    sw $ra,44($sp)
    sw $gp,40($sp)
    sw $s0,36($sp)
    sw $s1,32($sp)
    sw $s2,28($sp)
    sw $s3,24($sp)
    sw $s4,20($sp)
    li $a0,4096
    jal {MALLOC:#x}
    nop
    move $s4,$v0
    beqz $s4,fin
    nop
    {la('s3',V_RB)}
    {la('a0',V_CPD)}
    move $a1,$s3
    jal {FOPEN:#x}
    nop
    move $s0,$v0
    beqz $s0,init_only
    nop
    move $a0,$s0
    jal {FCLOSE:#x}
    nop
{copy(V_BK,V_TMP,'a')}
{copy(V_CPD,V_BK,'b')}
{copy(V_TMP,V_CPD,'c')}
    b fin
    nop
init_only:
{copy(V_BK,V_CPD,'d')}
fin:
    move $a0,$s4
    jal {FREE:#x}
    nop
    lw $ra,44($sp)
    lw $gp,40($sp)
    lw $s0,36($sp)
    lw $s1,32($sp)
    lw $s2,28($sp)
    lw $s3,24($sp)
    lw $s4,20($sp)
    addiu $sp,$sp,48
    j {RESUME:#x}
    nop
"""
ks=Ks(KS_ARCH_MIPS, KS_MODE_MIPS32+KS_MODE_LITTLE_ENDIAN)
enc=bytes(ks.asm(asm,CAVE)[0])
print(f"cave {len(enc)}b  end={CAVE+len(enc):#x}  strs={sb:#x}  entra={CAVE+len(enc)<=sb}")
assert CAVE+len(enc)<=sb
henc=bytes(ks.asm(f"j {CAVE:#x}\nnop",HOOK)[0]); henc+=b"\x00"*(16-len(henc))
print("hook:",henc.hex())

d=bytearray(open(SRC,'rb').read()); assert len(d)==0x1192ec
d[CAVE-0x400000:CAVE-0x400000+len(enc)]=enc
d[sb-0x400000:sb-0x400000+len(strblob)]=strblob
d[HOOK-0x400000:HOOK-0x400000+16]=henc
e_phoff,=struct.unpack_from('<I',d,0x1c); ph=e_phoff+3*0x20
struct.pack_into('<II',d,ph+16,0x113000,0x113000)
open(OUT,'wb').write(d)
print("OK",len(d))
