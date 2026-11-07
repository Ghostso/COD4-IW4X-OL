#!/usr/bin/env python3
"""列全部条目(只读)."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"
lines = io.open(P, encoding="utf-8").read().split("\n")
print("总字节 %d ; 行数 %d" % (len("\n".join(lines).encode("utf-8")), len(lines)))
for i, ln in enumerate(lines, 1):
    b = len(ln.encode("utf-8"))
    if ln.startswith("- ["):
        print("%6d  L%-3d %s" % (b, i, ln[:70]))
    elif ln.strip():
        print("%6d  L%-3d %s" % (b, i, ln[:70]))
