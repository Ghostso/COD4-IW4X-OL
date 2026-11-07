# -*- coding: utf-8 -*-
"""016: list MSVC RTTI type descriptors, optionally filtered."""
import re, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _015_lib import BASE, DATA, END, cstr

needles = [s.lower() for s in sys.argv[1:]]
pat = re.compile(rb"\.\?A[VU][\x20-\x7e]{1,240}?@@")
rows = []
for m in pat.finditer(DATA):
    name = m.group().decode("ascii")
    if needles and not any(n in name.lower() for n in needles):
        continue
    rows.append((BASE + m.start(), name))
print("type descriptors: %d" % len(rows))
for va, name in rows:
    print("0x%08X  %s" % (va, name))
