# -*- coding: utf-8 -*-
import sys, os, struct
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import _c046 as C
for lo,hi,nm in [(0x87BA40,0x87BA50,"0x87BA40 send-prim?"),
                 (0x87BFF0,0x87C010,"0x87BFF0 pkg-lookup?"),
                 (0x87C110,0x87C200,"0x87C110 dec1"),
                 (0x87D5A0,0x87D6A0,"0x87D5A0 dec2 head")]:
    print(C.dump(lo,hi,nm)); print()
