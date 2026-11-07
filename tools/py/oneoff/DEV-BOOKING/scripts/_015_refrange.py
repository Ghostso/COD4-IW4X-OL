# -*- coding: utf-8 -*-
"""015: find all code references to any dword VA inside a range."""
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_MEM  # noqa

lo = int(sys.argv[1], 16)
hi = int(sys.argv[2], 16)

WRITE = {"mov", "or", "and", "xor", "add", "sub", "inc", "dec", "movzx", "movsx", "xchg"}

for va in range(lo, hi, 4):
    pat = struct.pack("<I", va)
    i = DATA.find(pat)
    while i >= 0:
        ref = BASE + i
        ins = None
        for back in range(1, 12):
            st = ref - back
            if st < BASE:
                continue
            code = DATA[st - BASE: st - BASE + 24]
            x = next(MD.disasm(code, st), None)
            if x and x.address <= ref < x.address + x.size:
                ins = x
                break
        if ins and ins.mnemonic != "add":
            w = ""
            ops = ins.operands
            if ops and ops[0].type == X86_OP_MEM and ins.mnemonic in WRITE:
                w = "W"
            print("0x%08X -> 0x%08X  %-16s %s %s" % (ins.address, va, w,
                                                     ins.mnemonic, ins.op_str))
        i = DATA.find(pat, i + 1)
