# -*- coding: utf-8 -*-
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
from _common import *
import pefile
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
# sockets: WSASocketW/A, socket(23), accept/WSAAccept, bind, connect, listen
want={"WSASocketW","WSASocketA","socket","accept","WSAAccept","bind","connect","listen","WSARecv","WSARecvFrom","WSASend"}
ff=scan_ff15()
from collections import Counter
cnt=Counter()
for i in ff:
    t=tgt15(i)
    if t is None: continue
    tr=t-IB
    if 0xB02000<=tr<0xB07000:
        nm=slot(tr)
        if nm in want:
            cnt[nm]+=1
            rva=i.address-IB
            print("0x%06X %-12s slot=0x%08X" % (rva,nm,t))
print("counts:",dict(cnt))
