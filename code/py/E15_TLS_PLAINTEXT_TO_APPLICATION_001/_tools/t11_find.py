# -*- coding: utf-8 -*-
import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
for pat in [rb"down-update\.qq\.com", rb"GET %s HTTP/1\.1", rb"Content-Length", rb"POST request", rb"POST to GET"]:
    print("=== %r ==="%pat)
    for s in C.pe.sections:
        if s.SizeOfRawData==0: continue
        o,_=C.off(s.VirtualAddress); raw=C.d[o:o+s.SizeOfRawData]
        for m in list(re.finditer(re.escape(pat),raw))[:4]:
            va=C.IB+s.VirtualAddress+m.start()
            print("   0x%X sec=%s"%(va,s.Name.rstrip(b'\0').decode(errors='replace')))
            # xrefs
