#!/usr/bin/env python3
"""136 卷工具 D: 全量抽取 `<handler>_SF_Handler@?<ord>??Init@UiCpp<View>@@...` 名字,
按 View 分组 —— 这是"每个 View 注册了哪些 Flash 回调"的**权威清单**(名字直接写在数据里)."""
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()

PAT = re.compile(
    rb"\.\?A[VU]([A-Za-z0-9_]+)_SF_Handler@\?([0-9A-Z]+)\?\?Init@(UiCpp[A-Za-z0-9_]+)@@")

groups = defaultdict(list)
allh = []
for m in PAT.finditer(d):
    h = m.group(1).decode("latin1")
    ordv = m.group(2).decode("latin1")
    view = m.group(3).decode("latin1")
    groups[view].append((ordv, h, VA + m.start()))
    allh.append((view, ordv, h))

print("SF_Handler 名字总数 %d ; View 数 %d" % (len(allh), len(groups)))
for view in sorted(groups):
    lst = groups[view]
    print("\n== %s : %d 个 ==" % (view, len(lst)))
    for ordv, h, va in sorted(lst):
        print("   ?%-4s 0x%08X  %s" % (ordv, va, h))
