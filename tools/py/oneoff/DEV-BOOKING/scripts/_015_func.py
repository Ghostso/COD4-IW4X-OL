# -*- coding: utf-8 -*-
"""015: find function start by walking back to int3 padding, then disassemble."""
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa


def find_start(va, maxback=0x600):
    p = va
    while p > BASE and p > va - maxback:
        p -= 1
        if DATA[p - BASE] == 0xCC:
            q = p
            while q > BASE and DATA[q - BASE] == 0xCC:
                q -= 1
            cand = q + 1
            # verify the candidate disassembles forward and covers va
            insns = list(MD.disasm(DATA[cand - BASE: cand - BASE + (va - cand) + 16], cand))
            for ins in insns:
                if ins.address == va:
                    return cand
    return va


if __name__ == "__main__":
    for a in sys.argv[1:]:
        va = int(a, 16)
        st = find_start(va)
        print("==== 0x%08X  (function start 0x%08X)" % (va, st))
        for ins in MD.disasm(DATA[st - BASE: st - BASE + (va - st) + 0x60], st):
            mark = "   <<<" if ins.address == va else ""
            print("   0x%08X  %-20s %s %s%s"
                  % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
