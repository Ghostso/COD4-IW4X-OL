#!/usr/bin/env python3
"""Find writes that set a small state field to 5 in the decrypted image.

Useful for the objC queue client: its state is [object+4], and state 5 is the
success state checked by 0xB98AE0.  This scans the executable image for
mov dword ptr [reg+4], 5 and prints the surrounding instructions.
"""
from __future__ import annotations

import os
import re

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "_dyn100_run_20260925_182324", "live",
                   "image_best.bin")
BASE = 0x400000


def main() -> int:
    data = open(IMG, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    # mov dword ptr [reg+4], imm32 for common x86 registers.
    pat = re.compile(
        rb"\xc7[\x40-\x47\x80-\x87][\x04\x44\x84]"
        rb"\x05\x00\x00\x00")
    print("image:", IMG)
    hits = 0
    for m in pat.finditer(data):
        va = BASE + m.start()
        lo = max(0, m.start() - 24)
        blob = data[lo:m.start() + 16]
        print("\nVA 0x%08X" % va)
        for ins in md.disasm(blob, BASE + lo):
            mark = "  <== SET5" if ins.address == va else ""
            print("  %08X  %-20s %s %s%s" %
                  (ins.address, ins.bytes.hex(), ins.mnemonic,
                   ins.op_str, mark))
        hits += 1
        if hits >= 80:
            break
    print("\nhits=%d" % hits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
