# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
b = open(DLL,"rb").read()
targets = {
  0x10231050:"caller-func-start",
  0x10235CD0:"obj-ctor",
  0x10235E00:"recv-body",
  0x102311A0:"func-after",
  0x10231190:"ret4-thunk",
}
for va, label in targets.items():
    pat = struct.pack("<I", va)
    hits = []
    st = 0
    while True:
        j = b.find(pat, st)
        if j < 0: break
        r = off2rva(j)
        hits.append((j, r, sec_of_rva(r) if r else "?"))
        st = j+1
    print("%s  VA=0x%08X  hits=%d" % (label, va, len(hits)))
    for j, r, s in hits[:20]:
        print("    fileoff=0x%08X rva=%s sec=%s" % (j, hex(r) if r else None, s))
