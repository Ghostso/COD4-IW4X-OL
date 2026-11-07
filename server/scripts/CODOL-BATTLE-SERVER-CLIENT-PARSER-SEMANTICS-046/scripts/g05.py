# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
for nm,t in [("0x879AC0",0x879AC0),("0x87ED70",0x87ED70),("0x87EDB0",0x87EDB0),("0x87BFF0",0x87BFF0),("0x87BFD0",0x87BFD0)]:
    cs=C.e8_callers(t); print("%-10s %d callers: %s"%(nm,len(cs),", ".join("0x%X"%a for a,_ in cs)))
print()
print(C.dump(0x879B60,0x879C40))
