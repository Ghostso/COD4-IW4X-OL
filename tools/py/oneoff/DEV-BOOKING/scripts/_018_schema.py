# -*- coding: utf-8 -*-
"""018: search schema-ish tables for a field offset, and read name strings from the packed EXE."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _015_lib import BASE, DATA, END, cstr

need = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x168
lo, hi = 0xDF8000, 0xE00000
pat = struct.pack("<I", need)
print("=== dword 0x%X in [0x%X,0x%X) ===" % (need, lo, hi))
i = DATA.find(pat, lo - BASE, hi - BASE)
n = 0
while i >= 0 and i < hi - BASE:
    va = BASE + i
    neigh = struct.unpack_from("<8I", DATA, i - 8) if i >= 8 else ()
    # look for plausible string pointers in the surrounding 0x40 bytes
    ptrs = []
    for k in range(0, 0x40, 4):
        v = struct.unpack_from("<I", DATA, i - 8 + k)[0]
        if BASE + 0x400000 <= v < END:
            s = cstr(v, 64)
            if s:
                ptrs.append("0x%08X=%r" % (v, s))
    print("0x%08X  ctx=%s" % (va, " ".join("%08X" % x for x in neigh)))
    for p in ptrs:
        print("        near %s" % p)
    n += 1
    i = DATA.find(pat, i + 1, hi - BASE)
print("total %d" % n)

# ---- read strings from the packed EXE (section 2 raw) ----
EXE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "COD OL", "codoMP_client_shipRetail.exe")
print("=== EXE strings ===")
print("exe exists:", os.path.exists(EXE))
if os.path.exists(EXE):
    d = open(EXE, "rb").read()
    SEC2_VA, SEC2_RAW, SEC2_RS = 0x00A16000, 0x00702000, 0x00062000
    for a in sys.argv[2:]:
        va = int(a, 16)
        rva = va - 0x400000
        if SEC2_VA <= rva < SEC2_VA + SEC2_RS:
            fo = SEC2_RAW + (rva - SEC2_VA)
            raw = d[fo:fo + 96]
            s = raw.split(b"\x00")[0]
            print("  0x%08X  %r" % (va, s[:90]))
        else:
            print("  0x%08X  not in sec2 raw" % va)
