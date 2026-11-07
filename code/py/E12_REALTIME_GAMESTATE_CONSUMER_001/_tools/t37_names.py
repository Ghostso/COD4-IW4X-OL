# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
vas=[0xCD6184,0xCD6188,0xCD618C,0xCD6190,0xCD6194,0xCD6198,0xCD619C,0xCD61A0,0xCD61A4,0xCD61A8,0xCD61AC,0xCD61B0,0xCD61B4,0xCD61B8,0xCD61BC,0xCD61C0,0xCD61C4,0xCD61D8,0xCD61EC,0xCD6200]
for va in vas:
    b=C.bytes_rva(va-C.IB,24)
    print("  0x%X %r"%(va,b.split(b"\0")[0] if b else None))
