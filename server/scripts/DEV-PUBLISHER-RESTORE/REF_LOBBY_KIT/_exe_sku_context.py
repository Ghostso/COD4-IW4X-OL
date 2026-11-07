# -*- coding: utf-8 -*-
"""在客户端 exe 里, 打印用户点过的 SKU 附近的原始数据。

目的: 找 SKU -> Item 的映射表(如果它就在 exe 里)。
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(os.path.dirname(ROOT),
                    "run_codol_001", "sandbox_datafix_20260929",
                    "codoMP_client_shipRetail.exe")
UNKNOWN = os.path.join(ROOT, "unknown_skus.txt")


def clicked_skus():
    out = []
    for line in open(UNKNOWN, "r", encoding="utf-8", errors="replace"):
        m = re.match(r"\s*(\d+)", line)
        if m:
            out.append(int(m.group(1)))
    return sorted(set(out))


def main():
    b = open(GAME, "rb").read()
    print("exe=%s size=%d" % (GAME, len(b)))
    skus = clicked_skus()
    present = []
    for s in skus:
        off = b.find(struct.pack("<I", s))
        if off >= 0:
            present.append((s, off))
    print("clicked=%d, present=%d" % (len(skus), len(present)))
    print()
    for s, off in present[:16]:
        print("=" * 70)
        print("sku=%d off=0x%X" % (s, off))
        lo = max(0, off - 0x40)
        hi = min(len(b), off + 0x60)
        for o in range(lo, hi, 16):
            u = [struct.unpack_from("<I", b, o + k)[0] for k in range(0, 16, 4)]
            mark = " <==" if o <= off < o + 16 else ""
            print("  %08X  %s%s" % (o, " ".join("%08X" % v for v in u), mark))
    return 0


if __name__ == "__main__":
    sys.exit(main())
