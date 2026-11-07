#!/usr/bin/env python3
"""s138_rtti_map: map MSVC x86 RTTI class names -> vtable addresses.
TypeDescriptor: [pVFTable][spare][name...]  => td = nameVA-8
COL (x86): +0 sig, +4 offset, +8 cdOffset, +0xC pTD, +0x10 pCD
vtable = (address of dword holding COL) + 4
Usage: python -I tools/s138_rtti_map.py [substr]
"""
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
sub = sys.argv[1].lower() if len(sys.argv) > 1 else None


def rd(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f <= N - 4 else None


# 1) collect type descriptors
td = {}
for m in re.finditer(rb"\.\?A[VU][A-Za-z0-9_@?$<>,\-]{2,140}@@", d):
    nameva = VA + m.start()
    nm = m.group().decode("latin1")
    td[nameva - 8] = (nm, nameva)

# index td va -> name
tdset = set(td)

# 2) find COLs: scan dwords for pTD matching, checking fields at col+0xC
cols = {}
for m in re.finditer(rb"", d):
    pass
# direct scan: iterate 4-byte aligned
buf = d
for off in range(0, N - 0x14, 4):
    ptd = struct.unpack_from("<I", buf, off + 0x0C)[0]
    if ptd in tdset:
        sig = struct.unpack_from("<I", buf, off)[0]
        if sig in (0, 1):
            cols[VA + off] = ptd

# 3) for each COL find dword refs in .rdata (0xC00000..0xD80000)
out = []
colset = {}
for c, ptd in cols.items():
    colset.setdefault(ptd, []).append(c)
for ptd, cs in colset.items():
    nm = td[ptd][0]
    if sub and sub not in nm.lower():
        continue
    for c in cs:
        pat = struct.pack("<I", c)
        start = 0
        hits = []
        while True:
            i = buf.find(pat, start)
            if i < 0:
                break
            start = i + 1
            hits.append(VA + i)
        print("%-58s col 0x%08X vt=%s" % (nm, c, ",".join("0x%08X" % h for h in hits)))
