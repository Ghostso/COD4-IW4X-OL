# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
for nm,t in [("QOSCSPkg factory 0x85D2E0",0x85D2E0),("QOSSSPkg factory?",0x85D1C0),
             ("0x85D430 (QOS pkg->net)",0x85D430),("0x85D3A0 (decode2 pkg)",0x85D3A0),
             ("0x85DAF0",0x85DAF0),("0x85D500",0x85D500),("0x85D5A0",0x85D5A0)]:
    cs=C.e8_callers(t); print("%-30s %d callers: %s"%(nm,len(cs),", ".join("0x%X"%a for a,_ in cs)))
# Also: who calls the tqos net send 0x85D430 / 0x87BA40?
