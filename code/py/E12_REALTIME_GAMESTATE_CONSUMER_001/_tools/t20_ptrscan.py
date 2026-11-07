# -*- coding: utf-8 -*-
import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E12_REALTIME_GAMESTATE_CONSUMER_001\_tools")
from pe_helper import PE
C=PE(r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin")
def ptrscan(va):
    tv=0x400000+va; out=[]
    for s in C.pe.sections:
        if s.SizeOfRawData==0: continue
        o,_=C.off(s.VirtualAddress)
        raw=C.d[o:o+s.SizeOfRawData]
        for i in range(0,max(0,len(raw)-3)):
            if struct.unpack_from("<I",raw,i)[0]==tv:
                out.append((s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress+i))
    return out
for va in (0x34E7C0,0x350170,0x3512A0,0x8F1D0,0x3524F0,0x352570,0x74F090):
    r=ptrscan(va)
    print("0x%06X data ptr refs: %d  %s"%(va,len(r),[("0x%X"%x[1]) for x in r[:6]]))
