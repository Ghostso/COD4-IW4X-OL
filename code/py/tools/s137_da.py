#!/usr/bin/env python3
"""137: disassemble a VA range from the image (VA=off+0x400000)."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def cstr(va, maxlen=64):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    try:
        s = d[f:e].decode("latin1")
    except Exception:
        return None
    return s if all(32 <= c < 127 for c in s.encode("latin1")) else None


va = int(sys.argv[1], 0)
ln = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x200
halt = "--ret" in sys.argv
f = va - VA
for ins in md.disasm(d[f:f + ln], va):
    line = "  0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(),
                                      ins.mnemonic, ins.op_str)
    for tok in re.findall(r"0x[0-9a-f]+", ins.op_str):
        v = int(tok, 16)
        if VA <= v < VA + N and v % 4 == 0:
            s = cstr(v)
            if s:
                line += "   ; '%s'" % s
                break
    print(line)
    if halt and ins.mnemonic.startswith("ret"):
        break
