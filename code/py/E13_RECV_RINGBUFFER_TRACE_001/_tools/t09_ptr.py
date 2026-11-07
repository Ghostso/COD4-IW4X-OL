# -*- coding: utf-8 -*-
import sys,struct
sys.path.insert(0,r"D:\BaiduNetdiskDownload\使命召唤OL\E13_RECV_RINGBUFFER_TRACE_001\_tools")
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
for va,name in [(0x1B0430,"recvfromA"),(0x775AB0,"recvfromB"),(0x6029A0,"recvA"),(0x775A50,"recvB"),(0x78772D,"recvC"),(0x6B4DE0,"recvfromC"),(0x784F60,"recvD"),(0x605220,"recvE"),(0x602430,"recvF")]:
    r=ptrscan(va)
    print("0x%06X (%s): dataptr=%d %s"%(va,name,len(r),["%s@0x%X"%(s,x) for s,x in r[:6]]))
