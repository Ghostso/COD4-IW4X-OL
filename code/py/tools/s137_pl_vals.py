#!/usr/bin/env python3
"""137 R1a: all 'playlist N' values in corpus 6/14 (and other svc)."""
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

C = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\corpus\corpus.json"
data = json.load(open(C, encoding="utf-8"))
print("records:", len(data))
from collections import Counter
vals = Counter()
lines = Counter()
for r in data:
    p = bytes.fromhex(r["payload"])
    try:
        t = p.decode("latin1")
    except Exception:
        continue
    for m in re.finditer(r"playlist (\d+)", t):
        vals[int(m.group(1))] += 1
        # capture surrounding mmstart
    if "mmstart" in t and "playlist" in t:
        i = t.find("mmstart")
        lines[t[i:i + 260]] += 1
print("distinct 'playlist N' values:")
for v, n in sorted(vals.items()):
    print("   playlist %-4d  x%d" % (v, n))
print()
print("distinct mmstart-with-playlist lines: %d" % len(lines))
for s, n in lines.most_common(12):
    print("   x%-3d %r" % (n, s))
