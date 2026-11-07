#!/usr/bin/env python3
"""135 卷工具 H: 用"统一分批函数序言"全量普查分批函数族.

分批函数序言(实证):
  57        push edi
  8b f8     mov edi, eax        <- eax 由调用者放入(= &Container)
  56        push esi
  e8 ........ call <第一个注册器>

即 CC CC | 57 8B F8 56 E8

同时:
 - 报告 0x6AEBD0 / 0x728350 是否在 as_regfns_v2.json(828) 里
 - 报告每个分批函数的第一个 E8 目标
"""
import json
import re
import struct
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

E = r"E:\codol_re\client_image_20261027.bin"
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\tools"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)

PAT = re.compile(rb"\x57\x8b\xf8\x56\xe8(....)")
hits = []
for m in PAT.finditer(d):
    i = m.start()
    # 入口前必须是 cc cc (或有界)
    pre_cc = i >= 2 and d[i - 1] == 0xCC and d[i - 2] == 0xCC
    rel = struct.unpack("<i", m.group(1))[0]
    first = VA + i + 5 + 5 + rel
    hits.append((VA + i, first, pre_cc))

print("`57 8b f8 56 e8` 全镜像命中 %d 处" % len(hits))
cc_first = [h for h in hits if h[2]]
print("其中入口前为 cc cc 的: %d" % len(cc_first))
print()
regs = set(json.load(open(OUT + r"\as_regfns_v2.json")))
print("as_regfns_v2.json 里:")
for t in (0x6AEBD0, 0x728350, 0x5D43B0, 0x728380, 0x5D2E00):
    print("   0x%08X : %s" % (t, "在" if t in regs else "不在"))
print()
print("-- 分批函数(cc cc 前导) 及第一个注册器 --")
for va, first, _ in cc_first:
    print("   0x%08X  -> 首call 0x%08X  %s" % (
        va, first, "(=注册器)" if first in regs else "(非注册器)"))
