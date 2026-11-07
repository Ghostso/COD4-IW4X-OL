# -*- coding: utf-8 -*-
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
def scan_imm32(target_va):
    pat=struct.pack("<I",target_va); hits=[]; i=0; n=len(C._td)
    while i<=n-4:
        j=C._td.find(pat,i)
        if j<0: break
        hits.append(C._text["va"]+j); i=j+1
    return hits
names=[b"CSRecvPkgCount",b"GSRecvPkgCount",b"RecvSuccPkgCount",b"PkgSeq",b"LastRecvPkgSeq",
       b"ServiceID",b"ConproxyID",b"SessionID",b"BusinessPkgCount",b"Heartbeat"]
for nm in names:
    j=C._b.find(nm)
    if j<0: 
        print("%-20s NOTFOUND"%nm.decode()); continue
    r=C.off2rva(j)
    h=scan_imm32(r+C.IB) if r is not None else []
    print("%-20s @%08x  imm32refs=%s"%(nm.decode(), r, [hex(x) for x in h[:12]]))
