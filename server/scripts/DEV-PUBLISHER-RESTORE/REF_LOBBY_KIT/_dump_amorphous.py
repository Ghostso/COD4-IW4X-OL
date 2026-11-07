# -*- coding: utf-8 -*-
"""深挖 pcb_amorphous01 附近的结构 —— 用户说默认背景叫"抽象-凝烟"。

amorphous = 抽象。所以 pcb_amorphous01 就是那件默认背景。
目标: 找到 ref 旁边的 item ID。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, "mem_linear", "r_48110000_0105A000.bin")
KEYS = [b"pcb_amorphous01", b"pcb_default", b"pct_default",
        b"pct_rookie", b"bdg_default", b"pcb_abstract"]


def main():
    b = open(P, "rb").read()
    for key in KEYS:
        i = b.find(key)
        print("=" * 78)
        if i < 0:
            print("%s: 没找到" % key.decode())
            continue
        print("%s @0x%X" % (key.decode(), i))
        # 前后的可打印串
        lo = max(0, i - 0x100)
        hi = min(len(b), i + 0x140)
        strs = re.findall(rb"[ -~]{3,100}", b[lo:hi])
        print("  附近字符串:")
        for s in strs[:24]:
            print("    %s" % s.decode("latin1"))
        # 前后的 u32
        print("  附近 u32:")
        for o in range(lo, hi - 3, 4):
            v = struct.unpack_from("<I", b, o)[0]
            if v and 1 <= v <= 500000:
                print("    @0x%X (d=%+d) = %d" % (o, o - i, v))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
