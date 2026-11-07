#!/usr/bin/env python3
"""s137: test 'V!=2 body = [K-byte prefix matching a V=2 body] + tail'."""
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
def u32(x,o): return struct.unpack_from("<I", x, o)[0]

# all V=2 bodies (as byte strings) and their (K)
v2_bodies = set()
v2_by_len = collections.defaultdict(list)
v2_pairs = collections.defaultdict(list)
for x in fam:
    if x[1] == 2:
        b = x[10:]; v2_bodies.add(b); v2_by_len[len(b)].append(b)
        v2_pairs[(u32(x,4)>>10, struct.unpack_from("<H",x,8)[0]>>11)].append(b)

# For V!=2: is body[:K] in v2_bodies?
print("### 'body[:K] is a complete V=2 body' test")
for V in (4,6,8):
    xs = [x for x in fam if x[1] == V]
    hit = 0; tot = 0
    for x in xs:
        K = u32(x,4)>>10; b = x[10:]
        tot += 1
        if len(b) >= K and b[:K] in v2_bodies:
            hit += 1
    print("  V=0x%02X : body[:K] in V2-body-set : %d/%d" % (V, hit, tot))

# Report tail structure for V!=2
print()
print("### for each distinct V!=2 (K,m): prefix-match? + tail head")
seen = set()
for V in (4,6,8):
    for x in sorted(fam, key=lambda t:(t[1], len(t), t)):
        if x[1] != V: continue
        K = u32(x,4)>>10; m = struct.unpack_from("<H",x,8)[0]>>11; b = x[10:]
        key = (V,K,m,len(b))
        if key in seen: continue
        seen.add(key)
        pm = "YES" if (len(b)>=K and b[:K] in v2_bodies) else ("prefix" if any(bb[:K]==b[:K] for bb in v2_bodies if len(bb)>=K) else "no")
        print("  V=%X K=%-3d m=%-2d B=%-4d tail(%d)=%s  match=%s" % (V,K,m,len(b),len(b)-K, b[K:K+12].hex(), pm))

# body first byte >>3 (5-bit tag) distribution
print()
print("### body[0]>>3 (5-bit tag) distribution per V")
for V in (2,4,6,8):
    xs = [x for x in fam if x[1] == V]
    c = collections.Counter((x[10]>>3) if len(x)>10 else None for x in xs)
    print("  V=%X:"%V, sorted(c.items()))
