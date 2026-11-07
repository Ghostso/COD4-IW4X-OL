# -*- coding: utf-8 -*-
"""015: generic scan: memory stores of a given immediate size/value."""
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_IMM, X86_OP_MEM  # noqa

LO = int(sys.argv[1], 16)
HI = int(sys.argv[2], 16)
VAL = int(sys.argv[3], 16)
SIZE = int(sys.argv[4]) if len(sys.argv) > 4 else 0
CTX = int(sys.argv[5]) if len(sys.argv) > 5 else 0


def sweep(lo, hi):
    pos = lo
    while pos < hi:
        code = DATA[pos - BASE: min(hi - BASE, pos - BASE + 16)]
        ins = next(MD.disasm(code, pos), None)
        if ins is None or ins.size == 0:
            pos += 1
            continue
        yield ins
        pos += ins.size


n = 0
for ins in sweep(LO, HI):
    if ins.mnemonic not in ("mov", "or", "and", "xor", "add", "sub"):
        continue
    if not ins.operands or ins.operands[0].type != X86_OP_MEM:
        continue
    if ins.operands[0].size != SIZE and SIZE:
        continue
    if len(ins.operands) < 2 or ins.operands[1].type != X86_OP_IMM:
        continue
    if ins.operands[1].imm != VAL:
        continue
    n += 1
    print("0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
print("total %d" % n)
