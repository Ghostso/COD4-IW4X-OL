# -*- coding: utf-8 -*-
import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
o,_=C.off(0xC37200)
raw=C.d[o:o+0x200]
for m in re.finditer(rb"[ -~]{6,}",raw):
    print("  0x%X %r"%(C.IB+0xC37200+m.start(), m.group()[:60].decode("latin-1")))
