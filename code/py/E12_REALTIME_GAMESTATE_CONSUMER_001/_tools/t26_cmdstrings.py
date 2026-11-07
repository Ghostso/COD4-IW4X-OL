# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
for va in (0xCD61C4,0xCD61D8,0xCD61EC,0xCD6200,0xCD6214,0xCD6228,0xCD623C):
    b=C.bytes_rva(va-C.IB,20)
    print("  0x%X %r"%(va,b.split(b"\0")[0] if b else None))
