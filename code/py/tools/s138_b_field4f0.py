#!/usr/bin/env python3
"""s138_b_field4f0: find every instruction referencing displacement 0x4F0.
Scans for the 4-byte displacement 0x000004f0 in modrm forms, then disassembles
a window around each hit and keeps lines mentioning + 0x4f0.
Usage: python -I tools/s138_b_field4f0.py
"""
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)

pat = b"\xf0\x04\x00\x00"
hits = []
i = 0
while True:
    i = d.find(pat, i)
    if i < 0:
        break
    hits.append(i)
    i += 1

print("displacement hits: %d" % len(hits))


def entry_of(f):
    j = f
    while j > 1:
        if d[j - 1] == 0xCC and d[j - 2] == 0xCC:
            return VA + j
        j -= 1
    return None


rows = []
for h in hits:
    # disassemble from a bit before to land on instruction boundary; instead
    # disassemble the containing function start region is expensive. Use
    # heuristic: instruction starting at h-6..h-1 whose bytes decode ending at h+4.
    found = None
    for back in range(3, 10):
        s = h - back
        if s < 0:
            continue
        for ins in md.disasm(d[s:s + back + 4], VA + s):
            if ins.address + ins.size == VA + h + 4 and "0x4f0" in ins.op_str:
                found = ins
        if found:
            break
    if found is None:
        continue
    rows.append((found.address, found.mnemonic + " " + found.op_str))

for a, txt in rows:
    e = entry_of(a - VA)
    print("0x%08X  %-40s  func 0x%08X" % (a, txt, e or 0))
