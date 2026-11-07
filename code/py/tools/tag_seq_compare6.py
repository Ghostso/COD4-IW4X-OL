#!/usr/bin/env python3
"""用 v6 提取器比对 ser/der 标签序列。"""
import subprocess
import sys
from collections import Counter

out = subprocess.run(
    [sys.executable, "-I", "tools/serialize_extract6.py", "--tags"],
    capture_output=True, text=True, encoding="utf-8").stdout
m = {}
for line in out.splitlines():
    parts = line.split()
    if len(parts) < 3:
        continue
    cls, direction = parts[0], parts[1]
    tags = parts[2:]
    m.setdefault(cls, {})[direction] = tags
same = diff = empty = 0
for cls, d in m.items():
    s = d.get("ser")
    r = d.get("der")
    if not s or not r:
        empty += 1
        continue
    if s == r:
        same += 1
    else:
        diff += 1
        print("[DIFF] " + cls)
        print("   ser: " + " ".join(s))
        print("   der: " + " ".join(r))
        for i, (a, b) in enumerate(zip(s, r)):
            if a != b:
                print("   首个分叉 idx=%d  ser=%s der=%s" % (i, a, b))
                break
        if len(s) != len(r):
            print("   长度 ser=%d der=%d" % (len(s), len(r)))
print("SAME=%d DIFF=%d EMPTY=%d" % (same, diff, empty))
