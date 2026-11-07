# -*- coding: utf-8 -*-
"""在全部内存区里搜这些失败 SKU, 看它们出现在什么数据结构里。"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(ROOT, "mem_linear")
SKUS = (48, 1981, 1011, 15827, 19621, 31173, 31374, 31819, 41314)


def main():
    for sku in SKUS:
        pat = struct.pack("<I", sku)
        hits = []
        for fn in sorted(os.listdir(MEM)):
            p = os.path.join(MEM, fn)
            if not os.path.isfile(p):
                continue
            try:
                b = open(p, "rb").read()
            except Exception:
                continue
            i = 0
            while True:
                i = b.find(pat, i)
                if i < 0:
                    break
                hits.append((fn, i))
                i += 4
                if len(hits) > 40:
                    break
        print("=== sku %d: %d 处" % (sku, len(hits)))
        seen = set()
        for fn, i in hits[:8]:
            if fn in seen:
                continue
            seen.add(fn)
            b = open(os.path.join(MEM, fn), "rb").read()
            # 看前 8 个 u32
            ctx = [struct.unpack_from("<I", b, i + k)[0]
                   for k in range(-4, 20, 4) if 0 <= i + k <= len(b) - 4]
            print("   %s @0x%X  上下文 %s" % (fn, i, ctx))
    return 0


if __name__ == "__main__":
    sys.exit(main())
