# -*- coding: utf-8 -*-
"""015: show context around given call sites with correct instruction alignment."""
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, MD  # noqa


def aligned_window(va, before=0x30, after=0x50):
    """Find a start offset such that decoding lands exactly on va."""
    for back in range(before, 1, -1):
        st = va - back
        insns = list(MD.disasm(DATA[st - BASE: st - BASE + back + after], st))
        for ins in insns:
            if ins.address == va:
                return insns
    return []


for a in sys.argv[1:]:
    va = int(a, 16)
    print("==== 0x%08X" % va)
    for ins in aligned_window(va):
        mark = "   <<<" if ins.address == va else ""
        print("   0x%08X  %-20s %s %s%s"
              % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
