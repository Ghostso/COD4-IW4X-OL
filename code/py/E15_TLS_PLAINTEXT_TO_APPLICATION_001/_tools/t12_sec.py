# -*- coding: utf-8 -*-
import sys,re
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E15_TLS_PLAINTEXT_TO_APPLICATION_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
for sec in C.pe.sections:
    print("%-8s rva=0x%-9X vsize=0x%-9X raw=0x%-9X rawsize=0x%X"%(sec.Name.rstrip(b'\0').decode(errors='replace'),sec.VirtualAddress,sec.Misc_VirtualSize,sec.PointerToRawData,sec.SizeOfRawData))
print()
for va in (0xD28CA0,0xC5B440,0xC37CD4,0xC383FC,0xC38450,0xC38934):
    b=C.bytes_rva(va-C.IB,80)
    print("  0x%X %r"%(va,b.split(b"\0")[0] if b else None))
