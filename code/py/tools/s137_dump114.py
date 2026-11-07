#!/usr/bin/env python3
"""s137: dump full 11/4 payloads around the 0x13 blob to see outer context."""
import json, struct, collections, sys

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, "r", encoding="utf-8"))
if isinstance(recs, dict):
    recs = recs.get("records") or recs.get("data") or list(recs.values())

sel = [r for r in recs if r["svc"] == 11 and r["task"] == 4]
print("11/4 records:", len(sel))
# pick a few with different blob leads
picked = []
seen = set()
for r in sel:
    p = bytes.fromhex(r["payload"])
    # find 0x13 08 pattern
    k = p.find(b"\x13\x08")
    if k >= 0 and k + 6 <= len(p):
        ln = struct.unpack_from("<I", p, k + 2)[0]
        lead = p[k+6] if k+6 < len(p) else None
        key = (lead, ln)
        if lead not in seen:
            seen.add(lead)
            picked.append((r, k, ln, lead))
for r, k, ln, lead in picked[:12]:
    p = bytes.fromhex(r["payload"])
    print("=" * 70)
    print("run=%s idx=%s len=%s lead=0x%02X bloblen=%d" % (r.get("run"), r.get("idx"), r.get("len"), lead if lead is not None else -1, ln))
    print("  full payload:", p.hex())
    print("  before 0x13 (offset 0..%d):" % k, p[:k].hex())
    print("  blob region [%d:%d]:" % (k, k+6+ln), p[k:k+6+ln].hex())
    after = p[k+6+ln:]
    print("  after blob:", after.hex())
