#!/usr/bin/env python3
"""s138_serparse: decode a dwRoomMessage serialize/deserialize function into a
field list. Prints each bitstream op with the local source/dest it touches.

usage: s138_serparse.py <VA>   (function start)
"""
import re
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)

WL = {0xB77B10: "writeBits", 0xB777C0: "writeData",
      0xB774E0: "readBits", 0xB772E0: "readData",
      0x4F3EB0: "readBlob", 0x8F3EB0: "readBlob",
      0x8435D0: "error", 0xB75D40: "bitlen"}


def main(va):
    code = d[va - VA:va - VA + 0x400]
    insns = list(md.disasm(code, va))
    for k, ins in enumerate(insns[:160]):
        m, o = ins.mnemonic, ins.op_str
        mark = ""
        if m == "call" and o.startswith("0x"):
            t = int(o, 16)
            if t in WL:
                mark = "   <<< " + WL[t]
        if ins.address > va + 0x300:
            break
        print("0x%08X  %-24s %-8s %s%s" % (ins.address, ins.bytes.hex(), m, o, mark))
        if m == "ret":
            break


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print("=" * 70)
        main(int(a, 0))
