# -*- coding: utf-8 -*-
"""015: find all writes to a 2-byte memory operand at [base + disp].

Usage: python _015_wordwrite.py <disp_hex> [size]
"""
import os
import pickle
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM  # noqa

IDX = pickle.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "_015_idx.pkl"), "rb"))

disp = int(sys.argv[1], 16)
size = int(sys.argv[2]) if len(sys.argv) > 2 else 2

WRITE = {"mov", "or", "and", "xor", "add", "sub", "xchg", "inc", "dec", "not", "neg"}

n = 0
for va in sorted(IDX):
    code = DATA[va - BASE: va - BASE + 16]
    ins = next(MD.disasm(code, va), None)
    if ins is None:
        continue
    if ins.mnemonic not in WRITE:
        continue
    if not ins.operands or ins.operands[0].type != X86_OP_MEM:
        continue
    if ins.operands[0].size != size:
        continue
    m = ins.operands[0].mem
    if m.disp != disp or m.index != 0 or m.base == 0:
        continue
    n += 1
    print("0x%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
print("total %d" % n)
