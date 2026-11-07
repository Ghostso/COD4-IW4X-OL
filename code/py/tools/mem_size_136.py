#!/usr/bin/env python3
"""列出 MEMORY.md 各条目的字节数(只读)."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
lines = io.open(P, encoding="utf-8").read().split("\n")
tot = 0
rows = []
for i, ln in enumerate(lines, 1):
    b = len(ln.encode("utf-8"))
    tot += b + 1
    if ln.startswith("- ["):
        rows.append((b, i, ln[:56]))
print("总字节 %d ; 条目数 %d" % (tot, len(rows)))
for b, i, head in sorted(rows, reverse=True)[:16]:
    print("%6d  L%-3d %s" % (b, i, head))
