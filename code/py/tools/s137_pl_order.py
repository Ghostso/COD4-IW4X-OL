#!/usr/bin/env python3
"""137: parse playlist order from playlist_plain.txt; list index->playlist."""
import re
import sys

P = (r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt")
txt = open(P, "rb").read().decode("latin1")
order = []
ids = set()
cur = None
meta = {}
lines = txt.splitlines()
for i, ln in enumerate(lines):
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", ln)
    if m:
        cur = int(m.group(1))
        order.append(cur)
        ids.add(cur)
        # look back for @LOGAS comment
        for j in range(i - 1, max(-1, i - 4), -1):
            if "@LOGAS" in lines[j]:
                meta[cur] = lines[j].strip()
                break
    if cur is not None and re.match(r"^\s*map\s+\S", ln):
        pass

print("playlist ids count = %d" % len(order))
print("distinct ids = %d" % len(ids))
print("id 37 in file? ", 37 in ids)
print("min=%d max=%d" % (min(ids), max(ids)))
print()
print("file-order index -> id  (index 30..45):")
for i in range(30, min(46, len(order))):
    print("   num %-3d -> id %-4d  %s" % (i, order[i], meta.get(order[i], "")))
print()
print("full order:")
print(order)
