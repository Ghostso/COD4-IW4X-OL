# -*- coding: utf-8 -*-
"""分析 public.result —— 名片/徽章/称号的拥有状态很可能在这里。

对比:
  public.result = 33428 字节
  secure.result = 32983 字节
  差值 445 字节
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def find(name):
    for base, dirs, files in os.walk(ROOT):
        for fn in files:
            if fn == name:
                return os.path.join(base, fn)
    return None


def main():
    p = find("public.result")
    s = find("secure.result")
    print("public.result: %s" % p)
    print("secure.result: %s" % s)
    if not p:
        print("没找到 public.result")
        return 1
    b = open(p, "rb").read()
    print("长度: %d" % len(b))
    if s and os.path.exists(s):
        sb = open(s, "rb").read()
        print("secure.result 长度: %d, 差 %d" % (len(sb), len(b) - len(sb)))
    print()
    # 找可打印字符串(可能的 callsign 名)
    import re
    strs = re.findall(rb"[ -~]{4,}", b)
    print("可打印串 %d 个, 前 40:" % len(strs))
    for x in strs[:40]:
        print("  %s" % x.decode("latin1"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
