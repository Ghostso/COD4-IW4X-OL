# -*- coding: utf-8 -*-
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM
IMG = Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin").read_bytes()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
def read(va,n):
    o=va-BASE; return IMG[o:o+n] if 0<=o and o+n<=len(IMG) else b""
# search for writes to [reg+0x168] and [reg+0x16c] (A/B fields) in matching module 0x62xxxx-0x63xxxx
# pattern: mov [reg+disp], reg   -> 89 xx disp (disp=0x168 -> 68 01 00 00)
for disp in (0x168, 0x16c):
    pat = struct.pack('<I', disp)
    hits=[]; s=0
    while True:
        j=IMG.find(pat,s)
        if j<0: break
        va=BASE+j
        # check instruction is a mov [reg+disp], reg (89) or mov [reg+disp], imm (c7)
        if va >= 0x620000 and va < 0x63A000:
            # look back up to 3 bytes for the opcode
            for back in range(1,4):
                b = read(va-back, back)
                if b and (b[0] in (0x89, 0x8b, 0xc7, 0x3b, 0x39, 0x83, 0xff)):
                    hits.append((va-back, b.hex()))
                    break
        s=j+1
    print(f"disp 0x{disp:X} in matching module: {[(hex(a),c) for a,c in hits][:30]}")
