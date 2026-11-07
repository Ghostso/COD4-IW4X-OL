# -*- coding: utf-8 -*-
"""对比 public.result 与 secure.result, 定位差异区。

两者前部应当相同(玩家统计), 差异区就是 public 多出来的内容 ——
很可能是名片/徽章/称号的拥有与装备状态。
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "player_profiles", "public.result")
SEC = os.path.join(ROOT, "player_profiles", "secure.result")


def main():
    pub = open(PUB, "rb").read()
    sec = open(SEC, "rb").read()
    print("public=%d secure=%d" % (len(pub), len(sec)))

    # 找最长公共前缀
    n = min(len(pub), len(sec))
    i = 0
    while i < n and pub[i] == sec[i]:
        i += 1
    print("公共前缀: %d 字节 (0x%X)" % (i, i))
    print()
    print("public 从 %d 开始的 64 字节:" % i)
    print("  " + pub[i:i + 64].hex(" "))
    print("secure 从 %d 开始的 64 字节:" % i)
    print("  " + sec[i:i + 64].hex(" "))
    print()

    # 尾部对齐比较
    j = 0
    while j < n and pub[len(pub) - 1 - j] == sec[len(sec) - 1 - j]:
        j += 1
    print("公共后缀: %d 字节" % j)
    print()
    # 差异区
    print("public[%d:%d] (%d 字节):" % (i, len(pub) - j, len(pub) - j - i))
    print("  " + pub[i:min(i + 128, len(pub) - j)].hex(" "))
    return 0


if __name__ == "__main__":
    sys.exit(main())
