#!/usr/bin/env python3
"""136 卷工具 C: 按关键字列出 RTTI 雷名(找 GFx/Scaleform/AS 接口类的真名)."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
KW = sys.argv[1:] or ["Scaleform", "GFx", "ExternalInterface", "FsCommand",
                      "AS3", "Interpreter", "Amp", "FunctionHandler"]

names = {}
for m in re.finditer(rb"\.\?A[VU][A-Za-z0-9_@?$<>,\-]{2,120}@@", d):
    names[VA + m.start()] = m.group().decode("latin1")

print("RTTI 雷名总数 %d" % len(names))
for kw in KW:
    hit = [(va, nm) for va, nm in names.items() if kw.lower() in nm.lower()]
    print("\n== 关键字 '%s' : %d 个 ==" % (kw, len(hit)))
    for va, nm in sorted(hit)[:60]:
        print("   0x%08X  %s" % (va, nm))
