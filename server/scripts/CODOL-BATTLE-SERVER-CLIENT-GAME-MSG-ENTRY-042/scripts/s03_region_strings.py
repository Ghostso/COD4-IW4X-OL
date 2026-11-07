# -*- coding: utf-8 -*-
"""Attribute .text network clusters by their .rdata/.data string references. Read-only."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dll_common as C

def in_rdata(r):
    return 0x743000 <= r < 0xb02000

def get_ascii(r, maxlen=120):
    o = C.rva2off(r)
    if o is None: return None
    e = C._b.find(b"\0", o, o+maxlen)
    if e < 0 or e-o < 3: return None
    return C._b[o:e].decode("latin1")

def get_u16(r, maxlen=120):
    o = C.rva2off(r)
    if o is None: return None
    e = o
    while e+2 <= o+maxlen and C._b[e:e+2] != b"\0\0":
        if C._b[e+1] != 0: return None
        e += 2
    if e-o < 6: return None
    return C._b[o:e].decode("utf-16-le", "replace")

def scan_region(lo, hi):
    hits = []
    for ins in C.dis_range(lo, hi):
        rva = ins.address - C.IB
        for tok in ins.op_str.replace("["," ").replace("]"," ").replace(","," ").split():
            if not tok.startswith("0x"): continue
            try: v = int(tok,16)
            except Exception: continue
            if 0x10000000 <= v < 0x20000000:
                r = v - C.IB
                if in_rdata(r):
                    s = get_ascii(r) or get_u16(r)
                    if s: hits.append((rva, hex(r), s))
    return hits

regions = {
 "ping_0x23":    (0x235000, 0x236200),
 "openssl_0x2d": (0x2D9000, 0x2DA000),
 "cluster_0x41": (0x410000, 0x420000),
 "libcurl_0x42": (0x420000, 0x430000),
 "cluster_0x43": (0x430000, 0x440000),
 "cluster_0x44": (0x440000, 0x450000),
 "cluster_0x51": (0x510000, 0x520000),
 "cluster_0x64": (0x640000, 0x650000),
 "cluster_0x65": (0x650000, 0x660000),
 "cluster_0x66": (0x660000, 0x670000),
 "cluster_0x67": (0x670000, 0x680000),
 "cluster_0x68": (0x680000, 0x690000),
}
out = []
for name,(lo,hi) in regions.items():
    hits = scan_region(lo,hi)
    seen=set(); strs=[]
    for rva,tgt,s in hits:
        if (tgt,s) in seen: continue
        seen.add((tgt,s)); strs.append((rva,tgt,s))
    out.append("### %s  (%d distinct string refs)" % (name, len(strs)))
    for rva,tgt,s in strs[:70]:
        out.append("  %08x %-40s %s" % (rva, tgt, s[:110]))
    out.append("")
open(os.path.join(C.EV,"region_string_attribution.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("wrote region_string_attribution.txt (%d blocks)" % len(regions))
