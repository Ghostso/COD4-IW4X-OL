# -*- coding: utf-8 -*-
"""对失败的 SKU, 列出**全部**候选记录(不丢弃冲突项), 逐个看布局。

之前 _build_full_catalog.py 把"item 冲突"的 SKU 整条丢了(628 个),
48/1011/1981 这类小值很可能就是这样被误杀的。
"""
import os
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
MEMDIR = os.path.join(ROOT, "mem_linear")
STRIDE = 0x60
NONE = 0xFFFFFFFF
BAD = (48, 1011, 1981, 15827, 19621, 31173, 31374, 31819, 41314)


def main():
    want = set(BAD)
    cand = {s: [] for s in BAD}
    for fn in sorted(os.listdir(MEMDIR)):
        p = os.path.join(MEMDIR, fn)
        if not os.path.isfile(p):
            continue
        try:
            b = open(p, "rb").read()
        except Exception:
            continue
        for off in range(0, len(b) - STRIDE, 4):
            sku = struct.unpack_from("<I", b, off)[0]
            if sku not in want:
                continue
            f = [struct.unpack_from("<I", b, off + k)[0]
                 for k in range(0, STRIDE, 4)]
            cand[sku].append((fn, off, f))

    for s in BAD:
        c = cand[s]
        print("=" * 78)
        print("SKU %d: %d 条候选" % (s, len(c)))
        # 只看 +0x04==0 的
        clean = [x for x in c if x[2][1] == 0]
        print("  其中 +0x04==0 的: %d 条" % len(clean))
        sig = Counter()
        for fn, off, f in clean:
            sig[(f[2], f[3], f[4], f[5], f[7])] += 1
        for (f08, f0c, f10, f14, f1c), n in sig.most_common(8):
            print("    +08=%-8d +0C=%-8d +10=%-5d +14=%-8d +1C=%-10d x%d"
                  % (f08, f0c, f10, f14, f1c, n))
        # 打印第一条原始
        if clean:
            fn, off, f = clean[0]
            print("  首条: %s @0x%X" % (fn, off))
            print("    " + " ".join("%08X" % v for v in f[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
