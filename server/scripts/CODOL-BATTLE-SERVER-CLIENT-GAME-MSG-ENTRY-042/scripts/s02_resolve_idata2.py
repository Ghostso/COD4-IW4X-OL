# -*- coding: utf-8 -*-
"""Resolve the hidden .idata2 import table (anchor 0xB02000, 768 slots) and
enumerate every FF15 call site mapped to its API. Read-only."""
import sys, os, json, struct, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C

IAT_BASE = 0xB02000
N_SLOTS  = 0xC00 // 4

def read_hintname(rva):
    o = C.rva2off(rva)
    if o is None: return None
    e = C._b.find(b"\0", o+2, o+2+256)
    if e < 0: e = o+2+256
    return C._b[o+2:e].decode("latin1")

# ws2_32/wsock32 ordinal -> name from the local system DLLs (read-only, non-target)
import pefile
def export_table(path):
    t={}
    try:
        p=pefile.PE(path, fast_load=False)
        if hasattr(p,"DIRECTORY_ENTRY_EXPORT"):
            for e in p.DIRECTORY_ENTRY_EXPORT.symbols:
                if e.name: t[e.ordinal]=e.name.decode("latin1")
    except Exception: pass
    return t
WS2_ORD = export_table(r"C:\Windows\SysWOW64\ws2_32.dll")
WSK_ORD = export_table(r"C:\Windows\SysWOW64\wsock32.dll")

slots = {}
for k in range(N_SLOTS):
    sr = IAT_BASE + 4*k
    v = C.rd32(sr)
    if not v: 
        slots[sr] = ("NULL","","")
        continue
    if v & 0x80000000:
        ordv = v & 0xffff
        nm = WS2_ORD.get(ordv) or WSK_ORD.get(ordv) or ("ord_%d"%ordv)
        slots[sr] = ("ORDINAL", nm, ordv)
    else:
        nm = read_hintname(v) or "?"
        slots[sr] = ("NAME", nm, None)

named = {sr:v for sr,v in slots.items() if v[0]!="NULL"}
print("resolved non-null slots:", len(named))

# enumerate FF15
ff = C.scan_ff15()
def slot_of(ins):
    m=re.search(r"\[(0x[0-9a-f]+)\]", ins.op_str)
    return (int(m.group(1),16)-C.IB) if m else None
rows=[]
for ins in ff:
    sr=slot_of(ins)
    if sr in named:
        kind,nm,ordv = named[sr]
        rows.append((ins.address-C.IB, sr, nm, kind, ordv, C.sec_of_rva(ins.address-C.IB)))
print("FF15 sites resolving into .idata2:", len(rows))

# classify by API
cnt=collections.Counter(r[2] for r in rows)
NET = {"recv","recvfrom","WSARecv","WSARecvFrom","select","WSAPoll","WSAEventSelect",
       "WSAEnumNetworkEvents","WSAWaitForMultipleEvents","WSASocketW","WSASocketA","socket",
       "connect","bind","listen","accept","send","sendto","WSASend","WSASendTo","ioctlsocket",
       "WSAIoctl","closesocket","shutdown"}
net_rows=[r for r in rows if r[2] in NET]
print("NET call sites:", len(net_rows))
for k,v in collections.Counter(r[2] for r in net_rows).most_common():
    print("  %-28s %d"%(k,v))

# region clustering: group net callsites by 64KB region
reg=collections.Counter((r[0]>>16) for r in net_rows)
print("\nnet callsites by 64KB region:")
for k,v in sorted(reg.items()):
    print("  0x%02x0000-0x%02xffff : %d"%(k,k,v))

out=["RVA\tSLOT_RVA\tAPI\tKIND\tORDINAL\tSECTION"]
for rva,sr,nm,kind,ordv,sec in sorted(net_rows):
    out.append("%08x\t%08x\t%s\t%s\t%s\t%s"%(rva,sr,nm,kind,(ordv if ordv is not None else ""),sec))
open(os.path.join(C.EV,"net_api_callsites.tsv"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")

# also dump ALL resolved FF15 to a file for the record
allout=["RVA\tSLOT_RVA\tAPI\tKIND\tORDINAL\tSECTION"]
for rva,sr,nm,kind,ordv,sec in sorted(rows):
    allout.append("%08x\t%08x\t%s\t%s\t%s\t%s"%(rva,sr,nm,kind,(ordv if ordv is not None else ""),sec))
open(os.path.join(C.EV,"all_idata2_calls.tsv"),"w",encoding="utf-8",newline="").write("\n".join(allout)+"\n")
print("\nwrote net_api_callsites.tsv + all_idata2_calls.tsv")
