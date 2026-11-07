# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
for va in (0xC5650C,0xC59E20,0xC3F908,0xC39CC0,0xC3D0D2,0xCB3AF8,0xC37244):
    b=C.bytes_rva(va-C.IB,120)
    print("  0x%X %r"%(va,(b.split(b"\0")[0] if b else None)))
