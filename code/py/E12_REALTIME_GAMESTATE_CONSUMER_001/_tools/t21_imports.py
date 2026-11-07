# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
import pefile
C=pefile.PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin",fast_load=False)
IB=C.OPTIONAL_HEADER.ImageBase
imports={}
for e in getattr(C,"DIRECTORY_ENTRY_IMPORT",[]):
    dll=e.dll.decode(errors="replace")
    for imp in e.imports:
        nm=imp.name.decode(errors="replace") if imp.name else ("ord_%d"%imp.ordinal)
        imports[(dll,nm)]=imp.address
want=["recvfrom","recv","WSARecv","WSARecvFrom","select","ioctlsocket","WSAGetLastError","closesocket","sendto","send","WSASend","fread","ReadFile","CreateFileA","CreateFileW","fopen"]
print("=== network/file imports ===")
for (dll,nm),addr in sorted(imports.items()):
    if any(w.lower()==nm.lower() for w in want):
        print("  %-16s %-24s IAT VA 0x%X (RVA 0x%X)"%(dll,nm,addr,addr-IB))
