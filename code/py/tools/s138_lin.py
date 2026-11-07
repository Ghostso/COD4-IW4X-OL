#!/usr/bin/env python3
"""s138_lin <VA> <len> : linear disassembly of a range, prints everything."""
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, ml=90):
    o = va - VA
    if not (0 <= o < N - 1):
        return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2:
        return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


va = int(sys.argv[1], 0)
n = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x100
for ins in md.disasm(d[va - VA:va - VA + n], va):
    line = "0x%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
    for m in re.finditer(r"0x([0-9a-f]{5,8})", ins.op_str):
        s = cstr(int(m.group(1), 16))
        if s:
            line += "   ; '%s'" % s
    print(line)
