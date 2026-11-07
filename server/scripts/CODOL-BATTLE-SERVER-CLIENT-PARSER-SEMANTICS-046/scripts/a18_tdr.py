# -*- coding: utf-8 -*-
import sys, os, struct, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
IB=C.IB
print("=== all 'tdr' / 'TDR' related strings in image ===")
pat=re.compile(rb"[ -~]{4,}")
for m in pat.finditer(C._img):
    st=m.group().decode("latin1")
    if re.search(r"(?i)(tdr|lib_src|net-buffer|host-buffer|sizeinfo|versionindicator)", st):
        print("  0x%08X %r"%(m.start(), st))
