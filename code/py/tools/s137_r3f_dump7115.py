#!/usr/bin/env python3
"""s137: 打印某 run 的 71/15 解压全文."""
import json
import sys
import zlib

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, "r", encoding="utf-8"))
RUN = sys.argv[1]

def dec(p):
    for sig in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
        j = p.find(sig)
        if j >= 0:
            try:
                return zlib.decompress(p[j:])
            except Exception:
                return None
    return None

for r in recs:
    if r.get("svc") == 71 and r.get("task") == 15 and r.get("run") == RUN:
        d = dec(bytes.fromhex(r["payload"]))
        print("=" * 70)
        print("idx=%s len=%d" % (r.get("idx"), len(d) if d else -1))
        if d:
            for line in d.replace(b"\r", b"").split(b"\n"):
                if line.strip():
                    print("   ", line[:300])
