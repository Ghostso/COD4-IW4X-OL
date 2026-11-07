# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
for lo,hi,nm in [(0x87ED70,0x87EDB0,"0x87ED70"),(0x87EDB0,0x87EE10,"0x87EDB0"),
                 (0x879AC0,0x879B60,"0x879AC0 head")]:
    print(C.dump(lo,hi,nm)); print()
