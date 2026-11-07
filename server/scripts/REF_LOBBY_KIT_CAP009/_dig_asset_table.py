# -*- coding: utf-8 -*-
"""在 Base.dll 里看 0x239B120 这张资源注册表(stride 0x1C)。"""
import os
import re
import struct
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.abspath(os.path.join(ROOT, "..", "run_codol_001",
                                    "sandbox_datafix_20260929"))
DLL = os.path.join(GAME, "codoMP_client_shipRetailBase.dll")
TABLE = 0x239B120
STRIDE = 0x1C


def main():
    b = open(DLL, "rb").read()
    print("DLL bytes %d" % len(b))
    print("== raw at 0x%X ==" % TABLE)
    for r in range(24):
        row = b[TABLE + r * STRIDE:TABLE + (r + 1) * STRIDE]
        if len(row) < STRIDE:
            break
        vals = struct.unpack("<7I", row)
        print("  [%2d] %s" % (r, " ".join("%08X" % v for v in vals)))
    c = Counter()
    for r in range(4096):
        off = TABLE + r * STRIDE
        if off + 4 > len(b):
            break
        c[struct.unpack_from("<I", b, off)[0]] += 1
    print("type code (+0x00) top15:")
    for v, n in c.most_common(15):
        print("   %d (0x%X) x%d" % (v, v, n))
    print("nearby strings:")
    for s in re.findall(rb"[ -~]{4,80}", b[TABLE - 0x400:TABLE + 0x400])[:30]:
        print("   %s" % s.decode("latin1"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
