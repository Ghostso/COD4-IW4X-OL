# -*- coding: utf-8 -*-
import sys, os, pefile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C
data=C._bex
pe=pefile.PE(data=data, fast_load=False)
SECS=[(s.PointerToRawData, s.PointerToRawData+s.SizeOfRawData, s.VirtualAddress, s.Name.rstrip(b'\0').decode('latin1')) for s in pe.sections]
def sec_of_off(off):
    for raw,rend,va,nm in SECS:
        if raw<=off<rend: return nm, va, raw
    return "?", None, None
def dump(off, n, label):
    nm,va,raw=sec_of_off(off)
    print("### %s  file=%08x section=%s VA=%08x" % (label, off, nm, (va+(off-raw)) if va is not None else 0))
    seg=data[off:off+n]; i=0; cur=bytearray(); st=0
    while i<len(seg):
        c=seg[i]
        if 32<=c<127:
            if not cur: st=i
            cur.append(c)
        else:
            if len(cur)>=2: print("   VA=%08x  %s" % ((va+(off-raw)+st) if va is not None else off+st, cur.decode('latin1')))
            cur=bytearray()
        i+=1
    if cur: print("   VA=%08x  %s" % ((va+(off-raw)+st) if va is not None else off+st, cur.decode('latin1')))
    print()
dump(0x6abf00, 0x300, "net command naming")
dump(0x6abcb0, 0x2c0, "getchallenge/CL_")
dump(0x6b2160, 0x140, "CG_ServerCommand")
dump(0x6a06c0, 0x120, "gamestate/ConfigString")
dump(0x6a0d60, 0x120, "ExpectedNetConfigString")
