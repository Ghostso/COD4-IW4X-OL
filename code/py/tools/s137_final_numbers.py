#!/usr/bin/env python3
"""s137: consolidated numbers for the report."""
import json, struct, collections

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
def K(x): return struct.unpack_from("<I", x, 4)[0] >> 10
def M(x): return struct.unpack_from("<H", x, 8)[0] >> 11
v2 = [x for x in fam if x[1] == 2]
v2b = [x[10:] for x in v2]

# header facts
print("### header facts (all fam 0x02, n=%d)" % len(fam))
print("  byte[2]==0 :", all(x[2]==0 for x in fam), " byte[3]==0 :", all(x[3]==0 for x in fam))
print("  byte[4]==0 :", all(x[4]==0 for x in fam), " byte[7]==0 :", all(x[7]==0 for x in fam), " byte[8]==0 :", all(x[8]==0 for x in fam))
print("  u32@4 %1024==0 :", sum(1 for x in fam if struct.unpack_from('<I',x,4)[0]%1024==0), "/", len(fam))
print("  u16@8 %2048==0 :", sum(1 for x in fam if struct.unpack_from('<H',x,8)[0]%2048==0), "/", len(fam))
print("  byte9 %8==0    :", sum(1 for x in fam if x[9]%8==0), "/", len(fam))
print("  u32@4 == u16@5*256 :", sum(1 for x in fam if struct.unpack_from('<I',x,4)[0] == (struct.unpack_from('<H',x,5)[0]<<8)), "/", len(fam))

# K vs len
print()
print("### K = u32@4>>10  vs B=len-10")
for V in (2,4,6,8):
    xs=[x for x in fam if x[1]==V]
    print("  V=%X: K==B %d/%d ; K values %s" % (V, sum(1 for x in xs if K(x)==len(x)-10), len(xs), sorted(set(K(x) for x in xs))))

# K,M pair table
print()
print("### (K,M) pairs with counts (all V)")
t = collections.Counter((x[1], K(x), M(x)) for x in fam)
for k in sorted(t): print("   V=%X K=%-4d M=%-3d : %d" % (k[0],k[1],k[2],t[k]))
