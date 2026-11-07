# -*- coding: utf-8 -*-
"""分析已抓到的 mem_callsign/callsign_0x71B40000.bin (499712 字节)。

判断它是哪张表, 并看能不能从中恢复出完整的 Callsign 表结构。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(ROOT, "mem_callsign", "callsign_0x71B40000.bin")


def main():
    b = open(CAP, "rb").read()
    print("文件 %d 字节 (0x%X)" % (len(b), len(b)))
    # 可打印串统计
    strs = re.findall(rb"[ -~]{4,}", b)
    print("可打印串 %d 个" % len(strs))
    print()
    print("前 60 个串:")
    for s in strs[:60]:
        print("  %s" % s.decode("latin1"))
    print()
    # 统计前缀分布
    from collections import Counter
    pref = Counter()
    for s in strs:
        t = s.decode("latin1")
        m = re.match(r"([A-Za-z_]+)", t)
        if m:
            pref[m.group(1)] += 1
    print("前缀 top 25:", pref.most_common(25))
    print()
    # 是否像 CSV 表头
    for kw in (b"ref", b"name", b"title", b"TITLE_", b"callsign", b"unlock"):
        print("  含 %-12s : %d 次" % (kw.decode(), b.count(kw)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
