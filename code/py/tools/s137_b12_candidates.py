#!/usr/bin/env python3
"""s137 B12/B13 full-corpus statistical analysis."""
import json, struct, collections, math

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, "r", encoding="utf-8"))
if isinstance(recs, dict):
    recs = recs.get("records") or recs.get("data") or list(recs.values())
FIXED = {0x01: 1, 0x03: 1, 0x06: 2, 0x07: 4, 0x08: 4, 0x09: 8, 0x0a: 8}

def blobs(payload):
    out = []; i = 0; n = len(payload)
    while i < n:
        t = payload[i]; i += 1
        if t == 0x00: continue
        if t == 0x10:
            j = payload.find(b"\x00", i)
            if j < 0: break
            i = j + 1; continue
        if t in FIXED: i += FIXED[t]; continue
        if t in (0x13, 0x6b, 0x6c):
            if i >= n or payload[i] != 0x08: break
            i += 1
            if i + 4 > n: break
            ln = struct.unpack_from("<I", payload, i)[0]; i += 4
            data = payload[i:i+ln]; i += ln
            if t in (0x6b, 0x6c): i += 4
            if t == 0x13: out.append(data)
            continue
        break
    return out

inner = []
for r in recs:
    if r.get("svc") == 11 and r.get("task") == 4:
        for d in blobs(bytes.fromhex(r["payload"])):
            if len(d) >= 4 and struct.unpack_from("<I", d, 0)[0] == len(d) - 4:
                inner.append(d[4:])

def V(x): return x[1] if len(x) > 1 else None
def u32(x,o): return struct.unpack_from("<I", x, o)[0]
def u16(x,o): return struct.unpack_from("<H", x, o)[0]

print("### A. header field candidate formulas (all samples per V)")
CANDS_U32 = {
    "(len-10)<<10": lambda L: (L-10) << 10,
    "(len-8)<<10":  lambda L: (L-8) << 10,
    "(len-10)*4":   lambda L: (L-10) * 4,
    "(len-10)":     lambda L: (L-10),
    "(len-10)*1024":lambda L: (L-10) * 1024,
}
CANDS_U16 = {
    "(len-10)*4": lambda L: (L-10) * 4,
    "(len-10)":   lambda L: (L-10),
    "(len-10)*8": lambda L: (L-10) * 8,
}
for vv in (2,4,6,8):
    xs = [x for x in inner if x and x[0]==2 and V(x)==vv and len(x) >= 10]
    print(" V=0x%02X n=%d" % (vv, len(xs)))
    for name, fn in CANDS_U32.items():
        ok = sum(1 for x in xs if u32(x,4) == fn(len(x)))
        print("    u32@[4:8] == %-14s : %d/%d" % (name, ok, len(xs)))
    for name, fn in CANDS_U16.items():
        ok = sum(1 for x in xs if u16(x,8) == fn(len(x)))
        print("    u16@[8:10]== %-14s : %d/%d" % (name, ok, len(xs)))
    r = collections.Counter((u32(x,4)>>10) for x in xs)
    print("    K=u32>>10 value set:", sorted(r))
    print("    m=u16@8>>11 value set:", sorted(set(u16(x,8)>>11 for x in xs)))
    print("    byte4 always 0:", all(x[4]==0 for x in xs), " byte7/8 zero:", all(x[7]==0 and x[8]==0 for x in xs))
    print("    K vs (len-10):", collections.Counter(( (u32(x,4)>>10), len(x)-10) for x in xs).most_common(8))
