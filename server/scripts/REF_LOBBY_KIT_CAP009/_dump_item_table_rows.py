# -*- coding: utf-8 -*-
"""dump r_48110000_0105A000.bin 里 mp/item_*.csv 之后的实际数据区。

之前看到表名后跟一串 8 字节值(0x482892180000 这类) —— 那些是
ActionScript 的字符串指针。真正的"行数据"可能在别处。

这里: 找表名之后的**连续小整数数组**, 那才是 itemID。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")
NAME_RE = re.compile(rb"mp/item_[a-z0-9_]+\.csv")


def scan_ints(seg, label):
    """找 seg 里长度 >= 8 的连续 u32 小整数序列(1..500000)。"""
    runs = []
    cur = []
    for o in range(0, len(seg) - 3, 4):
        v = struct.unpack_from("<I", seg, o)[0]
        if 1 <= v <= 500000:
            cur.append((o, v))
        else:
            if len(cur) >= 8:
                runs.append(cur)
            cur = []
    if len(cur) >= 8:
        runs.append(cur)
    if runs:
        print("  %s: %d 段连续整数" % (label, len(runs)))
        for r in runs[:5]:
            print("     @0x%X 长度 %d: %s"
                  % (r[0][0], len(r), [v for _, v in r[:16]]))
    return runs


def main():
    b = open(P, "rb").read()
    ms = list(NAME_RE.finditer(b))
    print("找到 %d 个表名" % len(ms))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else min(len(b), m.end() + 0x1000)
        seg = b[m.end():end]
        print()
        print("=== %s (段 %d 字节) ===" % (m.group(0).decode(), len(seg)))
        scan_ints(seg, m.group(0).decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
