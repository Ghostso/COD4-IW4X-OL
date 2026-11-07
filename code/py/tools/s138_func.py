#!/usr/bin/env python3
"""s138_func: find function entry before a VA by scanning backwards for an int3
padding run (>=2 cc) followed by a plausible prologue (55 8b ec / 55 8b / 51/53..).
Then disassemble from that entry to the first ret.
usage: python -I tools\\s138_func.py <VA> [<VA>...]
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)


def find_entry(va):
    o = va - VA
    # scan backwards up to 0x4000
    for back in range(0, 0x6000):
        p = o - back
        if p < 0x1000:
            break
        # require 2+ cc immediately before p
        if d[p - 1] == 0xCC and d[p - 2] == 0xCC:
            # plausible start
            if d[p] == 0x55 or d[p] in (0x53, 0x56, 0x57, 0x51, 0x83, 0x81, 0xA1):
                return VA + p
    return None


def dis(entry, maxlen=0x3000):
    code = d[entry - VA:entry - VA + maxlen]
    for ins in md.disasm(code, entry):
        print("  0x%08X  %-22s %s %s" % (
            ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic.startswith("ret"):
            break


for a in sys.argv[1:]:
    va = int(a, 0)
    e = find_entry(va)
    print("== ref 0x%08X -> entry %s ==" % (va, hex(e) if e else "?"))
    if e:
        dis(e)
    print()
