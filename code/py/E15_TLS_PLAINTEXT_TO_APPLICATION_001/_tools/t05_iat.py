# -*- coding: utf-8 -*-
import sys,pefile
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=pefile.PE(p,fast_load=False); IB=C.OPTIONAL_HEADER.ImageBase
mp={}
for e in getattr(C,"DIRECTORY_ENTRY_IMPORT",[]):
    dll=e.dll.decode(errors="replace")
    for imp in e.imports:
        nm=imp.name.decode(errors="replace") if imp.name else "ord_%d"%imp.ordinal
        mp[imp.address]=(dll,nm)
for va in (0xBae354,0xBae3a8,0xBae3a4,0xBae138,0xBae490,0xBae4dc,0xBae50c,0xBae484,0xBae494,0xBae4a0,0xBae508):
    print("  0x%X %s"%(va,mp.get(va,"(not in import table)")))
