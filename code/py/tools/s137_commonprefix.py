#!/usr/bin/env python3
"""s137: common-prefix between V!=2 bodies and V=2 bodies; relation to K."""
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

# V=2 bodies grouped by (K, M)
v2 = [x[10:] for x in fam if x[1] == 2]
v2sets = collections.defaultdict(set)
for x in fam:
    if x[1] == 2: v2sets[(K(x), M(x))].add(x[10:])

print("### common prefix of V!=2 body vs best V=2 body, vs K")
res = collections.Counter()
for V in (4,6,8):
    for x in fam:
        if x[1] != V: continue
        b = x[10:]; k = K(x); m = M(x)
        best = 0
        for c in v2:
            n = 0
            while n < min(len(b), len(c)) and b[n] == c[n]: n += 1
            best = max(best, n)
        res[(V, k, m, len(b) - k, best)] += 1
for key in sorted(res):
    V,k,m,tail,best = key
    print("  V=%X K=%-3d m=%-2d tail=%-4d maxCP=%-3d n=%d %s" % (V,k,m,tail,best,res[key], "<-- CP==K" if best==k else ""))

# Also: does V=2 body of (K,M) exist?  do V!=2 samples share (K,M) with V=2?
print()
print("### (K,M) pair overlap between V=2 and V!=2")
v2pairs = set((K(x),M(x)) for x in fam if x[1]==2)
for V in (4,6,8):
    ps = set((K(x),M(x)) for x in fam if x[1]==V)
    print("  V=%X pairs=%s  in V2:%s" % (V, sorted(ps), sorted(ps & v2pairs)))
