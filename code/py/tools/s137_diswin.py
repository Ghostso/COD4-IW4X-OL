#!/usr/bin/env python3
"""通用窗口反汇编 + 串注释: s137_diswin.py <VA> [len]."""
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, mx=60):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > mx:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


va = int(sys.argv[1], 0)
ln = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x60
for ins in md.disasm(d[va - VA:va - VA + ln], va):
    line = "0x%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
    for tok in ins.op_str.replace(",", " ").split():
        if tok.startswith("0x"):
            try:
                s = cstr(int(tok, 16))
            except ValueError:
                s = None
            if s:
                line += "   ; '%s'" % s
    print(line)
