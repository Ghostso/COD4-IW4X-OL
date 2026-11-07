# -*- coding: utf-8 -*-
"""018: fast sweep - find disp32 byte pattern, decode locally, classify read/write (non-stack)."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _015_lib import BASE, DATA, END, MD
from capstone.x86 import X86_OP_MEM

WRITE = {"mov","movzx","movsx","or","and","xor","add","sub","inc","dec","xchg",
         "movups","movaps","movdqu","movdqa","stosd","cmove","cmovne"}

disp_targets = [int(x, 16) for x in sys.argv[1].split(",")]
skip_bases = {"esp", "ebp"}
out = []
for disp in disp_targets:
    pat = struct.pack("<I", disp)
    pos = 0
    while True:
        i = DATA.find(pat, pos)
        if i < 0:
            break
        pos = i + 1
        hit = None
        for back in range(1, 17):
            st = BASE + i - back
            if st < BASE:
                continue
            ins = next(MD.disasm(DATA[st - BASE: st - BASE + 20], st), None)
            if ins and ins.address <= BASE + i < ins.address + ins.size:
                hit = ins
                break
        if hit is None:
            continue
        for k, op in enumerate(hit.operands):
            if op.type == X86_OP_MEM and op.mem.disp == disp and op.mem.index == 0:
                base = hit.reg_name(op.mem.base) if op.mem.base else "?"
                if base in skip_bases:
                    break
                w = (k == 0 and hit.mnemonic in WRITE)
                out.append((disp, hit.address, "W" if w else "r", hit.mnemonic,
                            hit.op_str, base, hit.bytes.hex(), hit.size))
                break
out.sort()
print("total non-stack refs = %d" % len(out))
cur = None
for disp, va, w, mn, ops, base, hx, sz in out:
    if disp != cur:
        cur = disp
        print("--- disp 0x%X ---" % disp)
    print("  0x%08X [%s] %-20s %-34s base=%-4s size=%d" % (va, w, hx, mn + " " + ops, base, sz))
