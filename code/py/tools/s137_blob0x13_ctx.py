#!/usr/bin/env python3
"""s137: corpus-wide 0x13 blob scan: which svc/task, first byte, length, header shape."""
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

ctx = collections.Counter()
lead = collections.Counter()
for r in recs:
    for d in blobs(bytes.fromhex(r["payload"])):
        ok = len(d) >= 4 and struct.unpack_from("<I", d, 0)[0] == len(d) - 4
        ctx[(r["svc"], r["task"], ok, d[4] if len(d) > 4 else None)] += 1
        lead[(r["svc"], r["task"], d[4] if len(d) > 4 else None)] += 1

print("### 0x13 blob by (svc,task, firstbyte-of-inner):")
for k, c in lead.most_common(40):
    print("   svc=%-4s task=%-4s lead=%-4s : %d" % (k[0], k[1], k[2] if k[2] is None else "0x%02X" % k[2], c))
print()
print("### inner first byte overall:")
fb = collections.Counter()
for r in recs:
    for d in blobs(bytes.fromhex(r["payload"])):
        if len(d) > 4: fb[d[4]] += 1
print("  ", [(hex(k), v) for k, v in fb.most_common()])
print()
print("### inner length histogram for lead==0x02:")
lh = collections.Counter()
for r in recs:
    for d in blobs(bytes.fromhex(r["payload"])):
        if len(d) > 4 and d[4] == 0x02:
            lh[(r["svc"], r["task"], len(d) - 4)] += 1
print("  ", sorted(lh.items())[:60])
