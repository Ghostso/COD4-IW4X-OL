# -*- coding: utf-8 -*-
"""在内存转储里找客户端 SKU 目录(item id -> 价格/货币 的映射)。

线索: 客户端点购买时发的 sku id = 241, 242, 31774, 31816, 32223 (见
HANDOFF_20261005_LOBBY_BUGS.md §4.0)。这些 id 来自它**自己那份**目录,
目录在内存里应该以某种结构出现(id 数组, 或 id+price 的记录数组)。

做法: 扫所有转储, 找这些 u32 的**小端**出现位置, 报告密集区。
"""
import os
import re
import struct
import sys

DUMPDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mem_marketplace")

# 客户端实际发过的、且不在 exe 目录里的 SKU id(最可能是"服务端目录"独有)
TARGETS = [241, 242, 31774, 31816]
# 对照组: 已知在 exe 目录里的(应能同时找到)
KNOWN = [32223, 22858]


def scan_file(path):
    try:
        b = open(path, "rb").read()
    except Exception:
        return {}
    found = {}
    for v in TARGETS + KNOWN:
        pat = struct.pack("<I", v)
        hits = []
        i = b.find(pat)
        while i >= 0 and len(hits) < 40:
            hits.append(i)
            i = b.find(pat, i + 1)
        if hits:
            found[v] = hits
    return found


def main():
    files = sorted(os.listdir(DUMPDIR))
    print("转储文件 %d 个" % len(files))
    agg = {}
    for n, fn in enumerate(files):
        if not fn.endswith(".bin"):
            continue
        f = scan_file(os.path.join(DUMPDIR, fn))
        if f:
            agg[fn] = f
        if n % 2000 == 0:
            print("  ...%d/%d" % (n, len(files)))
    print("\n命中文件 %d 个" % len(agg))
    # 先看"同时含多个目标 id"的文件(最有可能是目录结构)
    multi = {k: v for k, v in agg.items() if len(v) >= 2}
    print("含 >=2 个 id 的文件: %d" % len(multi))
    for fn, f in list(multi.items())[:40]:
        print("  %-46s %s" % (fn, {k: len(v) for k, v in sorted(f.items())}))
    if not multi:
        print("  (无 —— 说明目录不是以裸 u32 数组存于这些窗口)")
        print("  单 id 命中的文件(取样):")
        for fn, f in list(agg.items())[:20]:
            print("    %-46s %s" % (fn, {k: len(v) for k, v in sorted(f.items())}))


if __name__ == "__main__":
    main()
