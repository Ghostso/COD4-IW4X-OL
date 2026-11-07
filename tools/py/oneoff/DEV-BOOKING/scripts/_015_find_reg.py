# -*- coding: utf-8 -*-
"""015: near each matching-singleton reference, look for writes to [obj+4..0x1C]."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM  # noqa

SINGLETON = 0x82E13FC
WRITE_MNEM = {"mov", "or", "and", "xor", "add", "sub", "xchg"}
WINDOW = 0x140


def scan(va, lo, hi):
    out = []
    code = DATA[lo - BASE: hi - BASE]
    for ins in MD.disasm(code, lo):
        if ins.address < lo or ins.address >= hi:
            continue
        if not ins.operands or ins.operands[0].type != X86_OP_MEM:
            continue
        if ins.mnemonic not in WRITE_MNEM:
            continue
        m = ins.operands[0].mem
        if m.disp in (4, 8, 0xC, 0x10, 0x14, 0x18, 0x1C) and m.base != 0 \
                and "dword" in ins.op_str:
            out.append(ins)
    return out


def main():
    pat = struct.pack("<I", SINGLETON)
    refs = []
    i = DATA.find(pat)
    while i >= 0:
        refs.append(BASE + i)
        i = DATA.find(pat, i + 1)
    for r in refs:
        lo = max(BASE, r - WINDOW)
        hi = min(END, r + WINDOW)
        hits = scan(r, lo, hi)
        if hits:
            print("=== ref 0x%08X" % r)
            for h in hits:
                print("      0x%08X  %-22s %s %s" % (h.address, h.bytes.hex(),
                                                     h.mnemonic, h.op_str))


if __name__ == "__main__":
    main()
