# -*- coding: utf-8 -*-
"""015: byte-pattern scanner over image_best.bin (hex pattern with ?? wildcards)."""
import re
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa


def build(pat):
    out = bytearray()
    mask = []
    for tok in pat.split():
        if tok in ("?", "??"):
            out.append(0)
            mask.append(False)
        else:
            out.append(int(tok, 16))
            mask.append(True)
    return bytes(out), mask


def main():
    pat = sys.argv[1]
    ctx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    needle, mask = build(pat)
    hits = 0
    for i in range(len(DATA) - len(needle)):
        ok = True
        for k in range(len(needle)):
            if mask[k] and DATA[i + k] != needle[k]:
                ok = False
                break
        if not ok:
            continue
        hits += 1
        va = BASE + i
        print("0x%08X" % va)
        if ctx:
            st = max(BASE, va - ctx)
            for ins in MD.disasm(DATA[st - BASE: va + ctx], st):
                if ins.address <= va < ins.address + ins.size:
                    print("      >> 0x%08X  %-22s %s" % (ins.address, ins.bytes.hex(),
                                                         ins.mnemonic + " " + ins.op_str))
                else:
                    print("         0x%08X  %-22s %s" % (ins.address, ins.bytes.hex(),
                                                         ins.mnemonic + " " + ins.op_str))
    print("total %d" % hits)


main()
