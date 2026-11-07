#!/usr/bin/env python3
"""s137 R3: 解压 71/15 遥测, 找 channel/932/枚举值线索."""
import collections
import json
import re
import sys
import zlib

CORPUS = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
recs = json.load(open(CORPUS, "r", encoding="utf-8"))
RUN = sys.argv[1] if len(sys.argv) > 1 else None

def dec(p):
    for sig in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
        j = p.find(sig)
        if j >= 0:
            try:
                return zlib.decompress(p[j:])
            except Exception:
                return None
    return None

alltext = []
for r in recs:
    if r.get("svc") == 71 and r.get("task") == 15:
        if RUN and r.get("run") != RUN:
            continue
        d = dec(bytes.fromhex(r["payload"]))
        if d:
            alltext.append((r.get("run"), r.get("idx"), d))
print("解压条数: %d (run=%s)" % (len(alltext), RUN))

# 找含 channel 的事件
pat = re.compile(rb"[A-Za-z]*[Cc]hannel[A-Za-z]*")
hits = collections.Counter()
for run, idx, d in alltext:
    for m in pat.finditer(d):
        hits[m.group()] += 1
print("\n含 channel 的 token:", dict(hits))

# 找 932 / 100,108,113,118,123,135,148
for tok in (b"932", b"100", b"108", b"113", b"118", b"123", b"135", b"148", b"1006"):
    n = 0
    samples = []
    for run, idx, d in alltext:
        for m in re.finditer(rb"(?<![0-9])" + tok + rb"(?![0-9])", d):
            n += 1
            if len(samples) < 3:
                lo = max(0, m.start() - 60)
                samples.append(d[lo:m.start() + 60])
    if n:
        print("\n=== token %s : %d ===" % (tok.decode(), n))
        for s in samples:
            print("   ...", s)

# 打印几个含 'Channel' 的事件全文
print("\n=== 含 Channel 的事件片段 ===")
seen = 0
for run, idx, d in alltext:
    if b"hannel" in d or b"932" in d:
        print("--- run=%s idx=%s len=%d" % (run, idx, len(d)))
        print("   ", d[:600])
        seen += 1
        if seen >= 6:
            break
