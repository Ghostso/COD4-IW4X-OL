#!/usr/bin/env python3
"""s137: 列出镜像里所有 dw_* 串 (保留文件避免管道问题)."""
import re
import sys

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
seen = set()
pat = re.compile(sys.argv[1].encode() if len(sys.argv) > 1 else rb"dw_[A-Za-z0-9_]{3,40}")
for m in pat.finditer(d):
    s = m.group().decode("latin1")
    if s not in seen:
        seen.add(s)
        print("0x%08X %s" % (VA + m.start(), s))
