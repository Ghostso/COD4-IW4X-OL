# -*- coding: utf-8 -*-
"""找默认名片那套(pcb_default / pct_default / bdg_default)的 item ID。

用户实测: 游戏里只有自带的一套 ——
    背景 "抽象-凝烟"   称号 "新兵"   徽章 "热血战场3"

如果默认那套的 item ID 出现在原始 7 件小仓库里, 映射就通了。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
KEYS = [b"pcb_default", b"pct_default", b"bdg_default", b"pci_default",
        b"pcf_default", b"pcb_amorphous01", b"PLAYERCARDS_PCB_DEFAULT_NAME"]
ORIG7 = [10007, 26666, 27724, 27725, 27720, 11016, 11722]


def main():
    for key in KEYS:
        print("=" * 74)
        print("KEY %s" % key.decode())
        n = 0
        for fn in sorted(os.listdir(MEMDIR)):
            p = os.path.join(MEMDIR, fn)
            if not os.path.isfile(p):
                continue
            try:
                b = open(p, "rb").read()
            except Exception:
                continue
            i = b.find(key)
            if i < 0:
                continue
            n += 1
            if n > 3:
                break
            print("  %s @0x%X" % (fn, i))
            # 前 0x60 / 后 0x80 的 u32, 标出命中 ORIG7 的
            lo = max(0, i - 0x60)
            hi = min(len(b), i + 0x80)
            for o in range(lo, hi - 3, 4):
                v = struct.unpack_from("<I", b, o)[0]
                tag = ""
                if v in ORIG7:
                    tag = "  <<< 原始7件之一!"
                if 1 <= v <= 500000:
                    print("     0x%X (d=%+d) = %-8d%s" % (o, o - i, v, tag))
        if n == 0:
            print("  (内存里没有)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
