# -*- coding: utf-8 -*-
import sys,pefile
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
C=pefile.PE(p,fast_load=False)
mp={}
for e in getattr(C,"DIRECTORY_ENTRY_IMPORT",[]):
    dll=e.dll.decode(errors="replace")
    for imp in e.imports:
        nm=imp.name.decode(errors="replace") if imp.name else "ord_%d"%imp.ordinal
        mp[imp.address]=(dll,nm)
for va in (0xbae1c0,0xbae500,0xbae504):
    print("  0x%X %s"%(va,mp.get(va,"(none)")))
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001\_tools")
from pe_helper import PE
C2=PE(p)
for va in (0xC9FC1C,0xC9FC0C,0xC9FC00):
    b=C2.bytes_rva(va-C2.IB,80)
    print("  0x%X %r"%(va,b.split(b"\0")[0] if b else None))
