#!/usr/bin/env python3
"""s138_playlist_blocks: 打印 playlist 文件里指定 playlist 的完整定义块(ascii-safe)。
用法: python -I tools/s138_playlist_blocks.py <playlist_id,...>
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = r"D:\BaiduNetdiskDownload\使命召唤OL\_byte_papers\playlist_plain.txt"
lines = open(P, encoding="latin1").read().splitlines()

want = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "1,10,37,50,123").split(",")]
starts = {}
for i, l in enumerate(lines):
    m = re.match(r"^\s*playlist\s+(\d+)\s*$", l)
    if m:
        starts.setdefault(int(m.group(1)), i)

order = sorted(starts.values())
for pid in want:
    if pid not in starts:
        print("playlist %d NOT FOUND" % pid)
        continue
    i = starts[pid]
    nxt = min([o for o in order if o > i], default=len(lines))
    print("===== playlist %d (lines %d..%d) =====" % (pid, i, nxt - 1))
    for j in range(i, nxt):
        s = lines[j]
        s = s.encode("ascii", "replace").decode("ascii")
        print("%5d %s" % (j, s))
    print()
