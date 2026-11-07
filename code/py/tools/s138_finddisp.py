#!/usr/bin/env python3
"""s138_finddisp <disphex> : find modrm+disp32 references to a struct displacement.
Usage: python -I tools/s138_finddisp.py 0x4f4
Prints instruction text + containing function entry.
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)

disp = int(sys.argv[1], 0)
pat = disp.to_bytes(4, "little")
hits = []
i = 0
while True:
    i = d.find(pat, i)
    if i < 0:
        break
    hits.append(i)
    i += 1


def entry_of(f):
    j = f
    while j > 1:
        if d[j - 1] == 0xCC and d[j - 2] == 0xCC:
            return VA + j
        j -= 1
    return None


seen = set()
for h in hits:
    got = None
    for back in range(2, 12):
        s = h - back
        if s < 0:
            continue
        for ins in md.disasm(d[s:s + back + 4], VA + s):
            if ins.address + ins.size == VA + h + 4 and ("0x%x" % disp) in ins.op_str:
                got = ins
        if got:
            break
    if got is None:
        continue
    key = (got.address, got.mnemonic, got.op_str)
    if key in seen:
        continue
    seen.add(key)
    print("0x%08X  %-34s %s %s   func 0x%08X"
          % (got.address, got.bytes.hex(), got.mnemonic, got.op_str,
             entry_of(got.address - VA) or 0))
