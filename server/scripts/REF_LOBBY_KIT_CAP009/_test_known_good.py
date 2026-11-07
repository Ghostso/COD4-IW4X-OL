# -*- coding: utf-8 -*-
"""决定性测试: 已知成功入库的 sku=32223 -> Item=18481。

如果运行时记录里 sku=32223 的 +0x14 == 18481, 那 +0x14 就是物品 ID,
整套映射成立。否则说明客户端物品 ID 与 exe/库存 编号不同。
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
STRIDE = 0x60


def main():
    for sku in (32223, 32225, 30887, 32229):
        pat = struct.pack("<I", sku)
        hits = []
        for fn in sorted(os.listdir(MEMDIR)):
            p = os.path.join(MEMDIR, fn)
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
                if i + STRIDE <= len(b):
                    f = [struct.unpack_from("<I", b, i + k)[0]
                         for k in range(0, STRIDE, 4)]
                    if f[1] == 0 and f[4] == 0:
                        hits.append((fn, i, f))
                i += 4
        print("=" * 72)
        print("sku=%d  clean hits=%d" % (sku, len(hits)))
        for fn, i, f in hits[:6]:
            print("  %s 0x%08X  %s" % (fn, i, " ".join("%08X" % v for v in f[:10])))
            print("      +0x08=%-8d +0x0C=%-8d +0x14=%-8d +0x1C=%d"
                  % (f[2], f[3], f[5], f[7]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
