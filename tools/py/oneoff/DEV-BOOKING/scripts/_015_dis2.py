# -*- coding: utf-8 -*-
"""015: resync disassembly of [lo,hi) with string/VA annotations.

Usage: python _015_dis2.py <lo> <hi>
"""
import os
import pickle
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD, cstr  # noqa
from capstone.x86 import X86_OP_IMM  # noqa

lo = int(sys.argv[1], 16)
hi = int(sys.argv[2], 16)

pos = lo
while pos < hi:
    code = DATA[pos - BASE: min(hi - BASE, pos - BASE + 16)]
    ins = next(MD.disasm(code, pos), None)
    if ins is None or ins.size == 0 or pos + ins.size > hi:
        pos += 1
        continue
    note = ""
    for op in ins.operands:
        if op.type == X86_OP_IMM and BASE <= op.imm < END:
            s = cstr(op.imm, 64)
            if s:
                note = '   ; "%s"' % s
    print("0x%08X  %-20s %-16s %s%s" % (ins.address, ins.bytes.hex(),
                                        ins.mnemonic, ins.op_str, note))
    pos += ins.size
