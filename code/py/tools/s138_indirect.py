#!/usr/bin/env python3
"""s138_indirect: find indirect writes through a register loaded with the address
of a global.  Pattern: `mov REG, imm32(TGT)` (B8..BF) or `lea REG, [imm32]`,
then within the next N instructions `mov [REG], imm` / `mov [REG+0], src`.
Also handles moffs `A3 TGT` (mov [TGT], eax) which refx already covers.
usage: python -I tools\\s138_indirect.py 0x76446B0
"""
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
CODE_OFF, CODE_SZ = 0x1000, 0x8A7000
REGS = {0: "eax", 1: "ecx", 2: "edx", 3: "ebx", 6: "esi", 7: "edi", 5: "ebp"}


def hits(t):
    pat = struct.pack("<I", t)
    seg = d[CODE_OFF:CODE_OFF + CODE_SZ]
    r = []
    i = 0
    while True:
        j = seg.find(pat, i)
        if j < 0:
            break
        r.append(CODE_OFF + j)
        i = j + 1
    return r


for arg in sys.argv[1:]:
    t = int(arg, 0)
    print("== indirect-write scan for 0x%08X ==" % t)
    seen = set()
    for h in hits(t):
        prev = d[h - 1]
        reg = None
        st = None
        if 0xB8 <= prev <= 0xBF:
            reg = REGS.get(prev - 0xB8)
            st = h - 1
        elif prev == 0x8D:
            # lea reg, [imm32]: 8D modrm(00 reg 101)
            mr = d[h - 2]
            if (mr & 0xC7) == 0x05:
                reg = REGS.get((mr >> 3) & 7)
                st = h - 2
        if not reg:
            continue
        # disassemble forward from st
        code = d[st:st + 160]
        insns = list(md.disasm(code, VA + st))[:12]
        found = False
        for ins in insns[1:]:
            if ins.mnemonic == "mov" and ins.op_str.startswith("[%s]" % reg):
                a = ins.address
                if a in seen:
                    found = True
                    break
                seen.add(a)
                print("  0x%08X  %-26s %s %s   (base=%s via 0x%08X)" % (
                    a, ins.bytes.hex(), ins.mnemonic, ins.op_str, reg, VA + st))
                found = True
                break
            # stop if reg is overwritten
            if ins.mnemonic == "mov" and ins.op_str.startswith(reg + ","):
                break
        if not found:
            pass
    print()
