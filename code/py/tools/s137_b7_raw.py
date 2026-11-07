#!/usr/bin/env python3
"""B7: dump 每个 SF_Handler RTTI 全串 + 前后邻串."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

HEAD = re.compile(rb"\.\?AU([A-Za-z0-9_]+)_SF_Handler@")


def cstr(f, maxlen=400):
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    return d[f:e].decode("latin1")


def prev_str(start):  # 前一个 null-terminated 串起点
    p = d.rfind(b"\x00", 0, start)
    return p + 1


for m in HEAD.finditer(d):
    f = m.start()
    s = cstr(f)
    if s is None:
        continue
    ps = prev_str(f)
    print("VA=%08X len=%d" % (VA + f, len(s)))
    print("   RAW : %s" % s)
    print("   BYTES:", " ".join("%02x" % c for c in d[f:f + len(s) + 1]))
    print()
