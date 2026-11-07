#!/usr/bin/env python3
"""s137: dissection hypotheses for room-family body + B13 counts."""
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
            if len(d) >= 8 and struct.unpack_from("<I", d, 0)[0] == len(d) - 4:
                inner.append(d[4:])
fam = [x for x in inner if x and x[0] == 2]
def u32(x,o): return struct.unpack_from("<I", x, o)[0]
def u16(x,o): return struct.unpack_from("<H", x, o)[0]

# 1. group by (V,K): is body[:K] constant within group?
print("### 1. body[:K] constancy within (V,K) groups")
for V in (2,4,6,8):
    xs = [x for x in fam if x[1]==V]
    g = collections.defaultdict(list)
    for x in xs: g[u32(x,4)>>10].append(x)
    for K, grp in sorted(g.items()):
        pref = set(x[10:10+K] for x in grp) if all(len(x) >= 10+K for x in grp) else None
        if pref is None:
            print("  V=%X K=%-4d n=%-3d body too short for K" % (V,K,len(grp)))
        else:
            print("  V=%X K=%-4d n=%-3d distinct body[:K]=%d  %s" % (V,K,len(grp),len(pref), list(pref)[0].hex() if len(pref)==1 else "(varies)"))

# 2. B13: candidate counts in body vs u16@[5:7]
print()
print("### 2. B13 candidate tests (V=02, n=112)")
xs = [x for x in fam if x[1]==2 and len(x) >= 10]
def nonzero_u32(b):
    return sum(1 for i in range(0, len(b)-3, 4) if u32(b,i) != 0)
def n_u32(b): return len(b)//4
def sane_floats(b):
    c = 0
    for i in range(0, len(b)-3, 4):
        f = struct.unpack_from("<f", b, i)[0]
        if -1e6 <= f <= 1e6 and (f == 0 or abs(f) > 1e-6): c += 1
    return c
tests = {
 'u16@5 == B (bytes)': lambda x,B: u16(x,5) == B,
 'u16@5 == B*4': lambda x,B: u16(x,5) == B*4,
 'u16@5 == B//4 (u32 count)': lambda x,B: u16(x,5) == B//4,
 'u16@5 == nonzero u32 count': lambda x,B: u16(x,5) == nonzero_u32(x[10:]),
 'u16@5 == sane float count': lambda x,B: u16(x,5) == sane_floats(x[10:]),
 'u16@5 == B*8 (bits)': lambda x,B: u16(x,5) == B*8,
 'u16@5 == B*2': lambda x,B: u16(x,5) == B*2,
 'u16@5 == (B//2)*8': lambda x,B: u16(x,5) == (B//2)*8,
}
for name, fn in tests.items():
    ok = sum(1 for x in xs if fn(x, len(x)-10))
    print("   %-32s : %d/%d" % (name, ok, len(xs)))

# 3. body starting field
print()
print("### 3. body first u32 vs K (V=02)")
c = collections.Counter()
for x in xs:
    b = x[10:]; K = u32(x,4)>>10
    if len(b) >= 4:
        c[(K, u32(b,0), u32(b,0)==K)] += 1
for k,v in c.most_common(20):
    print("   K=%-4d body_u32[0]=%-12d equal=%s : %d" % (k[0], k[1], k[2], v))

# 4. division / record-length test: B mod r for r in 1..20 across V
print()
print("### 4. record-length divisibility (how many samples have B % r == 0)")
for V in (2,4,6,8):
    xs2 = [x for x in fam if x[1]==V]
    Bs = [len(x)-10 for x in xs2]
    row = []
    for r in range(1, 17):
        ok = sum(1 for B in Bs if B % r == 0)
        row.append("%d:%d" % (r, ok))
    print("   V=%X n=%d  %s" % (V, len(Bs), " ".join(row)))
