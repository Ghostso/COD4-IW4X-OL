# -*- coding: utf-8 -*-
"""015: list all code references (using the aligned instruction index) to
absolute addresses in [lo,hi).  Handy for IAT slot xrefs.
"""
import os
import pickle
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, MD  # noqa
from capstone.x86 import X86_OP_IMM, X86_OP_MEM  # noqa

IDX = pickle.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "_015_idx.pkl"), "rb"))

lo = int(sys.argv[1], 16)
hi = int(sys.argv[2], 16)
mode = sys.argv[3] if len(sys.argv) > 3 else ""

hits = {}
for va in range(lo, hi, 4):
    pat = struct.pack("<I", va)
    i = DATA.find(pat)
    while i >= 0:
        ref = BASE + i
        for back in range(0, 8):
            st = ref - back
            if st not in IDX:
                continue
            code = DATA[st - BASE: st - BASE + 16]
            ins = next(MD.disasm(code, st), None)
            if ins is None:
                continue
            if not (ins.address <= ref < ins.address + ins.size):
                continue
            # must reference exactly this address
            ok = False
            for op in ins.operands:
                if op.type == X86_OP_IMM and op.imm == va:
                    ok = True
                elif op.type == X86_OP_MEM and op.mem.disp == va and op.mem.base == 0 and op.mem.index == 0:
                    ok = True
            if not ok:
                continue
            kind = "?"
            if ins.mnemonic in ("call", "jmp"):
                kind = "CALL/JMP"
            hits.setdefault(va, []).append((ins.address, ins.bytes.hex(),
                                            ins.mnemonic + " " + ins.op_str, kind))
            break
        i = DATA.find(pat, i + 1)

for va in sorted(hits):
    for a, b, t, k in hits[va]:
        if mode == "calls" and k != "CALL/JMP":
            continue
        print("0x%08X <- 0x%08X  %-20s %-8s %s" % (va, a, b, k, t))
if not hits:
    print("no refs in 0x%08X..0x%08X" % (lo, hi))
