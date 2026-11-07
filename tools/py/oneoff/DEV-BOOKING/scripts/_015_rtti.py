# -*- coding: utf-8 -*-
"""015: dump MSVC RTTI type descriptors (.?AV...) and their vtables."""
import re
import struct
import sys

sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\DEV-BOOKING\scripts")
from _015_lib import BASE, DATA, END, cstr, direct_callers  # noqa

needle = sys.argv[1].lower() if len(sys.argv) > 1 else None

pat = re.compile(rb"\.\?AV[\x20-\x7e]{1,200}?@@")
rows = []
for m in pat.finditer(DATA):
    name = m.group().decode("ascii")
    if needle and needle not in name.lower():
        continue
    va = BASE + m.start()
    rows.append((va, name))

print("type descriptors: %d" % len(rows))
for va, name in rows:
    # type_info: vftable(4) spare(4) name
    ti = va - 8
    # COL points at type_info: locator = sig(4) offset(4) cd(4) pTypeDescriptor(4)
    cols = []
    pat2 = struct.pack("<I", ti)
    i = DATA.find(pat2)
    while i >= 0:
        col = BASE + i - 0xC  # pTypeDescriptor is the 4th dword of COL
        sig = DATA[i - 0xC: i - 0x8]
        if sig == b"\x00\x00\x00\x00":
            cols.append(col)
        i = DATA.find(pat2, i + 1)
    print("0x%08X  %s   COL=%s" % (va, name, [hex(c) for c in cols]))
