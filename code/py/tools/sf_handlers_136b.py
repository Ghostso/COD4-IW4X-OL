#!/usr/bin/env python3
"""136 卷工具 E: 两种 mangled 形态都收, 并按 View 全量列 SF_Handler, 同时解序号(MSVC base-26).

形态(实测两种):
  A: .?AU<Name>_SF_Handler@?<n>??Init@UiCpp<View>@@...      (无 @ 收尾)
  B: .?AU<Name>_SF_Handler@?<n>@??Init@UiCpp<View>@@...     (有 @ 收尾)
"""
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()

PAT = re.compile(
    rb"\.\?A[VU]([A-Za-z0-9_]+)_SF_Handler@\?([0-9A-Z]+)(@?)\?\?Init@(UiCpp[A-Za-z0-9_]+)@@")
DIG = {chr(ord("0") + i): i for i in range(10)}
DIG.update({chr(ord("A") + i): 10 + i for i in range(16)})


def dec(s):
    v = 0
    for ch in s:
        v = v * 26 + DIG[ch]
    return v


groups = defaultdict(list)
forms = {"A(无@)": 0, "B(有@)": 0}
tot = 0
for m in PAT.finditer(d):
    h = m.group(1).decode("latin1")
    ords = m.group(2).decode("latin1")
    at = m.group(3).decode("latin1")
    view = m.group(4).decode("latin1")
    forms["B(有@)" if at else "A(无@)"] += 1
    groups[view].append((dec(ords), ords, at, h, VA + m.start()))
    tot += 1

print("SF_Handler 总数 %d ; View 数 %d ; 形态 %s" % (tot, len(groups), forms))
for view in sorted(groups):
    lst = sorted(groups[view])
    print("\n== %s : %d 个 ==" % (view, len(lst)))
    for n, ords, at, h, va in lst:
        print("   n=%-3d ?%s%s  0x%08X  %s" % (n, ords, at, va, h))
