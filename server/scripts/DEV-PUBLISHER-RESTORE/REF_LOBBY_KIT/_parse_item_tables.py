# -*- coding: utf-8 -*-
"""解析 r_48110000_0105A000.bin 里的 item 表结构。

已观察到的布局:
    "mp/item_cnc.csv\0" 之后紧跟一串 8 字节值(0x482892180000 这类),
    然后是 "mp/item_asy.csv\0", 又是指针串...

假设: 每个表 = 表名 + 指针数组(指向字符串池里的 ref/name/desc/icon)。
先用"表名 + 后续指针数量"把每张表切出来。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")
NAME_RE = re.compile(rb"mp/item_[a-z0-9_]+\.csv")


def main():
    b = open(P, "rb").read()
    ms = list(NAME_RE.finditer(b))
    print("找到 %d 个 mp/item_*.csv 表名" % len(ms))
    print()
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else min(len(b), m.end() + 0x400)
        seg = b[m.end():end]
        # 数一下紧跟的 8 字节"像指针"的值
        ptrs = []
        k = 0
        while k + 8 <= len(seg) and len(ptrs) < 400:
            v = struct.unpack_from("<Q", seg, k)[0]
            if v == 0:
                break
            if 0x10000000000 <= v <= 0x7FFFFFFFFFFF:
                ptrs.append(v)
                k += 8
            else:
                break
        print("%-26s 表名@0x%08X 段长 %-7d 连续指针 %d"
              % (m.group(0).decode(), m.start(), len(seg), len(ptrs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
