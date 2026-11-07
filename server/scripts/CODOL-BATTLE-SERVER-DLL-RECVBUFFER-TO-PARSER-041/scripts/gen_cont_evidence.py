# -*- coding: utf-8 -*-
import sys, os, io, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
import pefile
EV=C.EV
def tgt15(ins):
    m=re.search(r"\[(0x[0-9a-f]+)\]",ins.op_str); return int(m.group(1),16) if m else None
ordmap={}
q=pefile.PE(r"C:\Windows\SysWOW64\ws2_32.dll", fast_load=False)
for e in q.DIRECTORY_ENTRY_EXPORT.symbols:
    if e.name: ordmap[e.ordinal]=e.name.decode()
def slot(r):
    v=rd32(r)
    if not v: return None
    if v&0x80000000: return ordmap.get(v&0xffff,"ord%d"%(v&0xffff))
    hn=read_hintname(v); return hn[1].decode("latin1") if hn else "?"
want=["WSASocketW","WSASocketA","socket","accept","WSAAccept","bind","connect","listen"]
L=["RVA\tSECTION\tAPI\tSLOT_VA\tREGION_ATTRIBUTION"]
def attrib(rva):
    if 0x235000<=rva<0x240000: return "041 PING cluster (ICMP)"
    if 0x2D0000<=rva<0x2F0000: return "OpenSSL (crypto/bio)"
    if 0x420000<=rva<0x440000: return "libcurl"
    if 0x640000<=rva<0x680000: return "libcurl"
    return "unclassified"
for i in scan_ff15():
    t=tgt15(i)
    if t is None: continue
    tr=t-IB
    if 0xB02000<=tr<0xB07000:
        nm=slot(tr)
        if nm in want:
            rva=i.address-IB
            L.append("0x%06X\t%s\t%s\t0x%08X\t%s"%(rva,sec_of_rva(rva),nm,t,attrib(rva)))
io.open(os.path.join(EV,"continued_transport_search.tsv"),"w",encoding="utf-8",newline="").write("\n".join(L)+"\n")
print("\n".join(L))
