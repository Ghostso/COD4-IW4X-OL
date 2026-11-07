# -*- coding: utf-8 -*-
"""015: linear-sweep a VA range; show context around writes to [reg+disp]."""
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM  # noqa

lo = int(sys.argv[1], 16)
hi = int(sys.argv[2], 16)
disp = int(sys.argv[3], 16) if len(sys.argv) > 3 else 4
BEFORE = int(sys.argv[4]) if len(sys.argv) > 4 else 8
AFTER = int(sys.argv[5]) if len(sys.argv) > 5 else 5

WRITE_MNEM = {"mov", "or", "and", "xor", "add", "sub", "xchg", "movzx", "movsx"}

insns = list(MD.disasm(DATA[lo - BASE: hi - BASE], lo))
print("instructions:", len(insns))
for k, ins in enumerate(insns):
    if not ins.operands or ins.operands[0].type != X86_OP_MEM:
        continue
    m = ins.operands[0].mem
    if m.disp != disp or m.index != 0 or m.base == 0:
        continue
    if ins.mnemonic not in WRITE_MNEM:
        continue
    print("---- 0x%08X  %s" % (ins.address, ins.op_str))
    for j in range(max(0, k - BEFORE), min(len(insns), k + AFTER + 1)):
        i2 = insns[j]
        mark = " <<<" if j == k else ""
        print("     0x%08X  %-20s %s %s%s"
              % (i2.address, i2.bytes.hex(), i2.mnemonic, i2.op_str, mark))
